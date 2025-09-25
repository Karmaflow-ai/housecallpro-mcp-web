#!/usr/bin/env python3
"""Unified Housecall Pro MCP server exposed over SSE or streamable HTTP."""

from __future__ import annotations

import argparse
import os
from collections import OrderedDict
from pathlib import Path
from typing import OrderedDict as OrderedDictType

from dotenv import load_dotenv

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from housecallpro_auth import PassthroughTokenVerifier, configure_auth
from housecallpro_registry import register_modules

# Ensure environment variables from .env are available when running locally
load_dotenv()

DEFAULT_MODULES: OrderedDictType[str, str] = OrderedDict(
    [
        ("housecallpro_application", "application"),
        ("housecallpro_appointments", "appointments"),
        ("housecallpro_company", "company"),
        ("housecallpro_customers", "customers"),
        ("housecallpro_employees", "employees"),
        ("housecallpro_estimates", "estimates"),
        ("housecallpro_events", "events"),
        ("housecallpro_invoices", "invoices"),
        ("housecallpro_invoices_query", "invoices_query"),
        ("housecallpro_job_invoices", "job_invoices"),
        ("housecallpro_job_types", "job_types"),
        ("housecallpro_jobs", "jobs"),
        ("housecallpro_lead_sources", "lead_sources"),
        ("housecallpro_leads", "leads"),
        ("housecallpro_material_categories", "material_categories"),
        ("housecallpro_materials", "materials"),
        ("housecallpro_price_forms", "price_forms"),
        ("housecallpro_schedule", "schedule"),
        ("housecallpro_tags", "tags"),
        ("housecallpro_webhooks", "webhooks"),
    ]
)

INSTRUCTIONS = (
    "Unified Housecall Pro MCP server exposing customers, jobs, scheduling, invoicing, and more. "
    "Each tool is namespaced (e.g. 'customers.get_customers'). Provide an Authorization header "
    "with the Housecall Pro API key (Bearer) for every request, or configure a fallback key."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the unified Housecall Pro MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("HOUSECALLPRO_HOST", "0.0.0.0"),
        help="Interface to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("HOUSECALLPRO_PORT", "8000")),
        help="Port to bind (default: 8000)",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default=os.getenv("HOUSECALLPRO_TRANSPORT", "streamable-http"),
        help="Transport protocol for MCP (default: streamable-http)",
    )
    parser.add_argument(
        "--mount-path",
        default=os.getenv("HOUSECALLPRO_MOUNT_PATH", "/mcp"),
        help="Mount path for HTTP transports (default: /mcp)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("HOUSECALLPRO_LOG_LEVEL", "INFO"),
        help="Server log level (default: INFO)",
    )
    parser.add_argument(
        "--fallback-api-key",
        default=os.getenv("HOUSECALL_PRO_API_KEY"),
        help="Fallback Housecall Pro API key when Authorization header is absent",
    )
    default_require = os.getenv("HOUSECALLPRO_REQUIRE_API_KEY_HEADER", "1") not in {"0", "false", "False"}
    parser.add_argument(
        "--require-api-key-header",
        dest="require_api_key_header",
        action="store_true",
        default=default_require,
        help="Require Authorization bearer tokens from clients (default: enabled)",
    )
    parser.add_argument(
        "--no-require-api-key-header",
        dest="require_api_key_header",
        action="store_false",
        help="Allow requests without Authorization headers (use fallback API key)",
    )
    parser.add_argument(
        "--auth-issuer-url",
        default=os.getenv("HOUSECALLPRO_AUTH_ISSUER_URL", "https://mcp.local/issuer"),
        help="Issuer URL advertised to clients when requiring Authorization headers",
    )
    parser.add_argument(
        "--auth-resource-url",
        default=os.getenv("HOUSECALLPRO_AUTH_RESOURCE_URL", "http://localhost"),
        help="Resource server URL advertised to clients when requiring Authorization headers",
    )
    parser.add_argument(
        "--required-scope",
        dest="required_scopes",
        action="append",
        help="Scope required to access the MCP server (may be specified multiple times)",
    )
    return parser.parse_args()


def _resolve_required_scopes(args: argparse.Namespace) -> list[str] | None:
    if args.required_scopes:
        return list(dict.fromkeys(scope for scope in args.required_scopes if scope))
    env_scopes = os.getenv("HOUSECALLPRO_REQUIRED_SCOPES")
    if env_scopes:
        scopes = [scope.strip() for scope in env_scopes.split(",") if scope.strip()]
        return list(dict.fromkeys(scopes)) or None
    return None


def _normalize_mount_path(raw_path: str | None) -> str:
    path = (raw_path or "/mcp").strip()
    if not path:
        return "/mcp"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path

def build_server(
    host: str,
    port: int,
    log_level: str,
    *,
    auth_settings: AuthSettings | None,
    token_verifier: PassthroughTokenVerifier | None,
) -> FastMCP:
    server = FastMCP(
        "Housecall Pro",
        instructions=INSTRUCTIONS,
        host=host,
        port=port,
        log_level=log_level,
        warn_on_duplicate_tools=False,
        auth=auth_settings,
        token_verifier=token_verifier,
    )

    total_tools = register_modules(server, DEFAULT_MODULES)
    if total_tools == 0:
        raise RuntimeError("No Housecall Pro MCP tools were registered")

    return server


def main() -> None:
    args = parse_args()

    fallback_api_key = (args.fallback_api_key or "").strip() or None
    placeholder_value = fallback_api_key or "__housecallpro_placeholder__"
    os.environ.setdefault("HOUSECALL_PRO_API_KEY", placeholder_value)

    required_scopes = _resolve_required_scopes(args)
    configure_auth(fallback_api_key=fallback_api_key, required_scopes=required_scopes)

    token_verifier: PassthroughTokenVerifier | None = None
    auth_settings: AuthSettings | None = None

    if args.require_api_key_header:
        token_verifier = PassthroughTokenVerifier(required_scopes)
        auth_settings = AuthSettings(
            issuer_url=args.auth_issuer_url,
            resource_server_url=args.auth_resource_url,
            required_scopes=required_scopes,
        )

    server = build_server(
        args.host,
        args.port,
        args.log_level,
        auth_settings=auth_settings,
        token_verifier=token_verifier,
    )

    mount_path = _normalize_mount_path(args.mount_path)
    server.settings.mount_path = mount_path
    server.settings.streamable_http_path = mount_path

    transport = "streamable-http"
    if args.transport != transport:
        print(f"Overriding transport {args.transport!r} to {transport!r}")

    server.run(transport=transport)

if __name__ == "__main__":
    main()

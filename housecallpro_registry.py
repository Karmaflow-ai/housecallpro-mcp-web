"""Utilities for registering Housecall Pro MCP modules with a unified server."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Mapping

from mcp.server.fastmcp import FastMCP

from housecallpro_auth import build_authorization_headers


class ModuleRegistrationError(RuntimeError):
    """Raised when a module cannot be registered with the unified MCP server."""


def _get_module_mcp(module: ModuleType) -> FastMCP:
    """Return the FastMCP instance defined in a module."""
    mcp = getattr(module, "mcp", None)
    if mcp is None:
        raise ModuleRegistrationError(
            f"Module '{module.__name__}' does not expose an 'mcp' FastMCP instance."
        )
    return mcp


def _prepare_module(module: ModuleType) -> None:
    """Override module helpers to inject per-request authorization headers."""

    def dynamic_get_headers() -> dict[str, str]:
        return dict(build_authorization_headers())

    if hasattr(module, "get_headers"):
        setattr(module, "get_headers", dynamic_get_headers)


def register_namespace_tools(server: FastMCP, module_name: str, namespace: str) -> int:
    """Register all tools from a module under a namespace on the unified server."""
    module = importlib.import_module(module_name)
    _prepare_module(module)
    module_mcp = _get_module_mcp(module)

    registered = 0
    for tool in module_mcp._tool_manager.list_tools():  # type: ignore[attr-defined]
        tool_name = f"{namespace}.{tool.name}"
        title = tool.title or f"{namespace} {tool.name}".replace("_", " ").title()
        description = tool.description or (
            f"Housecall Pro {namespace.replace('_', ' ')} tool '{tool.name}'"
        )

        server.add_tool(
            tool.fn,
            name=tool_name,
            title=title,
            description=description,
            annotations=tool.annotations,
        )
        registered += 1

    return registered


def register_modules(server: FastMCP, modules: Mapping[str, str]) -> int:
    """Register tools from all modules in the mapping.

    Args:
        server: The unified FastMCP server instance.
        modules: Mapping of module import paths to their namespace prefixes.

    Returns:
        Total number of tools registered across all modules.
    """
    total = 0
    for module_name, namespace in modules.items():
        total += register_namespace_tools(server, module_name, namespace)
    return total

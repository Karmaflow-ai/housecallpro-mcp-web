"""Utilities for registering Housecall Pro MCP modules with a unified server."""

from __future__ import annotations

import functools
import importlib
from types import ModuleType
from typing import Mapping

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.func_metadata import FuncMetadata

from housecallpro_auth import build_authorization_headers


def _ensure_raw_argument_support() -> None:
    """Patch FastMCP to unwrap `raw_arguments` payloads before validation."""
    if getattr(FuncMetadata.call_fn_with_arg_validation, "_housecallpro_raw_args_patch", False):
        return

    original_call_fn = FuncMetadata.call_fn_with_arg_validation

    @functools.wraps(original_call_fn)
    def patched_call_fn_with_raw_support(
        self,
        fn,
        fn_is_async,
        arguments_to_validate,
        arguments_to_pass_directly,
    ):
        if isinstance(arguments_to_validate, dict) and "raw_arguments" in arguments_to_validate:
            raw_arguments = arguments_to_validate.get("raw_arguments") or {}
            remaining_arguments = {k: v for k, v in arguments_to_validate.items() if k != "raw_arguments"}
            if isinstance(raw_arguments, dict):
                merged_arguments = dict(raw_arguments)
                merged_arguments.update(remaining_arguments)
                arguments_to_validate = merged_arguments
            else:
                arguments_to_validate = remaining_arguments
        return original_call_fn(self, fn, fn_is_async, arguments_to_validate, arguments_to_pass_directly)

    setattr(patched_call_fn_with_raw_support, "_housecallpro_raw_args_patch", True)
    FuncMetadata.call_fn_with_arg_validation = patched_call_fn_with_raw_support  # type: ignore[method-assign]


_ensure_raw_argument_support()


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

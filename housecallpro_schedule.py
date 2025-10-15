#!/usr/bin/env python3
"""
Housecall Pro Schedule MCP Server

This server provides schedule management functionality for Housecall Pro,
including retrieving and updating schedule windows, and getting booking windows.
"""

import os
from typing import Optional, Dict, Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# FastMCP server
mcp = FastMCP("Housecall Pro Schedule")

# Configuration
API_KEY = os.getenv("HOUSECALL_PRO_API_KEY")
API_BASE_URL = "https://api.housecallpro.com"

if not API_KEY:
    raise ValueError("HOUSECALL_PRO_API_KEY environment variable is required")


def get_headers() -> Dict[str, str]:
    """
    Returns the headers needed for API requests including authentication.
    """
    return {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@mcp.tool()
async def get_schedule_windows() -> Dict[str, Any]:
    """
    Retrieves the organization's configured schedule availability.

    Returns:
        A dictionary containing the schedule availability including daily windows.
    """
    headers = get_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/company/schedule_availability",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def update_schedule_windows(schedule_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates the company's schedule availability configuration.

    Args:
        schedule_settings: Complete schedule availability payload matching the Housecall
                           Pro schema (e.g., daily_availabilities, buffers).

    Returns:
        A dictionary containing the updated schedule availability.
    """
    headers = get_headers()
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_BASE_URL}/company/schedule_availability",
            headers=headers,
            json=schedule_settings,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_booking_windows(
    start_date: Optional[str] = None, show_for_days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Retrieves available booking windows using configured online booking rules.

    Args:
        start_date: Optional date string (YYYY-MM-DD) indicating when to begin the search.
        show_for_days: Optional number of days to include in the response.

    Returns:
        A dictionary containing available booking windows.
    """
    headers = get_headers()
    params: Dict[str, Any] = {}
    if start_date:
        params["start_date"] = start_date
    if show_for_days is not None:
        params["show_for_days"] = str(show_for_days)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/company/schedule_availability/booking_windows",
            headers=headers,
            params=params or None,
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run() 

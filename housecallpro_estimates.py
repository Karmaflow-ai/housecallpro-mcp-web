#!/usr/bin/env python3
"""
Housecall Pro Estimates MCP Server

This server provides estimate management functionality for Housecall Pro,
including CRUD operations for estimates.
"""

import os
from typing import Optional, Dict, Any, List
import json

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# FastMCP server
mcp = FastMCP("Housecall Pro Estimates")

# Configuration
API_KEY = os.getenv("HOUSECALL_PRO_API_KEY")
API_BASE_URL = "https://api.housecallpro.com"

if not API_KEY:
    raise ValueError("HOUSECALL_PRO_API_KEY environment variable is required")


def get_headers() -> Dict[str, str]:
    """Get headers for API requests."""
    return {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def make_api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make an API request to Housecall Pro."""
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    
    # Add headers
    headers = get_headers()
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))
    
    try:
        with httpx.Client() as client:
            response = client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"}, indent=2)


@mcp.tool()
def get_estimates(
    page: Optional[int] = 1,
    page_size: Optional[int] = 50,
    customer_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Retrieve estimates from Housecall Pro.
    
    Args:
        page: Page number for pagination (default: 1)
        page_size: Number of results per page (default: 50, max: 200)
        customer_id: Filter by customer ID
        start_date: Filter estimates created after this date (YYYY-MM-DD format)
        end_date: Filter estimates created before this date (YYYY-MM-DD format)
    
    Returns:
        JSON string containing the estimates data
    """
    params = {
        "page": page,
        "page_size": min(page_size, 200)  # API max is 200
    }
    
    if customer_id:
        params["customer_id"] = customer_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    result = make_api_request("GET", "estimates", params=params)
    return json.dumps(result, indent=2)


_PLACEHOLDER_OPTION = {
    "name": "Estimate",
    "line_items": [
        {
            "name": "On-Site Assessment",
            "description": "Free in-home estimate visit",
            "unit_price": 0,
            "quantity": 1,
        }
    ],
}


@mcp.tool()
def create_estimate(
    customer_id: str,
    options: Optional[List[Dict[str, Any]]] = None,
    assigned_employee_ids: Optional[List[str]] = None,
    address_id: Optional[str] = None,
    lead_source: Optional[str] = None,
    note: Optional[str] = None,
    message: Optional[str] = None
) -> str:
    """
    Create a new estimate in Housecall Pro.

    Line items must be nested inside options (e.g. good/better/best tiers).
    Even a single-tier estimate needs at least one option wrapping its line
    items. If options is omitted or empty, a zero-dollar placeholder option
    is created automatically so the estimate can be filled in later by staff.

    Args:
        customer_id: ID of the customer (required)
        options: List of estimate options. Each option is a dict with:
              - name (str, required): display name (e.g. "Standard Install")
              - line_items (list, required): list of line item dicts with
                name (str), description (str, optional), unit_price (int, cents),
                quantity (number), unit_cost (int, cents, optional),
                taxable (bool, optional)
              - tags (list of str, optional)
              - tax (dict, optional): {taxable, tax_rate, tax_name}
            If omitted or empty, a $0 placeholder option is used.
        assigned_employee_ids: List of employee IDs to assign (optional)
        address_id: ID of an existing service address (optional)
        lead_source: Lead source name (optional)
        note: Internal note for the estimate (optional)
        message: Customer-facing message (optional)

    Returns:
        JSON string containing the created estimate data
    """
    if not options:
        options = [_PLACEHOLDER_OPTION]

    data = {
        "customer_id": customer_id,
        "options": options
    }

    if assigned_employee_ids:
        data["assigned_employee_ids"] = assigned_employee_ids
    if address_id:
        data["address_id"] = address_id
    if lead_source:
        data["lead_source"] = lead_source
    if note:
        data["note"] = note
    if message:
        data["message"] = message

    result = make_api_request("POST", "estimates", json=data)
    return json.dumps(result, indent=2)


@mcp.tool()
def add_estimate_option(
    estimate_id: str,
    name: str,
    line_items: List[Dict[str, Any]],
    tax: Optional[Dict[str, Any]] = None
) -> str:
    """
    Add an option to an existing estimate.

    Args:
        estimate_id: ID of the estimate (required)
        name: Display name for the option (required, e.g. "Option A")
        line_items: List of line item dicts (required). Each has:
            name (str), description (str, optional), unit_price (int, cents),
            quantity (number), unit_cost (int, cents, optional),
            taxable (bool, optional)
        tax: Tax config dict (optional): {taxable, tax_rate, tax_name}

    Returns:
        JSON string containing the created option data
    """
    data = {
        "name": name,
        "line_items": line_items
    }

    if tax:
        data["tax"] = tax

    result = make_api_request("POST", f"estimates/{estimate_id}/options", json=data)
    return json.dumps(result, indent=2)


@mcp.tool()
def add_estimate_option_note(
    estimate_id: str,
    option_id: str,
    content: str
) -> str:
    """
    Add a note to an estimate option.

    Args:
        estimate_id: ID of the estimate (required)
        option_id: ID of the estimate option (required)
        content: Note content (required)

    Returns:
        JSON string containing the created note with id and content
    """
    data = {
        "content": content
    }

    result = make_api_request("POST", f"estimates/{estimate_id}/options/{option_id}/notes", json=data)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
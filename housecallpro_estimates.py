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
    """Make an API request to Housecall Pro.

    Raises RuntimeError on HTTP 4xx/5xx so FastMCP surfaces the call as
    isError=true rather than a successful-looking JSON-string error blob.
    """
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"

    headers = get_headers()
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))

    with httpx.Client() as client:
        response = client.request(method, url, headers=headers, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                error_detail = exc.response.json()
            except Exception:
                error_detail = exc.response.text
            raise RuntimeError(
                f"Housecall Pro API {exc.response.status_code} for {endpoint}: {error_detail}"
            ) from exc
        return response.json() if response.content else {}


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


@mcp.tool()
def create_estimate(
    customer_id: str,
    address_id: str,
    assigned_employee_ids: List[str],
    options: List[Dict[str, Any]],
    lead_source: Optional[str] = None,
    note: Optional[str] = None,
) -> str:
    """
    Create a new estimate in Housecall Pro.

    Matches the HCP POST /estimates contract: estimates are composed of one
    or more options, and each option owns its own line_items. There is no
    root-level line_items field, and employees are assigned via the plural
    assigned_employee_ids array.

    Args:
        customer_id: HCP customer id, e.g. "cus_..." (required)
        address_id: HCP service address id, e.g. "adr_..." (required)
        assigned_employee_ids: Employee ids assigned to the estimate, e.g.
            ["pro_..."] (required; plural array, not singular employee_id)
        options: At least one estimate option (required). Each option is:
            {
              "name": str,
              "line_items": [
                {
                  "name": str,
                  "unit_price": int,   # cents
                  "quantity": float,
                  "kind": "labor" | "materials"
                }
              ],
              "message": Optional[str]
            }
        lead_source: Lead source label; must match a value configured in HCP.
        note: Estimate-level note (singular field name per HCP, not "notes").

    Returns:
        JSON string containing the created estimate data.
    """
    data: Dict[str, Any] = {
        "customer_id": customer_id,
        "address_id": address_id,
        "assigned_employee_ids": assigned_employee_ids,
        "options": options,
    }

    if lead_source:
        data["lead_source"] = lead_source
    if note:
        data["note"] = note

    result = make_api_request("POST", "estimates", json=data)
    return json.dumps(result, indent=2)


@mcp.tool()
def add_estimate_option_note(
    estimate_id: str,
    option_id: str,
    content: str
) -> str:
    """
    Create a new estimate option note.
    
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
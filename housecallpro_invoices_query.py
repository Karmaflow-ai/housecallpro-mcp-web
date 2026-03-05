#!/usr/bin/env python3
"""
Housecall Pro Invoices Query MCP Server

This server provides advanced invoice querying functionality for Housecall Pro,
allowing for filtering and sorting of invoices.
"""

import os
from typing import Optional, Dict, Any, List

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# FastMCP server
mcp = FastMCP("Housecall Pro Invoices Query")

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
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_headers()
    
    with httpx.Client() as client:
        response = client.request(method, url, headers=headers, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_detail = None
            try:
                error_detail = exc.response.json()
            except Exception:
                error_detail = exc.response.text
            raise RuntimeError(
                f"Housecall Pro API {exc.response.status_code} for {endpoint}: {error_detail}"
            ) from exc
        return response.json()


@mcp.tool()
async def get_invoices(
    customer_uuid: Optional[str] = None,
    status: Optional[str] = None,
    due_at_min: Optional[str] = None,
    due_at_max: Optional[str] = None,
    amount_due_min: Optional[int] = None,
    amount_due_max: Optional[int] = None,
    created_at_min: Optional[str] = None,
    created_at_max: Optional[str] = None,
    paid_at_min: Optional[str] = None,
    paid_at_max: Optional[str] = None,
    payment_method: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_direction: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves a list of invoices with extensive filtering and sorting options.

    Args:
        customer_uuid: Filter by customer UUID.
        status: Filter by status (open, pending_payment, paid, voided, uncollectible, canceled).
        due_at_min: Minimum due date filter (ISO 8601, e.g. 2025-09-05T00:00:00Z).
        due_at_max: Maximum due date filter (ISO 8601, e.g. 2026-01-04T00:00:00Z).
        amount_due_min: Minimum amount due in cents (e.g. 1 = $0.01).
        amount_due_max: Maximum amount due in cents.
        created_at_min: Return invoices created after this date (ISO 8601).
        created_at_max: Return invoices created before this date (ISO 8601).
        paid_at_min: Return invoices paid after this date (ISO 8601).
        paid_at_max: Return invoices paid before this date (ISO 8601).
        payment_method: Filter by payment method.
        page: The page number to retrieve.
        page_size: The number of invoices per page.
        sort_by: Field to sort by (amount, created_at, due_amount, due_at, invoice_number, paid_at, sent_at, status, updated_at).
        sort_direction: Sort direction (asc, desc).

    Returns:
        A dictionary containing a list of invoices and pagination info.
    """
    params = {
        k: v
        for k, v in {
            "customer_uuid": customer_uuid,
            "status": status,
            "due_at_min": due_at_min,
            "due_at_max": due_at_max,
            "amount_due_min": amount_due_min,
            "amount_due_max": amount_due_max,
            "created_at_min": created_at_min,
            "created_at_max": created_at_max,
            "paid_at_min": paid_at_min,
            "paid_at_max": paid_at_max,
            "payment_method": payment_method,
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_direction": sort_direction,
        }.items()
        if v is not None
    }

    return make_api_request("GET", "/invoices", params=params)


if __name__ == "__main__":
    mcp.run()
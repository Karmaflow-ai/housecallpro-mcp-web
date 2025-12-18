#!/usr/bin/env python3
"""
Housecall Pro Leads MCP Server

This server provides lead management functionality for Housecall Pro,
including CRUD operations for leads and related entities.
"""

import json
import os
from typing import Optional, Dict, Any, List

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# FastMCP server
mcp = FastMCP("Housecall Pro Leads")

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


def _extract_id(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        candidate = payload.get("id")
        if candidate:
            return str(candidate)
        for key in ("customer", "lead", "data"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                nested_id = nested.get("id")
                if nested_id:
                    return str(nested_id)
    return None


def _split_customer_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in (full_name or "").strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


async def make_api_request(
    method: str,
    endpoint: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Any] = None,
    data: Optional[Any] = None,
    files: Optional[Any] = None,
    timeout: float = 30.0,
) -> Any:
    """Make an API request to Housecall Pro."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_headers()

    request_kwargs: Dict[str, Any] = {
        "headers": headers,
        "timeout": timeout,
    }
    if params:
        request_kwargs["params"] = params
    if json_data is not None:
        request_kwargs["json"] = json_data
    if data is not None:
        request_kwargs["data"] = data
    if files is not None:
        request_kwargs["files"] = files

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **request_kwargs)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail: Any = None
        if exc.response is not None:
            try:
                error_detail = exc.response.json()
            except ValueError:
                error_detail = exc.response.text
        raise RuntimeError(
            f"Housecall Pro API {exc.response.status_code if exc.response else 'error'} "
            f"for {endpoint}: {error_detail}"
        ) from exc

    if not response.content:
        return {}

    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return response.json()

    return {"raw_response": response.text}


@mcp.tool()
async def get_leads(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_direction: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    employee_id: Optional[str] = None,
    job_type_id: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None
) -> str:
    """
    Retrieve leads with optional filtering and pagination.
    
    Args:
        page: Page number for pagination (default: 1)
        page_size: Number of leads per page (default: 25, max: 100)
        sort_by: Field to sort by (created_at, updated_at, status, source)
        sort_direction: Sort direction (asc, desc)
        status: Filter by lead status (new, contacted, qualified, unqualified, converted)
        source: Filter by lead source
        employee_id: Filter by assigned employee ID
        job_type_id: Filter by job type ID
        created_after: Filter leads created after this date (ISO 8601)
        created_before: Filter leads created before this date (ISO 8601)
        updated_after: Filter leads updated after this date (ISO 8601)
        updated_before: Filter leads updated before this date (ISO 8601)
        customer_name: Filter by customer name (partial match)
        customer_email: Filter by customer email
        customer_phone: Filter by customer phone number
    
    Returns:
        JSON string containing leads data or error message
    """
    try:
        params = {}
        
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = min(page_size, 100)  # API limit
        if sort_by:
            params["sort_by"] = sort_by
        if sort_direction:
            params["sort_direction"] = sort_direction
        if status:
            params["status"] = status
        if source:
            params["source"] = source
        if employee_id:
            params["employee_id"] = employee_id
        if job_type_id:
            params["job_type_id"] = job_type_id
        if created_after:
            params["created_after"] = created_after
        if created_before:
            params["created_before"] = created_before
        if updated_after:
            params["updated_after"] = updated_after
        if updated_before:
            params["updated_before"] = updated_before
        if customer_name:
            params["customer_name"] = customer_name
        if customer_email:
            params["customer_email"] = customer_email
        if customer_phone:
            params["customer_phone"] = customer_phone
        
        result = await make_api_request("GET", "/leads", params=params)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def get_lead(lead_id: str) -> str:
    """
    Retrieve a specific lead by ID.
    
    Args:
        lead_id: The unique identifier of the lead
    
    Returns:
        JSON string containing lead data or error message
    """
    try:
        if not lead_id:
            return json.dumps({"error": "lead_id is required"}, indent=2)
        
        result = await make_api_request("GET", f"/leads/{lead_id}")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def create_lead(
    customer_id: Optional[str] = None,
    customer: Optional[Dict[str, Any]] = None,
    assigned_employee_id: Optional[str] = None,
    address_id: Optional[str] = None,
    address: Optional[Dict[str, Any]] = None,
    lead_source: Optional[str] = None,
    line_items: Optional[List[Dict[str, Any]]] = None,
    note: Optional[str] = None,
    tags: Optional[List[str]] = None,
    tax_name: Optional[str] = None,
    tax_rate: Optional[float] = None,
) -> str:
    """
    Create a new lead.
    
    Args:
        customer_id: ID of an existing customer (either this or customer is required)
        customer: Customer object (either this or customer_id is required)
        assigned_employee_id: Employee ID to assign the lead to
        address_id: Existing address ID for the lead
        address: Address object for the lead
        lead_source: Lead source
        line_items: Array of line item objects
        note: Lead note
        tags: Lead tags
        tax_name: Tax name
        tax_rate: Tax rate
    
    Returns:
        JSON string containing created lead data or error message
    """
    try:
        resolved_customer_id = (customer_id or "").strip() or None
        if not resolved_customer_id and not customer:
            return json.dumps({"error": "customer_id or customer is required"}, indent=2)

        lead_data: Dict[str, Any] = {}
        if resolved_customer_id:
            lead_data["customer_id"] = resolved_customer_id
        if customer:
            lead_data["customer"] = customer

        if lead_source:
            lead_data["lead_source"] = lead_source
        if assigned_employee_id:
            lead_data["assigned_employee_id"] = assigned_employee_id
        if address_id:
            lead_data["address_id"] = address_id
        if address:
            lead_data["address"] = address
        if line_items is not None:
            lead_data["line_items"] = line_items
        if note is not None:
            lead_data["note"] = note
        if tags is not None:
            lead_data["tags"] = tags
        if tax_name:
            lead_data["tax_name"] = tax_name
        if tax_rate is not None:
            lead_data["tax_rate"] = tax_rate

        result = await make_api_request("POST", "/leads", json_data=lead_data)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def update_lead(
    lead_id: str,
    status: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
    customer_email: Optional[str] = None,
    address_street: Optional[str] = None,
    address_city: Optional[str] = None,
    address_state: Optional[str] = None,
    address_zip: Optional[str] = None,
    job_type_id: Optional[str] = None,
    source: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    employee_id: Optional[str] = None,
    priority: Optional[str] = None,
    estimated_value: Optional[float] = None,
    custom_fields: Optional[Dict[str, Any]] = None
) -> str:
    """
    Update an existing lead.
    
    Args:
        lead_id: The unique identifier of the lead to update (required)
        status: Lead status (new, contacted, qualified, unqualified, converted)
        customer_name: Name of the customer
        customer_phone: Customer phone number
        customer_email: Customer email address
        address_street: Street address
        address_city: City
        address_state: State
        address_zip: ZIP code
        job_type_id: ID of the job type for this lead
        source: Lead source (website, referral, phone, etc.)
        description: Description of the lead/work needed
        notes: Additional notes about the lead
        employee_id: ID of employee to assign the lead to
        priority: Lead priority (low, medium, high)
        estimated_value: Estimated value of the lead in dollars
        custom_fields: Additional custom fields as key-value pairs
    
    Returns:
        JSON string containing updated lead data or error message
    """
    try:
        if not lead_id:
            return json.dumps({"error": "lead_id is required"}, indent=2)
        
        update_data = {}
        
        # Add status update
        if status:
            update_data["status"] = status
        
        # Add customer updates
        if any([customer_name, customer_phone, customer_email]):
            update_data["customer"] = {}
            if customer_name:
                update_data["customer"]["name"] = customer_name
            if customer_phone:
                update_data["customer"]["phone"] = customer_phone
            if customer_email:
                update_data["customer"]["email"] = customer_email
        
        # Add address updates
        if any([address_street, address_city, address_state, address_zip]):
            update_data["address"] = {}
            if address_street:
                update_data["address"]["street"] = address_street
            if address_city:
                update_data["address"]["city"] = address_city
            if address_state:
                update_data["address"]["state"] = address_state
            if address_zip:
                update_data["address"]["zip"] = address_zip
        
        # Add lead detail updates
        if job_type_id:
            update_data["job_type_id"] = job_type_id
        if source:
            update_data["source"] = source
        if description:
            update_data["description"] = description
        if notes:
            update_data["notes"] = notes
        if employee_id:
            update_data["employee_id"] = employee_id
        if priority:
            update_data["priority"] = priority
        if estimated_value is not None:
            update_data["estimated_value"] = estimated_value
        if custom_fields:
            update_data["custom_fields"] = custom_fields
        
        if not update_data:
            return json.dumps({"error": "At least one field must be provided for update"}, indent=2)
        
        result = await make_api_request("PATCH", f"/leads/{lead_id}", json_data=update_data)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def convert_lead_to_job(
    lead_id: str,
    job_type_id: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    scheduled_start: Optional[str] = None,
    scheduled_end: Optional[str] = None,
    employee_ids: Optional[list] = None
) -> str:
    """
    Convert a lead to a job.
    
    Args:
        lead_id: The unique identifier of the lead to convert (required)
        job_type_id: ID of the job type for the new job
        description: Description for the new job
        priority: Job priority (low, medium, high)
        scheduled_start: Scheduled start time (ISO 8601)
        scheduled_end: Scheduled end time (ISO 8601)
        employee_ids: List of employee IDs to assign to the job
    
    Returns:
        JSON string containing created job data or error message
    """
    try:
        if not lead_id:
            return json.dumps({"error": "lead_id is required"}, indent=2)
        
        conversion_data = {}
        
        if job_type_id:
            conversion_data["job_type_id"] = job_type_id
        if description:
            conversion_data["description"] = description
        if priority:
            conversion_data["priority"] = priority
        if scheduled_start:
            conversion_data["scheduled_start"] = scheduled_start
        if scheduled_end:
            conversion_data["scheduled_end"] = scheduled_end
        if employee_ids:
            conversion_data["employee_ids"] = employee_ids
        
        result = await make_api_request("POST", f"/leads/{lead_id}/convert", json_data=conversion_data)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    mcp.run()
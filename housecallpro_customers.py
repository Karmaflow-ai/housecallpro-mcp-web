#!/usr/bin/env python3
"""
Housecall Pro Customers MCP Server

This server provides customer management functionality for Housecall Pro,
including CRUD operations for customers and their addresses.
"""

import os
from typing import Optional, Dict, Any, List

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# FastMCP server
mcp = FastMCP("Housecall Pro Customers")

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


async def make_api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make an API request to Housecall Pro."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_headers()
    
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()


def _normalize_str(value: Optional[str]) -> str:
    """Return a case-folded trimmed string for comparison."""
    if not isinstance(value, str):
        return ""
    return value.strip().casefold()


def _normalize_phone(value: Optional[str]) -> str:
    """Strip non-numeric characters from a phone number for comparison."""
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())




def _collect_customer_phone_numbers(customer: Dict[str, Any]) -> List[str]:
    """Gather the known phone number fields from a customer payload."""
    numbers: List[str] = []
    for key in ("phone", "mobile_number", "home_number", "work_number", "contact_phone"):
        value = customer.get(key)
        if isinstance(value, str):
            numbers.append(value)
    phone_numbers = customer.get("phone_numbers")
    if isinstance(phone_numbers, dict):
        iterable = phone_numbers.values()
    elif isinstance(phone_numbers, list):
        iterable = phone_numbers
    else:
        iterable = []

    for phone_entry in iterable:
        if isinstance(phone_entry, str):
            numbers.append(phone_entry)
        elif isinstance(phone_entry, dict):
            number = phone_entry.get("number") or phone_entry.get("value")
            if isinstance(number, str):
                numbers.append(number)
    return numbers


def _extract_customers(payload: Any) -> List[Dict[str, Any]]:
    """
    Extract a list of customer dictionaries from an API payload.

    Supports API responses that return either a list of customers or a wrapper
    object containing a customers/data/results/items collection.
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("customers", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        single_customer = payload.get("customer")
        if isinstance(single_customer, dict):
            return [single_customer]
        candidate_keys = {"id", "first_name", "last_name"}
        if any(key in payload for key in candidate_keys):
            return [payload]
    return []


# CUSTOMER ENDPOINTS

@mcp.tool()
async def get_customers(
    page: Optional[int] = 1,
    per_page: Optional[int] = 50,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company_name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    tags: Optional[str] = None,
    created_start: Optional[str] = None,
    created_end: Optional[str] = None,
    updated_start: Optional[str] = None,
    updated_end: Optional[str] = None
) -> dict:
    """
    Retrieve the best matching customer profile for the provided query details.

    The tool searches Housecall Pro for customers matching the supplied filters,
    returns the single most relevant profile, or reports that no confident match
    could be found.

    Args:
        page: Page number to fetch when querying the API (default: 1)
        per_page: Number of customers fetched per page (default: 50, max supported by API: 200)
        email: Exact email address to match
        phone: Phone number (any format) to match
        company_name: Company name to match
        first_name: Customer first name
        last_name: Customer last name
        tags: Filter by customer tags (comma-separated)
        created_start: Filter by creation date start (ISO 8601 format)
        created_end: Filter by creation date end (ISO 8601 format)
        updated_start: Filter by update date start (ISO 8601 format)
        updated_end: Filter by update date end (ISO 8601 format)
    """
    params = {
        "page": page,
        "per_page": per_page,
        "email": email,
        "phone": phone,
        "company_name": company_name,
        "first_name": first_name,
        "last_name": last_name,
        "tags": tags,
        "created_start": created_start,
        "created_end": created_end,
        "updated_start": updated_start,
        "updated_end": updated_end,
    }

    clean_params = {k: v for k, v in params.items() if v is not None}
    if "per_page" in clean_params:
        try:
            clean_params["per_page"] = max(1, min(int(clean_params["per_page"]), 200))
        except (ValueError, TypeError):
            clean_params.pop("per_page", None)
    if "page" in clean_params:
        try:
            clean_params["page"] = max(1, int(clean_params["page"]))
        except (ValueError, TypeError):
            clean_params.pop("page", None)

    if phone:
        clean_params.setdefault("q", str(phone).strip())

    api_response = await make_api_request("GET", "/customers", params=clean_params)
    customers = _extract_customers(api_response)
    if not customers:
        return {
            "error": "Customer not found",
            "details": {"reason": "No customers returned for supplied criteria"},
        }

    email_norm = _normalize_str(email)
    phone_norm = _normalize_phone(phone)
    first_norm = _normalize_str(first_name)
    last_norm = _normalize_str(last_name)
    company_norm = _normalize_str(company_name)

    email_norm = _normalize_str(email)
    phone_norm = _normalize_phone(phone)
    first_norm = _normalize_str(first_name)
    last_norm = _normalize_str(last_name)
    company_norm = _normalize_str(company_name)

    scored_customers: List[Dict[str, Any]] = []
    for customer in customers:
        reasons: List[str] = []
        score = 0

        customer_email = _normalize_str(customer.get("email"))
        if email_norm:
            if customer_email == email_norm:
                score += 100
                reasons.append("Exact email match")
            elif email_norm in customer_email and customer_email:
                score += 30
                reasons.append("Partial email match")

        if phone_norm:
            for candidate_phone in _collect_customer_phone_numbers(customer):
                if _normalize_phone(candidate_phone) == phone_norm:
                    score += 80
                    reasons.append("Phone number match")
                    break

        if first_norm and _normalize_str(customer.get("first_name")) == first_norm:
            score += 20
            reasons.append("First name match")
        if last_norm and _normalize_str(customer.get("last_name")) == last_norm:
            score += 20
            reasons.append("Last name match")
        if company_norm and company_norm in _normalize_str(customer.get("company_name")):
            score += 10
            reasons.append("Company name match")

        if score > 0:
            scored_customers.append(
                {
                    "customer": customer,
                    "score": score,
                    "match_reasons": sorted(set(reasons)),
                }
            )

    if not scored_customers:
        return {
            "error": "Customer not found",
            "details": {"reason": "No confident match", "customers_reviewed": len(customers)},
        }

    scored_customers.sort(key=lambda item: item["score"], reverse=True)
    best = scored_customers[0]
    if len(scored_customers) > 1 and scored_customers[1]["score"] == best["score"]:
        return {
            "error": "Customer match ambiguous",
            "details": {
                "reason": "Multiple customers share the top match score",
                "top_score": best["score"],
                "candidates_considered": len(scored_customers),
            },
        }

    return {
        "customer": best["customer"],
        "match_score": best["score"],
        "match_reasons": best["match_reasons"],
    }


@mcp.tool()
async def get_customer(customer_id: str) -> dict:
    """
    Get a specific customer by ID.
    
    Args:
        customer_id: The unique identifier for the customer
    """
    try:
        return await make_api_request("GET", f"/customers/{customer_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"Customer {customer_id} not found"}
        raise


@mcp.tool()
async def create_customer(
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    mobile_number: Optional[str] = None,
    home_number: Optional[str] = None,
    work_number: Optional[str] = None,
    company_name: Optional[str] = None,
    is_commercial: Optional[bool] = False,
    notifications_enabled: Optional[bool] = True,
    lead_source: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Create a new customer.
    
    Args:
        first_name: Customer's first name (required)
        last_name: Customer's last name (required)
        email: Customer's email address
        mobile_number: Customer's mobile phone number
        home_number: Customer's home phone number
        work_number: Customer's work phone number
        company_name: Company name for commercial customers
        is_commercial: Whether this is a commercial customer (default: False)
        notifications_enabled: Whether notifications are enabled (default: True)
        lead_source: How the customer was acquired
        tags: List of tags to assign to the customer
        notes: Notes about the customer
    """
    customer_data = {
        "first_name": first_name,
        "last_name": last_name
    }
    
    # Add optional fields if provided
    if email:
        customer_data["email"] = email
    if mobile_number:
        customer_data["mobile_number"] = mobile_number
    if home_number:
        customer_data["home_number"] = home_number
    if work_number:
        customer_data["work_number"] = work_number
    if company_name:
        customer_data["company_name"] = company_name
    if is_commercial is not None:
        customer_data["is_commercial"] = is_commercial
    if notifications_enabled is not None:
        customer_data["notifications_enabled"] = notifications_enabled
    if lead_source:
        customer_data["lead_source"] = lead_source
    if tags:
        customer_data["tags"] = tags
    if notes:
        customer_data["notes"] = notes
    
    return await make_api_request("POST", "/customers", json=customer_data)


@mcp.tool()
async def update_customer(
    customer_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    mobile_number: Optional[str] = None,
    home_number: Optional[str] = None,
    work_number: Optional[str] = None,
    company_name: Optional[str] = None,
    is_commercial: Optional[bool] = None,
    notifications_enabled: Optional[bool] = None,
    lead_source: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Update an existing customer.
    
    Args:
        customer_id: The unique identifier for the customer (required)
        first_name: Customer's first name
        last_name: Customer's last name
        email: Customer's email address
        mobile_number: Customer's mobile phone number
        home_number: Customer's home phone number
        work_number: Customer's work phone number
        company_name: Company name for commercial customers
        is_commercial: Whether this is a commercial customer
        notifications_enabled: Whether notifications are enabled
        lead_source: How the customer was acquired
        tags: List of tags to assign to the customer
        notes: Notes about the customer
    """
    customer_data = {}
    
    # Add fields that are provided (not None)
    if first_name is not None:
        customer_data["first_name"] = first_name
    if last_name is not None:
        customer_data["last_name"] = last_name
    if email is not None:
        customer_data["email"] = email
    if mobile_number is not None:
        customer_data["mobile_number"] = mobile_number
    if home_number is not None:
        customer_data["home_number"] = home_number
    if work_number is not None:
        customer_data["work_number"] = work_number
    if company_name is not None:
        customer_data["company_name"] = company_name
    if is_commercial is not None:
        customer_data["is_commercial"] = is_commercial
    if notifications_enabled is not None:
        customer_data["notifications_enabled"] = notifications_enabled
    if lead_source is not None:
        customer_data["lead_source"] = lead_source
    if tags is not None:
        customer_data["tags"] = tags
    if notes is not None:
        customer_data["notes"] = notes
    
    return await make_api_request("PUT", f"/customers/{customer_id}", json=customer_data)


@mcp.tool()
async def get_customer_addresses(customer_id: str) -> dict:
    """
    Get all addresses for a specific customer.
    
    Args:
        customer_id: The unique identifier for the customer
    """
    return await make_api_request("GET", f"/customers/{customer_id}/addresses")


@mcp.tool()
async def get_customer_address(customer_id: str, address_id: str) -> dict:
    """
    Get a specific address for a customer.
    
    Args:
        customer_id: The unique identifier for the customer
        address_id: The unique identifier for the address
    """
    try:
        return await make_api_request("GET", f"/customers/{customer_id}/addresses/{address_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"Address {address_id} not found for customer {customer_id}"}
        raise


@mcp.tool()
async def create_customer_address(
    customer_id: str,
    street: str,
    city: str,
    state: str,
    zip: str,
    country: Optional[str] = "US",
    type: Optional[str] = "service",
    notes: Optional[str] = None,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    is_primary: Optional[bool] = False
) -> dict:
    """
    Create a new address for a customer.
    
    Args:
        customer_id: The unique identifier for the customer (required)
        street: Street address (required)
        city: City (required)
        state: State (required)
        zip: ZIP code (required)
        country: Country code (default: "US")
        type: Address type (e.g., "service", "billing") (default: "service")
        notes: Notes about the address
        contact_name: Contact person at this address
        contact_phone: Contact phone for this address
        is_primary: Whether this is the primary address (default: False)
    """
    address_data = {
        "street": street,
        "city": city,
        "state": state,
        "zip": zip,
        "country": country,
        "type": type,
        "is_primary": is_primary
    }
    
    # Add optional fields if provided
    if notes:
        address_data["notes"] = notes
    if contact_name:
        address_data["contact_name"] = contact_name
    if contact_phone:
        address_data["contact_phone"] = contact_phone
    
    return await make_api_request("POST", f"/customers/{customer_id}/addresses", json=address_data)


# Run the server
if __name__ == "__main__":
    mcp.run() 

# Housecall Pro MCP Servers

Unified Model Context Protocol (MCP) access to the complete Housecall Pro API. This
repository ships with a **single FastMCP server** that exposes every domain tool
(customers, jobs, scheduling, invoicing, and more) to desktop or remote AI clients.

## Highlights
- 20+ Housecall Pro API domains registered on one server with consistent namespaces
- Web-ready deployment via SSE or streamable HTTP transports with configurable host/port
- Supports Claude Desktop, Claude API with MCP, and any compliant MCP client
- Per-request API key support: send a Bearer token (Authorization header) from your app

## Requirements
- Python 3.10+
- Pip / uv / Poetry (any modern Python package manager)
- Housecall Pro API key for each agent or tenant using the server

Install dependencies:

```bash
pip install -r requirements.txt
# or
uv sync
```

## Providing Housecall Pro API Keys
The MCP server expects the Housecall Pro API key to arrive with each request:

1. Configure your MCP client (or agent management UI) to send the API key as an
   `Authorization: Bearer <HOUSECALL_PRO_API_KEY>` header.
2. Optional: supply a fallback key for local testing by setting
   `HOUSECALL_PRO_API_KEY` (env var) or passing `--fallback-api-key` when starting
   the server.
3. When fallback is omitted and `--require-api-key-header` remains enabled
   (default), requests without the Authorization header receive an authentication
   error.

### Example configuration
If your app lets you add custom headers, simply paste the Housecall Pro API key
into the "API Key" field when selecting the **API Key (Bearer)** auth type. Any
extra headers (e.g., `{"X-Org": "Acme"}`) are forwarded untouched.

## Unified Server
Run the server locally (stdio transport) for development with an env fallback:

```bash
python housecallpro_server.py --transport stdio --fallback-api-key $Env:HOUSECALL_PRO_API_KEY --no-require-api-key-header
```

Expose the server on the network using SSE (default host/port shown), requiring
clients to send the API key header:

```bash
python housecallpro_server.py \
  --host 0.0.0.0 \
  --port 8000 \
  --transport sse \
  --auth-issuer-url https://mcp.example.com/issuer \
  --auth-resource-url https://mcp.example.com
```

Environment variable overrides:

| Variable | Default | Description |
| --- | --- | --- |
| `HOUSECALL_PRO_API_KEY` | _unset_ | Optional fallback API key when Authorization header is missing |
| `HOUSECALLPRO_REQUIRE_API_KEY_HEADER` | `1` | Set to `0` to allow missing Authorization headers |
| `HOUSECALLPRO_AUTH_ISSUER_URL` | `https://mcp.local/issuer` | Issuer URL advertised to clients |
| `HOUSECALLPRO_AUTH_RESOURCE_URL` | `http://localhost` | Resource server URL advertised to clients |
| `HOUSECALLPRO_REQUIRED_SCOPES` | _unset_ | Comma-separated scopes to embed in auth responses |
| `HOUSECALLPRO_HOST` | `0.0.0.0` | Bind address for SSE/HTTP transports |
| `HOUSECALLPRO_PORT` | `8000` | Listening port |
| `HOUSECALLPRO_TRANSPORT` | `sse` | Default transport (`stdio`, `sse`, `streamable-http`) |
| `HOUSECALLPRO_MOUNT_PATH` | `/mcp` | Base path when using SSE |
| `HOUSECALLPRO_LOG_LEVEL` | `INFO` | FastMCP log level |

Tools are namespaced by domain (`<namespace>.<tool>`). Examples:

| Namespace | Example Tools |
| --- | --- |
| `customers` | `customers.get_customers`, `customers.create_customer` |
| `jobs` | `jobs.get_jobs`, `jobs.create_job`, `jobs.add_job_note` |
| `invoices` | `invoices.get_invoice`, `invoices.create_invoice_payment` |
| `schedule` | `schedule.get_schedule`, `schedule.update_schedule_settings` |
| `webhooks` | `webhooks.list_webhooks`, `webhooks.create_webhook` |

The full server currently registers 96 tools across 20 modules.

## Client Configuration

### Claude Desktop (stdio)
Update `claude_desktop_config.json` with the template in
`claude_desktop.json.template`, then restart Claude Desktop. For stdio, provide
an env fallback API key or run the server with `--no-require-api-key-header`.

### Remote MCP Clients (SSE / streamable HTTP)
1. Deploy the server on your infrastructure (VM, container, etc.).
2. Configure TLS and networking (reverse proxy, firewall rules, etc.).
3. Point your MCP client at the SSE endpoint, typically
   `https://your-domain.example/mcp/sse` with message endpoint
   `https://your-domain.example/mcp/messages/` (matching `--mount-path`).
4. Supply the Housecall Pro API key via `Authorization: Bearer <token>`.
5. Rotate the keys regularly and store them in your platform's secret manager.

## Deployment Checklist
1. Provision secrets (Housecall Pro API keys, optional fallback).
2. Run `housecallpro_server.py` with the desired transport and auth metadata.
3. Terminate TLS at your reverse proxy and forward to the server's port.
4. Verify connectivity with the `mcp` CLI or your MCP-capable agent.
5. Monitor logs for rate limits and errors from the Housecall Pro API.

## Development Notes
- Domain modules keep their dedicated FastMCP instances for backwards
  compatibility. The unified server (`housecallpro_server.py`) imports these
  modules and re-registers their tools with namespaced identifiers.
- Add new API coverage by creating a `housecallpro_<domain>.py` file with tools,
  then append it to `DEFAULT_MODULES` in `housecallpro_server.py`.
- Run `python -m unittest` or your preferred testing strategy before deploying
  changes.

## License
It Aint, Use It As You Will

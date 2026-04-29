# coupa-mcp

MCP server for the [Coupa](https://www.coupa.com/) Procurement REST API. Exposes purchase orders, invoices, suppliers, requisitions, and approvals as Claude tools.

## Tools

| Tool | Description |
|---|---|
| `coupa_list_purchase_orders` | List POs with optional status/supplier filters |
| `coupa_get_purchase_order` | Get a single PO by ID |
| `coupa_search_purchase_orders` | Search POs with arbitrary query params |
| `coupa_list_invoices` | List invoices with optional filters |
| `coupa_get_invoice` | Get a single invoice by ID |
| `coupa_search_invoices` | Search invoices with arbitrary query params |
| `coupa_list_suppliers` | List suppliers with optional status filter |
| `coupa_get_supplier` | Get a single supplier by ID |
| `coupa_search_suppliers` | Search suppliers with arbitrary query params |
| `coupa_list_requisitions` | List requisitions with optional filters |
| `coupa_get_requisition` | Get a single requisition by ID |
| `coupa_search_requisitions` | Search requisitions with arbitrary query params |
| `coupa_create_requisition` | Create a new requisition with line items |
| `coupa_submit_requisition` | Submit a draft requisition for approval |
| `coupa_approve_object` | Approve a PO, invoice, or requisition |
| `coupa_reject_object` | Reject a PO, invoice, or requisition |

## Requirements

- Python 3.12+
- A Coupa instance with API key access

## Installation

```bash
git clone https://github.com/slach80/coupa.git
cd coupa
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
COUPA_API_URL=https://myinstance.coupahost.com/api
COUPA_API_KEY=your-api-key-here
```

Alternatively, pass the variables via your Claude Desktop config (see below) — no `.env` file needed in production.

## Running

### Development (MCP Inspector)

```bash
mcp dev src/coupa_mcp/server.py
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "coupa": {
      "command": "coupa-mcp",
      "env": {
        "COUPA_API_URL": "https://myinstance.coupahost.com/api",
        "COUPA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Project Structure

```
src/coupa_mcp/
├── server.py        # FastMCP entry point and tool registration
├── config.py        # Environment variable loading
├── client.py        # httpx async HTTP client with auth
└── tools/
    ├── purchase_orders.py
    ├── invoices.py
    ├── suppliers.py
    ├── requisitions.py
    └── approvals.py
```

## Auth

All requests use the `X-COUPA-API-KEY` header. The key is read from `COUPA_API_KEY` at startup.

## Coupa API Notes

- Pagination: `offset` and `limit` query params (max 50 per page)
- Filters: bracket notation — e.g. `fields[purchase_order][status]=issued`
- Approval actions: `PUT /{resource}/{id}/approve` and `PUT /{resource}/{id}/reject`
- Requisition submission: `PUT /requisitions/{id}/submit`

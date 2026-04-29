from mcp.server.fastmcp import FastMCP

from ..client import CoupaClient


def register(mcp: FastMCP, client: CoupaClient) -> None:

    @mcp.tool(
        name="coupa_list_invoices",
        description=(
            "List invoices from Coupa. Supports pagination and optional "
            "filtering by status or supplier."
        ),
    )
    async def list_invoices(
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        supplier_id: int | None = None,
    ) -> dict:
        params: dict = {"offset": offset, "limit": limit}
        if status:
            params["fields[invoice_header][status]"] = status
        if supplier_id:
            params["fields[invoice_header][supplier_id]"] = supplier_id
        return await client.get("/invoices", params=params)

    @mcp.tool(
        name="coupa_get_invoice",
        description="Retrieve a single invoice by its Coupa ID.",
    )
    async def get_invoice(id: int) -> dict:
        return await client.get(f"/invoices/{id}")

    @mcp.tool(
        name="coupa_search_invoices",
        description=(
            "Search invoices using arbitrary Coupa query parameters. "
            "Pass a dict of field:value pairs as 'query'. "
            "Example: {\"status\": \"pending_payment\", \"supplier[name]\": \"Acme Corp\"}"
        ),
    )
    async def search_invoices(
        query: dict,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        params = {**query, "offset": offset, "limit": limit}
        return await client.get("/invoices", params=params)

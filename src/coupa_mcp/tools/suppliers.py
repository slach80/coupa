from mcp.server.fastmcp import FastMCP

from ..client import CoupaClient


def register(mcp: FastMCP, client: CoupaClient) -> None:

    @mcp.tool(
        name="coupa_list_suppliers",
        description=(
            "List suppliers from Coupa. Supports pagination and optional "
            "filtering by status."
        ),
    )
    async def list_suppliers(
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> dict:
        params: dict = {"offset": offset, "limit": limit}
        if status:
            params["fields[supplier][status]"] = status
        return await client.get("/suppliers", params=params)

    @mcp.tool(
        name="coupa_get_supplier",
        description="Retrieve a single supplier by its Coupa ID.",
    )
    async def get_supplier(id: int) -> dict:
        return await client.get(f"/suppliers/{id}")

    @mcp.tool(
        name="coupa_search_suppliers",
        description=(
            "Search suppliers using arbitrary Coupa query parameters. "
            "Pass a dict of field:value pairs as 'query'. "
            "Example: {\"name\": \"Acme\", \"status\": \"active\"}"
        ),
    )
    async def search_suppliers(
        query: dict,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        params = {**query, "offset": offset, "limit": limit}
        return await client.get("/suppliers", params=params)

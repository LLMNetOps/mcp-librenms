"""Quick streamable-HTTP test: initialize, list tools, call ping."""
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client("http://127.0.0.1:5757/mcp") as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            print("server:", init.server_info.name, init.server_info.version)
            tools = await s.list_tools()
            print("tools:", len(tools.tools))
            res = await s.call_tool("ping", {})
            print("ping result:", res.content[0].text)


asyncio.run(main())
import asyncio
import json

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import BaseModel

from core.tools.base import ToolRegistry
from core.tools.book_transit import BookTransitTool
from core.tools.estimate_walk_time import EstimateWalkTimeTool
from core.tools.find_transit_trips import FindTransitTripsTool
from core.tools.get_opening_hours import GetOpeningHoursTool
from core.tools.hold_reservation import HoldReservationTool
from core.tools.lookup_price import LookupPriceTool
from core.tools.search_attractions import SearchAttractionsTool
from core.tools.send_confirmation import SendConfirmationTool


def get_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(BookTransitTool())
    registry.register(EstimateWalkTimeTool())
    registry.register(FindTransitTripsTool())
    registry.register(GetOpeningHoursTool())
    registry.register(HoldReservationTool())
    registry.register(LookupPriceTool())
    registry.register(SearchAttractionsTool())
    registry.register(SendConfirmationTool())
    return registry

def generate_json_schema(model: type[BaseModel]) -> dict:
    # A simple wrapper to get json schema from a pydantic model
    return model.model_json_schema()

async def run_server():
    app = Server("tripagent-mcp")
    registry = get_registry()
    
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        tools = []
        for tool in registry.list_read():
            tools.append(
                types.Tool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=generate_json_schema(tool.args_model)
                )
            )
        for tool in registry.list_write():
            tools.append(
                types.Tool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=generate_json_schema(tool.args_model)
                )
            )
        return tools

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        try:
            tool = registry.get(name)
        except KeyError:
            raise ValueError(f"Tool {name} not found")
            
        if tool.access == "write":
            # Write actions require human approval
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "Write actions require the human approval queue and are unavailable through MCP."})
                )
            ]
            
        # For read tools, execute them directly
        try:
            args = tool.args_model.model_validate(arguments)
            result = tool.execute(args)
            return [
                types.TextContent(
                    type="text",
                    text=result.model_dump_json()
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )
            ]

    # Run the server on stdio
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(run_server())

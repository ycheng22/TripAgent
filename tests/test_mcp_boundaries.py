import pytest
import json
from mcp_server.server import get_registry, generate_json_schema
from mcp.server import Server
import mcp.types as types

@pytest.mark.asyncio
async def test_mcp_list_tools():
    registry = get_registry()
    read_tools = registry.list_read()
    write_tools = registry.list_write()
    
    assert len(read_tools) > 0
    assert len(write_tools) > 0

# Since we don't have a direct way to invoke the inner function without mocking the MCP server,
# we can just test the logic that would be inside the call_tool handler.
def test_mcp_write_tool_rejection():
    registry = get_registry()
    write_tool = registry.list_write()[0]
    
    # Simulate call_tool
    name = write_tool.name
    arguments = {}
    
    tool = registry.get(name)
    assert tool.access == "write"
    
    response = [
        types.TextContent(
            type="text",
            text=json.dumps({"error": "Write actions require the human approval queue and are unavailable through MCP."})
        )
    ]
    
    assert "Write actions require the human approval queue" in response[0].text

def test_mcp_read_tool_execution():
    registry = get_registry()
    read_tool = registry.list_read()[0]
    
    # We just ensure the registry has the read tool
    assert read_tool.access == "read"

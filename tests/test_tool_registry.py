import pytest

from core.tools.base import ToolRegistry
from core.tools.hold_reservation import HoldReservationTool
from core.tools.search_attractions import SearchAttractionsTool


def test_read_tool_registers():
    registry = ToolRegistry()
    tool = SearchAttractionsTool()
    registry.register(tool)
    assert registry.get(tool.name) == tool
    assert tool in registry.list_read()

def test_write_tool_registers_with_idempotency_key():
    registry = ToolRegistry()
    tool = HoldReservationTool()
    registry.register(tool)
    assert registry.get(tool.name) == tool
    assert tool in registry.list_write()

def test_write_tool_fails_without_idempotency_key():
    from typing import Literal

    from pydantic import BaseModel
    class BadWriteTool:
        name = "bad_write"
        description = "bad"
        args_model = BaseModel
        access: Literal["write"] = "write"
        
        def execute(self, args):
            return None
            
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="must implement idempotency_key"):
        registry.register(BadWriteTool())

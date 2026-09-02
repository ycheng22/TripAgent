from typing import Literal, Protocol, Type, Any
from pydantic import BaseModel

class Tool(Protocol):
    name: str
    description: str
    args_model: Type[BaseModel]
    access: Literal["read", "write"]

    def execute(self, args: BaseModel) -> BaseModel:
        ...

    def idempotency_key(self, args: BaseModel) -> str:
        # Default implementation can be overridden or required by write tools
        ...

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.access == "write":
            # Check if it has a properly implemented idempotency_key.
            # In python Protocols, we can check if the class overrides it or test its presence.
            # Since idempotency_key might exist with a default on the protocol, we can just ensure 
            # it doesn't raise NotImplementedError or we can check if it's explicitly defined.
            # Let's check by trying to call it with a dummy args model or by inspecting the class.
            
            # A simple way to check if it's implemented:
            if not hasattr(tool, "idempotency_key") or tool.idempotency_key.__code__ is Tool.idempotency_key.__code__:
                if not getattr(tool, "_has_idempotency_key", False):
                    raise ValueError(f"Write tool {tool.name} must implement idempotency_key")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool {name} not found")
        return self._tools[name]

    def list_read(self) -> list[Tool]:
        return [t for t in self._tools.values() if t.access == "read"]

    def list_write(self) -> list[Tool]:
        return [t for t in self._tools.values() if t.access == "write"]

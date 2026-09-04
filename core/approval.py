import uuid
import asyncio
from typing import Any
from core.models import PendingAction, Constraint
from core.tools.base import ToolRegistry

class ApprovalQueue:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._actions: dict[str, PendingAction] = {}
        self._lock = asyncio.Lock()
        
    async def submit(self, tool_name: str, args: dict[str, Any], idempotency_key: str) -> PendingAction:
        async with self._lock:
            # Check for replay
            for action in self._actions.values():
                if action.idempotency_key == idempotency_key:
                    if action.status == "approved":
                        # Return as approved no-op
                        return action
            
            action_id = str(uuid.uuid4())
            action = PendingAction(
                action_id=action_id,
                tool_name=tool_name,
                args=args,
                idempotency_key=idempotency_key,
                status="pending"
            )
            self._actions[action_id] = action
            return action
            
    async def approve(self, action_id: str) -> PendingAction:
        async with self._lock:
            if action_id not in self._actions:
                raise KeyError(f"Action {action_id} not found")
                
            action = self._actions[action_id]
            if action.status != "pending":
                return action
                
            tool = self.registry.get(action.tool_name)
            args_model = tool.args_model.model_validate(action.args)
            
            # Execute tool
            result = tool.execute(args_model)
            
            action.status = "approved"
            action.result = result.model_dump() if hasattr(result, "model_dump") else result
            return action

    async def reject(self, action_id: str, reason: str) -> Constraint:
        async with self._lock:
            if action_id not in self._actions:
                raise KeyError(f"Action {action_id} not found")
                
            action = self._actions[action_id]
            action.status = "rejected"
            
            return Constraint(
                kind="rejection",
                value=f"Action {action.tool_name} rejected: {reason}",
                source="rejection",
                hard=True
            )
            
    async def get(self, action_id: str) -> PendingAction | None:
        async with self._lock:
            return self._actions.get(action_id)
            
    async def list_pending(self) -> list[PendingAction]:
        async with self._lock:
            return [a for a in self._actions.values() if a.status == "pending"]

# Global queue for Day 4 simplicity
_queue = None

def get_approval_queue(registry: ToolRegistry = None) -> ApprovalQueue:
    global _queue
    if _queue is None:
        if registry is None:
            registry = ToolRegistry() # just a stub for test imports without full initialization
        _queue = ApprovalQueue(registry)
    return _queue

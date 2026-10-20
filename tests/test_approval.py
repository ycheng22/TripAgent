
import pytest

from core.approval import ApprovalQueue
from core.tools.base import ToolRegistry


# Mock tool
class MockTool:
    name = "mock_write"
    access = "write"
    
    class MockArgs:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def model_dump(self):
            return self.__dict__
            
    class MockArgsModel:
        @classmethod
        def model_validate(cls, args):
            return MockTool.MockArgs(**args)
            
    args_model = MockArgsModel
    
    def execute(self, args):
        return {"status": "success", "executed_args": args.model_dump()}

@pytest.fixture
def registry():
    reg = ToolRegistry()
    # manually inject for test
    reg._tools["mock_write"] = MockTool()
    return reg

@pytest.fixture
def queue(registry):
    return ApprovalQueue(registry)

@pytest.mark.asyncio
async def test_submit_creates_pending_action(queue):
    action = await queue.submit("mock_write", {"val": 1}, "key-1")
    assert action.status == "pending"
    assert action.idempotency_key == "key-1"
    
    pending = await queue.list_pending()
    assert len(pending) == 1
    assert pending[0].action_id == action.action_id

@pytest.mark.asyncio
async def test_approve_executes_tool(queue):
    action = await queue.submit("mock_write", {"val": 2}, "key-2")
    approved = await queue.approve(action.action_id)
    
    assert approved.status == "approved"
    assert approved.result["status"] == "success"
    assert approved.result["executed_args"]["val"] == 2
    
    pending = await queue.list_pending()
    assert len(pending) == 0

@pytest.mark.asyncio
async def test_reject_creates_constraint(queue):
    action = await queue.submit("mock_write", {"val": 3}, "key-3")
    constraint = await queue.reject(action.action_id, "Too expensive")
    
    assert constraint.kind == "rejection"
    assert "Too expensive" in str(constraint.value)
    
    updated = await queue.get(action.action_id)
    assert updated.status == "rejected"

@pytest.mark.asyncio
async def test_idempotency_replay(queue):
    # First submit and approve
    action1 = await queue.submit("mock_write", {"val": 4}, "key-4")
    await queue.approve(action1.action_id)
    
    # Second submit with same key
    action2 = await queue.submit("mock_write", {"val": 4}, "key-4")
    
    # Should return the already approved action instead of a new pending one
    assert action2.action_id == action1.action_id
    assert action2.status == "approved"

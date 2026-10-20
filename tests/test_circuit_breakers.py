from core.planner.limits import CircuitBreakers, LimitConfig


def test_max_steps_breach():
    config = LimitConfig(max_steps=3)
    breakers = CircuitBreakers(config)
    assert breakers.check(step_count=4, total_tokens=0, total_cost=0.0) == "max_steps"
    assert breakers.check(step_count=3, total_tokens=0, total_cost=0.0) is None

def test_max_tokens_breach():
    config = LimitConfig(max_tokens_per_task=100)
    breakers = CircuitBreakers(config)
    assert breakers.check(step_count=1, total_tokens=101, total_cost=0.0) == "max_tokens"
    assert breakers.check(step_count=1, total_tokens=100, total_cost=0.0) is None

def test_max_cost_breach():
    config = LimitConfig(max_cost_per_task=0.05)
    breakers = CircuitBreakers(config)
    assert breakers.check(step_count=1, total_tokens=100, total_cost=0.06) == "max_cost"
    assert breakers.check(step_count=1, total_tokens=100, total_cost=0.05) is None

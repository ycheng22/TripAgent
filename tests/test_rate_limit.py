from core.rate_limit import check_rate_limit, record_live_call, reset_rate_limits


def test_rate_limiter_allows_under_quota() -> None:
    reset_rate_limits()
    ip = "192.168.1.50"

    for i in range(5):
        allowed, remaining, retry_after = check_rate_limit(ip, max_calls=5, window_seconds=600)
        assert allowed is True
        assert remaining == 5 - i
        assert retry_after == 0
        record_live_call(ip)

    # 6th call should be blocked
    allowed, remaining, retry_after = check_rate_limit(ip, max_calls=5, window_seconds=600)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_rate_limiter_per_ip_isolation() -> None:
    reset_rate_limits()
    ip_a = "10.0.0.1"
    ip_b = "10.0.0.2"

    for _ in range(5):
        record_live_call(ip_a)

    # IP A blocked
    allowed_a, _, _ = check_rate_limit(ip_a, max_calls=5, window_seconds=600)
    assert allowed_a is False

    # IP B still allowed
    allowed_b, remaining_b, _ = check_rate_limit(ip_b, max_calls=5, window_seconds=600)
    assert allowed_b is True
    assert remaining_b == 5

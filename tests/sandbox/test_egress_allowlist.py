from backend.sandbox.egress import is_allowed, parse_allowlist


def test_default_allowlist_permits_llm_hosts() -> None:
    assert is_allowed("api.deepseek.com", 443)
    assert is_allowed("api.anthropic.com", 443)
    assert not is_allowed("evil.example.com", 443)


def test_parse_custom_allowlist() -> None:
    rules = parse_allowlist("api.example.com:8443,foo.test")
    assert is_allowed("api.example.com", 8443, rules)
    assert is_allowed("foo.test", 443, rules)
    assert not is_allowed("bar.test", 443, rules)

from backend.api.security import escape_html


def test_xss_payload_escaped_in_api_helper() -> None:
    payload = '<img src=x onerror=alert(1)>'
    escaped = escape_html(payload)
    assert "onerror" in escaped
    assert "<img" not in escaped

from backend.api.security import escape_html


def test_escape_html_script_tag() -> None:
    payload = '<script>alert(1)</script>'
    escaped = escape_html(payload)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped

import json

import pytest

from backend.core.llm.json_parse import parse_json_response


def test_parse_json_response_plain_object() -> None:
    payload = parse_json_response('{"verdict":"confirm","confidence":0.9}')
    assert payload["verdict"] == "confirm"


def test_parse_json_response_markdown_fence() -> None:
    text = 'Here is the result:\n```json\n{"verdict":"reject"}\n```\n'
    payload = parse_json_response(text)
    assert payload["verdict"] == "reject"


def test_parse_json_response_prose_before_object() -> None:
    text = 'Analysis complete.\n{"findings":[{"rule_id":"llm.x","severity":"high"}]}'
    payload = parse_json_response(text)
    assert payload["findings"][0]["rule_id"] == "llm.x"


def test_parse_json_response_top_level_array() -> None:
    payload = parse_json_response('[{"rule_id":"llm.x"}]')
    assert payload["findings"][0]["rule_id"] == "llm.x"


def test_parse_json_response_empty_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_json_response("   ")

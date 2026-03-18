"""Tests for the extract_json helper in BaseAgent."""

from src.agents.base import extract_json


class TestExtractJson:
    def test_json_fenced(self):
        content = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        assert extract_json(content) == '{"key": "value"}'

    def test_bare_fenced(self):
        content = '```\n{"key": "value"}\n```'
        assert extract_json(content) == '{"key": "value"}'

    def test_no_fences(self):
        content = '  {"key": "value"}  '
        assert extract_json(content) == '{"key": "value"}'

    def test_empty_string(self):
        assert extract_json("") == ""

    def test_json_fence_with_trailing_text(self):
        content = 'Here is the result:\n```json\n{"a": 1}\n```\nDone!'
        assert extract_json(content) == '{"a": 1}'

"""Tests for output formatting."""

import json
import pytest

from elisity_cli.output import (
    apply_query,
    format_json,
    format_table,
    format_csv,
    format_yaml,
)


class TestOutputFormatters:
    """Unit tests for output formatters."""

    def test_format_json(self):
        data = {"name": "test", "value": 42}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42

    def test_format_json_list(self):
        data = [{"id": "1"}, {"id": "2"}]
        result = format_json(data)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_format_table_dict(self):
        data = {"id": "abc-123", "name": "TestSite"}
        result = format_table(data)
        assert "abc-123" in result
        assert "TestSite" in result

    def test_format_table_list(self):
        data = [
            {"id": "1", "name": "Site A"},
            {"id": "2", "name": "Site B"},
        ]
        result = format_table(data)
        assert "Site A" in result
        assert "Site B" in result

    def test_format_table_paginated(self):
        data = {
            "content": [{"id": "1", "name": "Item"}],
            "totalElements": 1,
        }
        result = format_table(data)
        assert "Item" in result

    def test_format_csv(self):
        data = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        result = format_csv(data)
        assert "id,name" in result
        assert "1,A" in result
        assert "2,B" in result

    def test_format_yaml(self):
        data = {"key": "value"}
        result = format_yaml(data)
        assert "key: value" in result

    def test_format_table_empty(self):
        result = format_table([])
        assert result  # Should not crash


class TestJMESPath:
    """Tests for JMESPath query filtering."""

    def test_simple_query(self):
        data = {"content": [{"name": "A"}, {"name": "B"}]}
        result = apply_query(data, "content[].name")
        assert result == ["A", "B"]

    def test_filter_query(self):
        data = [
            {"name": "online", "status": "ONLINE"},
            {"name": "offline", "status": "OFFLINE"},
        ]
        result = apply_query(data, "[?status=='ONLINE'].name")
        assert result == ["online"]

    def test_nested_query(self):
        data = {"a": {"b": {"c": 42}}}
        result = apply_query(data, "a.b.c")
        assert result == 42

    def test_no_query(self):
        data = {"test": True}
        result = apply_query(data, None)
        assert result == data

"""A source header or quoting change must not silently alter parsed facts."""

import csv

import pytest

from gas_intel.ingestion.parsers import csv_records


@pytest.mark.parametrize("payload", [b"", b"A,\n1,2\n", b"A,A\n1,2\n", b"B\n1\n"])
def test_invalid_header_contract_fails(payload: bytes) -> None:
    with pytest.raises(ValueError):
        csv_records(payload, {"A"})


@pytest.mark.parametrize("header", [b"B,A", b"A,B,C", b"A"])
def test_exact_schema_detects_reorder_addition_and_removal(header: bytes) -> None:
    with pytest.raises(ValueError, match="pinned schema"):
        csv_records(header + b"\n", {"A"}, ["A", "B"])


def test_bom_crlf_and_quoted_commas_preserve_strings() -> None:
    headers, rows = csv_records(b'\xef\xbb\xbfA,B\r\n0012,"Name, Inc."\r\n', {"A"})
    assert headers == ["A", "B"]
    assert list(rows) == [{"A": "0012", "B": "Name, Inc."}]


def test_unclosed_quote_is_an_error() -> None:
    _, rows = csv_records(b'A,B\n0012,"unfinished\n', {"A"})
    with pytest.raises(csv.Error):
        list(rows)


@pytest.mark.parametrize("record", [b"1", b"1,2,3"])
def test_wrong_column_count_fails(record: bytes) -> None:
    _, rows = csv_records(b"A,B\n" + record + b"\n", {"A"})
    with pytest.raises(ValueError, match="column count"):
        list(rows)

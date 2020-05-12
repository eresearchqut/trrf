from datetime import datetime

from rdrf.forms.dsl.utils import as_type, parse_date, parse_int


def test_parse_date():
    result1 = parse_date("2020-05-12")
    result2 = parse_date("12-05-2020")
    assert isinstance(result1, datetime)
    assert isinstance(result2, datetime)
    assert result1 == result2
    assert parse_date("2020-13-20") is None
    assert parse_date("abc") is None


def test_parse_int():
    assert parse_int("123") == 123
    assert parse_int("123.45") is None
    assert parse_int("abc") is None


def test_as_type():
    assert as_type('integer', '123') == 123
    assert isinstance(as_type('date', '2020-05-12'), datetime)
    assert as_type(None, "abc") == "abc"

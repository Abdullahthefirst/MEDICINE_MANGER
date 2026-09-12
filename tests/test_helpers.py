from datetime import date, datetime
from decimal import Decimal
import re

from core.helpers import clean_payload, money, number, reference


def test_reference_has_prefix_date_and_suffix():
    value = reference("MOV")
    assert re.fullmatch(r"MOV-\d{8}-[0-9A-F]{6}", value)


def test_clean_payload_converts_database_values():
    cleaned = clean_payload({
        "empty": "",
        "date": date(2026, 9, 12),
        "datetime": datetime(2026, 9, 12, 10, 30),
        "decimal": Decimal("2.50"),
        "text": "value",
    })
    assert cleaned == {
        "empty": None,
        "date": "2026-09-12",
        "datetime": "2026-09-12T10:30:00",
        "decimal": 2.5,
        "text": "value",
    }


def test_formatting_helpers_handle_invalid_values():
    assert money(1250) == "PKR 1,250"
    assert money("invalid") == "PKR 0"
    assert number(2.345, 2) == "2.35"

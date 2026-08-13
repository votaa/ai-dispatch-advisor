from app.data_loader import _coerce_field


def test_numeric_looking_identifiers_remain_strings() -> None:
    assert _coerce_field("incident_id", "1001") == "1001"
    assert _coerce_field("crew_id", "6140") == "6140"
    assert _coerce_field("feeder", "12") == "12"
    assert _coerce_field("customers_out", "2840") == 2840

from backend.app.services.financial_validation_service import (
    validate_financial_data,
    to_decimal,
    build_overall_result,
)


def test_to_decimal():
    assert to_decimal("1,234.50") == 1234.50
    assert to_decimal("(442,018)") == -442018
    assert to_decimal("-") == 0


def test_invoice_pass():
    data = {
        "fields": {
            "Subtotal": {"value": "1000"},
            "Tax": {"value": "180"},
            "Total": {"value": "1180"},
        },
        "line_items": [
            {
                "quantity": 10,
                "unit_price": 100,
                "line_total": 1000,
            }
        ],
    }

    result = validate_financial_data("invoice", data)

    assert result["overall_status"] == "PASS"


def test_invoice_fail():
    data = {
        "fields": {
            "Subtotal": {"value": "1000"},
            "Tax": {"value": "180"},
            "Total": {"value": "1300"},
        },
        "line_items": [
            {
                "quantity": 10,
                "unit_price": 100,
                "line_total": 1000,
            }
        ],
    }

    result = validate_financial_data("invoice", data)

    assert result["overall_status"] == "FAIL"


def test_cash_flow_pass():
    data = {
        "fields": {
            "Net cash from operating activities | 2025": {"value": "500"},
            "Net cash from investing activities | 2025": {"value": "-200"},
            "Net cash from financing activities | 2025": {"value": "100"},
            "Net increase in cash | 2025": {"value": "400"},
            "Opening cash | 2025": {"value": "1000"},
            "Closing cash | 2025": {"value": "1400"},
        }
    }

    result = validate_financial_data(
        "cash_flow_statement",
        data
    )

    assert result["overall_status"] == "PASS"


def test_not_applicable_when_no_checks():
    result = validate_financial_data(
        "invoice",
        {
            "fields": {},
            "line_items": []
        }
    )

    assert result["overall_status"] == "NOT_APPLICABLE"


def test_build_overall_result():
    assert build_overall_result([]) == "NOT_APPLICABLE"

    assert build_overall_result([
        {"status": "PASS"},
        {"status": "PASS"}
    ]) == "PASS"

    assert build_overall_result([
        {"status": "PASS"},
        {"status": "FAIL"}
    ]) == "FAIL"
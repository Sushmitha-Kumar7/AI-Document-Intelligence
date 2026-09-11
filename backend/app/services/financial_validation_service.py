from decimal import Decimal, InvalidOperation
import re


# Small tolerance for rounding differences in financial documents
TOLERANCE = Decimal("0.50")


# ============================================================
# BASIC HELPERS
# ============================================================

def get_field_value(field):
    """
    Extract the actual value from an ExtractedField dictionary.
    """
    if isinstance(field, dict):
        return field.get("value")
    return field


def to_decimal(value):
    """
    Convert extracted financial values into Decimal.

    Handles:
    - commas: 1,234,567
    - currency symbols
    - percentages
    - parentheses: (442,018) -> -442018
    - dash: - -> 0
    """
    if value is None:
        return None

    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    value = str(value).strip()

    if not value:
        return None

    # Parentheses represent negative values
    negative = value.startswith("(") and value.endswith(")")

    # Normalize common formatting
    value = (
        value.replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("%", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
    )

    # Dash means zero when explicitly shown in financial statements
    if value in {"-", "—", "–", "="}:
        return Decimal("0")

    # Extract numeric part
    match = re.search(r"-?\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        number = Decimal(match.group())

        if negative:
            number = -abs(number)

        return number

    except InvalidOperation:
        return None


def get_periods(fields):
    """
    Find comparative periods from field names such as:

    Capital | 31-Mar-18
    Capital | 31-Mar-17
    """
    periods = set()

    for key in fields:
        match = re.search(r"\|\s*(.+)$", key)

        if match:
            periods.add(match.group(1).strip())

    return sorted(periods)


def find_field_value(fields, keywords, period=None):
    """
    Find a field whose key contains all supplied keywords.

    Example:
        ["total", "assets"]

    can find:
        Total assets | 31-Mar-18
    """
    keywords = [k.lower() for k in keywords]

    for key, field in fields.items():

        key_lower = key.lower()

        if period and period.lower() not in key_lower:
            continue

        if all(keyword in key_lower for keyword in keywords):
            return get_field_value(field)

    return None


def find_field_by_aliases(fields, aliases, period=None):
    """
    Search using multiple possible phrases.

    Useful because financial statements can use different labels,
    for example:
        Total assets
        Total
        Total assets of the company
    """
    for alias in aliases:

        if isinstance(alias, str):
            keywords = alias.lower().split()
        else:
            keywords = alias

        value = find_field_value(fields, keywords, period)

        if value is not None:
            return value

    return None


def check_value(formula, inputs, calculated, reported):
    """
    Create one validation result.

    If either side is missing, return NOT_APPLICABLE.
    """
    if calculated is None or reported is None:
        return {
            "formula": formula,
            "inputs": inputs,
            "calculated": None,
            "reported": reported,
            "variance": None,
            "status": "NOT_APPLICABLE"
        }

    variance = calculated - reported

    status = (
        "PASS"
        if abs(variance) <= TOLERANCE
        else "FAIL"
    )

    return {
        "formula": formula,
        "inputs": inputs,
        "calculated": float(calculated),
        "reported": float(reported),
        "variance": float(variance),
        "status": status
    }


# ============================================================
# INVOICE VALIDATION
# ============================================================

def validate_invoice(fields, line_items=None):
    results = []
    line_items = line_items or []

    # --------------------------------------------------------
    # 1. Quantity × Unit Price - Discount ≈ Line Total
    # --------------------------------------------------------

    calculated_subtotal = Decimal("0")
    valid_line_totals = []

    for index, item in enumerate(line_items, start=1):

        if not isinstance(item, dict):
            continue

        quantity = to_decimal(
            get_field_value(item.get("quantity"))
        )

        unit_price = to_decimal(
            get_field_value(item.get("unit_price"))
        )

        line_total = to_decimal(
            get_field_value(item.get("line_total"))
        )

        # Optional line-item discount percentage
        discount = None

        for discount_key in [
            "discount",
            "discount_percentage",
            "discount_percent"
        ]:
            if item.get(discount_key) is not None:
                discount = to_decimal(
                    get_field_value(item.get(discount_key))
                )
                break

        # Support different possible discount field names
        discount = None

        for discount_key in [
            "discount",
            "discount_percent",
            "discount_percentage"
        ]:
            if discount_key in item:
                discount = to_decimal(
                    get_field_value(item.get(discount_key))
                )
                if discount is not None:
                    break

        if (
            quantity is not None
            and unit_price is not None
            and line_total is not None
        ):

            calculated = quantity * unit_price

            # Apply discount percentage when present
            if discount is not None:
                calculated = calculated * (
                    Decimal("1") - discount / Decimal("100")
                )

            formula = (
                f"Line {index}: quantity × unit price"
            )

            if discount is not None and discount > 0:
                formula += " − discount ≈ line total"

            inputs = {
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "discount_percentage": (
                    float(discount)
                    if discount is not None
                    else None
                )
            }

            if discount is not None:
                inputs["discount_percent"] = float(discount)

            results.append(
                check_value(
                    formula,
                    inputs,
                    calculated,
                    line_total
                )
            )

            valid_line_totals.append(line_total)

    # --------------------------------------------------------
    # 2. Sum of Line Totals ≈ Subtotal
    # --------------------------------------------------------

    if valid_line_totals:

        calculated_subtotal = sum(
            valid_line_totals,
            Decimal("0")
        )

        subtotal = None

        for key, field in fields.items():

            if "subtotal" in key.lower():

                subtotal = to_decimal(
                    get_field_value(field)
                )

                break

        if subtotal is not None:

            results.append(
                check_value(
                    "Sum of line totals ≈ subtotal",
                    {
                        "sum_line_totals": float(
                            calculated_subtotal
                        )
                    },
                    calculated_subtotal,
                    subtotal
                )
            )

    # --------------------------------------------------------
    # 3. Subtotal + Tax ≈ Total
    # --------------------------------------------------------

    subtotal = None
    tax_amount = None
    total_amount = None

    for key, field in fields.items():

        key_lower = key.lower()

        value = to_decimal(
            get_field_value(field)
        )

        if subtotal is None and "subtotal" in key_lower:
            subtotal = value

        if tax_amount is None and (
            "tax" in key_lower
            or "vat" in key_lower
            or "gst" in key_lower
        ):
            tax_amount = value

        if total_amount is None and (
            "total_amount" in key_lower
            or key_lower.strip() == "total"
            or "grand total" in key_lower
        ):
            total_amount = value

    if (
        subtotal is not None
        and tax_amount is not None
        and total_amount is not None
    ):

        calculated = subtotal + tax_amount

        results.append(
            check_value(
                "Subtotal + tax ≈ total amount",
                {
                    "subtotal": float(subtotal),
                    "tax_amount": float(tax_amount)
                },
                calculated,
                total_amount
            )
        )

    # --------------------------------------------------------
    # 4. Cash Paid - Total ≈ Change
    # --------------------------------------------------------

    cash_paid = None
    change = None

    for key, field in fields.items():

        key_lower = key.lower()

        value = to_decimal(
            get_field_value(field)
        )

        if cash_paid is None and (
            "cash paid" in key_lower
            or "amount paid" in key_lower
            or "paid amount" in key_lower
        ):
            cash_paid = value

        if change is None and "change" in key_lower:
            change = value

    if (
        cash_paid is not None
        and total_amount is not None
        and change is not None
    ):

        calculated = cash_paid - total_amount

        results.append(
            check_value(
                "Cash paid - total amount ≈ change",
                {
                    "cash_paid": float(cash_paid),
                    "total_amount": float(total_amount)
                },
                calculated,
                change
            )
        )

    return results

# ============================================================
# BALANCE SHEET VALIDATION
# ============================================================

def validate_balance_sheet(fields):

    results = []

    periods = get_periods(fields)

    for period in periods:

        # ----------------------------------------------------
        # 1. Total Liabilities ≈ Total Assets
        # ----------------------------------------------------

        total_liabilities = find_field_by_aliases(
            fields,
            [
                ["total", "liabilities"],
                ["total"]
            ],
            period
        )

        total_assets = find_field_by_aliases(
            fields,
            [
                ["total", "assets"]
            ],
            period
        )

        if (
            total_liabilities is not None
            and total_assets is not None
        ):

            liabilities = to_decimal(total_liabilities)
            assets = to_decimal(total_assets)

            results.append(
                check_value(
                    f"Total liabilities ≈ total assets ({period})",
                    {
                        "total_liabilities": float(liabilities)
                    },
                    liabilities,
                    assets
                )
            )

        # ----------------------------------------------------
        # 2. Capital & Liabilities Component Sum
        # ----------------------------------------------------

        liability_components = [
            ("capital", ["capital"]),
            ("reserves_and_surplus", ["reserves", "surplus"]),
            ("minority_interest", ["minority", "interest"]),
            ("deposits", ["deposits"]),
            ("borrowings", ["borrowings"]),
            (
                "other_liabilities_and_provisions",
                ["other", "liabilities", "provisions"]
            )
        ]

        component_values = {}
        all_components_available = True

        for name, keywords in liability_components:

            value = find_field_value(
                fields,
                keywords,
                period
            )

            value = to_decimal(value)

            if value is None:
                all_components_available = False
                break

            component_values[name] = value

        if (
            all_components_available
            and total_liabilities is not None
        ):

            calculated = sum(
                component_values.values(),
                Decimal("0")
            )

            results.append(
                check_value(
                    f"Capital and liabilities components ≈ total liabilities ({period})",
                    {
                        key: float(value)
                        for key, value
                        in component_values.items()
                    },
                    calculated,
                    to_decimal(total_liabilities)
                )
            )

        # ----------------------------------------------------
        # 3. Asset Component Sum
        # ----------------------------------------------------

        asset_components = [
            (
                "cash_and_balances_with_rbi",
                ["cash", "balances", "reserve", "bank", "india"]
            ),
            (
                "balances_with_banks",
                ["balances", "banks", "money", "call"]
            ),
            ("investments", ["investments"]),
            ("advances", ["advances"]),
            ("fixed_assets", ["fixed", "assets"]),
            ("other_assets", ["other", "assets"])
        ]

        asset_values = {}
        all_asset_components_available = True

        for name, keywords in asset_components:

            value = find_field_value(
                fields,
                keywords,
                period
            )

            value = to_decimal(value)

            if value is None:
                all_asset_components_available = False
                break

            asset_values[name] = value

        if (
            all_asset_components_available
            and total_assets is not None
        ):

            calculated = sum(
                asset_values.values(),
                Decimal("0")
            )

            results.append(
                check_value(
                    f"Asset components ≈ total assets ({period})",
                    {
                        key: float(value)
                        for key, value
                        in asset_values.items()
                    },
                    calculated,
                    to_decimal(total_assets)
                )
            )

    return results


# ============================================================
# PROFIT & LOSS VALIDATION
# ============================================================

def validate_profit_and_loss(fields):

    results = []

    periods = get_periods(fields)

    for period in periods:

        # ----------------------------------------------------
        # 1. Interest Earned + Other Income ≈ Total Income
        # ----------------------------------------------------

        interest_earned = to_decimal(
            find_field_value(
                fields,
                ["interest", "earned"],
                period
            )
        )

        other_income = to_decimal(
            find_field_value(
                fields,
                ["other", "income"],
                period
            )
        )

        total_income = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["total", "income"]
                ],
                period
            )
        )

        if (
            interest_earned is not None
            and other_income is not None
            and total_income is not None
        ):

            calculated = (
                interest_earned
                + other_income
            )

            results.append(
                check_value(
                    f"Interest earned + other income ≈ total income ({period})",
                    {
                        "interest_earned": float(
                            interest_earned
                        ),
                        "other_income": float(
                            other_income
                        )
                    },
                    calculated,
                    total_income
                )
            )

        # ----------------------------------------------------
        # 2. Expenditure Components ≈ Total Expenditure
        # ----------------------------------------------------

        interest_expended = to_decimal(
            find_field_value(
                fields,
                ["interest", "expended"],
                period
            )
        )

        operating_expenses = to_decimal(
            find_field_value(
                fields,
                ["operating", "expenses"],
                period
            )
        )

        provisions = to_decimal(
            find_field_value(
                fields,
                ["provisions", "contingencies"],
                period
            )
        )

        total_expenditure = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["total", "expenditure"]
                ],
                period
            )
        )

        if (
            interest_expended is not None
            and operating_expenses is not None
            and provisions is not None
            and total_expenditure is not None
        ):

            calculated = (
                interest_expended
                + operating_expenses
                + provisions
            )

            results.append(
                check_value(
                    f"Interest expended + operating expenses + provisions ≈ total expenditure ({period})",
                    {
                        "interest_expended": float(
                            interest_expended
                        ),
                        "operating_expenses": float(
                            operating_expenses
                        ),
                        "provisions": float(
                            provisions
                        )
                    },
                    calculated,
                    total_expenditure
                )
            )

        # ----------------------------------------------------
        # 3. Total Income - Total Expenditure
        #    ≈ Net Profit for the Year
        # ----------------------------------------------------

        net_profit = to_decimal(
            find_field_value(
                fields,
                ["net", "profit", "year"],
                period
            )
        )

        if (
            total_income is not None
            and total_expenditure is not None
            and net_profit is not None
        ):

            calculated = (
                total_income
                - total_expenditure
            )

            results.append(
                check_value(
                    f"Total income - total expenditure ≈ net profit for the year ({period})",
                    {
                        "total_income": float(total_income),
                        "total_expenditure": float(
                            total_expenditure
                        )
                    },
                    calculated,
                    net_profit
                )
            )

        # ----------------------------------------------------
        # 4. Net Profit - Minority Interest
        #    + Share in Profits of Associates
        #    ≈ Consolidated Profit
        # ----------------------------------------------------

        minority_interest = to_decimal(
            find_field_value(
                fields,
                ["minority", "interest"],
                period
            )
        )

        share_associates = to_decimal(
            find_field_value(
                fields,
                ["share", "profits", "associates"],
                period
            )
        )

        consolidated_profit = to_decimal(
            find_field_value(
                fields,
                ["consolidated", "profit", "year"],
                period
            )
        )

        if (
            net_profit is not None
            and minority_interest is not None
            and share_associates is not None
            and consolidated_profit is not None
        ):

            calculated = (
                net_profit
                - minority_interest
                + share_associates
            )

            results.append(
                check_value(
                    f"Net profit - minority interest + share in profits of associates ≈ consolidated profit ({period})",
                    {
                        "net_profit": float(net_profit),
                        "minority_interest": float(
                            minority_interest
                        ),
                        "share_in_profits_of_associates": float(
                            share_associates
                        )
                    },
                    calculated,
                    consolidated_profit
                )
            )
        # ----------------------------------------------------
        # 5. Consolidated Profit + Brought Forward
        #    + Impact on Amalgamation ≈ Total Profit
        # ----------------------------------------------------

        brought_forward = to_decimal(
            find_field_value(
                fields,
                [
                    "balance",
                    "profit",
                    "loss",
                    "account",
                    "brought",
                    "forward"
                ],
                period
            )
        )

        total_profit = to_decimal(
            find_field_value(
                fields,
                ["total", "profit"],
                period
            )
        )

        # Impact on amalgamation is an optional adjustment.
        # Include it only when the field exists in the extracted data.
        impact_on_amalgamation = to_decimal(
            find_field_value(
                fields,
                [
                    "impact",
                    "amalgamation"
                ],
                period
            )
        )

        if (
            consolidated_profit is not None
            and brought_forward is not None
            and total_profit is not None
        ):

            # If the document explicitly has no impact,
            # to_decimal("-") returns 0.
            if impact_on_amalgamation is None:
                impact_on_amalgamation = Decimal("0")

            calculated = (
                consolidated_profit
                + brought_forward
                + impact_on_amalgamation
            )

            # Show the correct formula depending on
            # whether an amalgamation adjustment exists.
            if impact_on_amalgamation != Decimal("0"):
                formula = (
                    f"Consolidated profit + brought forward balance "
                    f"+ impact on amalgamation ≈ total profit ({period})"
                )
            else:
                formula = (
                    f"Consolidated profit + brought forward balance "
                    f"≈ total profit ({period})"
                )

            results.append(
                check_value(
                    formula,
                    {
                        "consolidated_profit": float(
                            consolidated_profit
                        ),
                        "brought_forward_balance": float(
                            brought_forward
                        ),
                        "impact_on_amalgamation": float(
                            impact_on_amalgamation
                        )
                    },
                    calculated,
                    total_profit
                )
            )

        # ----------------------------------------------------
        # 6. Appropriations Components ≈ Total Appropriations
        # ----------------------------------------------------

        appropriation_names = [
            (
                "statutory_reserve",
                ["transfer", "statutory", "reserve"]
            ),
            (
                "tax_on_dividend",
                ["tax", "cess", "dividend"]
            ),
            (
                "dividend",
                ["dividend", "previous", "year", "paid"]
            ),
            (
                "general_reserve",
                ["transfer", "general", "reserve"]
            ),
            (
                "capital_reserve",
                ["transfer", "capital", "reserve"]
            ),
            (
                "investment_reserve",
                [
                    "investment",
                    "reserve",
                    "account"
                ]
            ),
            (
                "investment_fluctuation_reserve",
                [
                    "investment",
                    "fluctuation",
                    "reserve"
                ]
            ),
            (
                "balance_carried_over",
                [
                    "balance",
                    "carried",
                    "over",
                    "balance",
                    "sheet"
                ]
            )
        ]

        appropriation_values = {}
        all_appropriations_available = True

        for name, keywords in appropriation_names:

            value = find_field_value(
                fields,
                keywords,
                period
            )

            value = to_decimal(value)

            if value is None:
                all_appropriations_available = False
                break

            appropriation_values[name] = value

        total_appropriations = to_decimal(
            find_field_value(
                fields,
                ["total", "appropriations"],
                period
            )
        )

        if (
            all_appropriations_available
            and total_appropriations is not None
        ):

            calculated = sum(
                appropriation_values.values(),
                Decimal("0")
            )

            results.append(
                check_value(
                    f"Appropriation components ≈ total appropriations ({period})",
                    {
                        key: float(value)
                        for key, value
                        in appropriation_values.items()
                    },
                    calculated,
                    total_appropriations
                )
            )

    return results


# ============================================================
# CASH FLOW VALIDATION
# ============================================================

def validate_cash_flow(fields):

    results = []

    periods = get_periods(fields)

    for period in periods:

        # ----------------------------------------------------
        # Operating activities
        # ----------------------------------------------------

        operating = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["net", "cash", "operating"],
                    ["cash", "operating"]
                ],
                period
            )
        )

        # ----------------------------------------------------
        # Investing activities
        # ----------------------------------------------------

        investing = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["net", "cash", "investing"],
                    ["cash", "investing"]
                ],
                period
            )
        )

        # ----------------------------------------------------
        # Financing activities
        # ----------------------------------------------------

        financing = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["net", "cash", "financing"],
                    ["cash", "financing"]
                ],
                period
            )
        )

        # ----------------------------------------------------
        # Foreign exchange fluctuation
        # ----------------------------------------------------

        exchange = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["exchange", "fluctuation"],
                    ["foreign", "exchange"],
                    ["foreign", "currency"]
                ],
                period
            )
        )

        # If explicitly absent, treat it as zero.
        # Do NOT invent a non-zero value.
        if exchange is None:
            exchange = Decimal("0")

        # ----------------------------------------------------
        # Cash/cash equivalents on amalgamation
        # ----------------------------------------------------

        amalgamation = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    [
                        "cash",
                        "cash",
                        "equivalents",
                        "amalgamation"
                    ],
                    [
                        "cash",
                        "equivalents",
                        "amalgamation"
                    ],
                    [
                        "amalgamation"
                    ]
                ],
                period
            )
        )

        if amalgamation is None:
            amalgamation = Decimal("0")

        # ----------------------------------------------------
        # Net increase / decrease
        # ----------------------------------------------------

        net_increase = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["net", "increase"],
                    ["net", "increase", "decrease"]
                ],
                period
            )
        )

        if net_increase is None:

            net_decrease = to_decimal(
                find_field_by_aliases(
                    fields,
                    [
                        ["net", "decrease"]
                    ],
                    period
                )
            )

            if net_decrease is not None:
                net_increase = -abs(net_decrease)

        # ----------------------------------------------------
        # 1. Cash Flow Reconciliation
        # ----------------------------------------------------

        if (
            operating is not None
            and investing is not None
            and financing is not None
            and net_increase is not None
        ):

            calculated = (
                operating
                + investing
                + financing
                + exchange
                + amalgamation
            )

            results.append(
                check_value(
                    f"Cash flow reconciliation ({period})",
                    {
                        "operating_activities": float(
                            operating
                        ),
                        "investing_activities": float(
                            investing
                        ),
                        "financing_activities": float(
                            financing
                        ),
                        "exchange_fluctuation": float(
                            exchange
                        ),
                        "cash_and_cash_equivalents_on_amalgamation": float(
                            amalgamation
                        )
                    },
                    calculated,
                    net_increase
                )
            )

        # ----------------------------------------------------
        # Opening cash
        # ----------------------------------------------------

        opening_cash = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["opening", "cash"],
                    ["beginning", "cash"],
                    ["cash", "april", "1st"],
                    ["cash", "april", "1"]
                ],
                period
            )
        )

        # ----------------------------------------------------
        # Closing cash
        # ----------------------------------------------------

        closing_cash = to_decimal(
            find_field_by_aliases(
                fields,
                [
                    ["closing", "cash"],
                    ["ending", "cash"],
                    ["cash", "march", "31st"],
                    ["cash", "march", "31"]
                ],
                period
            )
        )

        # ----------------------------------------------------
        # 2. Opening Cash + Net Increase ≈ Closing Cash
        # ----------------------------------------------------

        if (
            opening_cash is not None
            and net_increase is not None
            and closing_cash is not None
        ):

            calculated = (
                opening_cash
                + net_increase
            )

            results.append(
                check_value(
                    f"Opening cash + net increase ≈ closing cash ({period})",
                    {
                        "opening_cash": float(
                            opening_cash
                        ),
                        "net_increase": float(
                            net_increase
                        )
                    },
                    calculated,
                    closing_cash
                )
            )

    return results


# ============================================================
# OVERALL STATUS
# ============================================================

def build_overall_result(results):

    if not results:
        return "NOT_APPLICABLE"

    statuses = [
        result.get("status")
        for result in results
    ]

    # Any failed applicable validation means FAIL
    if "FAIL" in statuses:
        return "FAIL"

    # At least one applicable PASS and no FAIL
    applicable = [
        status
        for status in statuses
        if status != "NOT_APPLICABLE"
    ]

    if applicable and all(
        status == "PASS"
        for status in applicable
    ):
        return "PASS"

    return "NOT_APPLICABLE"


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

def validate_financial_data(
    document_type,
    extraction_data
):

    fields = extraction_data.get(
        "fields",
        {}
    )

    line_items = extraction_data.get(
        "line_items",
        []
    )

    if document_type == "invoice":

        results = validate_invoice(
            fields,
            line_items
        )

    elif document_type == "balance_sheet":

        results = validate_balance_sheet(
            fields
        )

    elif document_type == "profit_and_loss":

        results = validate_profit_and_loss(
            fields
        )

    elif document_type == "cash_flow_statement":

        results = validate_cash_flow(
            fields
        )

    else:

        results = []

    return {
        "overall_status": build_overall_result(results),
        "checks": results
    }
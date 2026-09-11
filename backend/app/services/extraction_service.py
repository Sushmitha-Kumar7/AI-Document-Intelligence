import os
import io
import json
import base64

import fitz
from PIL import Image, ImageEnhance, ImageOps
from dotenv import load_dotenv
from openai import OpenAI

from app.schemas.extraction import ExtractionResult


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o"


# =========================================================
# IMAGE HELPERS
# =========================================================

def image_to_jpeg(image: Image.Image) -> bytes:
    image = ImageOps.exif_transpose(image).convert("RGB")

    # Keep enough resolution for small text/numbers
    max_side = 2600

    if max(image.size) > max_side:
        ratio = max_side / max(image.size)

        image = image.resize(
            (
                int(image.width * ratio),
                int(image.height * ratio)
            )
        )

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=95
    )

    return output.getvalue()


def render_document_pages(filename: str, content: bytes):
    """
    Converts JPG/PNG/PDF into page images.

    Returns:
    [
        {
            "page_number": 1,
            "image": <PIL Image>
        }
    ]
    """

    pages = []

    if filename.lower().endswith(".pdf"):

        pdf = fitz.open(
            stream=content,
            filetype="pdf"
        )

        for index, page in enumerate(pdf):

            pix = page.get_pixmap(
                matrix=fitz.Matrix(2.5, 2.5),
                alpha=False
            )

            image_bytes = pix.tobytes("png")

            image = Image.open(
                io.BytesIO(image_bytes)
            ).convert("RGB")

            pages.append(
                {
                    "page_number": index + 1,
                    "image": image
                }
            )

        pdf.close()

    else:

        image = Image.open(
            io.BytesIO(content)
        )

        image = ImageOps.exif_transpose(
            image
        ).convert("RGB")

        pages.append(
            {
                "page_number": 1,
                "image": image
            }
        )

    return pages


def create_table_crops(image: Image.Image):
    """
    Creates two enlarged invoice table views:

    1. Main table
    2. Numeric columns
    """

    image = ImageOps.exif_transpose(
        image
    ).convert("RGB")

    width, height = image.size

    # Main invoice table
    table = image.crop(
        (
            int(width * 0.02),
            int(height * 0.28),
            int(width * 0.99),
            int(height * 0.72)
        )
    )

    # Numeric side of invoice table
    numeric = image.crop(
        (
            int(width * 0.43),
            int(height * 0.28),
            int(width * 0.99),
            int(height * 0.72)
        )
    )

    crops = []

    for crop in [table, numeric]:

        crop = crop.resize(
            (
                crop.width * 2,
                crop.height * 2
            )
        )

        crop = ImageEnhance.Contrast(
            crop
        ).enhance(1.20)

        crop = ImageEnhance.Sharpness(
            crop
        ).enhance(1.50)

        crops.append(crop)

    return crops


def encode_image(image: Image.Image):

    image_bytes = image_to_jpeg(image)

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return f"data:image/jpeg;base64,{encoded}"


# =========================================================
# NORMALIZATION
# =========================================================

def clean_confidence(value):

    if value is None:
        return None

    try:

        value = float(value)

        if value < 0:
            value = 0

        if value > 1:
            value = 1

        return value

    except Exception:
        return None


def normalize_evidence(evidence):

    if not isinstance(evidence, list):
        return []

    result = []

    for item in evidence:

        if not isinstance(item, dict):
            continue

        source_text = item.get(
            "source_text"
        )

        if not source_text:
            continue

        source_text = str(
            source_text
        ).strip()

        if not source_text:
            continue

        page_number = item.get(
            "page_number"
        )

        try:

            if page_number is not None:
                page_number = int(page_number)

        except Exception:

            page_number = None

        result.append(
            {
                "source_text": source_text,
                "page_number": page_number
            }
        )

    return result


def normalize_field(field):

    if field is None:

        return {
            "value": None,
            "evidence": [],
            "confidence": None
        }

    if not isinstance(field, dict):

        return {
            "value": str(field),
            "evidence": [],
            "confidence": None
        }

    value = field.get(
        "value"
    )

    if value is not None:
        value = str(value).strip()

    return {
        "value": value,
        "evidence": normalize_evidence(
            field.get(
                "evidence",
                []
            )
        ),
        "confidence": clean_confidence(
            field.get(
                "confidence"
            )
        )
    }


def normalize_result(data, document_type):

    if not isinstance(data, dict):
        data = {}

    result = {
        "document_type": document_type,
        "fields": {},
        "line_items": [],
        "extraction_notes": []
    }

    # -----------------------------------------------------
    # FIELDS
    # -----------------------------------------------------

    fields = data.get(
        "fields",
        {}
    )

    if isinstance(fields, dict):

        for name, value in fields.items():

            result["fields"][name] = normalize_field(
                value
            )

    # -----------------------------------------------------
    # LINE ITEMS
    # -----------------------------------------------------

    line_items = data.get(
        "line_items",
        []
    )

    if isinstance(line_items, list):

        for item in line_items:

            if not isinstance(item, dict):
                continue

            normalized_item = {}

            for key in [
                "description",
                "quantity",
                "unit_price",
                "line_total",
                "tax_rate",
                "discount"
            ]:

                normalized_item[key] = normalize_field(
                    item.get(key)
                )

            result["line_items"].append(
                normalized_item
            )

    # -----------------------------------------------------
    # NOTES
    # -----------------------------------------------------

    notes = data.get(
        "extraction_notes",
        []
    )

    if isinstance(notes, list):

        result["extraction_notes"] = [
            str(note)
            for note in notes
            if note
        ]

    return result


# =========================================================
# INVOICE PROMPT
# =========================================================

INVOICE_PROMPT = """
You are a financial document extraction system.

Carefully inspect the ORIGINAL INVOICE IMAGE and the enlarged
table views provided.

DO NOT calculate or guess values.

Read exactly what is visibly printed on the invoice.

Return ONLY valid JSON.

Required JSON structure:

{
  "document_type": "invoice",

  "fields": {

    "invoice_number": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "invoice_date": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "vendor_name": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "customer_name": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "currency": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "subtotal": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "tax_amount": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "discount": {
      "value": null,
      "evidence": [],
      "confidence": null
    },

    "total_amount": {
      "value": null,
      "evidence": [],
      "confidence": null
    }
  },

  "line_items": [
    {
      "description": {
        "value": null,
        "evidence": [],
        "confidence": null
      },

      "quantity": {
        "value": null,
        "evidence": [],
        "confidence": null
      },

      "unit_price": {
        "value": null,
        "evidence": [],
        "confidence": null
      },

      "line_total": {
        "value": null,
        "evidence": [],
        "confidence": null
      },

      "tax_rate": {
        "value": null,
        "evidence": [],
        "confidence": null
      },

      "discount": {
        "value": null,
        "evidence": [],
        "confidence": null
      }
    }
  ],

  "extraction_notes": []
}


EXTREMELY IMPORTANT TABLE RULES

The invoice may contain columns similar to:

Sl No
Description of Goods
HSN/SAC
Quantity
Rate (Incl. of Tax)
Rate
per
Disc. %
Amount


COLUMN MAPPING:

1. quantity

Use ONLY the value under the Quantity column.

Return ONLY the numeric quantity.

Example:

Printed:
48 PCS

Return:
"48"

NOT:
"48 PCS"


2. unit_price

Use ONLY the value under the SECOND "Rate" column.

This is the tax-exclusive Rate.

DO NOT use:

Rate (Incl. of Tax)

DO NOT calculate a rate yourself.

DO NOT divide amount by quantity.

Read the printed value directly from the tax-exclusive
Rate column.


3. discount

Use ONLY the value physically printed under "Disc. %"
for that SAME ROW.

Example:

99 %

Return:

"99"

If the cell is empty:

"value": null


VERY IMPORTANT:

GST 9%, CGST 9%, SGST 9%, tax percentages printed
below the product table ARE NOT DISCOUNTS.

Never put GST percentages into the discount field.


4. line_total

Use the EXACT value printed under the final "Amount"
column.

DO NOT calculate:

quantity * rate

DO NOT reconstruct the amount.

Read the printed Amount cell exactly.


5. tax_rate

Only fill this if a tax rate is explicitly associated with
that individual line item.

Do NOT automatically copy GST shown in the invoice summary
into every product row.

If not explicitly linked to that row:

"value": null


6. descriptions

Product descriptions may wrap across multiple lines.

Combine all visible description lines belonging to the same
serial number into ONE description.

Do not accidentally attach the next product's description.


7. line count

Count the visible serial numbers in the first column.

Create exactly one line_items object for each visible product row.

Do not merge products.

Do not omit products.


INVOICE TOTALS

subtotal:

Use the taxable/subtotal value BEFORE CGST/SGST/GST.

tax_amount:

If CGST and SGST are separately printed,
return their COMBINED tax amount.

You MAY add separately printed tax components for this field.

Do not confuse one GST component with total tax.

total_amount:

Use the final invoice total / amount chargeable.

discount:

Only use invoice-level discount if one is explicitly printed.


EVIDENCE

Whenever practical, provide the exact visible text which
supports the extracted value.

Example:

{
  "value": "52.08",
  "evidence": [
    {
      "source_text": "52.08",
      "page_number": 1
    }
  ],
  "confidence": 0.98
}

Never invent evidence text.


CONFIDENCE

0.95 - 1.0:
clearly visible

0.75 - 0.94:
readable but slightly unclear

below 0.75:
uncertain

If a value cannot be reliably read:

"value": null

Do NOT guess.

Most importantly:

DO NOT change values merely to make arithmetic correct.

Extraction must come from the document image.
"""


# =========================================================
# GENERIC FINANCIAL DOCUMENT PROMPT
# =========================================================

def build_financial_prompt(
    document_type,
    text
):

    return f"""
You are a financial document extraction system.

Document type:
{document_type}

Your task is to extract ALL financial information visible
in the document image.

Use the OCR text only as supporting context.

If OCR conflicts with the image,
TRUST THE IMAGE.

OCR:

{text[:12000]}


=========================================================
GENERAL EXTRACTION RULES
=========================================================

Return ONLY valid JSON.

These documents may contain multiple comparative periods,
such as:

As at 31-Mar-17 | As at 31-Mar-16

OR

2025 | 2024

OR

Current Year | Previous Year


You MUST preserve EVERY visible period.

DO NOT discard the second/previous/comparative period.

For financial statements, each period must be represented
as a SEPARATE FIELD.


Example:

Capital    5,125,091    5,056,373


Return:

"fields": {{

    "Capital | 31-Mar-17": {{
        "value": "5,125,091",
        "evidence": [
            {{
                "source_text":
                "Capital 5,125,091 5,056,373",
                "page_number": 1
            }}
        ],
        "confidence": 0.95
    }},

    "Capital | 31-Mar-16": {{
        "value": "5,056,373",
        "evidence": [
            {{
                "source_text":
                "Capital 5,125,091 5,056,373",
                "page_number": 1
            }}
        ],
        "confidence": 0.95
    }}

}}


The exact period labels must come from the document.

If the document contains only one period,
create only one field.


IMPORTANT RULES:

1. Extract values exactly as printed.

2. DO NOT calculate missing values.

3. DO NOT modify values to make accounting equations balance.

4. DO NOT guess.

5. Preserve commas and decimal values where visible.

6. Parentheses indicate negative values.

Example:

(1,250)

must be extracted as:

"-1,250"

7. Extract ALL visible financial line items.

8. Extract totals separately.

9. Extract subtotals separately.

10. Preserve the original printed field names as much as possible.

11. Do not merge different financial fields.

12. Do not omit comparative periods.

13. For each value, provide evidence containing the visible
source text and page number whenever practical.

14. Confidence:

0.95 - 1.0 = clearly visible

0.75 - 0.94 = readable but slightly unclear

below 0.75 = uncertain

15. If a value cannot be reliably read:

"value": null

DO NOT guess.

16. If a financial statement explicitly prints "-" or "—"
for a numeric field, treat it as zero and return:

"value": "0"

Do NOT omit the field.

17. Preserve negative values represented using parentheses.

18. Extract every visible value even if it is not needed
for the validation rules.


=========================================================
BALANCE SHEET
=========================================================

For balance sheets, extract ALL visible items under:

CAPITAL AND LIABILITIES

and

ASSETS

including:

- Capital
- Reserves and surplus
- Minority interest
- Deposits
- Borrowings
- Other liabilities and provisions
- Total liabilities
- Cash and balances with Reserve Bank
- Balances with banks
- Investments
- Advances
- Fixed assets
- Other assets
- Total assets
- Contingent liabilities
- Bills for collection

Also extract any additional visible balance-sheet items.

Preserve each comparative period separately.


=========================================================
PROFIT AND LOSS
=========================================================

For profit and loss statements, extract ALL visible:

- Income
- Expenditure
- Profit/loss
- Appropriation
- Comparative period values

Examples include:

- Interest earned
- Other income
- Total income
- Interest expended
- Operating expenses
- Provisions and contingencies
- Total expenditure
- Profit before minority interest
- Minority interest
- Consolidated net profit
- Appropriations
- Profit carried forward

Also extract any additional visible items.

Preserve each comparative period separately.


=========================================================
CASH FLOW STATEMENT
=========================================================

For cash flow statements, you MUST extract ALL visible
cash-flow line items.

At minimum, extract the following fields whenever they
are visible:


OPERATING ACTIVITIES

- Consolidated profit before income tax
- Net cash flow (used in) / from operating activities


INVESTING ACTIVITIES

- Purchase of fixed assets
- Proceeds from sale of fixed assets
- Investment in subsidiaries and / or joint ventures
- Net cash used in investing activities


FINANCING ACTIVITIES

- Increase in minority interest
- Money received on exercise of stock options by employees
- Increase / (decrease) in borrowings
- Redemption of subordinated debt
- Dividend paid during the year
- Tax on dividend
- Net cash generated from financing activities


OTHER CASH FLOW ADJUSTMENTS

VERY IMPORTANT:

You MUST extract this field if visible:

"Effect of exchange fluctuation on translation reserve"


You MUST NOT omit it merely because it appears
after the financing activities section.

Also extract:

"Cash and cash equivalents on amalgamation"

If the document explicitly shows "-" or "—" for this
field, return:

"value": "0"

Do NOT omit the field.


NET CASH MOVEMENT

- Net increase / (decrease) in cash and cash equivalents


OPENING CASH

- Cash and cash equivalents as at April 1st


CLOSING CASH

- Cash and cash equivalents as at March 31st


CRITICAL CASH FLOW RULE

For EACH comparative period, the following fields must
be independently extracted if visible:

1. Net cash flow (used in) / from operating activities
2. Net cash used in investing activities
3. Net cash generated from financing activities
4. Effect of exchange fluctuation on translation reserve
5. Cash and cash equivalents on amalgamation
6. Net increase / (decrease) in cash and cash equivalents
7. Cash and cash equivalents as at April 1st
8. Cash and cash equivalents as at March 31st


Example:

If the document shows:

Net cash generated from financing activities
(58,929,743) 378,151,341

Effect of exchange fluctuation on translation reserve
(282,622) 282,433

Cash and cash equivalents on amalgamation
295,617 -

Net increase / (decrease) in cash and cash equivalents
102,422,381 25,424,601


You MUST return separate fields:

"Net cash generated from financing activities | 31-Mar-17"

"Net cash generated from financing activities | 31-Mar-16"

"Effect of exchange fluctuation on translation reserve | 31-Mar-17"

"Effect of exchange fluctuation on translation reserve | 31-Mar-16"

"Cash and cash equivalents on amalgamation | 31-Mar-17"

"Cash and cash equivalents on amalgamation | 31-Mar-16"

"Net increase / (decrease) in cash and cash equivalents | 31-Mar-17"

"Net increase / (decrease) in cash and cash equivalents | 31-Mar-16"


The "-" for the 31-Mar-16 amalgamation value MUST become:

"value": "0"


Do NOT calculate these values.

Read them directly from the document.


Also extract any additional visible cash-flow items.


=========================================================
EVIDENCE
=========================================================

For every extracted field, provide evidence whenever practical.

Evidence should contain:

- Exact or near-exact visible source text
- Correct page number

Example:

{{
    "value": "-282,622",
    "evidence": [
        {{
            "source_text":
            "Effect of exchange fluctuation on translation reserve (282,622) 282,433",
            "page_number": 2
        }}
    ],
    "confidence": 0.98
}}


Never invent evidence.

Do not use evidence from another field.


=========================================================
OUTPUT FORMAT
=========================================================

Use exactly this general structure:

{{
    "document_type": "{document_type}",

    "fields": {{

        "FIELD NAME | PERIOD": {{
            "value": "VALUE",
            "evidence": [
                {{
                    "source_text": "EXACT VISIBLE TEXT",
                    "page_number": 1
                }}
            ],
            "confidence": 0.95
        }}

    }},

    "line_items": [],

    "extraction_notes": []
}}


If there is no comparative period, use:

"FIELD NAME": {{
    "value": "VALUE",
    "evidence": [],
    "confidence": 0.95
}}


Do not invent a period.


=========================================================
FINAL INSTRUCTION
=========================================================

EXTRACT WHAT IS PRINTED.

DO NOT CALCULATE.

DO NOT GUESS.

DO NOT DROP COMPARATIVE PERIODS.

DO NOT OMIT VISIBLE CASH FLOW ADJUSTMENTS.

For Cash Flow Statements especially,
DO NOT OMIT:

- Effect of exchange fluctuation on translation reserve
- Cash and cash equivalents on amalgamation

even when they appear on a separate line after
financing activities.
"""


# =========================================================
# OPENAI VISION - INVOICE
# =========================================================

def call_invoice_vision(pages):

    content = [
        {
            "type": "text",
            "text": INVOICE_PROMPT
        }
    ]

    for page in pages:

        page_number = page["page_number"]
        image = page["image"]

        # -------------------------------------------------
        # ORIGINAL PAGE
        # -------------------------------------------------

        content.append(
            {
                "type": "text",
                "text":
                    f"PAGE {page_number} - ORIGINAL FULL PAGE"
            }
        )

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": encode_image(image),
                    "detail": "high"
                }
            }
        )

        # -------------------------------------------------
        # TABLE CROPS
        # -------------------------------------------------

        table_crop, numeric_crop = create_table_crops(
            image
        )

        content.append(
            {
                "type": "text",
                "text":
                    f"PAGE {page_number} - ENLARGED PRODUCT TABLE"
            }
        )

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": encode_image(table_crop),
                    "detail": "high"
                }
            }
        )

        content.append(
            {
                "type": "text",
                "text":
                    (
                        f"PAGE {page_number} - "
                        "ENLARGED NUMERIC COLUMNS. "
                        "Pay special attention to Quantity, "
                        "Rate (Incl. of Tax), Rate, Disc. %, Amount."
                    )
            }
        )

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": encode_image(numeric_crop),
                    "detail": "high"
                }
            }
        )

    response = client.chat.completions.create(

        model=MODEL,

        temperature=0,

        response_format={
            "type": "json_object"
        },

        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    return json.loads(
        response.choices[0].message.content
    )


# =========================================================
# OPENAI VISION - FINANCIAL DOCUMENTS
# =========================================================

def call_financial_vision(
    document_type,
    pages,
    text
):

    content = [
        {
            "type": "text",
            "text": build_financial_prompt(
                document_type,
                text
            )
        }
    ]

    for page in pages:

        content.append(
            {
                "type": "text",
                "text": f"PAGE {page['page_number']}"
            }
        )

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": encode_image(
                        page["image"]
                    ),
                    "detail": "high"
                }
            }
        )

    response = client.chat.completions.create(

        model=MODEL,

        temperature=0,

        response_format={
            "type": "json_object"
        },

        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    return json.loads(
        response.choices[0].message.content
    )


# =========================================================
# MAIN EXTRACTION FUNCTION
# =========================================================

def extract_fields(
    document_type,
    text,
    content,
    filename
):

    try:

        # -------------------------------------------------
        # API KEY CHECK
        # -------------------------------------------------

        if not os.getenv(
            "OPENAI_API_KEY"
        ):

            return {
                "success": False,
                "error":
                    "OPENAI_API_KEY is missing"
            }

        # -------------------------------------------------
        # RENDER DOCUMENT
        # -------------------------------------------------

        pages = render_document_pages(
            filename,
            content
        )

        if not pages:

            return {
                "success": False,
                "error":
                    "Could not create document images."
            }

        # -------------------------------------------------
        # INVOICE
        # -------------------------------------------------

        if document_type == "invoice":

            raw_result = call_invoice_vision(
                pages
            )

        # -------------------------------------------------
        # OTHER FINANCIAL DOCUMENTS
        # -------------------------------------------------

        else:

            raw_result = call_financial_vision(
                document_type,
                pages,
                text
            )

        # -------------------------------------------------
        # NORMALIZE
        # -------------------------------------------------

        normalized = normalize_result(
            raw_result,
            document_type
        )

        # -------------------------------------------------
        # PYDANTIC VALIDATION
        # -------------------------------------------------

        validated = ExtractionResult.model_validate(
            normalized
        )

        # -------------------------------------------------
        # FINAL RESULT
        # -------------------------------------------------

        return {
            "success": True,
            "data": validated.model_dump()
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
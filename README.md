# Intelligent Document Extraction, Validation & API Platform

An AI-powered document intelligence platform for extracting, structuring, and validating financial information from invoices and financial statements.

## Live Application

- Frontend: https://ai-document-intelligence-w925.onrender.com/
- Backend API: https://ai-document-intelligence-w925.onrender.com/api/v1
- Swagger / OpenAPI: https://ai-document-intelligence-w925.onrender.com/docs
- Health Check: https://ai-document-intelligence-w925.onrender.com/api/v1/health
- GitHub: https://github.com/Sushmitha-Kumar7/AI-Document-Intelligence

## Solution Overview

The system accepts financial documents in PDF, JPG, and PNG formats and processes them through the following pipeline:

Upload → File Validation → OCR/Text Extraction → AI Extraction → Structured JSON → Financial Validation → Database Storage → Dashboard

Supported document types:

- Invoice
- Balance Sheet
- Profit & Loss Statement
- Cash Flow Statement

The system extracts meaningful document fields and financial line items and performs deterministic financial validation checks.

## Key Features

- PDF, JPG and PNG document support
- File type and integrity validation
- Maximum 3-page document validation
- Native PDF text extraction
- OCR for scanned/image-based documents
- AI-powered structured information extraction
- Invoice line-item extraction
- Financial statement extraction
- Deterministic financial validation
- PASS / FAIL / NOT_APPLICABLE validation status
- Database-backed document history
- Document preview from dashboard
- Raw JSON result view
- REST API with Swagger/OpenAPI documentation
- Deployed frontend and backend

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic

### Document Processing

- PyMuPDF
- Tesseract OCR
- Pillow

### AI

- OpenAI API
- GPT-4o

### Frontend

- HTML
- CSS
- JavaScript

### Deployment

- Docker
- Render

## Architecture

```text
                         User
                           |
                           v
                  Frontend Dashboard
                           |
                           v
                     FastAPI API
                           |
                           v
                   File Validation
                           |
                           v
                OCR / Text Extraction
                           |
                           v
                    AI Extraction
                       GPT-4o
                           |
                           v
                   Structured JSON
                           |
                           v
                 Financial Validation
                           |
                           v
                    SQLite Database
                           |
                           v
                  Dashboard / Results
```

## Project Structure

```text
AI-Document-Intelligence/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── documents.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   └── document.py
│   │   ├── schemas/
│   │   │   ├── document.py
│   │   │   └── extraction.py
│   │   ├── services/
│   │   │   ├── document_validation_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── financial_validation_service.py
│   │   │   └── document_service.py
│   │   └── repositories/
│   │       └── document_repository.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── result.html
│   ├── script.js
│   ├── result.js
│   └── style.css
│
├── docs/
├── sample_outputs/
├── tests/
├── .env.example
├── .gitignore
├── Dockerfile
└── README.md
```

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Sushmitha-Kumar7/AI-Document-Intelligence.git
cd AI-Document-Intelligence
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file inside the `backend` directory:

```env
OPENAI_API_KEY=your_api_key_here
```

The API key must not be committed to GitHub.

### 6. Start the Application

Open a terminal inside the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000/
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### Process Document

```text
POST /api/v1/documents/process
```

Multipart form data:

```text
file = uploaded document
document_type = invoice
```

Supported document types:

```text
invoice
balance_sheet
profit_and_loss
cash_flow_statement
```

Example using cURL:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents/process" \
  -F "file=@sample_invoice.pdf" \
  -F "document_type=invoice"
```

### List Processed Documents

```text
GET /api/v1/documents
```

Returns the processed document history stored by the application.

### Document Lookup

```text
GET /api/v1/documents/{document_name}
```

### Open Stored Document

```text
GET /api/v1/documents/file/{document_id}
```

### Health Check

```text
GET /api/v1/health
```

Example response:

```json
{
  "status": "healthy",
  "service": "document-intelligence-api"
}
```

## Document Extraction

The system extracts meaningful information available in the uploaded financial document.

### Invoice

The system extracts:

- Invoice number
- Invoice date
- Vendor name
- Customer name
- Currency
- Subtotal
- Tax amount
- Discount
- Total amount
- Line items
- Quantity
- Unit price
- Line total

### Balance Sheet

The system extracts:

- Statement periods
- Currency
- Assets
- Liabilities
- Equity
- Other visible financial line items

### Profit & Loss Statement

The system extracts:

- Statement periods
- Currency
- Revenue
- Cost of goods sold
- Gross profit
- Operating expenses
- Operating profit
- Tax
- Net profit
- Other visible income and expense items

### Cash Flow Statement

The system extracts:

- Statement periods
- Currency
- Operating activities
- Investing activities
- Financing activities
- Opening cash
- Net change in cash
- Closing cash
- Other visible line items

Missing values are returned as `null` rather than being invented.

## OCR and Document Processing

Native PDF text is extracted using PyMuPDF.

For scanned PDFs and image-based documents, Tesseract OCR is used.

The OCR implementation supports both Windows and Linux environments, including the deployed Render environment.

## AI Extraction

OpenAI GPT-4o is used to convert document content into structured JSON.

The extraction process is designed to:

- Preserve values from the source document
- Extract relevant financial information
- Handle missing values using `null`
- Extract invoice line items
- Provide source evidence where available

## Financial Validation

After AI extraction, deterministic financial validation checks are performed.

### Invoice Validation

The system checks applicable financial relationships such as:

- Quantity × Unit Price ≈ Line Total
- Line totals reconcile with subtotal where applicable
- Subtotal + Tax ≈ Total
- Discounts are considered when available

### Balance Sheet Validation

The system checks:

- Assets ≈ Liabilities + Equity
- Component totals where sufficient values are available

### Profit & Loss Validation

The system checks applicable relationships such as:

- Income components reconcile with total income
- Expense components reconcile with total expenditure
- Income and expenditure reconcile with profit
- Additional profit/appropriation calculations where applicable

### Cash Flow Validation

The system checks:

- Operating + Investing + Financing + FX changes reconcile with net cash change
- Opening cash + net change reconcile with closing cash where applicable

Each validation result contains:

- Check/formula
- Input values
- Calculated value
- Reported value
- Variance
- Status

Possible validation statuses:

```text
PASS
FAIL
NOT_APPLICABLE
```

A validation check is marked `NOT_APPLICABLE` when the required source fields are unavailable rather than assuming or inventing values.

## Database and Persistence

SQLite with SQLAlchemy is used to store processed document metadata.

Stored information includes:

- Document ID
- Original filename
- Document type
- Stored file path
- Processing status
- Upload timestamp

The dashboard retrieves processed document history through the API.

## Deployment

The application is containerized using Docker and deployed on Render.

The Docker image installs Tesseract OCR for Linux-based deployment.

The frontend and backend are served through the same deployed application.

## Testing

The project includes tests for:

- File validation
- Financial validation
- API processing flow
- Supported document types
- Invalid document scenarios

The application was also tested using:

- Invoice documents
- Balance Sheet documents
- Profit & Loss documents
- Cash Flow documents
- Image-based documents
- Financial validation scenarios

## Known Limitations

- SQLite is suitable for this assessment but should be replaced with PostgreSQL or another production database for larger deployments.
- Render free-tier storage is ephemeral. Production deployment should use persistent database and object storage.
- OCR accuracy depends on document image quality.
- AI extraction accuracy may vary for complex or poor-quality documents.
- The current implementation supports documents up to 3 pages as required by the case study.

## Production Improvements

For a production deployment, the following improvements can be considered:

- PostgreSQL for production database storage
- S3-compatible object storage for uploaded documents
- Authentication and authorization
- Background processing for large documents
- Rate limiting
- Improved monitoring and logging
- More extensive automated testing
- OCR preprocessing for difficult scans
- Model evaluation and confidence monitoring
- Human review workflow for low-confidence extractions

## AI / Tool Usage Declaration

ChatGPT was used during development for:

- Code generation assistance
- Debugging
- Error analysis
- API implementation guidance
- Documentation assistance
- Improving extraction prompts and logic

The generated suggestions were reviewed, modified, implemented, and tested during development.

## License

This project was developed as part of an AI Engineer internship technical case study.
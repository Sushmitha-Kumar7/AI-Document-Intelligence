from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_text: Optional[str] = None
    page_number: Optional[int] = None


class ExtractedField(BaseModel):
    value: Optional[Any] = None
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: Optional[float] = None


class InvoiceLineItem(BaseModel):
    description: Optional[ExtractedField] = None
    quantity: Optional[ExtractedField] = None
    unit_price: Optional[ExtractedField] = None
    line_total: Optional[ExtractedField] = None
    tax_rate: Optional[ExtractedField] = None
    discount: Optional[ExtractedField] = None


class ExtractionResult(BaseModel):
    document_type: str
    fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    extraction_notes: List[str] = Field(default_factory=list)
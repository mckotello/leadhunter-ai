import enum
import re
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl


class NeedType(str, enum.Enum):
    WEBSITE = "website"
    ECOMMERCE = "ecommerce"
    PERSONAL_ACCOUNT = "personal_account"
    AUTOMATION = "automation"
    CRM_INTEGRATION = "crm_integration"
    TELEGRAM_BOT = "telegram_bot"
    AI = "ai"
    OTHER = "other"


class SearchCreate(BaseModel):
    niche: str = Field(..., min_length=1, max_length=256)
    region: str = Field(..., min_length=1, max_length=256)
    keywords: str = Field(default="", max_length=512)
    need_type: NeedType = NeedType.OTHER
    limit: int = Field(default=20, ge=1, le=200)


class SearchTaskRead(BaseModel):
    id: int
    query: str
    filters: dict | None
    status: str
    total_found: int
    total_processed: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CompanyRead(BaseModel):
    id: int
    name: str
    website: str | None
    industry: str | None
    description: str | None
    region: str | None
    phone: str | None
    email: str | None
    social_links: dict | None

    model_config = {"from_attributes": True}


class SourceRead(BaseModel):
    id: int
    source_url: str
    source_type: str
    collected_at: datetime
    extracted_data: dict | None

    model_config = {"from_attributes": True}


class LeadNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class LeadNoteRead(BaseModel):
    id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedOfferRead(BaseModel):
    id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    status: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)


class LeadListItem(BaseModel):
    id: int
    company_id: int
    company_name: str
    industry: str | None
    primary_need: str | None
    score: int | None
    temperature: str | None
    status: str

    model_config = {"from_attributes": True}


class LeadDetail(BaseModel):
    id: int
    score: int | None
    temperature: str | None
    status: str
    detected_needs: list | None
    recommended_services: list | None
    ai_analysis: dict | None
    score_explanation: str | None
    confidence: float | None
    company: CompanyRead
    sources: list[SourceRead]
    notes: list[LeadNoteRead]
    offers: list[GeneratedOfferRead]
    created_at: datetime
    updated_at: datetime


class DashboardStats(BaseModel):
    total_companies: int
    analyzed_leads: int
    hot_leads: int
    warm_leads: int
    search_tasks: int
    temperature_distribution: dict[str, int]
    recent_companies: list[CompanyRead]


class FactReference(BaseModel):
    fact: str
    source_url: str | None = None


class AIAnalysisResult(BaseModel):
    business_summary: str
    identified_issues: list[str]
    assumed_needs: list[str]
    recommended_service: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[FactReference]


class ScoringResult(BaseModel):
    score: int = Field(ge=0, le=100)
    temperature: str
    explanation: str
    breakdown: dict[str, int]


class OfferDraft(BaseModel):
    introduction: str
    business_problem: str
    proposed_solution: str
    expected_benefit: str
    first_message_draft: str


def normalize_company_name(name: str) -> str:
    cleaned = re.sub(r"[«»\"'""]", "", name.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^(ооо|оао|зао|ип|ao|llc)\s+", "", cleaned)
    return cleaned


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None

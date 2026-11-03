import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(str, enum.Enum):
    NEW = "new"
    ANALYZED = "analyzed"
    QUALIFIED = "qualified"
    IN_PROGRESS = "in_progress"
    CONTACTED = "contacted"
    REJECTED = "rejected"
    CLIENT = "client"


class LeadTemperature(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    POTENTIAL = "potential"
    LOW = "low"


class SearchTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    website: Mapped[str | None] = mapped_column(String(2048), index=True)
    industry: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(256))
    social_links: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    normalized_name: Mapped[str | None] = mapped_column(String(512), index=True)
    domain: Mapped[str | None] = mapped_column(String(256), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    leads: Mapped[list["Lead"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    sources: Mapped[list["Source"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    score: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[LeadTemperature | None] = mapped_column(Enum(LeadTemperature))
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.NEW)
    detected_needs: Mapped[list | None] = mapped_column(JSONB, default=list)
    recommended_services: Mapped[list | None] = mapped_column(JSONB, default=list)
    ai_analysis: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    score_explanation: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="leads")
    notes: Mapped[list["LeadNote"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    offers: Mapped[list["GeneratedOffer"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    source_type: Mapped[str] = mapped_column(String(64))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    company: Mapped["Company"] = relationship(back_populates="sources")


class SearchTask(Base):
    __tablename__ = "search_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    status: Mapped[SearchTaskStatus] = mapped_column(Enum(SearchTaskStatus), default=SearchTaskStatus.PENDING)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    total_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadNote(Base):
    __tablename__ = "lead_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="notes")


class GeneratedOffer(Base):
    __tablename__ = "generated_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="offers")

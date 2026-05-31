from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Column, JSON

class JobBase(SQLModel):
    title: str = Field(index=True)
    company_name: str = Field(index=True)
    location: str = Field(index=True)
    
    # Niche criteria flags
    is_remote: bool = Field(default=False, index=True)
    is_new_grad: bool = Field(default=False, index=True)
    visa_sponsorship: bool = Field(default=False, index=True)
    
    employment_type: str = Field(default="Full-time")
    experience_level: Optional[str] = Field(default=None, index=True)
    
    # Metadata
    source: str = Field(index=True)                  # e.g., "greenhouse:stripe"
    source_url: str = Field(index=True)             # Original URL crawled
    canonical_url: Optional[str] = Field(default=None, index=True) # Cleaned unique URL
    
    published_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str = Field(index=True)            # SHA-256 hash of title & content

class Job(JobBase, table=True):
    __tablename__ = "jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True, index=True)
    score: float = Field(default=0.0)                # Scoring for matching logic
    
    # Use SQLAlchemy general JSON to preserve SQLite portability while backing PG JSON/JSONB
    raw_details: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Self-referential deduplication hierarchy
    parent_job_id: Optional[int] = Field(default=None, foreign_key="jobs.id", index=True)

class CrawlHistory(SQLModel, table=True):
    __tablename__ = "crawl_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str = Field(index=True)
    status: str = Field(index=True)                 # "running", "success", "failed"
    jobs_discovered: int = Field(default=0)
    jobs_added: int = Field(default=0)
    jobs_deduplicated: int = Field(default=0)
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

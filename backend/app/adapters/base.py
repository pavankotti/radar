from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class RawJobPayload(BaseModel):
    """Temporary schema holding raw scraped data before normalization."""
    title: str
    company_name: str
    location: str
    description_html: str
    source_url: str
    raw_payload: dict
    published_at: Optional[datetime] = None

class NormalizedJob(BaseModel):
    """Normalized schema representing a single structured job post."""
    title: str
    company_name: str
    location: str
    is_remote: bool
    is_new_grad: bool
    visa_sponsorship: bool
    employment_type: str = "Full-time"
    experience_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: str
    source_url: str
    canonical_url: str
    published_at: Optional[datetime] = None
    raw_payload: dict
    content_hash: str

class BaseAdapter(ABC):
    """
    Abstract Base Class representing a single target data source.
    """
    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique key identifying the source, e.g., 'greenhouse:stripe'"""
        pass

    @abstractmethod
    async def discover(self) -> List[str]:
        """
        Phase 1: Discover available job postings.
        Returns a list of unique identifiers or deep links.
        """
        pass

    @abstractmethod
    async def fetch_detail(self, job_identifier: str) -> RawJobPayload:
        """
        Phase 2: Scrape or retrieve detailed payload for a single job post.
        """
        pass

    @abstractmethod
    def normalize(self, raw: RawJobPayload) -> NormalizedJob:
        """
        Phase 3: Clean text, analyze keywords, tag skills, and yield NormalizedJob.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Returns True if the source target is active and reachable.
        """
        pass

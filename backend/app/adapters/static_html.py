import hashlib
from bs4 import BeautifulSoup
import httpx
from typing import List, Optional
from datetime import datetime
from app.adapters.base import BaseAdapter, RawJobPayload, NormalizedJob

class StaticHtmlAdapter(BaseAdapter):
    """
    Ingestion Adapter for static HTML corporate career sites.
    """
    def __init__(self, company_name: str, career_url: str, job_link_selector: str = "a[href*='/jobs/']"):
        self.company_name = company_name.strip()
        self.career_url = career_url.strip()
        self.selector = job_link_selector
        self._client = httpx.AsyncClient(
            timeout=20.0,
            headers={
                "User-Agent": "JobRadarIntelligenceEngine/1.0 (Portfolio Project; pavan)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            },
            follow_redirects=True
        )

    @property
    def source_id(self) -> str:
        return f"static:{self.company_name.lower().replace(' ', '_')}"

    async def discover(self) -> List[str]:
        """
        Parses career portal to locate listing links using selector strategies.
        """
        response = await self._client.get(self.career_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        discovered_links = []
        
        # Apply css selectors
        for anchor in soup.select(self.selector):
            href = anchor.get("href")
            if not href:
                continue
                
            # Build full absolute URL if relative
            if href.startswith("/"):
                # Parse host
                base_parts = self.career_url.split("/")
                host = "/".join(base_parts[:3]) # e.g. https://example.com
                full_url = f"{host}{href}"
            elif not href.startswith("http"):
                full_url = f"{self.career_url.rstrip('/')}/{href}"
            else:
                full_url = href
                
            discovered_links.append(full_url)
            
        return list(set(discovered_links))

    async def fetch_detail(self, job_url: str) -> RawJobPayload:
        """
        Retrieves job detail page and extracts structural content blocks.
        """
        response = await self._client.get(job_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Heuristics to find title
        title_element = (
            soup.select_one("h1") 
            or soup.select_one(".job-title") 
            or soup.select_one(".title")
        )
        title = title_element.text.strip() if title_element else "Unknown Role"
        
        # Heuristics to find description text block
        desc_element = (
            soup.select_one(".job-description") 
            or soup.select_one(".description") 
            or soup.select_one("#job-desc")
            or soup.select_one("div.content")
            or soup.body
        )
        description_html = str(desc_element) if desc_element else ""
        
        # Heuristics to extract location
        location_element = (
            soup.select_one(".location")
            or soup.select_one(".job-location")
            or soup.select_one("[class*='location']")
        )
        location = location_element.text.strip() if location_element else "HQ / Remote"

        return RawJobPayload(
            title=title,
            company_name=self.company_name,
            location=location,
            description_html=description_html,
            source_url=job_url,
            raw_payload={"html": response.text}
        )

    def normalize(self, raw: RawJobPayload) -> NormalizedJob:
        """
        Standardizes scraped HTML fields into the clean Canonical shape.
        """
        title_lower = raw.title.lower()
        desc_lower = raw.description_html.lower()
        location_lower = raw.location.lower()
        
        # Flag remote indicators
        is_remote = "remote" in title_lower or "remote" in location_lower or "remote" in desc_lower
        
        # Flag new grad indicators
        is_new_grad = any(k in title_lower for k in ["new grad", "entry", "intern", "junior", "associate"])
        
        # Flag sponsorship indicators
        visa_sponsorship = any(v in desc_lower for v in ["visa sponsorship", "h-1b", "h1b", "sponsorship", "opt"])
        
        # Extract tags
        tech_keywords = ["python", "javascript", "typescript", "go", "react", "nextjs", "node", "postgres", "aws"]
        tags = [kw for kw in tech_keywords if kw in desc_lower]
        
        # Normalize URL
        canonical = raw.source_url.split("?")[0].split("#")[0].strip()
        
        # Calculate structure hash
        hash_input = f"{raw.title}|{raw.description_html}".encode("utf-8")
        content_hash = hashlib.sha256(hash_input).hexdigest()

        return NormalizedJob(
            title=raw.title,
            company_name=raw.company_name,
            location=raw.location,
            is_remote=is_remote,
            is_new_grad=is_new_grad,
            visa_sponsorship=visa_sponsorship,
            tags=tags,
            source=self.source_id,
            source_url=raw.source_url,
            canonical_url=canonical,
            raw_payload=raw.raw_payload,
            content_hash=content_hash
        )

    async def health_check(self) -> bool:
        try:
            res = await self._client.get(self.career_url)
            return res.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()

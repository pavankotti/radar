import hashlib
from typing import List, Optional
import httpx
from datetime import datetime
from app.adapters.base import BaseAdapter, RawJobPayload, NormalizedJob

class GreenhouseAdapter(BaseAdapter):
    """
    Ingestion Adapter for Greenhouse ATS Board API.
    """
    def __init__(self, company_id: str):
        self.company_id = company_id.lower().strip()
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def source_id(self) -> str:
        return f"greenhouse:{self.company_id}"

    async def discover(self) -> List[str]:
        """
        Queries Greenhouse JSON jobs endpoint to discover active IDs.
        """
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.company_id}/jobs"
        response = await self._client.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Discovers and returns a list of integer IDs as strings
        jobs_list = data.get("jobs", [])
        return [str(job["id"]) for job in jobs_list]

    async def fetch_detail(self, job_identifier: str) -> RawJobPayload:
        """
        Pulls rich detail payload from Greenhouse API.
        """
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.company_id}/jobs/{job_identifier}?questions=true"
        response = await self._client.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Parse update date if present
        published_date = None
        updated_at_str = data.get("updated_at")
        if updated_at_str:
            try:
                # ISO date format parsing
                published_date = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            except ValueError:
                pass
                
        location_name = data.get("location", {}).get("name", "Unknown")
        
        return RawJobPayload(
            title=data.get("title", "Untitled Role"),
            company_name=self.company_id.capitalize(),
            location=location_name,
            description_html=data.get("content", ""),
            source_url=data.get("absolute_url", ""),
            raw_payload=data,
            published_at=published_date
        )

    def normalize(self, raw: RawJobPayload) -> NormalizedJob:
        """
        Standardizes raw Greenhouse structure to NormalizedJob schema.
        Matches targeted New-Grad SWE, Remote, and Visa flags.
        """
        title_lower = raw.title.lower()
        location_lower = raw.location.lower()
        desc_lower = raw.description_html.lower()
        
        # 1. Identify Remote
        # Checks title, location, or direct Greenhouse metadata properties
        is_remote = (
            "remote" in title_lower 
            or "remote" in location_lower 
            or raw.raw_payload.get("location", {}).get("name", "").lower() == "remote"
            or "work from home" in desc_lower
        )
        
        # 2. Identify New Grad / Entry level
        new_grad_terms = [
            "new grad", "university graduate", "associate", 
            "junior", "jr", "entry level", "graduate engineer", "intern"
        ]
        is_new_grad = any(term in title_lower for term in new_grad_terms)
        
        # 3. Identify Visa Sponsorship Friendly
        visa_terms = [
            "sponsorship available", "h-1b", "h1b", "opt", "stem extension",
            "visa sponsorship", "cpt", "sponsorship is offered", "visa friendly"
        ]
        # Reject matches with explicit 'no visa' statements
        has_negative_cues = "no visa sponsorship" in desc_lower or "does not offer sponsorship" in desc_lower or "unable to sponsor" in desc_lower
        visa_sponsorship = any(term in desc_lower for term in visa_terms) and not has_negative_cues
        
        # 4. Extract tech stack tags
        tech_keywords = [
            "python", "javascript", "typescript", "go", "golang", "rust", "cpp",
            "c++", "java", "kotlin", "ruby", "react", "nextjs", "vue", "angular",
            "node", "django", "fastapi", "postgres", "mysql", "mongodb", "aws", 
            "gcp", "docker", "kubernetes", "graphql"
        ]
        # Check boundary/word matches to prevent substring overlapping
        tags = []
        for kw in tech_keywords:
            if f" {kw} " in f" {desc_lower} " or f"({kw})" in desc_lower or f"/{kw}" in desc_lower:
                tags.append(kw)
                
        # Clean canonical URL (strip referral and tracking parameters)
        # If the URL uses a custom domain (e.g. Stripe) passing the job ID via gh_jid, map it to direct Greenhouse URL
        if "gh_jid=" in raw.source_url:
            job_id_param = raw.source_url.split("gh_jid=")[-1].split("&")[0].split("#")[0]
            canonical = f"https://boards.greenhouse.io/{self.company_id}/jobs/{job_id_param}"
        elif raw.raw_payload.get("id"):
            canonical = f"https://boards.greenhouse.io/{self.company_id}/jobs/{raw.raw_payload.get('id')}"
        else:
            canonical = raw.source_url.split("?")[0].split("#")[0].strip()
        
        # Create structural content hash of the role description to catch modifications
        hash_input = f"{raw.title}|{raw.description_html}".encode("utf-8")
        content_hash = hashlib.sha256(hash_input).hexdigest()
        
        # Detect experience requirements if listed
        experience_level = None
        if "senior" in title_lower or "sr" in title_lower or "lead" in title_lower or "principal" in title_lower:
            experience_level = "Senior"
        elif "mid" in title_lower or "ii" in title_lower:
            experience_level = "Mid"
        elif is_new_grad:
            experience_level = "Entry"

        return NormalizedJob(
            title=raw.title,
            company_name=raw.company_name,
            location=raw.location,
            is_remote=is_remote,
            is_new_grad=is_new_grad,
            visa_sponsorship=visa_sponsorship,
            employment_type="Full-time" if "intern" not in title_lower else "Internship",
            experience_level=experience_level,
            tags=tags,
            source=self.source_id,
            source_url=raw.source_url,
            canonical_url=canonical,
            published_at=raw.published_at,
            raw_payload=raw.raw_payload,
            content_hash=content_hash
        )

    async def health_check(self) -> bool:
        """Verifies connection and availability of targets."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.company_id}/jobs"
        try:
            res = await self._client.get(url)
            return res.status_code == 200
        except Exception:
            return False
            
    async def close(self):
        """Cleanup http client connection session."""
        await self._client.aclose()

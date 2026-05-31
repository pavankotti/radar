import re
from sqlmodel import Session, select
from app.models.job import Job
from typing import Optional

def sanitize_title(title: str) -> str:
    """Removes common job title noise like location, schedule, or extra characters."""
    title = title.lower()
    # Remove everything in parentheses/brackets e.g. "Software Engineer (Remote)" -> "Software Engineer"
    title = re.sub(r"[\(\[\{].*?[\)\]\}]", "", title)
    # Remove common suffixes
    noise = ["- remote", "- hybrid", "- onsite", "full time", "part time", "temporary", "/ remote"]
    for n in noise:
        title = title.replace(n, "")
    # Standardize whitespace
    return " ".join(title.split()).strip()

def calculate_jaccard_similarity(t1: str, t2: str) -> float:
    """Calculates Jaccard token set similarity for fuzzy title comparisons."""
    t1_clean = sanitize_title(t1)
    t2_clean = sanitize_title(t2)
    
    tokens1 = set(t1_clean.split())
    tokens2 = set(t2_clean.split())
    
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)

def find_duplicate(session: Session, new_job: Job, similarity_threshold: float = 0.85) -> Optional[Job]:
    """
    Analyzes the database to identify duplicate postings.
    Returns the primary (parent) Job if duplicate found, else None.
    """
    # 1. Deterministic URL match
    if new_job.canonical_url:
        stmt = select(Job).where(Job.canonical_url == new_job.canonical_url)
        existing = session.exec(stmt).first()
        if existing:
            return existing
            
    # 2. Structural hash match
    stmt = select(Job).where(Job.content_hash == new_job.content_hash)
    existing = session.exec(stmt).first()
    if existing:
        return existing
        
    # 3. Fuzzy title and location similarity under the same company
    stmt = select(Job).where(
        Job.company_name == new_job.company_name,
        Job.parent_job_id == None  # Only compare against parent listings to avoid duplicate chains
    )
    company_jobs = session.exec(stmt).all()
    
    for job in company_jobs:
        # Check title similarity
        similarity = calculate_jaccard_similarity(job.title, new_job.title)
        
        # Check location matches loosely (e.g. both remote, or same string)
        location_match = (
            job.location.lower() == new_job.location.lower()
            or (job.is_remote and new_job.is_remote)
        )
        
        if similarity >= similarity_threshold and location_match:
            return job
            
    return None

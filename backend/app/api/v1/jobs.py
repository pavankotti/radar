from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select, or_, func
from sqlalchemy import cast, String
from typing import List, Optional
from app.api.deps import get_db
from app.models.job import Job

router = APIRouter()

@router.get("/")
def read_jobs(
    db: Session = Depends(get_db),
    offset: int = 0,
    limit: int = Query(default=20, le=100),
    q: Optional[str] = Query(None, description="Search query matching title or tags"),
    is_remote: Optional[bool] = Query(None, description="Filter remote positions"),
    is_new_grad: Optional[bool] = Query(None, description="Filter new grad entry positions"),
    visa_sponsorship: Optional[bool] = Query(None, description="Filter visa-friendly positions"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    include_duplicates: bool = Query(False, description="Whether to include deduplicated duplicate job listings")
):
    """
    Search, filter, and fetch normalized job postings.
    """
    stmt = select(Job)
    
    # 1. Deduplication Filter
    # Default is to hide duplicates (which have a parent_job_id assigned)
    if not include_duplicates:
        stmt = stmt.where(Job.parent_job_id == None)
        stmt = stmt.where(Job.is_active == True)
        
    # 2. Hard filters
    if is_remote is not None:
        stmt = stmt.where(Job.is_remote == is_remote)
    if is_new_grad is not None:
        stmt = stmt.where(Job.is_new_grad == is_new_grad)
    if visa_sponsorship is not None:
        stmt = stmt.where(Job.visa_sponsorship == visa_sponsorship)
    if company:
        stmt = stmt.where(func.lower(Job.company_name) == company.lower().strip())
        
    # 3. Search query (matches title or elements in tags list)
    if q:
        search_term = f"%{q.lower().strip()}%"
        # Since tags is a JSON column, we use casting/string checks or matching inside SQL
        stmt = stmt.where(
            or_(
                func.lower(Job.title).like(search_term),
                func.lower(Job.company_name).like(search_term),
                func.lower(Job.location).like(search_term),
                func.lower(cast(Job.tags, String)).like(search_term),
                func.lower(cast(Job.raw_details, String)).like(search_term)
            )
        )
        
    # Order by scraping time (newest first)
    stmt = stmt.order_by(Job.scraped_at.desc())
    
    # Execute paginated query
    total = len(db.exec(stmt).all())
    stmt = stmt.offset(offset).limit(limit)
    results = db.exec(stmt).all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "jobs": results
    }

@router.get("/{job_id}")
def read_job_by_id(job_id: int, db: Session = Depends(get_db)):
    """
    Fetches detailed metadata and structural raw payload for a single job post.
    """
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If this is a duplicate, fetch parent info
    parent = None
    if job.parent_job_id:
        parent = db.get(Job, job.parent_job_id)
        
    # Find child duplicates of this job
    stmt = select(Job).where(Job.parent_job_id == job.id)
    duplicates = db.exec(stmt).all()
    
    return {
        "job": job,
        "parent_listing": parent,
        "duplicate_listings": duplicates
    }

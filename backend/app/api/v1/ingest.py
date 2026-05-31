from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime
from typing import List
from app.api.deps import get_db
from app.database import engine
from app.models.job import Job, CrawlHistory
from app.adapters.greenhouse import GreenhouseAdapter
from app.core.dedupe import find_duplicate

router = APIRouter()

async def run_greenhouse_crawler_sync(company_id: str):
    """
    Synchronous fallback runner for lightweight background tasks.
    Spawns its own independent database session and fetches details concurrently with a Semaphore.
    """
    import asyncio
    source_id = f"greenhouse:{company_id}"
    
    with Session(engine) as db:
        history = CrawlHistory(source_id=source_id, status="running", started_at=datetime.utcnow())
        db.add(history)
        db.commit()
        db.refresh(history)
        
        adapter = GreenhouseAdapter(company_id)
        try:
            job_identifiers = await adapter.discover()
            
            # Process in batches of 25 to prevent Out Of Memory (OOM) on Render's 512MB free tier
            chunk_size = 25
            added = 0
            deduped = 0
            
            for i in range(0, len(job_identifiers), chunk_size):
                chunk = job_identifiers[i:i + chunk_size]
                
                tasks = [adapter.fetch_detail(job_id) for job_id in chunk]
                raw_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for raw in raw_results:
                    if isinstance(raw, Exception):
                        print(f"Failed to fetch detailed job payload: {raw}")
                        continue
                    try:
                        normalized = adapter.normalize(raw)
                        
                        db_job = Job(
                            title=normalized.title,
                            company_name=normalized.company_name,
                            location=normalized.location,
                            is_remote=normalized.is_remote,
                            is_new_grad=normalized.is_new_grad,
                            visa_sponsorship=normalized.visa_sponsorship,
                            employment_type=normalized.employment_type,
                            experience_level=normalized.experience_level,
                            tags=normalized.tags,
                            source=normalized.source,
                            source_url=normalized.source_url,
                            canonical_url=normalized.canonical_url,
                            published_at=normalized.published_at,
                            raw_details=normalized.raw_payload,
                            content_hash=normalized.content_hash
                        )
                        
                        # Check for duplicates in DB
                        parent = find_duplicate(db, db_job)
                        if parent:
                            db_job.parent_job_id = parent.id
                            db_job.is_active = False  # Set to inactive as it is a secondary post
                            deduped += 1
                        else:
                            added += 1
                            
                        db.add(db_job)
                    except Exception as inner_error:
                        print(f"Failed to normalize/save job: {inner_error}")
                
                # Commit batch and yield to event loop to free memory and prevent blocking
                db.commit()
                await asyncio.sleep(0)
            
            history.status = "success"
            history.jobs_discovered = len(job_identifiers)
            history.jobs_added = added
            history.jobs_deduplicated = deduped
            
        except Exception as e:
            history.status = "failed"
            history.error_message = str(e)
        finally:
            history.completed_at = datetime.utcnow()
            await adapter.close()
            db.add(history)
            db.commit()

@router.post("/greenhouse/{company_id}")
async def trigger_greenhouse_ingest(
    company_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers manual career-page scrape for a Greenhouse board ID.
    Leverages FastAPI BackgroundTasks for concurrent, non-blocking execution.
    """
    # Simple validation on input
    company_id_clean = company_id.lower().strip()
    if not company_id_clean:
        raise HTTPException(status_code=400, detail="Invalid company ID")
        
    # Check if already running to prevent overlap
    stmt = select(CrawlHistory).where(
        CrawlHistory.source_id == f"greenhouse:{company_id_clean}",
        CrawlHistory.status == "running"
    )
    running_task = db.exec(stmt).first()
    if running_task:
        return {
            "status": "already_running",
            "message": f"Scraper is already active for greenhouse:{company_id_clean}",
            "started_at": running_task.started_at
        }
        
    # Trigger task in background with its own self-managed session
    background_tasks.add_task(run_greenhouse_crawler_sync, company_id_clean)
    
    return {
        "status": "triggered",
        "message": f"Ingestion pipeline started for Greenhouse board '{company_id_clean}'."
    }

@router.get("/history")
def read_crawl_history(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=50)
):
    """
    Retrieves previous crawl executions, completion status, and statistics.
    """
    stmt = select(CrawlHistory).order_by(CrawlHistory.started_at.desc()).limit(limit)
    history = db.exec(stmt).all()
    return history

from fastapi import APIRouter
from app.api.v1.jobs import router as jobs_router
from app.api.v1.ingest import router as ingest_router

api_router = APIRouter()
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])

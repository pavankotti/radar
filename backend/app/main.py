from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import api_router

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A high-performance Job Intelligence Engine focused on New-Grad, Remote, and Visa-Friendly software roles.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set CORS middleware (supports modern rich interactive dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """Initializes tables inside the SQLModel database engine."""
    init_db()

@app.get("/", tags=["Health"])
def root_health_check():
    """Root health check confirmation endpoint."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs"
    }

# Register major V1 endpoints under standard path prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

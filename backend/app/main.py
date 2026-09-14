import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.core.config import settings
from backend.app.database.session import engine, Base, SessionLocal

from backend.app.api.classes import router as classes_router
from backend.app.api.subjects import router as subjects_router
from backend.app.api.faculty import router as faculty_router
from backend.app.api.rooms import router as rooms_router
from backend.app.api.timetable import router as timetable_router
from backend.app.api.demo import router as demo_router

logger = logging.getLogger("uvicorn.error")

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready Academic Timetable Optimizer using Backtracking CSP engine and MRV heuristics.",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Middleware with configurable allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True if settings.ALLOWED_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Production Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again or contact the administrator."}
    )

# Health Checks for load balancers, cloud probes, and monitors
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION
    }

# API Routers
app.include_router(classes_router, prefix="/api")
app.include_router(subjects_router, prefix="/api")
app.include_router(faculty_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")
app.include_router(timetable_router, prefix="/api")
app.include_router(demo_router, prefix="/api")

# Static file serving for single-page web app
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_index():
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": f"{settings.PROJECT_NAME} Backend API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

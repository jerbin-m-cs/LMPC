from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from .database import engine, Base
from .routers.auth_router import router as auth_router
from .routers.scan_router import router as scan_router
from .routers.reports_router import router as reports_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Legal Metrology Compliance Checker",
    description="Scan product labels and verify compliance with LMPC Rules 2011",
    version="1.0.0"
)

# Include routers
app.include_router(auth_router)
app.include_router(scan_router)
app.include_router(reports_router)

# Ensure directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/")
    async def serve_frontend():
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not found"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
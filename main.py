"""Main entry point for the BLIMS application."""
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from blims.api.routes import router as api_router
from blims.core.service import SampleService

# Service dependency
def get_sample_service():
    """Dependency for getting the sample service."""
    return SampleService()


app = FastAPI(
    title="BLIMS - Biolab Laboratory Information Management System",
    description="A modern LIMS for tracking samples, metadata, files, and lineage",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "BLIMS API",
        "version": "0.1.0",
        "description": "Sample tracking and lineage management for laboratories",
    }


if __name__ == "__main__":
    """Run the application with uvicorn when script is executed directly."""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
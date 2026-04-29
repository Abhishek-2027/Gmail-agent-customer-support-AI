import os
import logging

# Disable ChromaDB telemetry and suppress its error logs
os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from schema import EmailRequest, OutputResponse
from pipeline import run_pipeline
from retrieval import init_rag
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize RAG on startup
    logger.info("Initializing RAG...")
    init_rag()
    yield
    # Cleanup (if any)

app = FastAPI(title="Mumzworld Customer Support AI", lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/analyze", response_model=OutputResponse)
async def analyze_email(request: EmailRequest):
    try:
        # Run the AI pipeline
        result = await run_pipeline(request.email_text)
        
        # Validate output against Strict Pydantic Schema
        validated_output = OutputResponse(**result)
        return validated_output

    except ValidationError as e:
        logger.error(f"JSON Validation Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI produced invalid format: {e.errors()}")
    except Exception as e:
        logger.error(f"Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve Frontend Static Files (at the end to allow API routes to match first)
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

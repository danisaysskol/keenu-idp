import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ALLOWED_ORIGINS env var lets Vercel/other domains be added without a redeploy.
# Comma-separated list, e.g.:
#   ALLOWED_ORIGINS=https://keenu-idp.vercel.app,http://localhost:5173
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173",
)
ALLOW_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured.")
    logger.info("Model: %s | CORS origins: %s", settings.gemini_model, ALLOW_ORIGINS)

    output_path = Path(settings.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_path.resolve())

    dataset_path = Path(__file__).parent.parent.parent / "dataset"
    if dataset_path.exists():
        categories = [d.name for d in dataset_path.iterdir() if d.is_dir()]
        logger.info("Dataset categories: %s", categories)

    yield
    logger.info("Shutting down Keenu IDP backend.")


app = FastAPI(
    title="Keenu IDP API",
    description="Intelligent Document Processing for Keenu – Simplifying Digital Payments",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

output_path = Path(settings.output_dir)
output_path.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_path)), name="output")

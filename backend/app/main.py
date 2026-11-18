import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.router import api_router
from backend.app.scheduler.job_runner import SchedulerService

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("chirp")

scheduler = SchedulerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Chirp Class Assignment Bot backend...")
    # Initialize database tables
    await init_db()
    logger.info("Database initialized successfully.")

    # Start persistent scheduler
    await scheduler.start()
    logger.info("Scheduler background loop started.")

    yield

    # Shutdown
    logger.info("Shutting down Chirp services...")
    await scheduler.stop()
    logger.info("Chirp backend stopped.")


app = FastAPI(
    title="Chirp - Class Assignment Bot",
    description="Intelligent WhatsApp-based academic assignment assistant for university classes",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )

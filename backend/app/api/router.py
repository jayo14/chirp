from fastapi import APIRouter
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.webhook import router as webhook_router
from backend.app.api.routes.assignments import router as assignments_router
from backend.app.api.routes.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(webhook_router)
api_router.include_router(assignments_router)
api_router.include_router(admin_router)

from fastapi import APIRouter

from app.api import dashboard, export, leads, search

api_router = APIRouter()
api_router.include_router(search.router, tags=["search"])
api_router.include_router(leads.router, tags=["leads"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(export.router, tags=["export"])

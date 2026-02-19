"""
Master API router that aggregates all versioned endpoint routers.
Developed by: MERO:TG@QP4RM
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    devices,
    metrics,
    alerts,
    reports,
    websocket,
    system,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(system.router, prefix="/system", tags=["System"])

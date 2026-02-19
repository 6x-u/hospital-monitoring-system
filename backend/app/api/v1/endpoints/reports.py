from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from app.api.v1.endpoints.auth import get_current_active_user
from app.db.session import get_db
from app.models.models import Metric, Alert, Device, User
from app.core.rbac import RoleChecker

router = APIRouter()
allow_viewor_reports = RoleChecker(["admin", "engineer", "viewer"])


@router.get("/metrics/summary-report", dependencies=[Depends(allow_viewor_reports)])
async def generate_metrics_summary_report(
    start_date: datetime = Query(..., description="Start date for report"),
    end_date: datetime = Query(None, description="End date for report (defaults to now)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate a summary report of average metrics per device over a time range.
    """
    if not end_date:
        end_date = datetime.utcnow()

    query = (
        select(
            Metric.device_id,
            func.avg(Metric.cpu_usage_percent).label("avg_cpu"),
            func.avg(Metric.ram_usage_percent).label("avg_ram"),
            func.max(Metric.max_temperature_celsius).label("max_temp"),
            func.avg(Metric.network_latency_ms).label("avg_latency"),
        )
        .where(Metric.collected_at >= start_date, Metric.collected_at <= end_date)
        .group_by(Metric.device_id)
    )
    result = await db.execute(query)
    rows = result.all()

    report_data = []
    for row in rows:
        device = await db.get(Device, row.device_id)
        report_data.append({
            "hostname": device.hostname if device else "Unknown",
            "device_id": str(row.device_id),
            "avg_cpu_percent": round(row.avg_cpu, 2) if row.avg_cpu else 0,
            "avg_ram_percent": round(row.avg_ram, 2) if row.avg_ram else 0,
            "max_temperature_celsius": round(row.max_temp, 1) if row.max_temp else 0,
            "avg_latency_ms": round(row.avg_latency, 1) if row.avg_latency else 0,
        })

    return {
        "report_type": "metrics_summary",
        "generated_at": datetime.utcnow(),
        "generated_by": current_user.username,
        "period": {"start": start_date, "end": end_date},
        "data": report_data
    }


@router.get("/alerts/history-report", dependencies=[Depends(allow_viewor_reports)])
async def generate_alerts_history_report(
    start_date: datetime = Query(..., description="Start date for report"),
    end_date: datetime = Query(None, description="End date for report (defaults to now)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate a historical report of alerts triggered over a time range.
    """
    if not end_date:
        end_date = datetime.utcnow()

    query = (
        select(Alert)
        .where(Alert.created_at >= start_date, Alert.created_at <= end_date)
        .order_by(desc(Alert.created_at))
    )
    result = await db.execute(query)
    alerts = result.scalars().all()

    alert_summary = {
        "total": len(alerts),
        "critical": len([a for a in alerts if a.severity == "critical"]),
        "high": len([a for a in alerts if a.severity == "high"]),
        "medium": len([a for a in alerts if a.severity == "medium"]),
        "low": len([a for a in alerts if a.severity == "low"]),
    }

    return {
        "report_type": "alerts_history",
        "generated_at": datetime.utcnow(),
        "generated_by": current_user.username,
        "period": {"start": start_date, "end": end_date},
        "summary": alert_summary,
        "details": [
            {
                "id": str(a.id),
                "title": a.title,
                "severity": a.severity,
                "created_at": a.created_at,
                "status": a.status,
                "device_id": str(a.device_id),
            }
            for a in alerts
        ]
    }

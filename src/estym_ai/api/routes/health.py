"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "estym_ai",
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness_check():
    """Check if all dependencies are available."""
    checks = {}

    # Check database
    try:
        from ...db.session import get_async_engine

        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}

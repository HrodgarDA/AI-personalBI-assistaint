from fastapi import APIRouter, HTTPException
from src.services.recovery import recovery_service
import psutil
import os

router = APIRouter()

@router.post("/recover")
async def run_recovery():
    try:
        fixed, total = await recovery_service.recover_uncategorized()
        return {"status": "success", "fixed": fixed, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hardware")
async def get_hardware_info():
    total_ram = psutil.virtual_memory().total / (1024**3)
    cpu_cores = os.cpu_count() or 1
    return {
        "ram_gb": round(total_ram, 2),
        "cpu_cores": cpu_cores,
        "recommended_concurrency": min(4, max(1, int(total_ram / 4)))
    }

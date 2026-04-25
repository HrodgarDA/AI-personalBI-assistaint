from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os
from src.database.session import get_db
from src.api import schemas
from src.worker.tasks import process_file_ingestion
from src.services.ingestion_service import IngestionService

router = APIRouter(
    prefix="/upload",
    tags=["upload"]
)

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze", response_model=schemas.AnalysisResult)
async def analyze_file(
    file: UploadFile = File(...),
    bank_profile_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    file_ext = os.path.splitext(file.filename)[1].lower()
    file_id = f"temp_{uuid.uuid4()}"
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    service = IngestionService(db)
    result = await service.analyze_file(file_path, bank_profile_id)

    # Keep file for ingestion after confirm — caller should use same path
    # Cleanup only on error
    if "error" in result and result["error"]:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=result["error"])

    # Attach file_path to result so frontend can confirm ingestion
    result["_file_path"] = file_path
    return result

@router.post("/confirm")
async def confirm_ingestion(
    file_path: str = Form(...),
    bank_profile_id: int = Form(1),
):
    """Start ingestion of an already-analyzed file."""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found. Re-upload required.")
    task = process_file_ingestion.delay(file_path, bank_profile_id)
    return {"task_id": task.id, "status": "PENDING", "progress": 0.0}

@router.post("/", response_model=schemas.TaskStatus)
async def upload_file(
    file: UploadFile = File(...),
    bank_profile_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".xlsx", ".csv"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Supported: PDF, XLSX, CSV")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    task = process_file_ingestion.delay(file_path, bank_profile_id)

    return {"task_id": task.id, "status": "PENDING", "progress": 0.0}

@router.get("/status/{task_id}", response_model=schemas.TaskStatus)
async def get_task_status(task_id: str):
    from celery.result import AsyncResult
    res = AsyncResult(task_id)
    info = res.info if isinstance(res.info, dict) else {}

    return {
        "task_id": task_id,
        "status": res.status,
        "progress": info.get("progress", 1.0 if res.ready() else 0.0),
        "logs": info.get("logs", []),
        "result": res.result if res.ready() else None
    }

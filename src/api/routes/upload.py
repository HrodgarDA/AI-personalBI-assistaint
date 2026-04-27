from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from src.worker.celery_app import celery_app
import shutil
import os
import uuid

router = APIRouter()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_file(profile_name: str, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Trigger Celery task
    task = celery_app.send_task("process_file_ingestion", args=[file_path, profile_name])
    
    return {"task_id": task.id, "filename": file.filename}

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None,
        "info": task_result.info if not task_result.ready() else None
    }

from src.worker.celery_app import celery_app
from src.services.extractor import TransactionExtractor
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="process_file_ingestion", bind=True)
def process_file_ingestion(self, file_path: str, profile_name: str = "Default"):
    self.update_state(state="PROGRESS", meta={"msg": f"Starting ingestion for {profile_name}..."})
    
    # Run async logic in sync Celery task
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.run_coroutine_threadsafe(run_ingestion(file_path, profile_name, self), loop)
        return future.result()
    else:
        return asyncio.run(run_ingestion(file_path, profile_name, self))

async def run_ingestion(file_path, profile_name, task_obj):
    extractor = TransactionExtractor()
    
    # 1. Extraction
    task_obj.update_state(state="PROGRESS", meta={"msg": "Extracting transactions from PDF..."})
    raw_rows = await extractor.extract(file_path)
    
    # 2. AI Classification (Batch)
    task_obj.update_state(state="PROGRESS", meta={"msg": f"Classifying {len(raw_rows)} transactions..."})
    classified = await extractor.classify_batch(raw_rows)
    
    # 3. Database Save
    task_obj.update_state(state="PROGRESS", meta={"msg": "Saving to database..."})
    await extractor.save_to_db(classified)
    
    return {"processed": len(classified), "status": "complete"}

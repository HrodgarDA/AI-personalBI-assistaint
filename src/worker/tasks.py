import asyncio
import logging
from src.worker.celery_app import celery_app
from src.services.ingestion_service import IngestionService
from src.services.ai_pipeline import AIPipeline
from src.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="process_file_ingestion")
def process_file_ingestion(self, file_path: str, bank_profile_id: int):
    """Celery task to ingest a file and then trigger AI extraction with live logs."""
    logs = []
    
    def add_log(msg):
        logs.append(msg)
        self.update_state(state='PROGRESS', meta={'logs': logs, 'progress': 0.5})
        logger.info(msg)

    async def run():
        async with AsyncSessionLocal() as db:
            add_log(f"📥 Starting ingestion of {os.path.basename(file_path)}")
            ingestion_service = IngestionService(db)
            count = await ingestion_service.ingest_file(file_path, bank_profile_id)
            add_log(f"✅ Ingested {count} transactions.")
            
            add_log("🤖 Starting AI Classification pipeline...")
            ai_pipeline = AIPipeline(db)
            
            # We can pass a callback to the pipeline if we want more granular logs
            await ai_pipeline.run_full_extraction(bank_profile_id)
            add_log("🎉 AI Pipeline completed successfully.")
            
    import os
    asyncio.run(run())
    return {"status": "completed", "logs": logs}

@celery_app.task(name="run_ai_classification")
def run_ai_classification(bank_profile_id: int):
    """Celery task to run AI classification on pending transactions."""
    async def run():
        async with AsyncSessionLocal() as db:
            ai_pipeline = AIPipeline(db)
            await ai_pipeline.run_full_extraction(bank_profile_id)
            
    asyncio.run(run())
    return {"status": "completed"}

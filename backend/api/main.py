from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import upload, transactions, metadata, maintenance

app = FastAPI(title="AI Personal BI Assistant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(metadata.router, prefix="/api/metadata", tags=["Metadata"])
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["Maintenance"])

@app.get("/")
async def root():
    return {"message": "AI Personal BI Assistant API is running"}

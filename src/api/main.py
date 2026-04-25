from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.session import engine, Base
from src.api.routes import transactions, upload, profiles, categories, merchants
import uvicorn

app = FastAPI(
    title="AI Personal BI Assistant API",
    description="Backend API for financial data extraction and classification",
    version="0.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transactions.router)
app.include_router(upload.router)
app.include_router(profiles.router)
app.include_router(categories.router)
app.include_router(merchants.router)

@app.get("/")
async def root():
    return {"message": "Welcome to AI Personal BI Assistant API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

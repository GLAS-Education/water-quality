from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import os
from sync import router as sync_router
from query import router as query_router
from auth import router as auth_router
from manage import router as manage_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Water Quality Sensor Data API",
    description="API for receiving, managing, and querying water quality sensor data with Slack authentication",
    version="2.0.0"
)

# Get frontend URL from environment variable
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Dynamic CORS origins based on frontend URL
origins = [frontend_url]

# Add additional allowed origins if needed
additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS", "").split(",")
origins.extend([origin.strip() for origin in additional_origins if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync_router)
app.include_router(query_router)
app.include_router(auth_router)
app.include_router(manage_router)

@app.get("/")
async def root():
    return {"message": "Sensor Data API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

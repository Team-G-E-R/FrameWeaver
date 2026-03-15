from fastapi import FastAPI
from app.routes_jobs import router as jobs_router
from .routes_auth import router as auth_router

app = FastAPI(title="Game Asset Generator API", version="0.1.0")

app.include_router(jobs_router)
app.include_router(auth_router)

@app.get("/api/ping")
def ping():
    return {"ok": True}

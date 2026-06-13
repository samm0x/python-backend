from fastapi import FastAPI , Request
from backend.routes import router , limiter
from backend.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from backend.middleware import LoggingMiddleware , MaintenanceMiddleware
from fastapi.responses import JSONResponse
from backend.v1 import router as v1_router
from backend.v2 import router as v2_router
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

app.state.limiter = limiter

app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")

@app.get("/")
def root():
    return {"message": "API id running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(MaintenanceMiddleware)
Base.metadata.create_all(bind=engine)


@app.exception_handler(403)
async def forbidden_handler(
        request: Request,
        exc
):
    return JSONResponse(status_code=403, content={"success": False, "message": "Access denied"})

@app.exception_handler(Exception)
async def global_exception_handler(
        request: Request,
        exc: Exception
):

    return JSONResponse(status_code=500,content={"success": False,
                                                 "message": "Internal server error"}
                        )

os.makedirs("uploads", exist_ok=True)

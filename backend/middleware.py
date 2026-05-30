import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        ip = request.client.host
        method = request.method
        path = request.url.path
        status_code = response.status_code

        print(
            f"""
IP: {ip}
METHOD: {method}
PATH: {path}
STATUS: {status_code}
TIMI:{process_time:.4f}s
"""
        )
        return response

class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        maintenance = False
        if maintenance:
            return JSONResponse(status_code=503, content={"message": "Server under maintenance"})
        response = await call_next(request)
        return response
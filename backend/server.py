# server.py
import os
import sys
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel
import subprocess
from gdrive_loader import download_apk, extract_app_icon, get_apk_info

# Add project root to sys.path so we can import tests.*
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # root: f:\projects\test-automation-platform
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tests.test_runner import run_tests_and_get_suggestions
# from gdrive_loader import download_apk, 

app = FastAPI()

# CORS: allow your React dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],  # adjust if your frontend runs on a different port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use absolute path and auto-create the dir
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 1. Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

class TestRequest(BaseModel):
    url: str

manager = ConnectionManager()

@app.get("/device-status")
async def device_status():
    """
    Returns whether at least one physical Android device is connected via ADB.
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.strip().splitlines()[1:]  # skip header
        connected = any("\tdevice" in line for line in lines)
        return {"connected": connected}
    except Exception:
        # If adb is not installed or any error occurs, treat as no device
        return {"connected": False}

# 2. WebSocket Endpoint (Frontend connects here)
@app.websocket("/ws/test-status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except:
        manager.active_connections.remove(websocket)

# 3. The "Loopback" Endpoint (Pytest calls this)
@app.post("/api/log-step")
async def log_step(data: dict):
    # Broadcast log to UI immediately
    await manager.broadcast({"type": "LOG", "payload": data})
    return {"status": "ok"}

# 4. The "Profiler" Endpoint (Sidecar calls this)
@app.post("/api/metric")
async def log_metric(data: dict):
    # Broadcast CPU/Memory data to UI
    await manager.broadcast({"type": "METRIC", "payload": data})
    return {"status": "ok"}

@app.post("/api/module-status")
async def module_status(data: dict):
    """
    Accepts { "module": "Login", "status": "running/completed/failed", "message": "optional" }
    and broadcasts it to all WebSocket clients.
    """
    module = data.get("module")
    status = data.get("status")
    message = data.get("message", "")

    await manager.broadcast({
        "type": "MODULE",
        "payload": {
            "module": module,
            "status": status,
            "message": message,
        }
    })
    return {"status": "ok"}

@app.post("/start-test")
async def start_test(request: TestRequest, background_tasks: BackgroundTasks):
    try:

        # Tell frontend: starting download
        await manager.broadcast({
            "type": "LOG",
            "payload": {"message": "Starting APK download...", "status": "INFO"}
        })
        # 1. Download the APK (This happens immediately)
        apk_path = download_apk(request.url)

        # 2. Extract Icon immediately after download
        icon_url = extract_app_icon(apk_path)

        # Construct full URL for Frontend
        full_icon_url = f"http://localhost:8000{icon_url}" if icon_url else None

        info = get_apk_info(apk_path) or {}
        app_name = info.get("app_name")
        package_name = info.get("package_name")
        
        # 2. Trigger the actual Automation Test in the background
        # (We will add the test_runner logic in the next step)
        # background_tasks.add_task(run_appium_test, apk_path)
        
        # Add the test run to background tasks
        # This runs the test AFTER the response is sent to UI
        background_tasks.add_task(run_tests_and_get_suggestions, apk_path)

        return {
            "status": "success", 
            "message": "APK Downloaded. Test Starting...",
            "app_icon": full_icon_url,
            "app_name": app_name,
            "package_name": package_name,
            "apk_path": apk_path
        }
    
    except Exception as e:
        await manager.broadcast({
            "type": "LOG",
            "payload": {"message": f"Download failed: {str(e)}", "status": "FAILED"}
        })
        raise HTTPException(status_code=400, detail=f"Download Failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
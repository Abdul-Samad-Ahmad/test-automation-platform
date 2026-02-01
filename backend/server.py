# server.py
import os
import sys
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
import subprocess
import socket
import asyncio
from gdrive_loader import download_apk, extract_app_icon, get_apk_info
from typing import List, Optional, Dict

# Add project root to sys.path so we can import tests.*
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # root: f:\projects\test-automation-platform
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tests.test_runner import run_tests_and_get_suggestions, stop_current_tests
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

APKS_DIR = os.path.join(os.path.dirname(__file__), "temp_apks")
os.makedirs(APKS_DIR, exist_ok=True)

# Serve generated Allure report (will be created by test_runner)
ALLURE_REPORT_DIR = os.path.join(BASE_DIR, "allure-report")
os.makedirs(ALLURE_REPORT_DIR, exist_ok=True)
app.mount("/allure-report", StaticFiles(directory=ALLURE_REPORT_DIR, html=True), name="allure-report")

_allure_proc: subprocess.Popen | None = None
_allure_port: int | None = None

ALLURE_CMD = r"C:\Users\Pramo\scoop\shims\allure"

def _start_allure_server() -> str:
    """
    Starts (or restarts) `allure open` server for the generated allure-report folder.
    Returns the URL the frontend should open.
    Requires: Allure CLI installed and in PATH.
    """
    global _allure_proc, _allure_port

    if not os.path.isdir(ALLURE_REPORT_DIR):
        raise HTTPException(status_code=404, detail=f"Allure report dir not found: {ALLURE_REPORT_DIR}")

    # Kill previous server if running
    if _allure_proc is not None and _allure_proc.poll() is None:
        try:
            _allure_proc.terminate()
        except Exception:
            pass
        _allure_proc = None

    _allure_port = _pick_free_port()

    # Start Allure server
    # (Allure CLI: `allure open -h <host> -p <port> <report_dir>`)
    _allure_proc = subprocess.Popen(
        ["allure", "open", "-h", "127.0.0.1", "-p", str(_allure_port), ALLURE_REPORT_DIR],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )

    return f"http://127.0.0.1:{_allure_port}"


class RunCompleteEvent(BaseModel):
    report_url: str

class ExistingTestRequest(BaseModel):
    apk_name: str
    tests_to_run: Optional[List[Dict[str, str]]] = None  # Added field

class LogMessage(BaseModel):
    message: str
    status: str = "INFO"

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
    tests_to_run: Optional[List[Dict[str, str]]] = None # Added field

manager = ConnectionManager()

@app.post("/api/run-complete")
async def run_complete(event: RunCompleteEvent):
    # Push an explicit event so frontend can react
    await manager.broadcast({
        "type": "RUN_COMPLETE",
        "payload": {"report_url": event.report_url}
    })
    return {"ok": True}

def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])

@app.post("/api/allure/start")
async def allure_start():
    """
    Start Allure server (allure open) and return the URL.
    """
    port = _pick_free_port()
    subprocess.Popen(
        [ALLURE_CMD, "open", "-h", "127.0.0.1", "-p", str(port), ALLURE_REPORT_DIR],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )
    url = f"http://127.0.0.1:{port}"
    return JSONResponse({"url": url})

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
async def log_step(msg: LogMessage):
    # Broadcast log to UI immediately
    await manager.broadcast({
        "type": "LOG",
        "payload": {
            "message": msg.message,
            "status": msg.status,
        }
    })
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
        background_tasks.add_task(
                   run_tests_and_get_suggestions, 
                   apk_path, 
                   tests_to_run=request.tests_to_run
               )
        
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

@app.post("/start-test-existing")
async def start_test_existing(request: ExistingTestRequest, background_tasks: BackgroundTasks):
    """
    Start tests using an already-downloaded APK in backend/temp_apks.
    """
    try:
        apk_path = os.path.join(APKS_DIR, request.apk_name)

        if not os.path.isfile(apk_path):
            raise HTTPException(status_code=404, detail="APK not found on server")

        await manager.broadcast({
            "type": "LOG",
            "payload": {
                "message": f"Using existing APK: {request.apk_name}",
                "status": "INFO",
            }
        })

        # Extract icon / app info
        icon_url = extract_app_icon(apk_path)
        full_icon_url = f"http://localhost:8000{icon_url}" if icon_url else None

        info = get_apk_info(apk_path) or {}
        app_name = info.get("app_name")
        package_name = info.get("package_name")

        # Run tests in background
        background_tasks.add_task(
            run_tests_and_get_suggestions, 
            apk_path, 
            tests_to_run=request.tests_to_run
        )
        return {
            "status": "success",
            "message": "Using existing APK. Test Starting...",
            "app_icon": full_icon_url,
            "app_name": app_name,
            "package_name": package_name,
            "apk_path": apk_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        await manager.broadcast({
            "type": "LOG",
            "payload": {"message": f"Failed to start test: {str(e)}", "status": "FAILED"}
        })
        raise HTTPException(status_code=400, detail=f"Failed: {str(e)}")
    
@app.get("/api/apk-list")
async def list_apks():
    """
    Return list of already-downloaded APK files from backend/temp_apks.
    """
    try:
        files = []
        for name in os.listdir(APKS_DIR):
            if name.lower().endswith((".apk", ".apks")):
                files.append(name)
        return {"apks": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/stop-test")
async def stop_test():
    """
    Stop the currently running pytest process (if any).
    Called by the frontend Stop Test button.
    """
    print("DEBUG: /stop-test called") 
    stopped = stop_current_tests()
    print(f"DEBUG: stop_current_tests() -> {stopped}")

    if stopped:
        await manager.broadcast({
            "type": "LOG",
            "payload": {
                "message": "Backend: test process stopped on user request.",
                "status": "FAILED",
            }
        })
        return {"status": "stopped"}
    else:
        return {"status": "no-process"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
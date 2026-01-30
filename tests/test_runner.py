import os
import shutil
# Disable auto-loading of 3rd-party pytest plugins (like browserstack)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
import sys
import pytest
import allure_pytest  # pip install allure-pytest
import requests
import subprocess
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CURRENT_PROC: Optional[subprocess.Popen] = None

RESULTS_DIR = "allure-results"
REPORT_DIR = "allure-report"

def _ensure_clean_allure_dirs(project_root: str) -> None:
    os.makedirs(os.path.join(project_root, RESULTS_DIR), exist_ok=True)
    # Clean report dir (html) so you don’t open an old report
    report_path = os.path.join(project_root, REPORT_DIR)
    if os.path.isdir(report_path):
        shutil.rmtree(report_path, ignore_errors=True)

def _generate_and_open_allure_report(project_root: str) -> None:
    """
    Generates and opens Allure HTML report.
    """
    allure_cmd = r"C:\Users\ABDUL SAMAD\scoop\shims\allure"
    try:
        send_log("Generating Allure HTML report...", "INFO")
        subprocess.run(
            [allure_cmd, "generate", "allure-results", "-o", "allure-report", "--clean"],
            cwd=project_root,
            check=True,
            shell=True
        )
        send_log("Allure HTML report generated.", "SUCCESS")
        send_log("Opening Allure report in browser...", "INFO")
        subprocess.Popen(
            [allure_cmd, "open", "allure-report"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
    except Exception as e:
        send_log(f"Allure CLI not found or failed: {e}", "FAILED")

# def _generate_allure_report(project_root: str) -> None:
#     """
#     Generates HTML report into <project_root>/allure-report
#     Requires: Allure CLI installed and available in PATH.
#     """
#     try:
#         send_log("Generating Allure HTML report...", "INFO")
#         subprocess.run(
#             ["allure", "generate", RESULTS_DIR, "-o", REPORT_DIR, "--clean"],
#             cwd=project_root,
#             check=False,
#         )
#         send_log("Allure HTML report generated.", "SUCCESS")
#     except Exception:
#         send_log("Allure CLI not found or failed to generate report.", "FAILED")


# def notify_allure_open() -> None:
#     """
#     Ask backend to start Allure server (allure open/serve) and broadcast RUN_COMPLETE.
#     Backend should implement POST /api/allure/start.
#     """
#     try:
#         requests.post(f"{BACKEND_URL}/api/allure/start", timeout=10)
#     except Exception:
#         pass
    
def _notify_report_ready() -> None:
    try:
        report_url = f"{BACKEND_URL}/allure-report/index.html"
        requests.post(
            f"{BACKEND_URL}/api/run-complete",
            json={"report_url": report_url},
            timeout=3,
        )
        send_log(f"Allure report ready: {report_url}", "SUCCESS")
    except Exception:
        pass

def send_log(message: str, status: str = "INFO") -> None:
    """Send one log line to the frontend via /api/log-step."""
    try:
        requests.post(
            f"{BACKEND_URL}/api/log-step",
            json={"message": message, "status": status},
            timeout=3,
        )
    except Exception:
        # Don't break tests if backend logging fails
        pass

def run_pytest_with_logs(pytest_args, module_name: str) -> bool:
  """
  Run pytest in a subprocess and stream all stdout lines
  into the WebSocket log console.
  """
  send_module_status(module_name, "running", f"Starting {module_name} tests")
  send_log(f"==== Running {module_name} tests ====", "INFO")

  # Build command: python -m pytest <args>
  cmd = [os.sys.executable, "-m", "pytest"] + pytest_args

  proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    cwd=os.path.dirname(os.path.dirname(__file__)),  # project root
  )

  # Stream each line to frontend
  assert proc.stdout is not None
  for line in proc.stdout:
    send_log(line.rstrip("\n"), "INFO")

  proc.wait()
  success = (proc.returncode == 0)

  if success:
    send_module_status(module_name, "completed", f"{module_name} tests passed")
    send_log(f"{module_name} tests passed", "SUCCESS")
  else:
    send_module_status(module_name, "failed", f"{module_name} tests failed")
    send_log(f"{module_name} tests failed", "FAILED")

  return success

def send_module_status(module: str, status: str, message: str = ""):
    """Notify backend which module is running/completed."""
    try:
        requests.post(
            f"{BACKEND_URL}/api/module-status",
            json={"module": module, "status": status, "message": message},
            timeout=3,
        )
    except Exception:
        # Do not break tests if backend is down
        pass

def stop_current_tests() -> bool:
    global CURRENT_PROC
    if CURRENT_PROC is None:
        return False

    try:
        send_log("Stopping tests on user request...", "FAILED")
        CURRENT_PROC.terminate()
        try:
            CURRENT_PROC.wait(timeout=5)
        except subprocess.TimeoutExpired:
            CURRENT_PROC.kill()
        send_log("Test process terminated.", "FAILED")
    except Exception as e:
        send_log(f"Error while stopping tests: {e}", "FAILED")
    finally:
        CURRENT_PROC = None

    return True

def run_pytest_streaming(pytest_args: list[str], module_name: str, clean_allure: bool = False) -> bool:
    """
    Run pytest in a subprocess and stream ALL stdout lines to the frontend log console.
    Also writes allure results to allure-results.
    """
    global CURRENT_PROC

    project_root = os.path.dirname(os.path.dirname(__file__))

    send_module_status(module_name, "running", f"Starting {module_name} tests")
    send_log(f"==== Running {module_name} tests ====", "INFO")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p", "allure_pytest", 
        "-s",
        "-vv",
        f"--alluredir={RESULTS_DIR}",
    ]
    if clean_allure:
        cmd.append("--clean-alluredir")

    cmd += pytest_args

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    CURRENT_PROC = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    proc = CURRENT_PROC
    assert proc.stdout is not None
    for line in proc.stdout:
        send_log(line.rstrip("\n"), "INFO")

    proc.wait()
    ok = proc.returncode == 0
    CURRENT_PROC = None

    if ok:
        send_module_status(module_name, "completed", f"{module_name} tests passed")
        send_log(f"{module_name} tests passed", "SUCCESS")
    else:
        send_module_status(module_name, "failed", f"{module_name} tests failed")
        send_log(f"{module_name} tests failed", "FAILED")

    return ok

def run_tests_and_get_suggestions(apk_path: str) -> None:
    """
    Entry point called from FastAPI (background task).
    Runs tests -> generates Allure report -> asks backend to open Allure server.
    """
    project_root = os.path.dirname(os.path.dirname(__file__))

    if not os.path.exists(apk_path):
        send_log(f"APK not found at {apk_path}", "FAILED")
        return

    _ensure_clean_allure_dirs(project_root)

    send_log(f"Running tests for APK: {apk_path}", "INFO")

    overall_ok = True

    # First module: clean allure-results once at the start
    login_ok = run_pytest_streaming(
        ["tests/test_cases/state_client/test_login_pytest.py", f"--apk={apk_path}", "-v"],
        module_name="Login",
        clean_allure=True,
    )
    overall_ok = overall_ok and login_ok

    # Add more modules similarly (DO NOT clean_allure again)
    # dashboard_ok = run_pytest_streaming(
    #     ["tests/test_cases/test_dashboard_pytest.py", f"--apk={apk_path}", "-v"],
    #     module_name="Dashboard",
    # )
    # overall_ok = overall_ok and dashboard_ok

    if overall_ok:
        send_log("All modules passed", "SUCCESS")
    else:
        send_log("Some modules failed", "FAILED")

    # Generate report AFTER tests
    _generate_and_open_allure_report(project_root)

    # Tell backend to start Allure server and broadcast RUN_COMPLETE (frontend opens it)
    # notify_allure_open()

if __name__ == "__main__":
    # run_tests_and_get_suggestions()
    # Example usage for manual testing
    # import sys
    # if len(sys.argv) > 1:
    #     apk = sys.argv[1]
    # else:
    #     print("Usage: python tests/test_runner.py <apk_path>")
    #     sys.exit(1)
    # run_tests_and_get_suggestions(apk)
    import sys

    if len(sys.argv) <= 1:
        print("Usage: python tests/test_runner.py <apk_path>")
        raise SystemExit(1)

    run_tests_and_get_suggestions(sys.argv[1])
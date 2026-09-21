from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml.model_registry import public_model_metadata
import subprocess
import os
import threading
from urllib.error import URLError
from urllib.request import urlopen
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import threading
import time
import tempfile
from uuid import uuid4

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)
TERRAFORM_DIR = os.path.join(
    PROJECT_ROOT,
    "terraform"
)
OPERATION_FILE = os.path.join(tempfile.gettempdir(), "ai-iac-project-operation.json")
CONTAINER_NAME = "ai-iac-terraform"
OPERATION_TIMEOUT = 300

operation_lock = threading.Lock()
active_process = None
active_operation = None

app = FastAPI(
    title="AI Infrastructure Controller",
    description="Recoverable Terraform controller for the local AI service",
    version="2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_operation(operation):
    with open(OPERATION_FILE, 'w') as f:
        json.dump(operation, f, indent=2)


def public_operation(operation):
    if not operation:
        return None
    return {
        key: value
        for key, value in operation.items()
        if key not in {"command", "started_monotonic"}
    }


def load_saved_operation():
    if not os.path.exists(OPERATION_FILE):
        return None
    try:
        with open(OPERATION_FILE, 'r') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def terraform_process_running():
    try:
        result = subprocess.run(
            ["pgrep", "-af", r"terraform (plan|apply|destroy)"],
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())
    except OSError:
        return False


def run_command(command, timeout=20):
    environment = os.environ.copy()
    environment.setdefault("DOCKER_API_VERSION", "1.43")
    environment.setdefault("DOCKER_CONTEXT", "desktop-linux")
    try:
        result = subprocess.run(
            command,
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout} seconds."
    except OSError as error:
        return 127, "", f"Unable to run command: {error}"


def ai_service_is_healthy():
    try:
        with urlopen("http://127.0.0.1:8001/", timeout=3) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def docker_state():
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", CONTAINER_NAME],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return "OFFLINE"
        return "RUNNING" if result.stdout.strip() == "running" else result.stdout.strip().upper()
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"


def reconcile():
    global active_operation
    saved = load_saved_operation()
    with operation_lock:
        operation = active_operation or saved
    process_busy = terraform_process_running()

    if operation and operation.get("status") == "RUNNING" and not process_busy:
        operation["status"] = "RECONCILED"
        operation["finished_at"] = utc_now()
        operation["success"] = None
        operation["error"] = "Controller recovered after the Terraform process ended; inspect reconciled infrastructure state."
        operation.pop("started_monotonic", None)
        save_operation(operation)
        with operation_lock:
            if active_operation is operation:
                active_operation = None
        operation = None

    if process_busy:
        terraform = "BUSY"
    else:
        code, output, error = run_command(["terraform", "show", "-no-color"])
        terraform = "READY" if code == 0 else "ERROR"

    container = docker_state()
    ai_online = container == "RUNNING" and ai_service_is_healthy()
    return {
        "terraform": terraform,
        "docker": "ONLINE" if container == "RUNNING" else container,
        "container": container,
        "ai_service": "ONLINE" if ai_online else "OFFLINE",
        "deployed": ai_online,
        "container_name": CONTAINER_NAME,
        "image": "ai-iac-service:latest",
        "port": "8001 -> 8000",
        "operation": public_operation(operation) if process_busy else None,
    }


def finish_operation(operation, process, return_code, output, error, timed_out=False):
    global active_process, active_operation
    operation["finished_at"] = utc_now()
    operation["duration_seconds"] = round(time.monotonic() - operation["started_monotonic"], 2)
    operation["output"] = output[-12000:]
    operation["error"] = error[-4000:] if error else ""
    operation["success"] = return_code == 0 and not timed_out
    operation["status"] = "TIMEOUT" if timed_out else ("COMPLETED" if operation["success"] else "FAILED")
    operation.pop("started_monotonic", None)
    save_operation(operation)
    with operation_lock:
        active_process = None
        active_operation = None


def run_operation(operation):
    global active_process
    command = operation["command"]
    environment = os.environ.copy()
    environment.setdefault("DOCKER_API_VERSION", "1.43")
    environment.setdefault("DOCKER_CONTEXT", "desktop-linux")
    try:
        process = subprocess.Popen(
            command,
            cwd=TERRAFORM_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env=environment,
        )
        with operation_lock:
            active_process = process
        try:
            stdout, stderr = process.communicate(timeout=OPERATION_TIMEOUT)
            finish_operation(operation, process, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            finish_operation(operation, process, 124, stdout, stderr, timed_out=True)
    except OSError as error:
        finish_operation(operation, None, 127, "", str(error))


def start_operation(kind):
    global active_operation
    commands = {
        "plan": ["terraform", "plan", "-no-color"],
        "deploy": ["terraform", "apply", "-no-color", "-auto-approve"],
        "destroy": ["terraform", "destroy", "-no-color", "-auto-approve"],
    }
    with operation_lock:
        saved = load_saved_operation()
        if active_operation and active_operation.get("status") == "RUNNING":
            raise HTTPException(status_code=409, detail=active_operation)
        process_busy = terraform_process_running()
        if saved and saved.get("status") == "RUNNING" and not process_busy:
            saved["status"] = "RECONCILED"
            saved["finished_at"] = utc_now()
            saved["error"] = "Previous controller operation had no running Terraform process."
            save_operation(saved)
        if process_busy:
            raise HTTPException(status_code=409, detail="A Terraform operation is already in progress.")
        operation = {
            "operation_id": f"{kind}-{uuid4().hex[:12]}",
            "operation": kind,
            "command": commands[kind],
            "status": "RUNNING",
            "started_at": utc_now(),
            "finished_at": None,
            "success": None,
            "output": "",
            "error": "",
            "started_monotonic": time.monotonic(),
        }
        active_operation = operation
        save_operation(operation)
    thread = threading.Thread(target=run_operation, args=(operation,), daemon=True)
    thread.start()
    return public_operation(operation)


@app.get("/")
def home():
    return {"service": "AI Infrastructure Controller", "status": "active"}


@app.get("/status")
def infrastructure_status():
    state = reconcile()
    return {"success": state["terraform"] != "ERROR", **state}


@app.get("/diagnostics")
def diagnostics():
    state = reconcile()
    terraform_code, _, _ = run_command(["terraform", "version"], timeout=10)
    model_loaded = (Path(PROJECT_ROOT) / "ml" / "models" / "breast_cancer.pkl").exists()
    return {
        "controller": "ONLINE",
        "terraform": "AVAILABLE" if terraform_code == 0 else "OFFLINE",
        "terraform_state": state["terraform"],
        "docker": state["docker"],
        "container": state["container"],
        "ai_service": state["ai_service"],
        "model": "LOADED" if model_loaded else "MISSING",
        "operation": state["operation"],
    }


@app.get("/models")
def models():
    return {"models": public_model_metadata()}


@app.get("/operations/active")
def active_operation_status():
    state = reconcile()
    operation = state["operation"]
    if operation and operation.get("status") == "RUNNING":
        return {"operation": public_operation(operation)}
    return {"operation": None}


@app.get("/operations/{operation_id}")
def operation_status(operation_id: str):
    reconcile()
    with operation_lock:
        operation = active_operation if active_operation and active_operation.get("operation_id") == operation_id else load_saved_operation()
    if not operation or operation.get("operation_id") != operation_id:
        raise HTTPException(status_code=404, detail="Operation not found.")
    return public_operation(operation)


@app.post("/plan", status_code=202)
def plan_infrastructure():
    return start_operation("plan")


@app.post("/deploy", status_code=202)
def deploy_infrastructure():
    return start_operation("deploy")


@app.post("/destroy", status_code=202)
def destroy_infrastructure():
    return start_operation("destroy")


__all__ = ["app"]

__version__ = "2.0"

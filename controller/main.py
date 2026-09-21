from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import threading


app = FastAPI(
    title="AI Infrastructure Controller",
    description="Controller for Terraform-based AI infrastructure",
    version="1.0"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

TERRAFORM_DIR = os.path.join(
    PROJECT_ROOT,
    "terraform"
)


# --------------------------------------------------
# TERRAFORM OPERATION LOCK
# --------------------------------------------------

terraform_lock = threading.Lock()


# --------------------------------------------------
# TERRAFORM COMMAND
# --------------------------------------------------

def run_terraform(command):

    if not terraform_lock.acquire(blocking=False):

        raise HTTPException(
            status_code=409,
            detail="A Terraform operation is already in progress. Please wait for it to finish."
        )

    try:

        result = subprocess.run(
            command,
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "output": "",
            "error": "Terraform command timed out after 5 minutes."
        }

    except Exception as e:

        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

    finally:

        terraform_lock.release()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "service": "AI Infrastructure Controller",
        "status": "active"
    }


# --------------------------------------------------
# STATUS
# --------------------------------------------------

@app.get("/status")
def infrastructure_status():

    result = run_terraform([
        "terraform",
        "show",
        "-no-color"
    ])

    output = result["output"]

    deployed = (
        result["success"]
        and "ai-iac-terraform" in output
    )

    return {
        "success": result["success"],
        "deployed": deployed,
        "output": output,
        "error": result["error"]
    }


# --------------------------------------------------
# DEPLOY
# --------------------------------------------------

@app.post("/deploy")
def deploy_infrastructure():

    result = run_terraform([
        "terraform",
        "apply",
        "-no-color",
        "-auto-approve"
    ])

    return result


# --------------------------------------------------
# DESTROY
# --------------------------------------------------

@app.post("/destroy")
def destroy_infrastructure():

    result = run_terraform([
        "terraform",
        "destroy",
        "-no-color",
        "-auto-approve"
    ])

    return result
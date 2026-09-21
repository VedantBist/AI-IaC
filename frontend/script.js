// ============================================================
// AI-IAC FRONTEND CONTROLLER
// ============================================================

const CONTROLLER_URL = "http://127.0.0.1:9000";
const AI_SERVICE_URL = "http://127.0.0.1:8001";


// ============================================================
// DOM ELEMENTS
// ============================================================

const deployBtn = document.getElementById("deployBtn");
const destroyBtn = document.getElementById("destroyBtn");
const predictBtn = document.getElementById("predictBtn");

const clearActivity = document.getElementById("clearActivity");

const headerStatus = document.getElementById("headerStatus");

const terraformState = document.getElementById("terraformState");
const dockerState = document.getElementById("dockerState");
const aiState = document.getElementById("aiState");

const predictionResult = document.getElementById("predictionResult");
const predictionMeta = document.getElementById("predictionMeta");

const activityLog = document.getElementById("activityLog");


// ============================================================
// SAMPLE INPUT
// Breast Cancer dataset — 30 features
// ============================================================

const sampleFeatures = [
    17.99, 10.38, 122.8, 1001.0, 0.1184,
    0.2776, 0.3001, 0.1471, 0.2419, 0.07871,
    1.095, 0.9053, 8.589, 153.4, 0.006399,
    0.04904, 0.05373, 0.05373, 0.03003, 0.006193,
    25.38, 17.33, 184.6, 2019.0, 0.1622,
    0.6656, 0.7119, 0.2654, 0.4601, 0.1189
];


// ============================================================
// HELPERS
// ============================================================

function getTime() {

    return new Date().toLocaleTimeString(
        [],
        {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false
        }
    );
}


function addLog(message, type = "") {

    const line = document.createElement("div");

    line.className = `log-line ${type}`;

    line.innerHTML = `
        <span class="log-time">${getTime()}</span>
        <span>${escapeHtml(message)}</span>
    `;

    activityLog.appendChild(line);

    activityLog.scrollTop = activityLog.scrollHeight;
}


function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


function setState(element, state) {

    element.textContent = state.toUpperCase();

    const indicator = element
        .parentElement
        .querySelector(".state-indicator");

    if (!indicator) return;

    indicator.classList.remove(
        "ready",
        "offline",
        "loading"
    );

    const normalized = state.toLowerCase();

    if (
        normalized === "online" ||
        normalized === "running" ||
        normalized === "ready"
    ) {

        indicator.classList.add("ready");

    } else if (
        normalized === "offline" ||
        normalized === "error"
    ) {

        indicator.classList.add("offline");

    } else {

        indicator.classList.add("loading");

    }
}


function setButtonsDisabled(disabled) {

    deployBtn.disabled = disabled;
    destroyBtn.disabled = disabled;
    predictBtn.disabled = disabled;
}


function setHeaderStatus(text) {

    headerStatus.textContent = text.toUpperCase();
}


// ============================================================
// CHECK INFRASTRUCTURE STATUS
// ============================================================

async function checkStatus(log = false) {

    try {

        const response = await fetch(
            `${CONTROLLER_URL}/status`
        );

        if (!response.ok) {
            throw new Error(
                `Controller returned HTTP ${response.status}`
            );
        }

        const data = await response.json();

        if (data.success && data.deployed) {

            setState(terraformState, "READY");
            setState(dockerState, "RUNNING");
            setState(aiState, "ONLINE");

            setHeaderStatus("SYSTEM ONLINE");

            if (log) {
                addLog(
                    "Infrastructure is active.",
                    "system-log"
                );
            }

        } else {

            setState(terraformState, "READY");
            setState(dockerState, "OFFLINE");
            setState(aiState, "OFFLINE");

            setHeaderStatus("INFRASTRUCTURE OFFLINE");

            if (log) {
                addLog(
                    "Infrastructure is currently offline.",
                    "system-log"
                );
            }
        }

        return data;

    } catch (error) {

        setState(terraformState, "ERROR");
        setState(dockerState, "UNKNOWN");
        setState(aiState, "UNKNOWN");

        setHeaderStatus("CONTROLLER ERROR");

        if (log) {
            addLog(
                `Controller connection failed: ${error.message}`
            );
        }

        return null;
    }
}


// ============================================================
// DEPLOY
// ============================================================

async function deployInfrastructure() {

    setButtonsDisabled(true);

    setState(terraformState, "DEPLOYING");
    setState(dockerState, "WAITING");
    setState(aiState, "WAITING");

    setHeaderStatus("DEPLOYING");

    addLog(
        "Starting infrastructure deployment..."
    );

    try {

        const response = await fetch(
            `${CONTROLLER_URL}/deploy`,
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Terraform deployment request failed."
            );
        }

        if (data.success) {

            addLog(
                "Terraform deployment completed successfully.",
                "system-log"
            );

            addLog(
                "Docker container created by Terraform."
            );

            await new Promise(
                resolve => setTimeout(resolve, 1000)
            );

            await checkStatus();

            predictionResult.textContent = "—";

            predictionMeta.textContent =
                "Infrastructure restored. Ready for inference.";

        } else {

            addLog(
                "Terraform deployment failed."
            );

            if (data.error) {

                addLog(
                    data.error
                );
            }

            setState(terraformState, "ERROR");
            setState(dockerState, "OFFLINE");
            setState(aiState, "OFFLINE");

            setHeaderStatus("DEPLOYMENT FAILED");
        }

    } catch (error) {

        addLog(
            `Deployment error: ${error.message}`
        );

        setState(terraformState, "ERROR");
        setState(dockerState, "OFFLINE");
        setState(aiState, "OFFLINE");

        setHeaderStatus("DEPLOYMENT FAILED");

    } finally {

        setButtonsDisabled(false);
    }
}


// ============================================================
// DESTROY
// ============================================================

async function destroyInfrastructure() {

    setButtonsDisabled(true);

    setState(terraformState, "DESTROYING");
    setState(dockerState, "STOPPING");
    setState(aiState, "OFFLINE");

    setHeaderStatus("DESTROYING");

    addLog(
        "Starting infrastructure destruction..."
    );

    try {

        const response = await fetch(
            `${CONTROLLER_URL}/destroy`,
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Terraform destroy request failed."
            );
        }

        if (data.success) {

            addLog(
                "Terraform destroy completed successfully.",
                "system-log"
            );

            addLog(
                "AI infrastructure has been removed."
            );

            setState(terraformState, "READY");
            setState(dockerState, "OFFLINE");
            setState(aiState, "OFFLINE");

            setHeaderStatus(
                "INFRASTRUCTURE OFFLINE"
            );

            predictionResult.textContent = "—";

            predictionMeta.textContent =
                "AI service is not currently reachable.";

        } else {

            addLog(
                "Terraform destruction failed."
            );

            if (data.error) {
                addLog(data.error);
            }

            setState(terraformState, "ERROR");

            setHeaderStatus(
                "DESTRUCTION FAILED"
            );
        }

    } catch (error) {

        addLog(
            `Destruction error: ${error.message}`
        );

        setState(terraformState, "ERROR");

        setHeaderStatus(
            "DESTRUCTION FAILED"
        );

    } finally {

        setButtonsDisabled(false);
    }
}


// ============================================================
// RUN PREDICTION
// ============================================================

async function runPrediction() {

    predictBtn.disabled = true;

    predictionResult.textContent =
        "PROCESSING";

    predictionMeta.textContent =
        "Sending inference request to AI service...";

    addLog(
        "Sending prediction request to AI service..."
    );

    try {

        const response = await fetch(
            `${AI_SERVICE_URL}/predict`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    features: sampleFeatures
                })
            }
        );

        if (!response.ok) {

            throw new Error(
                `AI service returned HTTP ${response.status}`
            );
        }

        const data = await response.json();

        predictionResult.textContent =
            data.prediction.toUpperCase();

        predictionMeta.textContent =
            `Class ${data.class} · Live inference completed`;

        addLog(
            `Prediction completed: ${data.prediction}`,
            "system-log"
        );

        setState(aiState, "ONLINE");

    } catch (error) {

        predictionResult.textContent =
            "UNAVAILABLE";

        predictionMeta.textContent =
            "AI service is not currently reachable.";

        addLog(
            `Prediction failed: ${error.message}`
        );

        setState(aiState, "OFFLINE");

    } finally {

        predictBtn.disabled = false;
    }
}


// ============================================================
// CLEAR ACTIVITY
// ============================================================

clearActivity.addEventListener(
    "click",
    () => {

        activityLog.innerHTML = "";

        addLog(
            "Activity console cleared.",
            "system-log"
        );

    }
);


// ============================================================
// BUTTON EVENTS
// ============================================================

deployBtn.addEventListener(
    "click",
    deployInfrastructure
);


destroyBtn.addEventListener(
    "click",
    destroyInfrastructure
);


predictBtn.addEventListener(
    "click",
    runPrediction
);


// ============================================================
// INITIALIZATION
// ============================================================

async function initializeDashboard() {

    addLog(
        "AI Infrastructure Control initialized.",
        "system-log"
    );

    addLog(
        "Connecting to controller..."
    );

    await checkStatus(true);
}


initializeDashboard();
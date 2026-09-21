const CONTROLLER_URL = "http://127.0.0.1:9000";
const AI_SERVICE_URL = "http://127.0.0.1:8001";
const POLL_INTERVAL = 1500;
const MAX_POLL_TIME = 5 * 60 * 1000;

const elements = {
    deploy: document.getElementById("deployBtn"), plan: document.getElementById("planBtn"), destroy: document.getElementById("destroyBtn"), diagnostics: document.getElementById("diagnosticsBtn"), demo: document.getElementById("demoBtn"), predict: document.getElementById("predictBtn"), sample: document.getElementById("sampleBtn"), model: document.getElementById("modelSelect"), inputs: document.getElementById("featureInputs"), catalogue: document.getElementById("modelCatalogue"), terraform: document.getElementById("terraformState"), docker: document.getElementById("dockerState"), ai: document.getElementById("aiState"), stateLabel: document.getElementById("stateLabel"), header: document.getElementById("headerStatus"), terminalStatus: document.getElementById("terminalStatus"), log: document.getElementById("activityLog"), result: document.getElementById("predictionResult"), resultMeta: document.getElementById("predictionMeta"), history: document.getElementById("predictionHistory"), deployHistory: document.getElementById("deploymentHistory"),
};
let registry = {};
let operationId = null;
let operationPoll = null;

const getTime = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
const escapeHtml = (value) => { const div = document.createElement("div"); div.textContent = value; return div.innerHTML; };

function addLog(message, type = "") {
    const line = document.createElement("div"); line.className = `log-line ${type}`;
    line.innerHTML = `<span class="log-time">${getTime()}</span><span>${escapeHtml(message)}</span>`;
    elements.log.appendChild(line); elements.log.scrollTop = elements.log.scrollHeight;
}

function setState(element, state) {
    element.textContent = state.toUpperCase();
    const indicator = element.parentElement.querySelector(".state-indicator");
    indicator.classList.remove("ready", "offline", "loading");
    const normalized = state.toLowerCase();
    indicator.classList.add(["online", "running", "ready"].includes(normalized) ? "ready" : ["offline", "error"].includes(normalized) ? "offline" : "loading");
}

function setInfrastructureState(state) {
    elements.stateLabel.textContent = state; elements.header.textContent = state === "READY" ? "SYSTEM ONLINE" : state === "OFFLINE" ? "INFRASTRUCTURE OFFLINE" : `TERRAFORM ${state}`; elements.terminalStatus.textContent = state;
    const busy = ["PLANNING", "DEPLOYING", "DESTROYING", "BUSY", "TIMEOUT"].includes(state);
    elements.deploy.disabled = busy || state === "READY"; elements.destroy.disabled = busy || state === "OFFLINE" || state === "UNKNOWN"; elements.plan.disabled = busy; elements.demo.disabled = busy; elements.predict.disabled = busy || state !== "READY";
}

function renderStatus(data) {
    setState(elements.terraform, data.terraform || "UNKNOWN"); setState(elements.docker, data.docker || "UNKNOWN"); setState(elements.ai, data.ai_service || "UNKNOWN");
    document.getElementById("containerName").textContent = data.container_name || "ai-iac-terraform"; document.getElementById("imageName").textContent = data.image || "ai-iac-service:latest"; document.getElementById("portMapping").textContent = data.port || "8001 -> 8000";
    const operationState = data.operation ? `${data.operation.operation.toUpperCase()}ING` : data.deployed ? "READY" : data.terraform === "ERROR" ? "ERROR" : "OFFLINE"; setInfrastructureState(operationState);
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, options); let data = {};
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok) { const detail = typeof data.detail === "string" ? data.detail : data.detail?.error || "Request failed."; throw new Error(detail); }
    return data;
}

async function checkStatus(log = false) {
    try { const data = await requestJson(`${CONTROLLER_URL}/status`); renderStatus(data); if (log) addLog(data.deployed ? "Infrastructure is online." : `Infrastructure is ${data.terraform.toLowerCase()}.`, "system-log"); return data; }
    catch (_) { setState(elements.terraform, "UNKNOWN"); setState(elements.docker, "UNKNOWN"); setState(elements.ai, "UNKNOWN"); setInfrastructureState("ERROR"); if (log) addLog("Infrastructure controller is unavailable."); return null; }
}

async function recoverOperation() {
    try { const response = await requestJson(`${CONTROLLER_URL}/operations/active`); if (response.operation?.status === "RUNNING") { operationId = response.operation.operation_id; addLog(`Recovered ${response.operation.operation} operation ${operationId}.`); pollOperation(); } }
    catch (_) { addLog("Could not recover operation history."); }
}

function buttonLabel(button, text) { const label = button.querySelector("span") || button; if (!button.dataset.defaultText) button.dataset.defaultText = label.textContent; label.textContent = text; }
function restoreButton(button) { const label = button.querySelector("span") || button; if (button.dataset.defaultText) label.textContent = button.dataset.defaultText; }

async function startOperation(kind) {
    if (kind === "destroy" && !window.confirm("Destroy the Terraform-managed AI infrastructure?")) return;
    const button = elements[kind]; buttonLabel(button, `${kind[0].toUpperCase() + kind.slice(1)}ing...`); setInfrastructureState(`${kind.toUpperCase()}ING`); addLog(`Starting Terraform ${kind} operation...`);
    try { const data = await requestJson(`${CONTROLLER_URL}/${kind}`, { method: "POST" }); operationId = data.operation_id; addLog(`Operation ${operationId} accepted.`); saveHistory("deployments", { event: `${kind} started`, time: getTime() }); renderHistory(); return pollOperation(); }
    catch (error) { addLog(error.message); setInfrastructureState("BUSY"); restoreButton(button); }
}

function pollOperation() {
    if (operationPoll) clearInterval(operationPoll); const started = Date.now();
    return new Promise((resolve) => { operationPoll = setInterval(async () => {
        if (Date.now() - started > MAX_POLL_TIME) { clearInterval(operationPoll); operationPoll = null; setInfrastructureState("TIMEOUT"); addLog("Frontend polling limit reached; reconciling actual infrastructure."); await checkStatus(true); resolve(null); return; }
        try { const operation = await requestJson(`${CONTROLLER_URL}/operations/${operationId}`); const state = operation.status; setInfrastructureState(state === "RUNNING" ? `${operation.operation.toUpperCase()}ING` : state === "COMPLETED" ? "READY" : state === "TIMEOUT" ? "TIMEOUT" : "ERROR");
            if (state !== "RUNNING") { clearInterval(operationPoll); operationPoll = null; addLog(`${operation.operation} ${state.toLowerCase()}.`, operation.success ? "system-log" : ""); if (operation.output) addLog(operation.output.slice(-500)); await checkStatus(); restoreButton(elements.deploy); restoreButton(elements.plan); restoreButton(elements.destroy); resolve(operation); }
        } catch (error) { addLog(`Operation status unavailable: ${error.message}`); }
    }, POLL_INTERVAL); });
}

function renderModel(model) {
    if (!model) return;
    document.getElementById("modelDescription").textContent = model.description; document.getElementById("modelAlgorithm").textContent = model.algorithm; document.getElementById("modelTask").textContent = model.task; document.getElementById("modelFeatures").textContent = model.features; document.getElementById("modelDataset").textContent = model.dataset; document.getElementById("modelOutput").textContent = model.output;
    elements.inputs.innerHTML = model.feature_names?.length ? model.feature_names.map((name, index) => `<label>${escapeHtml(name)}<input type="number" step="any" data-feature="${index}" value="${model.sample[index]}"></label>`).join("") : `<div class="sample-summary">${model.features} numeric features ready in the sample vector.</div>`;
}
function selectedModel() { return registry[elements.model.value]; }
function sampleValues() { const model = selectedModel(); return model.feature_names?.length ? [...elements.inputs.querySelectorAll("input")].map((input) => Number(input.value)) : model.sample; }
function renderCatalogue() { elements.catalogue.innerHTML = Object.values(registry).map((model) => `<article class="model-item"><strong>${escapeHtml(model.display_name)}</strong><span>${escapeHtml(model.algorithm)}</span><small>${escapeHtml(model.task)}</small></article>`).join(""); }

async function loadModels() {
    let data;
    try { data = await requestJson(`${AI_SERVICE_URL}/models`); }
    catch (_) { data = await requestJson(`${CONTROLLER_URL}/models`); addLog("AI service is offline; loaded the model registry from the controller.", "system-log"); }
    registry = Object.fromEntries(data.models.map((model) => [model.model_id, model])); elements.model.innerHTML = Object.values(registry).map((model) => `<option value="${model.model_id}">${escapeHtml(model.display_name)}</option>`).join(""); renderCatalogue(); renderModel(selectedModel());
}

async function runPrediction() {
    const model = selectedModel(); const features = sampleValues();
    if (!model || features.length !== model.features || features.some((value) => !Number.isFinite(value))) { elements.result.textContent = "INVALID INPUT"; elements.resultMeta.textContent = `Enter exactly ${model?.features || "the required number of"} numeric features.`; return; }
    buttonLabel(elements.predict, "Running..."); elements.predict.disabled = true; elements.result.textContent = "PROCESSING"; elements.resultMeta.textContent = "Sending inference request..."; addLog(`${model.display_name} prediction requested.`);
    try { const data = await requestJson(`${AI_SERVICE_URL}/predict`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model: model.model_id, features }) }); elements.result.textContent = String(data.prediction).toUpperCase(); elements.resultMeta.textContent = `${data.class === null ? "Regression output" : `Class ${data.class}`} / Live inference completed`; addLog(`Result: ${data.prediction}`, "system-log"); saveHistory("predictions", { model: model.display_name, result: data.prediction, time: getTime() }); renderHistory(); }
    catch (error) { elements.result.textContent = "UNAVAILABLE"; elements.resultMeta.textContent = error.message; addLog(error.message); }
    finally { restoreButton(elements.predict); await checkStatus(); }
}

async function runDemo() {
    const status = await checkStatus(true);
    if (!status?.deployed) {
        addLog("Demo requires infrastructure; starting deployment.");
        await startOperation("deploy");
        const deployed = await checkStatus(true);
        if (!deployed?.deployed) return;
    }
    await runPrediction();
}

function saveHistory(key, item) { const items = JSON.parse(localStorage.getItem(key) || "[]"); localStorage.setItem(key, JSON.stringify([item, ...items].slice(0, 12))); }
function renderHistory() { const prediction = JSON.parse(localStorage.getItem("predictions") || "[]"); const deployments = JSON.parse(localStorage.getItem("deployments") || "[]"); elements.history.innerHTML = prediction.length ? prediction.map((item) => `<div class="history-row"><span>${escapeHtml(item.model)}</span><strong>${escapeHtml(String(item.result))}</strong><small>${escapeHtml(item.time)}</small></div>`).join("") : `<div class="empty-history">No predictions yet.</div>`; elements.deployHistory.innerHTML = deployments.length ? deployments.map((item) => `<div class="history-row"><span>${escapeHtml(item.event)}</span><small>${escapeHtml(item.time)}</small></div>`).join("") : `<div class="empty-history">No deployment events yet.</div>`; }
async function showDiagnostics() { try { const data = await requestJson(`${CONTROLLER_URL}/diagnostics`); Object.entries(data).filter(([key]) => key !== "operation").forEach(([key, value]) => addLog(`${key}: ${value}`)); } catch (error) { addLog(`Diagnostics unavailable: ${error.message}`); } }

elements.model.addEventListener("change", () => renderModel(selectedModel())); elements.sample.addEventListener("click", () => renderModel(selectedModel())); elements.predict.addEventListener("click", runPrediction); elements.deploy.addEventListener("click", () => startOperation("deploy")); elements.plan.addEventListener("click", () => startOperation("plan")); elements.destroy.addEventListener("click", () => startOperation("destroy")); elements.diagnostics.addEventListener("click", showDiagnostics); elements.demo.addEventListener("click", runDemo);
document.getElementById("clearActivity").addEventListener("click", () => { elements.log.innerHTML = ""; addLog("Activity console cleared.", "system-log"); }); document.getElementById("clearHistory").addEventListener("click", () => { localStorage.removeItem("predictions"); localStorage.removeItem("deployments"); renderHistory(); });

async function initialize() { addLog("AI Infrastructure Control initialized.", "system-log"); renderHistory(); try { await loadModels(); } catch (error) { addLog(`Model registry unavailable: ${error.message}`); } await checkStatus(true); await recoverOperation(); }
initialize();

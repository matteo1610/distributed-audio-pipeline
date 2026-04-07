const dom = {
  apiBase: document.getElementById("apiBase"),
  registerForm: document.getElementById("registerForm"),
  loginForm: document.getElementById("loginForm"),
  uploadForm: document.getElementById("uploadForm"),
  audioFile: document.getElementById("audioFile"),
  meBtn: document.getElementById("meBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  statusForm: document.getElementById("statusForm"),
  resultsBtn: document.getElementById("resultsBtn"),
  healthBtn: document.getElementById("healthBtn"),
  metricsBtn: document.getElementById("metricsBtn"),
  startPollingBtn: document.getElementById("startPollingBtn"),
  stopPollingBtn: document.getElementById("stopPollingBtn"),
  clearLogBtn: document.getElementById("clearLogBtn"),
  logOutput: document.getElementById("logOutput"),
  lastJobId: document.getElementById("lastJobId"),
  jobIdInput: document.getElementById("jobIdInput"),
};

const storageKeys = {
  apiBase: "pipeline.apiBase",
  token: "pipeline.token",
  lastJobId: "pipeline.lastJobId",
};

let pollingHandle = null;

function now() {
  return new Date().toLocaleTimeString();
}

function log(message, kind = "info") {
  const line = `[${now()}] ${message}`;
  dom.logOutput.textContent += `${line}\n`;
  dom.logOutput.scrollTop = dom.logOutput.scrollHeight;
  if (kind === "warn") {
    console.warn(line);
  } else {
    console.log(line);
  }
}

function getApiBase() {
  return dom.apiBase.value.trim().replace(/\/$/, "");
}

function getToken() {
  return localStorage.getItem(storageKeys.token) || "";
}

function setToken(token) {
  if (token) {
    localStorage.setItem(storageKeys.token, token);
  } else {
    localStorage.removeItem(storageKeys.token);
  }
}

function setLastJobId(jobId) {
  dom.lastJobId.textContent = jobId || "none";
  dom.jobIdInput.value = jobId || "";
  if (jobId) {
    localStorage.setItem(storageKeys.lastJobId, jobId);
  }
}

async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      detail = data.detail || JSON.stringify(data);
    } catch (_err) {
      const fallback = await response.text();
      if (fallback) {
        detail = fallback;
      }
    }
    throw new Error(detail);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function requireToken() {
  const token = getToken();
  if (!token) {
    throw new Error("No token found. Please login first.");
  }
}

async function fetchStatus(jobId) {
  const status = await apiRequest(`/api/jobs/${jobId}`);
  log(`Job ${status.job_id} status: ${status.status}`);
  if (status.error_message) {
    log(`Job error: ${status.error_message}`, "warn");
  }
  return status;
}

function startPolling() {
  const jobId = dom.jobIdInput.value.trim();
  if (!jobId) {
    log("Enter a job ID before polling.", "warn");
    return;
  }

  stopPolling();
  pollingHandle = setInterval(async () => {
    try {
      requireToken();
      const status = await fetchStatus(jobId);
      if (["completed", "failed"].includes(status.status)) {
        stopPolling();
        log(`Polling stopped because job is ${status.status}.`);
      }
    } catch (err) {
      stopPolling();
      log(`Polling stopped: ${err.message}`, "warn");
    }
  }, 2000);

  log(`Started polling for job ${jobId} every 2s.`);
}

function stopPolling() {
  if (pollingHandle) {
    clearInterval(pollingHandle);
    pollingHandle = null;
  }
}

function wireEvents() {
  dom.apiBase.addEventListener("change", () => {
    const value = getApiBase();
    localStorage.setItem(storageKeys.apiBase, value);
    log(`API base updated to ${value}`);
  });

  dom.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(dom.registerForm);
    const payload = {
      username: String(fd.get("username") || ""),
      email: String(fd.get("email") || ""),
      password: String(fd.get("password") || ""),
    };

    try {
      const user = await apiRequest("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      log(`Registered user ${user.username}.`);
      dom.registerForm.reset();
    } catch (err) {
      log(`Register failed: ${err.message}`, "warn");
    }
  });

  dom.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(dom.loginForm);

    try {
      const body = new URLSearchParams({
        username: String(fd.get("username") || ""),
        password: String(fd.get("password") || ""),
      });
      const tokenResponse = await apiRequest("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      setToken(tokenResponse.access_token);
      log("Login successful. Token stored in localStorage.");
    } catch (err) {
      log(`Login failed: ${err.message}`, "warn");
    }
  });

  dom.logoutBtn.addEventListener("click", () => {
    setToken("");
    stopPolling();
    log("Logged out.");
  });

  dom.meBtn.addEventListener("click", async () => {
    try {
      requireToken();
      const me = await apiRequest("/auth/me");
      log(`Current user: ${me.username} (${me.email})`);
    } catch (err) {
      log(`Me request failed: ${err.message}`, "warn");
    }
  });

  dom.uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = dom.audioFile.files?.[0];
    if (!file) {
      log("Choose a file first.", "warn");
      return;
    }

    try {
      requireToken();
      const formData = new FormData();
      formData.append("file", file);
      const result = await apiRequest("/api/uploads", {
        method: "POST",
        body: formData,
      });
      setLastJobId(result.job_id);
      log(`Upload accepted. Job ID: ${result.job_id}`);
    } catch (err) {
      log(`Upload failed: ${err.message}`, "warn");
    }
  });

  dom.statusForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      requireToken();
      const jobId = dom.jobIdInput.value.trim();
      if (!jobId) {
        throw new Error("Job ID is required");
      }
      await fetchStatus(jobId);
    } catch (err) {
      log(`Status request failed: ${err.message}`, "warn");
    }
  });

  dom.resultsBtn.addEventListener("click", async () => {
    try {
      requireToken();
      const jobId = dom.jobIdInput.value.trim();
      if (!jobId) {
        throw new Error("Job ID is required");
      }
      const results = await apiRequest(`/api/jobs/${jobId}/results`);
      log(`Results for ${results.job_id}: ${JSON.stringify(results.features)}`);
    } catch (err) {
      log(`Results request failed: ${err.message}`, "warn");
    }
  });

  dom.healthBtn.addEventListener("click", async () => {
    try {
      const health = await apiRequest("/health");
      log(`Health: ${JSON.stringify(health)}`);
    } catch (err) {
      log(`Health check failed: ${err.message}`, "warn");
    }
  });

  dom.metricsBtn.addEventListener("click", async () => {
    try {
      const metrics = await apiRequest("/metrics");
      const lines = metrics
        .split("\n")
        .filter((line) => line && !line.startsWith("#"))
        .slice(0, 12);
      log(`Metrics sample:\n${lines.join("\n")}`);
    } catch (err) {
      log(`Metrics fetch failed: ${err.message}`, "warn");
    }
  });

  dom.startPollingBtn.addEventListener("click", () => {
    try {
      requireToken();
      startPolling();
    } catch (err) {
      log(err.message, "warn");
    }
  });

  dom.stopPollingBtn.addEventListener("click", () => {
    stopPolling();
    log("Polling stopped.");
  });

  dom.clearLogBtn.addEventListener("click", () => {
    dom.logOutput.textContent = "";
  });
}

function boot() {
  const savedApiBase = localStorage.getItem(storageKeys.apiBase);
  const savedJobId = localStorage.getItem(storageKeys.lastJobId);
  if (savedApiBase) {
    dom.apiBase.value = savedApiBase;
  }
  if (savedJobId) {
    setLastJobId(savedJobId);
  }

  wireEvents();
  log("Console ready.");
}

boot();

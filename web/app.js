const platformSelect = document.getElementById("platformSelect");
const accountPlatformSelect = document.getElementById("accountPlatformSelect");
const urlTableBody = document.getElementById("urlTableBody");
const addForm = document.getElementById("addForm");
const accountForm = document.getElementById("accountForm");
const runScrapeBtn = document.getElementById("runScrapeBtn");
const downloadBtn = document.getElementById("downloadBtn");
const downloadPlatformSelect = document.getElementById("downloadPlatformSelect");
const progressContainer = document.getElementById("progressContainer");
const statusLog = document.getElementById("statusLog");

const platformMap = new Map();
const progressBars = new Map();

function logStatus(message) {
  const div = document.createElement("div");
  div.className = "status-line";
  div.textContent = message;
  statusLog.prepend(div);
}

async function loadPlatforms() {
  const res = await fetch("/api/platforms");
  const platforms = await res.json();
  platformSelect.innerHTML = "";
  accountPlatformSelect.innerHTML = "";
  downloadPlatformSelect.innerHTML = "";
  platforms.forEach((p) => {
    platformMap.set(p.id, p.name);
    const option = document.createElement("option");
    option.value = p.name;
    option.textContent = p.name;
    platformSelect.appendChild(option);
    accountPlatformSelect.appendChild(option.cloneNode(true));
    downloadPlatformSelect.appendChild(option.cloneNode(true));
  });
}

async function loadUrls() {
  const res = await fetch("/api/monitored-urls");
  const urls = await res.json();
  urlTableBody.innerHTML = "";
  urls.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${platformMap.get(u.platform_id) || u.platform_id}</td>
      <td class="url-cell">${u.url}</td>
      <td>${u.label || ""}</td>
      <td>
        <input type="checkbox" ${u.is_active ? "checked" : ""} data-id="${u.id}" class="active-toggle" />
      </td>
      <td>${u.last_checked_at || "-"}</td>
      <td><button data-id="${u.id}" class="delete-btn">Delete</button></td>
    `;
    urlTableBody.appendChild(tr);
  });
}

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    platform: platformSelect.value,
    url: document.getElementById("urlInput").value,
    label: document.getElementById("labelInput").value || null,
    is_active: document.getElementById("activeInput").checked,
  };

  const res = await fetch("/api/monitored-urls", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    addForm.reset();
    document.getElementById("activeInput").checked = true;
    await loadUrls();
  } else {
    logStatus("Failed to add URL");
  }
});

accountForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    platform: accountPlatformSelect.value,
    username: document.getElementById("accountUsername").value,
    email: document.getElementById("accountEmail").value || null,
    password: document.getElementById("accountPassword").value,
    is_active: document.getElementById("accountActive").checked,
  };

  const res = await fetch("/api/accounts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    accountForm.reset();
    document.getElementById("accountActive").checked = true;
    logStatus("Account added");
  } else {
    logStatus("Failed to add account");
  }
});

urlTableBody.addEventListener("click", async (e) => {
  if (e.target.classList.contains("delete-btn")) {
    const id = e.target.dataset.id;
    await fetch(`/api/monitored-urls/${id}`, { method: "DELETE" });
    await loadUrls();
  }
});

urlTableBody.addEventListener("change", async (e) => {
  if (e.target.classList.contains("active-toggle")) {
    const id = e.target.dataset.id;
    await fetch(`/api/monitored-urls/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: e.target.checked }),
    });
    await loadUrls();
  }
});

runScrapeBtn.addEventListener("click", async () => {
  const res = await fetch("/api/run-scrape", { method: "POST" });
  if (!res.ok) {
    const data = await res.json();
    logStatus(data.detail || "Scrape already running");
  }
});

downloadBtn.addEventListener("click", () => {
  const platform = downloadPlatformSelect.value;
  window.location.href = `/api/download-new?platform=${encodeURIComponent(platform)}`;
});

function ensureProgressBar(platform) {
  if (progressBars.has(platform)) return progressBars.get(platform);

  const wrapper = document.createElement("div");
  wrapper.className = "progress-block";
  const title = document.createElement("div");
  title.className = "progress-title";
  title.textContent = platform;
  const bar = document.createElement("div");
  bar.className = "progress-bar";
  const fill = document.createElement("div");
  fill.className = "progress-fill";
  bar.appendChild(fill);
  const label = document.createElement("div");
  label.className = "progress-label";
  label.textContent = "0%";

  wrapper.appendChild(title);
  wrapper.appendChild(bar);
  wrapper.appendChild(label);
  progressContainer.appendChild(wrapper);

  const entry = { fill, label };
  progressBars.set(platform, entry);
  return entry;
}

function updateProgress(platform, percent, message) {
  const entry = ensureProgressBar(platform);
  entry.fill.style.width = `${percent}%`;
  entry.label.textContent = `${percent}% ${message || ""}`.trim();
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "status") {
      logStatus(data.message);
    }
    if (data.type === "progress") {
      updateProgress(data.platform, data.percent, data.stage);
    }
    if (data.type === "milestone") {
      updateProgress(data.platform, data.current ? Math.round((data.current / data.total) * 100) : 0, data.stage);
    }
    if (data.type === "done") {
      updateProgress(data.platform, 100, "done");
      logStatus(`${data.platform} saved ${data.saved} posts`);
    }
    if (data.type === "error") {
      logStatus(`${data.platform}: ${data.message}`);
    }
  };

  ws.onclose = () => {
    setTimeout(connectWebSocket, 2000);
  };
}

async function init() {
  await loadPlatforms();
  await loadUrls();
  connectWebSocket();
}

init();

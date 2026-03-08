const platformSelect = document.getElementById("platformSelect");
const accountPlatformSelect = document.getElementById("accountPlatformSelect");
const urlTableBody = document.getElementById("urlTableBody");
const activeUrlTableBody = document.getElementById("activeUrlTableBody");
const accountsTableBody = document.getElementById("accountsTableBody");
const addForm = document.getElementById("addForm");
const accountForm = document.getElementById("accountForm");
const runScrapeBtn = document.getElementById("runScrapeBtn");
const downloadBtn = document.getElementById("downloadBtn");
const progressContainer = document.getElementById("progressContainer");
const statusLog = document.getElementById("statusLog");

const filterPlatform = document.getElementById("filterPlatform");
const filterActive = document.getElementById("filterActive");
const filterSearch = document.getElementById("filterSearch");
const prevPage = document.getElementById("prevPage");
const nextPage = document.getElementById("nextPage");
const pageInfo = document.getElementById("pageInfo");
const urlsPrevPage = document.getElementById("urlsPrevPage");
const urlsNextPage = document.getElementById("urlsNextPage");
const urlsPageInfo = document.getElementById("urlsPageInfo");

const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const closeSettingsBtn = document.getElementById("closeSettingsBtn");
const openAccountsBtn = document.getElementById("openAccountsBtn");
const openUrlsBtn = document.getElementById("openUrlsBtn");
const openPlatformsBtn = document.getElementById("openPlatformsBtn");
const accountsModal = document.getElementById("accountsModal");
const urlsModal = document.getElementById("urlsModal");
const platformsModal = document.getElementById("platformsModal");
const closeAccountsBtn = document.getElementById("closeAccountsBtn");
const closeUrlsBtn = document.getElementById("closeUrlsBtn");
const closePlatformsBtn = document.getElementById("closePlatformsBtn");
const themeToggle = document.getElementById("themeToggle");
const headlessToggle = document.getElementById("headlessToggle");
const runParallelToggle = document.getElementById("runParallelToggle");
const platformToggles = document.getElementById("platformToggles");

const platformMap = new Map();
const platformStatus = new Map();
const progressBars = new Map();
let allUrls = [];
let allAccounts = [];
let currentPage = 1;
const pageSize = 10;
let urlsCurrentPage = 1;
const urlsPageSize = 10;

function logStatus(message) {
  const div = document.createElement("div");
  div.className = "status-line";
  div.textContent = message;
  statusLog.prepend(div);
}

function showToast(message, type = "info") {
  if (window.Toastify) {
    Toastify({
      text: message,
      duration: 2500,
      gravity: "top",
      position: "right",
      close: false,
      backgroundColor:
        type === "error"
          ? "#c0392b"
          : type === "success"
          ? "#1f8f7a"
          : "#2c3e50",
    }).showToast();
    return;
  }
  logStatus(message);
}

function appendProgressDetail(platform, message) {
  const entry = ensureProgressBar(platform);
  if (!entry.details) return;
  const item = document.createElement("div");
  item.className = "progress-detail";
  item.textContent = message;
  entry.details.prepend(item);
}
async function loadPlatforms() {
  const res = await fetch("/api/platforms");
  const platforms = await res.json();
  platformSelect.innerHTML = "";
  accountPlatformSelect.innerHTML = "";
  filterPlatform.innerHTML = '<option value="all">All</option>';
  platformMap.clear();
  platformStatus.clear();
  platforms.forEach((p) => {
    platformMap.set(p.id, p.name);
    platformStatus.set(p.name, p.is_active !== false);
    const option = document.createElement("option");
    option.value = p.name;
    option.textContent = p.name;
    platformSelect.appendChild(option);
    accountPlatformSelect.appendChild(option.cloneNode(true));
    filterPlatform.appendChild(option.cloneNode(true));
  });
  renderPlatformToggles(platforms);
  hideUnselectedProgress();
}

async function loadUrls() {
  const res = await fetch("/api/monitored-urls");
  allUrls = await res.json();
  renderUrlsTable();
  renderActiveUrls();
}

async function loadAccounts() {
  const res = await fetch("/api/accounts");
  allAccounts = await res.json();
  accountsTableBody.innerHTML = "";
  allAccounts.forEach((a) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${platformMap.get(a.platform_id) || a.platform_id}</td>
      <td>${a.username}</td>
      <td>${a.email || ""}</td>
      <td>
        <input type="checkbox" ${a.is_active ? "checked" : ""} data-id="${a.id}" class="account-active-toggle" />
      </td>
      <td><button data-id="${a.id}" class="delete-account-btn">Delete</button></td>
    `;
    accountsTableBody.appendChild(tr);
  });
}

function renderUrlsTable() {
  urlTableBody.innerHTML = "";
  const totalPages = Math.max(1, Math.ceil(allUrls.length / urlsPageSize));
  urlsCurrentPage = Math.min(urlsCurrentPage, totalPages);
  const start = (urlsCurrentPage - 1) * urlsPageSize;
  const pageItems = allUrls.slice(start, start + urlsPageSize);

  pageItems.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${platformMap.get(u.platform_id) || u.platform_id}</td>
      <td class="url-cell">${u.url}</td>
      <td>${u.label || ""}</td>
      <td>
        <input type="checkbox" ${u.is_active ? "checked" : ""} data-id="${u.id}" class="active-toggle" />
      </td>
      <td>${formatDate(u.last_checked_at)}</td>
      <td>${formatDate(u.last_exported_at)}</td>
      <td>
        <div class="action-icons">
          <button data-id="${u.id}" class="action-icon edit-btn" title="Edit">✎</button>
          <button data-id="${u.id}" class="action-icon delete-btn" title="Delete">🗑</button>
        </div>
      </td>
    `;
    urlTableBody.appendChild(tr);
  });

  urlsPageInfo.textContent = `Page ${urlsCurrentPage} of ${totalPages}`;
  urlsPrevPage.disabled = urlsCurrentPage === 1;
  urlsNextPage.disabled = urlsCurrentPage === totalPages;
}

function renderActiveUrls() {
  const platformFilter = filterPlatform.value;
  const activeFilter = filterActive.value;
  const search = filterSearch.value.toLowerCase();

  let filtered = allUrls.slice();
  if (platformFilter !== "all") {
    filtered = filtered.filter(
      (u) => (platformMap.get(u.platform_id) || "") === platformFilter
    );
  }
  if (activeFilter !== "all") {
    filtered = filtered.filter((u) => String(u.is_active) === activeFilter);
  }
  if (search) {
    filtered = filtered.filter((u) => (u.label || "").toLowerCase().includes(search));
  }

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  currentPage = Math.min(currentPage, totalPages);
  const start = (currentPage - 1) * pageSize;
  const pageItems = filtered.slice(start, start + pageSize);

  activeUrlTableBody.innerHTML = "";
  pageItems.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${platformMap.get(u.platform_id) || u.platform_id}</td>
      <td>${u.label || "-"}</td>
      <td>${u.is_active ? "Yes" : "No"}</td>
      <td>${formatDate(u.last_checked_at)}</td>
      <td>${formatDate(u.last_exported_at)}</td>
    `;
    activeUrlTableBody.appendChild(tr);
  });

  pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  prevPage.disabled = currentPage === 1;
  nextPage.disabled = currentPage === totalPages;
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
    showToast("URL added", "success");
  } else {
    showToast("Failed to add URL", "error");
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
    showToast("Account added", "success");
    await loadAccounts();
  } else {
    showToast("Failed to add account", "error");
  }
});

urlTableBody.addEventListener("click", async (e) => {
  if (e.target.classList.contains("edit-btn")) {
    const id = e.target.dataset.id;
    const current = allUrls.find((u) => String(u.id) === String(id));
    if (!current) return;
    const newUrl = window.prompt("Edit URL", current.url);
    if (newUrl === null) return;
    const newLabel = window.prompt("Edit Label", current.label || "");
    if (newLabel === null) return;

    await fetch(`/api/monitored-urls/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: newUrl, label: newLabel }),
    });
    await loadUrls();
    showToast("URL updated", "success");
  }
  if (e.target.classList.contains("delete-btn")) {
    const id = e.target.dataset.id;
    await fetch(`/api/monitored-urls/${id}`, { method: "DELETE" });
    await loadUrls();
    showToast("URL deleted", "success");
  }
});

urlsPrevPage.addEventListener("click", () => {
  urlsCurrentPage = Math.max(1, urlsCurrentPage - 1);
  renderUrlsTable();
});
urlsNextPage.addEventListener("click", () => {
  urlsCurrentPage += 1;
  renderUrlsTable();
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
    showToast("URL status updated", "success");
  }
});

accountsTableBody.addEventListener("click", async (e) => {
  if (e.target.classList.contains("delete-account-btn")) {
    const id = e.target.dataset.id;
    await fetch(`/api/accounts/${id}`, { method: "DELETE" });
    await loadAccounts();
    showToast("Account deleted", "success");
  }
});

accountsTableBody.addEventListener("change", async (e) => {
  if (e.target.classList.contains("account-active-toggle")) {
    const id = e.target.dataset.id;
    await fetch(`/api/accounts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: e.target.checked }),
    });
    await loadAccounts();
    showToast("Account status updated", "success");
  }
});

runScrapeBtn.addEventListener("click", async () => {
  const res = await fetch("/api/run-scrape", { method: "POST" });
  if (!res.ok) {
    const data = await res.json();
    showToast(data.detail || "Scrape already running", "error");
  }
});

downloadBtn.addEventListener("click", () => {
  window.location.href = `/api/download-new`;
});

function ensureProgressBar(platform) {
  if (progressBars.has(platform)) return progressBars.get(platform);

  const wrapper = document.createElement("div");
  wrapper.className = "progress-block";
  wrapper.dataset.platform = platform;
  const icon = document.createElement("div");
  icon.className = "progress-icon";
  const img = document.createElement("img");
  const iconMap = {
    linkedin: "/static/images/linkedin.webp",
    facebook: "/static/images/facebook.webp",
    x: "/static/images/x.jpg",
    instagram: "/static/images/instagram.webp",
    ig: "/static/images/instagram.webp",
  };
  img.src = iconMap[platform] || "/static/images/linkedin.webp";
  img.alt = platform;
  icon.appendChild(img);
  const bar = document.createElement("div");
  bar.className = "progress-bar";
  const fill = document.createElement("div");
  fill.className = "progress-fill";
  bar.appendChild(fill);
  const label = document.createElement("div");
  label.className = "progress-label";
  label.textContent = "0%";

  wrapper.appendChild(icon);
  const barWrap = document.createElement("div");
  barWrap.appendChild(bar);
  barWrap.appendChild(label);
  wrapper.appendChild(barWrap);
  const detailsToggle = document.createElement("button");
  detailsToggle.className = "details-toggle";
  detailsToggle.textContent = "Details";
  const details = document.createElement("div");
  details.className = "progress-details hidden";
  detailsToggle.addEventListener("click", () => {
    details.classList.toggle("hidden");
  });
  wrapper.appendChild(detailsToggle);
  wrapper.appendChild(details);
  progressContainer.appendChild(wrapper);

  const entry = { fill, label, details };
  progressBars.set(platform, entry);
  return entry;
}

function updateProgress(platform, percent, message) {
  const entry = ensureProgressBar(platform);
  entry.fill.style.width = `${percent}%`;
  entry.label.textContent = `${percent}% ${message || ""}`.trim();
}

function formatDate(value) {
  if (!value) return "-";
  try {
    const date = new Date(value);
    return date.toLocaleString();
  } catch (e) {
    return value;
  }
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "status") {
      if (data.platform) {
        appendProgressDetail(data.platform, data.message);
      } else {
        logStatus(data.message);
      }
    }
    if (data.type === "progress") {
      showProgressForPlatform(data.platform);
      updateProgress(data.platform, data.percent, data.stage);
    }
    if (data.type === "milestone") {
      showProgressForPlatform(data.platform);
      updateProgress(
        data.platform,
        data.current ? Math.round((data.current / data.total) * 100) : 0,
        data.stage
      );
    }
    if (data.type === "done") {
      showProgressForPlatform(data.platform);
      updateProgress(data.platform, 100, "done");
      appendProgressDetail(data.platform, `Saved ${data.saved} posts`);
      showToast(`${data.platform} saved ${data.saved} posts`, "success");
    }
    if (data.type === "error") {
      showProgressForPlatform(data.platform);
      appendProgressDetail(data.platform, `Error: ${data.message}`);
      showToast(`${data.platform}: ${data.message}`, "error");
    }
  };

  ws.onclose = () => {
    setTimeout(connectWebSocket, 2000);
  };
}

function openModal(modal) {
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal(modal) {
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

settingsBtn.addEventListener("click", () => openModal(settingsModal));
closeSettingsBtn.addEventListener("click", () => closeModal(settingsModal));
openAccountsBtn.addEventListener("click", () => openModal(accountsModal));
closeAccountsBtn.addEventListener("click", () => closeModal(accountsModal));
openUrlsBtn.addEventListener("click", () => openModal(urlsModal));
closeUrlsBtn.addEventListener("click", () => closeModal(urlsModal));
openPlatformsBtn.addEventListener("click", () => openModal(platformsModal));
closePlatformsBtn.addEventListener("click", () => closeModal(platformsModal));

themeToggle.addEventListener("change", () => {
  const isDark = themeToggle.checked;
  document.body.classList.toggle("dark", isDark);
  localStorage.setItem("theme", isDark ? "dark" : "light");
});

filterPlatform.addEventListener("change", () => {
  currentPage = 1;
  renderActiveUrls();
});
filterActive.addEventListener("change", () => {
  currentPage = 1;
  renderActiveUrls();
});
filterSearch.addEventListener("input", () => {
  currentPage = 1;
  renderActiveUrls();
});
prevPage.addEventListener("click", () => {
  currentPage = Math.max(1, currentPage - 1);
  renderActiveUrls();
});
nextPage.addEventListener("click", () => {
  currentPage += 1;
  renderActiveUrls();
});

async function init() {
  await loadPlatforms();
  for (const name of platformMap.values()) {
    ensureProgressBar(name);
  }
  await loadUrls();
  await loadAccounts();
  renderActiveUrls();
  await loadSettings();
  hideUnselectedProgress();
  connectWebSocket();
}

const savedTheme = localStorage.getItem("theme");
if (savedTheme === "dark") {
  document.body.classList.add("dark");
  themeToggle.checked = true;
}

init();

async function loadSettings() {
  const res = await fetch("/api/settings");
  if (!res.ok) return;
  const data = await res.json();
  headlessToggle.checked = data.headless === true;
  runParallelToggle.checked = data.run_parallel === true;
}

headlessToggle.addEventListener("change", async () => {
  await saveSettings();
});
runParallelToggle.addEventListener("change", async () => {
  await saveSettings();
});

async function saveSettings() {
  const res = await fetch("/api/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      headless: headlessToggle.checked,
      run_parallel: runParallelToggle.checked,
    }),
  });
  if (!res.ok) {
    showToast("Failed to update settings", "error");
  } else {
    showToast("Settings updated", "success");
    hideUnselectedProgress();
  }
}

function renderPlatformToggles(enabled) {
  platformToggles.innerHTML = "";
  for (const platform of enabled) {
    const label = document.createElement("label");
    label.className = "platform-row";
    label.innerHTML = `
      ${platform.name}
      <span class="switch">
        <input type="checkbox" data-id="${platform.id}" value="${platform.name}" ${
      platform.is_active ? "checked" : ""
    } />
        <span class="slider"></span>
      </span>
    `;
    platformToggles.appendChild(label);
  }
  platformToggles.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", async (e) => {
      const id = e.target.dataset.id;
      const res = await fetch(`/api/platforms/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: e.target.checked }),
      });
      if (!res.ok) {
        showToast("Failed to update platform", "error");
        e.target.checked = !e.target.checked;
        return;
      }
      await loadPlatforms();
      showToast("Platform updated", "success");
    });
  });
}

function showProgressForPlatform(platform) {
  const entry = ensureProgressBar(platform);
  if (entry && entry.fill && entry.label) {
    entry.fill.closest(".progress-block").classList.remove("hidden");
  }
}

function hideUnselectedProgress() {
  const enabled = new Set(
    Array.from(platformStatus.entries())
      .filter(([, active]) => active)
      .map(([name]) => name)
  );
  document.querySelectorAll(".progress-block").forEach((block) => {
    const platform = block.dataset.platform;
    block.classList.toggle("hidden", !enabled.has(platform));
  });
}

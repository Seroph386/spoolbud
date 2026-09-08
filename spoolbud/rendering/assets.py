"""Known-good CSS and browser scripts used by SpoolBud pages."""

BASE_STYLES = """
[hidden] { display: none !important; }

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.5;
  background:
    radial-gradient(circle at top left, rgba(32, 155, 137, 0.12), transparent 35%),
    radial-gradient(circle at top right, rgba(217, 119, 6, 0.10), transparent 28%),
    var(--bg);
  color: var(--text);
}

a {
  color: var(--link);
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  background: var(--surface-muted);
  border-radius: 6px;
  padding: 0.1rem 0.35rem;
}

.shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 1rem;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 0.85rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: 0 14px 40px rgba(15, 23, 42, 0.08);
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand a {
  color: var(--text);
  text-decoration: none;
}

.brand strong {
  font-size: 1.05rem;
  letter-spacing: 0.02em;
}

.brand span {
  color: var(--text-muted);
  font-size: 0.92rem;
}

.nav {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.nav-link,
.menu-toggle,
.theme-toggle,
.button {
  appearance: none;
  border: 1px solid var(--border);
  background: var(--surface-muted);
  color: var(--text);
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  text-decoration: none;
  font: inherit;
  cursor: pointer;
  transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
}

.nav-link:hover,
.menu-toggle:hover,
.theme-toggle:hover,
.button:hover {
  transform: translateY(-1px);
  border-color: var(--border-strong);
}

.nav-link.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.menu-toggle {
  border-radius: 12px;
  min-width: 2.5rem;
  padding: 0.55rem 0.7rem;
}

.side-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  opacity: 0;
  pointer-events: none;
  transition: opacity 160ms ease;
  z-index: 35;
}

.side-overlay.open {
  opacity: 1;
  pointer-events: auto;
}

.side-nav {
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  width: min(19rem, 88vw);
  background: var(--surface);
  border-right: 1px solid var(--border);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25);
  transform: translateX(-102%);
  transition: transform 180ms ease;
  z-index: 40;
  padding: 1rem;
  box-sizing: border-box;
  display: grid;
  gap: 1rem;
  align-content: start;
}

.side-nav.open {
  transform: translateX(0);
}

.side-nav-links {
  display: grid;
  gap: 0.6rem;
}

.side-nav .nav-link,
.side-nav .theme-toggle {
  border-radius: 12px;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 22px;
  padding: 1.4rem;
  box-shadow: 0 14px 40px rgba(15, 23, 42, 0.08);
}

.hero {
  display: grid;
  gap: 1rem;
  margin-bottom: 1rem;
}

.hero h1,
.panel h1,
.panel h2,
.panel h3,
.card h3 {
  margin-top: 0;
}

.muted {
  color: var(--text-muted);
}

.stack {
  display: grid;
  gap: 1rem;
}

.toolbar {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: center;
}

.input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
  background: var(--surface-muted);
  color: var(--text);
  font: inherit;
}

textarea.input {
  min-height: 9rem;
  resize: vertical;
}

.scanner-wrap {
  display: grid;
  gap: 0.75rem;
}

.scanner-video {
  width: 100%;
  max-width: 26rem;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: #000;
}

.scanner-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: none;
  place-items: center;
  z-index: 45;
  padding: 1rem;
  box-sizing: border-box;
}

.scanner-modal.open {
  display: grid;
}

.scanner-modal-card {
  width: min(38rem, 100%);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem;
  display: grid;
  gap: 0.8rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.destination-grid {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.destination-grid .button {
  min-height: 48px;
  overflow-wrap: anywhere;
}

.card {
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem;
  background: var(--surface-muted);
}

.qr-card {
  text-align: center;
  overflow-wrap: anywhere;
}

.qr-card img {
  width: 100%;
  max-width: 160px;
  background: white;
  border-radius: 12px;
}

.spool-list {
  display: grid;
  gap: 0.75rem;
}

.spool-meta {
  font-size: 0.95rem;
}

.color-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.75rem;
}

.color-swatch {
  width: 1rem;
  height: 1rem;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  flex: 0 0 auto;
}

.summary {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  padding: 0.45rem 0.8rem;
  background: var(--surface-muted);
  color: var(--text-muted);
  border: 1px solid var(--border);
}

ul.clean {
  margin: 0;
  padding-left: 1.2rem;
}

:root {
  color-scheme: light;
  --bg: #f4f6f4;
  --surface: rgba(255, 255, 255, 0.88);
  --surface-muted: #eef3ef;
  --text: #13231d;
  --text-muted: #52645d;
  --border: rgba(19, 35, 29, 0.12);
  --border-strong: rgba(19, 35, 29, 0.24);
  --link: #0f766e;
  --accent: #0f766e;
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #11191a;
  --surface: rgba(18, 28, 29, 0.92);
  --surface-muted: #1a2527;
  --text: #edf7f2;
  --text-muted: #a6bbb4;
  --border: rgba(237, 247, 242, 0.10);
  --border-strong: rgba(237, 247, 242, 0.22);
  --link: #6ee7d5;
  --accent: #0f766e;
}

@media (max-width: 780px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .nav {
    justify-content: space-between;
  }

  .nav-link,
  .theme-toggle,
  .button {
    text-align: center;
  }
}
"""

THEME_SCRIPT = """
(() => {
  const storageKey = "spoolbud-theme";

  function preferredTheme() {
    const stored = window.localStorage.getItem(storageKey);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const toggles = [document.getElementById("themeToggle"), document.getElementById("themeToggleSide")];
    for (const toggle of toggles) {
      if (!toggle) {
        continue;
      }
      toggle.textContent = theme === "dark" ? "Light mode" : "Dark mode";
      toggle.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
    }
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    window.localStorage.setItem(storageKey, next);
    applyTheme(next);
  }

  function setSideMenuOpen(open) {
    const sideNav = document.getElementById("sideNav");
    const sideOverlay = document.getElementById("sideOverlay");
    const menuToggle = document.getElementById("menuToggle");
    if (!sideNav || !sideOverlay || !menuToggle) {
      return;
    }
    sideNav.classList.toggle("open", open);
    sideOverlay.classList.toggle("open", open);
    menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  applyTheme(preferredTheme());
  window.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("themeToggle");
    if (toggle) {
      applyTheme(document.documentElement.dataset.theme || preferredTheme());
      toggle.addEventListener("click", toggleTheme);
    }
    const sideToggle = document.getElementById("themeToggleSide");
    if (sideToggle) {
      sideToggle.addEventListener("click", toggleTheme);
    }
    const menuToggle = document.getElementById("menuToggle");
    const sideOverlay = document.getElementById("sideOverlay");
    if (menuToggle) {
      menuToggle.addEventListener("click", () => {
        const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
        setSideMenuOpen(!isOpen);
      });
    }
    if (sideOverlay) {
      sideOverlay.addEventListener("click", () => setSideMenuOpen(false));
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setSideMenuOpen(false);
      }
    });
  });
})();
"""

COMMON_SCRIPT = r"""
async function requestJson(url, body) {
  const response = await fetch(url, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Request failed. Please try again.");
  }
  return data;
}

function parseSpoolId(value) {
  let raw = String(value || "").trim();
  try {
    const url = new URL(raw, window.location.origin);
    if (url.pathname === "/scan") raw = url.searchParams.get("value") || raw;
  } catch (_) {}
  for (const pattern of [/web\+spoolman:s-(\d+)/i, /\/spool\/show\/(\d+)/,
      /\/spool\/(\d+)/, /[?&]spool_id=(\d+)/, /^(\d+)$/]) {
    const match = raw.match(pattern);
    if (match && Number(match[1]) > 0) return String(Number(match[1]));
  }
  return null;
}

function labelBase(value) {
  const url = new URL(value.trim());
  if (!["https:", "http:"].includes(url.protocol) || url.search || url.hash || url.username || url.password) {
    throw new Error("Enter an HTTP or HTTPS SpoolBud base URL without query parameters or credentials.");
  }
  return url.href.replace(/\/$/, "");
}

function spoolScanLink(base, id) {
  return `${base}/scan?value=${encodeURIComponent(id)}&stay=1`;
}

function createLabelCard(title, qrValue, description = "", color = null) {
  const card = document.createElement("article");
  card.className = "card qr-card stack";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const details = document.createElement("div");
  details.textContent = description;
  if (color && /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(color)) {
    const swatch = document.createElement("span");
    swatch.className = "color-swatch";
    swatch.style.backgroundColor = color;
    swatch.setAttribute("aria-label", `Color ${color}`);
    details.prepend(swatch);
    details.append(` · ${color}`);
  }
  const qr = document.createElement("img");
  qr.alt = `QR for ${title}`;
  qr.src = `/qr.svg?value=${encodeURIComponent(qrValue)}`;
  const payload = document.createElement("code");
  payload.textContent = qrValue;
  card.append(heading, details, qr, payload);
  return card;
}
"""

BINS_PAGE_SCRIPT = r"""
(() => {
  const binsEl = document.getElementById("bins");
  const statusEl = document.getElementById("status");
  const gridEl = document.getElementById("grid");
  const baseEl = document.getElementById("publicBase");
  baseEl.value = window.location.origin;

  async function loadBins(source) {
    statusEl.textContent = "Loading destinations...";
    try {
      const data = await requestJson(`/api/bins?source=${source}`);
      binsEl.value = data.bins.join("\n");
      statusEl.textContent = data.warning || `Loaded ${data.bins.length} destinations.`;
    } catch (error) {
      statusEl.textContent = error.message;
    }
  }

  function renderLabels() {
    try {
      const base = labelBase(baseEl.value);
      const locations = [...new Set(binsEl.value.split("\n").map(value => value.trim().toUpperCase()).filter(Boolean))];
      gridEl.replaceChildren();
      for (const location of locations) {
        const target = `${base}/bin/${encodeURIComponent(location)}?stay=1`;
        gridEl.appendChild(createLabelCard(location, target));
      }
      statusEl.textContent = `Prepared ${locations.length} destination QR labels.`;
    } catch (error) {
      statusEl.textContent = error.message;
    }
  }

  document.getElementById("loadDefault").addEventListener("click", () => loadBins("default"));
  document.getElementById("loadSpoolman").addEventListener("click", () => loadBins("all"));
  document.getElementById("render").addEventListener("click", renderLabels);
  loadBins("all");
})();
"""

SPOOLS_PAGE_SCRIPT = r"""
(() => {
  const inputEl = document.getElementById("spools");
  const statusEl = document.getElementById("spoolStatus");
  const gridEl = document.getElementById("spoolGrid");
  const baseEl = document.getElementById("spoolPublicBase");
  const searchEl = document.getElementById("spoolSearch");
  let spools = new Map();
  baseEl.value = window.location.origin;

  function filterLabels() {
    const query = searchEl.value.trim().toLowerCase();
    for (const card of gridEl.children) card.hidden = !card.textContent.toLowerCase().includes(query);
  }

  function renderSpools() {
    try {
      const base = labelBase(baseEl.value);
      const ids = [...new Set(inputEl.value.split("\n").map(parseSpoolId).filter(Boolean))];
      gridEl.replaceChildren();
      for (const id of ids) {
        const spool = spools.get(Number(id));
        const scanLink = spoolScanLink(base, id);
        const fullUrl = document.getElementById("spoolQrFormat").value === "full-url";
        const stay = document.getElementById("includeStayFlag").checked;
        const qrValue = fullUrl ? (stay ? scanLink : scanLink.replace("&stay=1", "")) : `web+spoolman:s-${id}`;
        const description = spool ? `${spool.description} · Location: ${spool.locations.join(", ") || "Unassigned"}` : "";
        const card = createLabelCard(`Spool ${id}`, qrValue, description, spool?.color_hex);
        const select = document.createElement("a");
        select.href = spoolScanLink(window.location.origin, id);
        select.textContent = "Select in SpoolBud";
        card.appendChild(select);
        gridEl.appendChild(card);
      }
      filterLabels();
      statusEl.textContent = `Prepared ${ids.length} spool QR labels.`;
    } catch (error) {
      statusEl.textContent = error.message;
    }
  }

  document.getElementById("loadSpoolmanSpools").addEventListener("click", async () => {
    statusEl.textContent = "Loading spools from Spoolman...";
    try {
      const data = await requestJson("/api/spools");
      spools = new Map(data.spools.map(spool => [spool.id, spool]));
      inputEl.value = data.spool_ids.join("\n");
      renderSpools();
    } catch (error) {
      statusEl.textContent = error.message;
    }
  });
  document.getElementById("loadSpoolSample").addEventListener("click", () => {
    inputEl.value = "1\n2\n3";
    renderSpools();
  });
  document.getElementById("renderSpools").addEventListener("click", renderSpools);
  searchEl.addEventListener("input", filterLabels);
})();
"""


SCANNER_CORE_SCRIPT = r"""
function createQrScanner(config) {
  const triggerButton = document.getElementById(config.triggerButtonId || config.startButtonId);
  const startButton = document.getElementById(config.startButtonId);
  const stopButton = document.getElementById(config.stopButtonId);
  const statusEl = document.getElementById(config.statusId);
  const videoEl = document.getElementById(config.videoId);
  const canvasEl = document.getElementById(config.canvasId);
  const modalEl = config.modalId ? document.getElementById(config.modalId) : null;
  const closeButton = config.closeButtonId ? document.getElementById(config.closeButtonId) : null;
  const referenceEl = config.referenceId ? document.getElementById(config.referenceId) : null;

  if (!triggerButton || !startButton || !stopButton || !statusEl || !videoEl || !canvasEl) {
    return;
  }

  let stream = null;
  let timer = null;
  let detector = null;
  let scanMode = null;
  let jsQrLoadPromise = null;
  let canvasContext = null;

  function setStatus(message) {
    statusEl.textContent = message;
  }

  function stopScanner() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (stream) {
      for (const track of stream.getTracks()) {
        track.stop();
      }
      stream = null;
    }
    detector = null;
    scanMode = null;
    videoEl.srcObject = null;
    startButton.disabled = false;
    stopButton.disabled = true;
  }

  function setModalOpen(open) {
    if (!modalEl) {
      return;
    }
    modalEl.classList.toggle("open", open);
  }

  function handleScanValue(rawValue) {
    const result = config.handleValue(String(rawValue || "").trim());
    if (!result || !result.url) {
      return false;
    }

    setStatus(result.status || `Scanned ${rawValue}. Opening next step...`);
    stopScanner();
    window.location.href = result.url;
    return true;
  }

  async function loadCompatibilityScanner() {
    if (typeof window.jsQR === "function") {
      return window.jsQR;
    }

    if (!jsQrLoadPromise) {
      jsQrLoadPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js";
        script.async = true;
        script.onload = () => {
          if (typeof window.jsQR === "function") {
            resolve(window.jsQR);
            return;
          }
          reject(new Error("compat-load-failed"));
        };
        script.onerror = () => reject(new Error("compat-load-failed"));
        document.head.appendChild(script);
      }).catch((error) => {
        jsQrLoadPromise = null;
        throw error;
      });
    }

    return jsQrLoadPromise;
  }

  async function chooseScannerMode() {
    if ("BarcodeDetector" in window) {
      try {
        detector = new window.BarcodeDetector({ formats: ["qr_code"] });
        return "barcode-detector";
      } catch (error) {
        detector = null;
      }
    }

    setStatus("Loading compatibility scanner for this browser...");
    await loadCompatibilityScanner();
    return "jsqr";
  }

  async function openCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("camera-unsupported");
    }

    try {
      return await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: "environment" } },
      });
    } catch (error) {
      return navigator.mediaDevices.getUserMedia({ audio: false, video: true });
    }
  }

  async function detectWithBarcodeDetector() {
    if (!detector || !videoEl.videoWidth || !videoEl.videoHeight) {
      return;
    }

    const codes = await detector.detect(videoEl);
    for (const code of codes) {
      if (handleScanValue(code.rawValue)) {
        return;
      }
    }
  }

  async function detectWithJsQr() {
    if (typeof window.jsQR !== "function" || !videoEl.videoWidth || !videoEl.videoHeight) {
      return;
    }

    if (!canvasContext) {
      canvasContext = canvasEl.getContext("2d", { willReadFrequently: true });
    }
    if (!canvasContext) {
      throw new Error("compat-canvas-failed");
    }

    const width = videoEl.videoWidth;
    const height = videoEl.videoHeight;
    if (canvasEl.width !== width) {
      canvasEl.width = width;
    }
    if (canvasEl.height !== height) {
      canvasEl.height = height;
    }

    canvasContext.drawImage(videoEl, 0, 0, width, height);
    const image = canvasContext.getImageData(0, 0, width, height);
    const code = window.jsQR(image.data, width, height, { inversionAttempts: "attemptBoth" });
    if (code) {
      handleScanValue(code.data);
    }
  }

  async function checkFrame() {
    if (!scanMode || !videoEl.videoWidth || !videoEl.videoHeight) {
      return;
    }

    try {
      if (scanMode === "barcode-detector") {
        await detectWithBarcodeDetector();
      } else if (scanMode === "jsqr") {
        await detectWithJsQr();
      }
    } catch (error) {
      setStatus(config.readFailureMessage);
    }
  }

  async function startScanner() {
    try {
      scanMode = await chooseScannerMode();
      stream = await openCamera();
      videoEl.srcObject = stream;
      await videoEl.play();
      timer = window.setInterval(checkFrame, 350);
      if (scanMode === "jsqr") {
        setStatus(config.compatPrompt);
      } else {
        setStatus(config.prompt);
      }
      startButton.disabled = true;
      stopButton.disabled = false;
    } catch (error) {
      if (error && error.message === "compat-load-failed") {
        setStatus(config.compatLoadFailureMessage);
      } else if (error && error.message === "camera-unsupported") {
        setStatus(config.cameraUnsupportedMessage);
      } else {
        setStatus("Camera access failed. Check browser camera permissions.");
      }
      stopScanner();
    }
  }

  startButton.addEventListener("click", startScanner);
  triggerButton.addEventListener("click", async () => {
    setModalOpen(true);
    setStatus("Opening camera...");
    await startScanner();
  });
  stopButton.addEventListener("click", () => {
    stopScanner();
    setStatus("Scanner stopped.");
  });
  if (closeButton) {
    closeButton.addEventListener("click", () => {
      stopScanner();
      setModalOpen(false);
      setStatus(config.closedStatus || "Scanner closed.");
    });
  }
  if (modalEl) {
    modalEl.addEventListener("click", (event) => {
      if (event.target === modalEl) {
        stopScanner();
        setModalOpen(false);
      }
    });
  }

  if (referenceEl && !referenceEl.value && config.referenceValue) {
    referenceEl.value = config.referenceValue;
  }
}
"""


TAG_SCAN_PAGE_SCRIPT = r"""
(() => {
  const form = document.getElementById("tagScanForm");
  const uid = document.getElementById("tagUid");
  const readerId = document.getElementById("tagReaderId");
  const status = document.getElementById("tagScanStatus");
  const submit = document.getElementById("submitTagScan");
  const read = document.getElementById("readNfc");
  const stop = document.getElementById("stopNfc");
  let controller = null;
  let busy = false;

  function stopReading() {
    controller?.abort();
    controller = null;
    read.disabled = busy;
    stop.hidden = true;
  }

  async function resolveUid(value) {
    if (busy) return;
    busy = true;
    stopReading();
    submit.disabled = true;
    for (const id of ["currentSelection", "continueSelection"]) {
      const previous = document.getElementById(id);
      if (previous) previous.hidden = true;
    }
    status.textContent = "Asking Spoolman to identify the tag...";
    try {
      const body = {uid: value};
      if (readerId.value.trim()) body.reader_id = readerId.value.trim();
      const result = await requestJson("/api/tag/scan", body);
      if (result.matched_spool_id !== null) {
        window.location.href = "/selected";
        return;
      }
      status.textContent = result.detail;
    } catch (error) {
      status.textContent = error.message;
    } finally {
      busy = false;
      submit.disabled = false;
      read.disabled = false;
      uid.select();
    }
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    resolveUid(uid.value.trim());
  });
  read.hidden = !(window.isSecureContext && "NDEFReader" in window);
  read.addEventListener("click", async () => {
    if (busy || controller) return;
    controller = new AbortController();
    const signal = controller.signal;
    read.disabled = true;
    stop.hidden = false;
    try {
      const reader = new NDEFReader();
      reader.onreading = event => {
        if (signal.aborted) return;
        // Use the hardware serial only. Never inspect NDEF records for IDs.
        uid.value = event.serialNumber || "";
        resolveUid(uid.value);
      };
      reader.onreadingerror = () => {
        if (!signal.aborted) resolveUid("");
      };
      await reader.scan({signal});
      if (!signal.aborted) status.textContent = "Hold a supported NFC tag near the phone.";
    } catch (error) {
      if (error.name !== "AbortError") status.textContent = "Could not start NFC reading. Check permissions and hardware, or use a reader to enter the UID.";
      stopReading();
    }
  });
  stop.addEventListener("click", () => {
    stopReading();
    status.textContent = "NFC reading stopped.";
  });
  window.addEventListener("pagehide", stopReading);
})();
"""


HOME_SCAN_PAGE_SCRIPT = SCANNER_CORE_SCRIPT + r"""
(() => {
  createQrScanner({
    triggerButtonId: "startSpoolScanner",
    startButtonId: "runSpoolScanner",
    stopButtonId: "stopSpoolScanner",
    statusId: "spoolScannerStatus",
    videoId: "spoolScannerVideo",
    canvasId: "spoolScannerCanvas",
    modalId: "spoolScannerModal",
    closeButtonId: "closeSpoolScanner",
    referenceId: "spoolScanReference",
    referenceValue: "web+spoolman:s-42",
    prompt: "Point your camera at a Spoolman spool QR code.",
    compatPrompt: "Point your camera at a Spoolman spool QR code. Compatibility scanner is active for this browser.",
    readFailureMessage: "Scanner could not read a supported spool QR yet. Keep the QR in view.",
    compatLoadFailureMessage: "This browser needs the compatibility scanner, but it could not be loaded. Try again or open the QR with your camera app.",
    cameraUnsupportedMessage: "This browser cannot open the camera from this page. Try Safari or your phone camera app.",
    handleValue(rawValue) {
      if (!parseSpoolId(rawValue)) {
        return null;
      }
      return {
        url: spoolScanLink(window.location.origin, parseSpoolId(rawValue)),
        status: "Spool scanned. Choose a destination...",
      };
    },
  });
})();
"""


SCAN_PAGE_SCRIPT = SCANNER_CORE_SCRIPT + r"""
(() => {
  const actions = document.getElementById("selectionActions");
  const spoolId = Number(actions.dataset.spoolId);
  const grid = document.getElementById("destinations");
  const search = document.getElementById("destinationSearch");
  const status = document.getElementById("moveStatus");
  const destinationStatus = document.getElementById("destinationStatus");
  let busy = false;

  function filterDestinations() {
    const query = search.value.trim().toUpperCase();
    for (const button of grid.children) button.hidden = !button.textContent.includes(query);
  }

  async function submitAction(location) {
    if (busy) return;
    busy = true;
    const controls = actions.querySelectorAll("button, input");
    controls.forEach(control => { control.disabled = true; });
    status.textContent = location === null ? "Clearing selection..." : "Updating Spoolman...";
    try {
      const data = await requestJson(location === null ? "/api/selection/clear" : "/api/move",
        location === null ? {spool_id: spoolId} : {spool_id: spoolId, location});
      if (location === null) {
        window.location.href = "/";
        return;
      }
      document.getElementById("selectedHeading").textContent = `Spool ${data.spool_id} moved to ${data.location}`;
      document.getElementById("spoolDetails").hidden = true;
      actions.hidden = true;
      document.getElementById("moveComplete").hidden = false;
      window.history.replaceState(null, "", "/");
    } catch (error) {
      status.textContent = error.message;
      status.scrollIntoView({block: "nearest"});
    } finally {
      busy = false;
      actions.querySelectorAll("button, input").forEach(control => { control.disabled = false; });
    }
  }

  requestJson("/api/bins?source=all").then(data => {
    for (const location of data.bins) {
      const button = document.createElement("button");
      button.className = "button";
      button.type = "button";
      button.textContent = location;
      button.disabled = busy;
      button.addEventListener("click", () => submitAction(location));
      grid.appendChild(button);
    }
    filterDestinations();
    destinationStatus.textContent = data.warning || "Choose a bucket or printer position below.";
  }).catch(() => {
    destinationStatus.textContent = "Could not load destinations. Enter a location below or scan its bin QR.";
  });
  search.addEventListener("input", filterDestinations);
  document.getElementById("destinationForm").addEventListener("submit", event => {
    event.preventDefault();
    if (search.value.trim()) submitAction(search.value.trim());
  });
  document.getElementById("cancelSelection").addEventListener("click", () => submitAction(null));

  function toBinUrl(rawValue) {
    const value = String(rawValue || "").trim();
    const suffix = `?stay=1&spool_id=${spoolId}`;
    try {
      const url = new URL(value, window.location.origin);
      if (url.pathname.startsWith("/bin/")) {
        return `/bin/${encodeURIComponent(decodeURIComponent(url.pathname.slice(5)))}` + suffix;
      }
    } catch (_) {}
    const cleaned = value.toUpperCase().replace(/\s+/g, "");
    if (/^[A-Z]-\d{3}$/.test(cleaned)) {
      return `/bin/${encodeURIComponent(cleaned)}` + suffix;
    }
    return null;
  }

  createQrScanner({
    triggerButtonId: "startBinScanner",
    startButtonId: "runBinScanner",
    stopButtonId: "stopBinScanner",
    statusId: "scannerStatus",
    videoId: "scannerVideo",
    canvasId: "scannerCanvas",
    modalId: "binScannerModal",
    closeButtonId: "closeBinScanner",
    referenceId: "spoolBudBase",
    referenceValue: `${window.location.origin}/bin/`,
    prompt: "Point your camera at a bin QR code.",
    compatPrompt: "Point your camera at a bin QR code. Compatibility scanner is active for this browser.",
    readFailureMessage: "Scanner could not read that frame yet. Keep the QR in view.",
    compatLoadFailureMessage: "This browser needs the compatibility scanner, but it could not be loaded. Try again or open the bin QR with your camera app.",
    cameraUnsupportedMessage: "This browser cannot open the camera from this page. Try Safari or your phone camera app.",
    handleValue(rawValue) {
      const target = toBinUrl(rawValue);
      if (!target) {
        return null;
      }
      return {
        url: target,
        status: `Scanned ${rawValue}. Updating location...`,
      };
    },
  });
})();
"""


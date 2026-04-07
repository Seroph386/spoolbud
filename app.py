from __future__ import annotations

import io
import os
import re
from html import escape
from typing import Any

import httpx
import segno
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

SPOOLMAN_BASE = os.getenv("SPOOLMAN_BASE", "https://filament.igetno.net").rstrip("/")
API_TOKEN = os.getenv("SPOOLMAN_API_TOKEN", "")
COOKIE_NAME = os.getenv("COOKIE_NAME", "last_spool_id")
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

app = FastAPI(title="SpoolBud Helper")

SPOOL_ID_PATTERNS = [
    r"(?i)web\+spoolman:s-(\d+)",
    r"/spool/show/(\d+)",
    r"/spool/(\d+)",
    r"[?&]spool_id=(\d+)",
    r"^(\d+)$",
]

LOCATION_KEYS = ("location", "bin", "storage_location")
EXTRA_LOCATION_KEYS = ("location", "bin")

BASE_STYLES = """
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

.card {
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem;
  background: var(--surface-muted);
}

.qr-card {
  text-align: center;
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

BINS_PAGE_SCRIPT = r"""
(() => {
  const binsEl = document.getElementById("bins");
  const statusEl = document.getElementById("status");
  const gridEl = document.getElementById("grid");
  const publicBaseEl = document.getElementById("publicBase");
  const loadDefaultButton = document.getElementById("loadDefault");
  const loadSpoolmanButton = document.getElementById("loadSpoolman");
  const renderButton = document.getElementById("render");

  if (!binsEl || !statusEl || !gridEl || !publicBaseEl || !loadDefaultButton || !loadSpoolmanButton || !renderButton) {
    return;
  }

  if (!publicBaseEl.value) {
    publicBaseEl.value = window.location.origin;
  }

  async function loadBins(source) {
    statusEl.textContent = `Loading bins from ${source}...`;
    try {
      const response = await fetch(`/api/bins?source=${encodeURIComponent(source)}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Request failed");
      }
      binsEl.value = data.bins.join("\n");
      statusEl.textContent = `Loaded ${data.bins.length} bins from ${data.source}.`;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      statusEl.textContent = `Failed to load bins: ${message}`;
    }
  }

  function renderLabels() {
    const lines = binsEl.value
      .split("\n")
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);
    const publicBase = publicBaseEl.value.trim().replace(/\/$/, "");

    if (!publicBase) {
      statusEl.textContent = "Enter a public helper base URL first.";
      return;
    }

    gridEl.innerHTML = "";
    for (const location of [...new Set(lines)]) {
      const target = `${publicBase}/bin/${encodeURIComponent(location)}`;
      const qrSrc = `/qr.svg?value=${encodeURIComponent(target)}`;
      const card = document.createElement("article");
      card.className = "card qr-card";
      card.innerHTML = `
        <h3>${location}</h3>
        <img alt="QR for ${location}" src="${qrSrc}" />
        <div class="muted">${target}</div>
      `;
      gridEl.appendChild(card);
    }

    statusEl.textContent = `Rendered ${gridEl.children.length} QR labels.`;
  }

  loadDefaultButton.addEventListener("click", () => loadBins("default"));
  loadSpoolmanButton.addEventListener("click", () => loadBins("spoolman"));
  renderButton.addEventListener("click", renderLabels);
  loadBins("default");
})();
"""

SPOOLS_PAGE_SCRIPT = r"""
(() => {
  const spoolInputEl = document.getElementById("spools");
  const statusEl = document.getElementById("spoolStatus");
  const gridEl = document.getElementById("spoolGrid");
  const renderButton = document.getElementById("renderSpools");
  const loadSampleButton = document.getElementById("loadSpoolSample");
  const loadSpoolmanButton = document.getElementById("loadSpoolmanSpools");
  const formatEl = document.getElementById("spoolQrFormat");
  const publicBaseEl = document.getElementById("spoolPublicBase");
  const includeStayEl = document.getElementById("includeStayFlag");
  const spoolmanBaseEl = document.getElementById("spoolmanBase");

  if (!spoolInputEl || !statusEl || !gridEl || !renderButton || !loadSampleButton || !loadSpoolmanButton || !formatEl || !publicBaseEl || !includeStayEl || !spoolmanBaseEl) {
    return;
  }

  if (!publicBaseEl.value) {
    publicBaseEl.value = window.location.origin;
  }

  function parseSpoolId(value) {
    const trimmed = value.trim();
    const patterns = [
      /web\+spoolman:s-(\d+)/i,
      /\/spool\/show\/(\d+)/,
      /\/spool\/(\d+)/,
      /[?&]spool_id=(\d+)/,
      /^(\d+)$/,
    ];
    for (const pattern of patterns) {
      const match = trimmed.match(pattern);
      if (match) {
        return match[1];
      }
    }
    return null;
  }

  async function loadSpoolsFromSpoolman() {
    statusEl.textContent = "Loading spool IDs from Spoolman...";
    try {
      const response = await fetch("/api/spools");
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Request failed");
      }
      spoolInputEl.value = data.spool_ids.join("\n");
      statusEl.textContent = `Loaded ${data.spool_ids.length} spool IDs from Spoolman.`;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      statusEl.textContent = `Failed to load spools: ${message}`;
    }
  }

  function renderSpools() {
    const lines = spoolInputEl.value
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean);

    const format = formatEl.value;
    const publicBase = publicBaseEl.value.trim().replace(/\/$/, "");
    const includeStayFlag = Boolean(includeStayEl.checked);

    gridEl.innerHTML = "";

    for (const value of [...new Set(lines)]) {
      const spoolId = parseSpoolId(value);
      if (!spoolId) {
        continue;
      }

      const spoolmanUrl = `/spool/show/${spoolId}`;
      let qrValue = `web+spoolman:s-${spoolId}`;

      if (format === "full-url") {
        if (!publicBase) {
          statusEl.textContent = "Enter a public SpoolBud base URL first.";
          return;
        }
        const spoolmanBase = spoolmanBaseEl.value.trim().replace(/\/$/, "");
        const spoolValue = `${spoolmanBase}${spoolmanUrl}`;
        qrValue = `${publicBase}/scan?value=${encodeURIComponent(spoolValue)}`;
        if (includeStayFlag) {
          qrValue += "&stay=1";
        }
      }

      const qrSrc = `/qr.svg?value=${encodeURIComponent(qrValue)}`;
      const spoolUrl = `${window.location.origin}/select/${encodeURIComponent(spoolId)}`;
      const card = document.createElement("article");
      card.className = "card qr-card";
      card.innerHTML = `
        <h3>Spool ${spoolId}</h3>
        <img alt="QR for spool ${spoolId}" src="${qrSrc}" />
        <div class="muted"><code>${qrValue}</code></div>
        <div class="muted"><a href="${spoolUrl}">Select in SpoolBud</a></div>
      `;
      gridEl.appendChild(card);
    }

    statusEl.textContent = `Rendered ${gridEl.children.length} spool QR labels.`;
  }

  loadSampleButton.addEventListener("click", () => {
    spoolInputEl.value = "1\n2\n3";
    renderSpools();
  });
  loadSpoolmanButton.addEventListener("click", loadSpoolsFromSpoolman);
  renderButton.addEventListener("click", renderSpools);
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


HOME_SCAN_PAGE_SCRIPT = SCANNER_CORE_SCRIPT + r"""
(() => {
  function extractSpoolId(value) {
    const trimmed = String(value || "").trim();
    const patterns = [
      /web\+spoolman:s-(\d+)/i,
      /\/spool\/show\/(\d+)/,
      /\/spool\/(\d+)/,
      /[?&]spool_id=(\d+)/,
      /^(\d+)$/,
    ];

    for (const pattern of patterns) {
      const match = trimmed.match(pattern);
      if (match) {
        return match[1];
      }
    }
    return null;
  }

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
      if (!extractSpoolId(rawValue)) {
        return null;
      }
      return {
        url: `/scan?value=${encodeURIComponent(rawValue)}&stay=1`,
        status: `Scanned spool QR. Opening bin scanner...`,
      };
    },
  });
})();
"""


SCAN_PAGE_SCRIPT = SCANNER_CORE_SCRIPT + r"""
(() => {
  function toBinUrl(rawValue) {
    const value = String(rawValue || "").trim();
    const directMatch = value.match(/\/bin\/([^\/?#]+)/i);
    if (directMatch) {
      return `/bin/${encodeURIComponent(directMatch[1])}`;
    }

    const cleaned = value.toUpperCase().replace(/\s+/g, "");
    if (/^[A-Z]-\d{3}$/.test(cleaned)) {
      return `/bin/${encodeURIComponent(cleaned)}`;
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


def wants_scan_stay(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def extract_spool_id(value: str | None) -> int | None:
    if not value:
        return None

    raw_value = value.strip()
    for pattern in SPOOL_ID_PATTERNS:
        match = re.search(pattern, raw_value)
        if match:
            return int(match.group(1))
    return None


def spool_url(spool_id: int) -> str:
    return f"{SPOOLMAN_BASE}/spool/show/{spool_id}"


def normalize_location(location: str) -> str:
    return location.strip().upper()


def default_bins() -> list[str]:
    front = [f"F-{index:03d}" for index in range(1, 21)]
    back = [f"B-{index:03d}" for index in range(1, 5)]
    return front + back


def auth_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    return headers


def spool_location_values(spool: dict[str, Any]) -> set[str]:
    values: set[str] = set()

    for key in LOCATION_KEYS:
        value = spool.get(key)
        if value:
            values.add(normalize_location(str(value)))

    extra = spool.get("extra")
    if isinstance(extra, dict):
        for key in EXTRA_LOCATION_KEYS:
            value = extra.get(key)
            if value:
                values.add(normalize_location(str(value)))

    return values


def spools_in_location(spools: list[dict[str, Any]], location: str) -> list[dict[str, Any]]:
    normalized_location = normalize_location(location)
    return [spool for spool in spools if normalized_location in spool_location_values(spool)]


def spool_summary(spool: dict[str, Any]) -> str:
    details: list[str] = []
    filament = spool.get("filament")
    if isinstance(filament, dict):
        vendor = filament.get("vendor")
        if isinstance(vendor, dict) and vendor.get("name"):
            details.append(str(vendor["name"]))
        for key in ("name", "material"):
            value = filament.get(key)
            if value:
                details.append(str(value))

    for key in ("name", "material"):
        value = spool.get(key)
        if value:
            details.append(str(value))

    unique_details = list(dict.fromkeys(details))
    if unique_details:
        return " / ".join(unique_details)
    return "No extra material details from Spoolman"


def spool_display_name(spool: dict[str, Any]) -> str | None:
    value = spool.get("name")
    if value:
        return str(value)

    filament = spool.get("filament")
    if isinstance(filament, dict):
        filament_name = filament.get("name")
        if filament_name:
            return str(filament_name)

    summary = spool_summary(spool)
    if summary != "No extra material details from Spoolman":
        return summary
    return None


def selected_spool_id(request: Request | None) -> int | None:
    if request is None:
        return None
    return extract_spool_id(request.cookies.get(COOKIE_NAME, ""))


def spool_color_hex(spool: dict[str, Any]) -> str | None:
    filament = spool.get("filament")
    candidates: list[Any] = []
    if isinstance(filament, dict):
        candidates.append(filament.get("color_hex"))
    candidates.append(spool.get("color_hex"))

    for value in candidates:
        if not value:
            continue
        normalized = str(value).strip()
        if re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", normalized):
            return normalized.upper()

    return None


def nav_link(label: str, href: str, *, active: bool = False, external: bool = False) -> str:
    class_name = "nav-link active" if active else "nav-link"
    rel = ' rel="noreferrer"' if external else ""
    target = ' target="_blank"' if external else ""
    return f'<a class="{class_name}" href="{escape(href, quote=True)}"{rel}{target}>{escape(label)}</a>'


def render_page(
    title: str,
    body: str,
    *,
    request: Request | None = None,
    active_nav: str = "home",
    status_code: int = 200,
) -> HTMLResponse:
    current_spool_id = selected_spool_id(request)
    nav_links = [
        nav_link("Home", "/", active=active_nav == "home"),
        nav_link("Bin Labels", "/bins", active=active_nav == "bins"),
        nav_link("Spool Labels", "/spools", active=active_nav == "spools"),
    ]
    if current_spool_id is not None:
        nav_links.append(nav_link(f"Spool {current_spool_id}", spool_url(current_spool_id), external=True))
    nav_links.append(nav_link("Spoolman", SPOOLMAN_BASE, external=True))

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)} · SpoolBud</title>
    <style>{BASE_STYLES}</style>
  </head>
  <body>
    <div class="shell">
      <header class="topbar">
        <div class="topbar-left">
          <button id="menuToggle" class="menu-toggle" type="button" aria-expanded="false" aria-controls="sideNav" aria-label="Open navigation menu">☰</button>
          <div class="brand">
            <a href="/"><strong>SpoolBud</strong></a>
            <span>Fast QR workflows for Spoolman bins</span>
          </div>
        </div>
        <button id="themeToggle" class="theme-toggle" type="button">Dark mode</button>
      </header>
      <div id="sideOverlay" class="side-overlay" aria-hidden="true"></div>
      <nav id="sideNav" class="side-nav" aria-label="Primary">
        <div class="side-nav-links">
          {"".join(nav_links)}
          <button id="themeToggleSide" class="theme-toggle" type="button">Dark mode</button>
        </div>
      </nav>
      {body}
    </div>
    <script>{THEME_SCRIPT}</script>
  </body>
</html>
"""
    return HTMLResponse(html, status_code=status_code)


def render_spool_cards(spools: list[dict[str, Any]]) -> str:
    cards: list[str] = []
    for spool in spools:
        spool_id = spool.get("id", "?")
        link_markup = ""
        color_markup = ""
        if isinstance(spool_id, int):
            link_markup = (
                f'<p><a href="{escape(spool_url(spool_id), quote=True)}" '
                'target="_blank" rel="noreferrer">Open in Spoolman</a></p>'
            )
        color_hex = spool_color_hex(spool)
        if color_hex:
            color_markup = (
                '<div class="color-row">'
                f'<span class="color-swatch" style="background:{escape(color_hex, quote=True)};"></span>'
                f'<span class="muted">Color {escape(color_hex)}</span>'
                "</div>"
            )
        cards.append(
            f"""
            <article class="card">
              <h3>Spool {escape(str(spool_id))}</h3>
              <p class="spool-meta muted">{escape(spool_summary(spool))}</p>
              {color_markup}
              {link_markup}
            </article>
            """
        )
    return "".join(cards)


async def fetch_spoolman_spools() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(f"{SPOOLMAN_BASE}/api/v1/spool", headers=auth_headers())
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []


async def fetch_spoolman_spool(spool_id: int) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(f"{SPOOLMAN_BASE}/api/v1/spool/{spool_id}", headers=auth_headers())
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


async def fetch_spoolman_locations() -> list[str]:
    spools = await fetch_spoolman_spools()
    seen: set[str] = set()

    for spool in spools:
        seen.update(spool_location_values(spool))

    return sorted(seen)


async def fetch_spools_in_location(location: str) -> list[dict[str, Any]]:
    return spools_in_location(await fetch_spoolman_spools(), location)


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        return await client.patch(
            f"{SPOOLMAN_BASE}/api/v1/spool/{spool_id}",
            headers=auth_headers(),
            json={"location": location},
        )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    current_spool_id = selected_spool_id(request)
    current_spool_markup = (
        f'<span class="chip">Selected spool: <strong>{current_spool_id}</strong></span>' if current_spool_id else ""
    )
    body = f"""
    <main class="stack">
      <section class="panel hero">
        <div class="summary">
          <span class="chip">Two-scan workflow</span>
          <span class="chip">Cookie-backed spool selection</span>
          {current_spool_markup}
        </div>
        <div>
          <h1>Scan a spool, then scan a bin</h1>
          <p class="muted">Open SpoolBud, scan a Spoolman spool QR, then scan a stable bin QR such as <code>/bin/F-001</code> to update its location in Spoolman.</p>
        </div>
      </section>

      <section class="panel scanner-wrap">
        <h2>Scan a Spoolman QR</h2>
        <p class="muted">Start here for the in-browser flow: scan a native Spoolman spool QR such as <code>web+spoolman:s-42</code>, then SpoolBud will open the bin scanner on the next screen.</p>
        <div class="toolbar">
          <button id="startSpoolScanner" class="button" type="button">Open scanner</button>
        </div>
        <p id="spoolScannerStatus" class="muted">Tap <strong>Open scanner</strong> to scan a spool QR in a popup.</p>
        <label>
          <div class="muted">Supported spool QR payload example</div>
          <input id="spoolScanReference" class="input" value="" readonly />
        </label>
      </section>
      <section id="spoolScannerModal" class="scanner-modal" aria-hidden="true">
        <div class="scanner-modal-card">
          <div class="toolbar">
            <button id="runSpoolScanner" class="button" type="button">Start camera</button>
            <button id="stopSpoolScanner" class="button" type="button" disabled>Stop scanner</button>
            <button id="closeSpoolScanner" class="button" type="button">Close</button>
          </div>
          <video id="spoolScannerVideo" class="scanner-video" playsinline muted></video>
          <canvas id="spoolScannerCanvas" hidden></canvas>
        </div>
      </section>

      <section class="panel">
        <h2>Quick Links</h2>
        <ul class="clean">
          <li><a href="/bins">Open the bin label generator</a></li>
          <li><a href="/spools">Open the Spoolman-compatible spool label generator</a></li>
          <li><a href="/healthz">Check health output</a></li>
          <li><a href="/status">Inspect JSON session status</a></li>
          <li><a href="{escape(SPOOLMAN_BASE, quote=True)}" target="_blank" rel="noreferrer">Open Spoolman</a></li>
        </ul>
      </section>
    </main>
    <script>{HOME_SCAN_PAGE_SCRIPT}</script>
    """
    return render_page("Home", body, request=request, active_nav="home")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "spoolman_base": SPOOLMAN_BASE}


@app.get("/scan")
async def scan(request: Request, value: str, stay: str | None = Query(default=None)):
    spool_id = extract_spool_id(value)
    if spool_id is None:
        raise HTTPException(status_code=400, detail="Could not parse spool ID from QR value")

    if wants_scan_stay(stay):
        spool_name_markup = ""
        spool_details_notice = ""
        try:
            spool = await fetch_spoolman_spool(spool_id)
        except httpx.HTTPError:
            spool = {}
            spool_details_notice = (
                '<p class="muted">SpoolBud selected this spool, but could not load its details from Spoolman right now.</p>'
            )

        if spool:
            display_name = spool_display_name(spool)
            if display_name:
                spool_name_markup = f'<p><strong>{escape(display_name)}</strong></p>'

        body = f"""
        <main class="stack">
          <section class="panel">
            <h1>Spool {spool_id} selected</h1>
            {spool_name_markup}
            <p class="muted">You can stay in SpoolBud and scan a bin QR directly from this page. WebKit-based browsers such as Chrome on iPhone automatically use a compatibility scanner.</p>
            {spool_details_notice}
            <p><a href="{escape(spool_url(spool_id), quote=True)}" target="_blank" rel="noreferrer">Open this spool in Spoolman</a></p>
          </section>

          <section class="panel scanner-wrap">
            <div class="toolbar">
              <button id="startBinScanner" class="button" type="button">Open bin scanner</button>
            </div>
            <p id="scannerStatus" class="muted">Tap <strong>Open bin scanner</strong> to scan a bin QR in a popup.</p>
            <label>
              <div class="muted">Bin URL prefix (reference)</div>
              <input id="spoolBudBase" class="input" value="" readonly />
            </label>
          </section>
          <section id="binScannerModal" class="scanner-modal" aria-hidden="true">
            <div class="scanner-modal-card">
              <div class="toolbar">
                <button id="runBinScanner" class="button" type="button">Start camera</button>
                <button id="stopBinScanner" class="button" type="button" disabled>Stop scanner</button>
                <button id="closeBinScanner" class="button" type="button">Close</button>
              </div>
              <video id="scannerVideo" class="scanner-video" playsinline muted></video>
              <canvas id="scannerCanvas" hidden></canvas>
            </div>
          </section>
        </main>
        <script>{SCAN_PAGE_SCRIPT}</script>
        """
        response = render_page("Spool Selected", body, request=request)
    else:
        response = RedirectResponse(url=spool_url(spool_id), status_code=302)

    response.set_cookie(COOKIE_NAME, str(spool_id), max_age=COOKIE_MAX_AGE, samesite="Lax")
    return response


@app.get("/select/{spool_id}")
def select_spool(spool_id: int):
    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    response.set_cookie(COOKIE_NAME, str(spool_id), max_age=COOKIE_MAX_AGE, samesite="Lax")
    return response


@app.get("/bin/{location}")
async def set_location(location: str, request: Request):
    normalized_location = normalize_location(location)
    spool_id = selected_spool_id(request)

    if spool_id is None:
        try:
            matching_spools = await fetch_spools_in_location(normalized_location)
        except httpx.HTTPError as exc:
            body = f"""
            <main class="panel">
              <h1>Bin lookup failed</h1>
              <p class="muted">No spool is currently selected, and SpoolBud could not load the contents of <strong>{escape(normalized_location)}</strong> from Spoolman.</p>
              <pre class="card">{escape(str(exc))}</pre>
            </main>
            """
            return render_page("Bin Lookup Failed", body, request=request, status_code=502)

        if matching_spools:
            body = f"""
            <main class="stack">
              <section class="panel">
                <h1>Contents of {escape(normalized_location)}</h1>
                <p class="muted">No spool was selected in this browser, so this scan is showing what Spoolman currently lists in the bin instead.</p>
              </section>
              <section class="spool-list grid">
                {render_spool_cards(matching_spools)}
              </section>
            </main>
            """
            return render_page(f"Bin {normalized_location}", body, request=request)

        body = f"""
        <main class="panel">
          <h1>{escape(normalized_location)} is empty</h1>
          <p class="muted">No spool is selected in this browser, and Spoolman does not currently list any spools in this bin.</p>
          <p>Scan a spool QR first if you want this bin scan to update a location.</p>
        </main>
        """
        return render_page(f"Bin {normalized_location}", body, request=request)

    resp = await patch_spool_location(spool_id, normalized_location)
    if resp.status_code >= 400:
        body = f"""
        <main class="panel">
          <h1>Update failed</h1>
          <p class="muted">Tried to set spool <strong>{spool_id}</strong> to <strong>{escape(normalized_location)}</strong>.</p>
          <pre class="card">{escape(resp.text)}</pre>
        </main>
        """
        return render_page("Update Failed", body, request=request, status_code=502)

    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    response.delete_cookie(COOKIE_NAME, samesite="Lax")
    return response


@app.get("/status", response_class=JSONResponse)
def status(request: Request) -> dict[str, object]:
    spool_id = selected_spool_id(request)
    return {
        "selected_spool_id": spool_id,
        "selected_spool_url": spool_url(spool_id) if spool_id else None,
    }


@app.get("/api/bins", response_class=JSONResponse)
async def api_bins(source: str = Query(default="default", pattern="^(default|spoolman)$")):
    if source == "spoolman":
        try:
            bins = await fetch_spoolman_locations()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to load bins from Spoolman: {exc}") from exc
        if bins:
            return {"source": "spoolman", "bins": bins}

    return {"source": "default", "bins": default_bins()}




@app.get("/api/spools", response_class=JSONResponse)
async def api_spools():
    try:
        spools = await fetch_spoolman_spools()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load spools from Spoolman: {exc}") from exc

    spool_ids = sorted({spool.get("id") for spool in spools if isinstance(spool.get("id"), int)})
    return {"source": "spoolman", "spool_ids": spool_ids}

@app.get("/qr.svg")
def qr_svg(value: str = Query(min_length=1, max_length=2048)) -> Response:
    qr = segno.make(value)
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=7, border=2)
    return Response(buffer.getvalue(), media_type="image/svg+xml")


@app.get("/bins", response_class=HTMLResponse)
def bins_page(request: Request) -> HTMLResponse:
    body = f"""
    <main class="stack">
      <section class="panel">
        <h1>Bin QR Generator</h1>
        <p class="muted">Generate stable QR labels for <code>/bin/&lt;location&gt;</code>. Load defaults, pull current locations from Spoolman, then render printable labels below.</p>
      </section>

      <section class="panel stack">
        <div class="toolbar">
          <label style="flex: 1 1 24rem;">
            <div class="muted">Public SpoolBud base URL</div>
            <input id="publicBase" class="input" value="" />
          </label>
          <button id="loadDefault" class="button" type="button">Load defaults</button>
          <button id="loadSpoolman" class="button" type="button">Load from Spoolman</button>
          <button id="render" class="button" type="button">Render labels</button>
        </div>

        <label>
          <div class="muted">Bin codes, one per line</div>
          <textarea id="bins" class="input"></textarea>
        </label>

        <div id="status" class="muted"></div>
        <div id="grid" class="grid"></div>
      </section>
    </main>
    <script>{BINS_PAGE_SCRIPT}</script>
    """
    return render_page("Bin Labels", body, request=request, active_nav="bins")


@app.get("/spools", response_class=HTMLResponse)
def spools_page(request: Request) -> HTMLResponse:
    body = f"""
    <main class="stack">
      <section class="panel">
        <h1>Spoolman-Compatible Spool QR Labels</h1>
        <p class="muted">Generate spool QR payloads in the <code>web+spoolman:s-&lt;id&gt;</code> format that Spoolman's built-in camera scanner understands.</p>
      </section>

      <section class="panel stack">
        <div class="toolbar">
          <button id="loadSpoolSample" class="button" type="button">Load sample IDs</button>
          <button id="loadSpoolmanSpools" class="button" type="button">Load from Spoolman</button>
          <button id="renderSpools" class="button" type="button">Render spool labels</button>
        </div>

        <label style="max-width: 24rem;">
          <div class="muted">QR format</div>
          <select id="spoolQrFormat" class="input">
            <option value="spoolman">Spoolman scanner payload (web+spoolman)</option>
            <option value="full-url">Full SpoolBud /scan URL</option>
          </select>
        </label>

        <label>
          <div class="muted">Public SpoolBud base URL (for full URL format)</div>
          <input id="spoolPublicBase" class="input" value="" />
        </label>

        <label>
          <input id="includeStayFlag" type="checkbox" checked /> Include <code>&amp;stay=1</code> in full URL QR labels
        </label>

        <input id="spoolmanBase" type="hidden" value="{escape(SPOOLMAN_BASE, quote=True)}" />

        <label>
          <div class="muted">Spool IDs or Spoolman spool URLs, one per line</div>
          <textarea id="spools" class="input" placeholder="42&#10;108&#10;256"></textarea>
        </label>

        <div id="spoolStatus" class="muted"></div>
        <div id="spoolGrid" class="grid"></div>
      </section>
    </main>
    <script>{{script}}</script>
    """.replace("{script}", SPOOLS_PAGE_SCRIPT)
    return render_page("Spool Labels", body, request=request, active_nav="spools")

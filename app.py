from __future__ import annotations

import re
from html import escape
from typing import Any

import httpx
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import ValidationError

from spoolbud.config import settings
from spoolbud.clients.spoolman import SpoolmanClient
from spoolbud.parsing.spool_ids import extract_spool_id
from spoolbud.services.spool_selection import clear_selected_spool, get_selected_spool, set_selected_spool
from spoolbud.services.qr import render_qr_svg
from spoolbud.services.bins import (
    configured_bins as build_configured_bins,
    default_bins,
    get_bin_contents,
    get_spoolman_locations,
    move_selected_spool_to_bin,
    normalize_location,
    spool_location_values,
    spools_in_location,
)
from spoolman_tags import TagScanError, TagScanRequest, resolve_tag

# Compatibility aliases remain while responsibilities move into the package.
SPOOLMAN_BASE = settings.spoolman_base
API_TOKEN = settings.spoolman_api_token
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = settings.cookie_max_age
DESTINATIONS = settings.destinations

app = FastAPI(title="SpoolBud Helper")

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


def wants_scan_stay(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def spool_url(spool_id: int) -> str:
    return f"{SPOOLMAN_BASE}/spool/show/{spool_id}"


def configured_bins() -> list[str]:
    return build_configured_bins(DESTINATIONS)


def auth_headers() -> dict[str, str]:
    return SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).auth_headers()


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


def selected_spool_id(request: Request | None) -> int | None:
    return get_selected_spool(request, cookie_name=COOKIE_NAME, parser=extract_spool_id)


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
        if re.fullmatch(r"[0-9a-fA-F]{6}", normalized):
            normalized = "#" + normalized
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
    <script>{COMMON_SCRIPT}</script>
  </head>
  <body>
    <div class="shell">
      <header class="topbar">
        <div class="topbar-left">
          <button id="menuToggle" class="menu-toggle" type="button" aria-expanded="false" aria-controls="sideNav" aria-label="Open navigation menu">☰</button>
          <div class="brand">
            <a href="/"><strong>SpoolBud</strong></a>
            <span>NFC and QR workflows for Spoolman</span>
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


def render_spool_cards(spools: list[dict[str, Any]], *, compact: bool = False) -> str:
    cards: list[str] = []
    for spool in spools:
        spool_id = spool.get("id", "?")
        link_markup = ""
        color_markup = ""
        if isinstance(spool_id, int) and not compact:
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
            <article class="{"" if compact else "card"}">
              {"" if compact else f'<h3>Spool {escape(str(spool_id))}</h3>'}
              <p class="spool-meta muted">{escape(spool_summary(spool))}</p>
              <p class="muted">Location: {escape(", ".join(sorted(spool_location_values(spool))) or "Unassigned")}</p>
              {color_markup}
              {link_markup}
            </article>
            """
        )
    return "".join(cards)


async def fetch_spoolman_spools() -> list[dict[str, Any]]:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).get_spools()


async def fetch_spoolman_spool(spool_id: int) -> dict[str, Any]:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).get_spool(spool_id)


async def fetch_spoolman_locations() -> list[str]:
    return await get_spoolman_locations(fetch_spoolman_spools)


async def fetch_spools_in_location(location: str) -> list[dict[str, Any]]:
    return await get_bin_contents(location, fetch_spoolman_spools)


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).update_spool_location(spool_id, location)


def require_selection(request: Request, expected_spool_id: int) -> None:
    if selected_spool_id(request) != expected_spool_id:
        raise HTTPException(409, "Spool selection changed or was cleared. Scan your spool again before continuing.")


async def move_selected_spool(request: Request, spool_id: int, location: str) -> str:
    return await move_selected_spool_to_bin(
        request,
        spool_id,
        location,
        get_selection=selected_spool_id,
        update_location=patch_spool_location,
    )


def clear_selection(response: Response) -> Response:
    return clear_selected_spool(response, cookie_name=COOKIE_NAME)


def set_selection(response: Response, spool_id: int) -> Response:
    return set_selected_spool(response, spool_id, cookie_name=COOKIE_NAME, max_age=COOKIE_MAX_AGE)


@app.post("/api/tag/scan")
async def scan_tag(request: Request):
    # Validate here so even malformed scans clear an older pending selection.
    try:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise ValueError("Expected JSON")
        scan = TagScanRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        return clear_selection(JSONResponse({"detail": "Send a JSON scan with a hardware UID and valid reader details. No spool was selected."}, status_code=400))
    try:
        spool_id = await resolve_tag(scan, base_url=SPOOLMAN_BASE, headers=auth_headers())
    except TagScanError as exc:
        return clear_selection(JSONResponse({"detail": str(exc)}, status_code=exc.status_code))
    if spool_id is None:
        return clear_selection(JSONResponse({"matched_spool_id": None, "detail": "This tag is not linked to a spool. Link it in Spoolman, then scan again."}))
    return set_selection(JSONResponse({"matched_spool_id": spool_id}), spool_id)


@app.post("/api/move")
async def move_spool(request: Request, spool_id: int = Body(gt=0), location: str = Body()):
    location = await move_selected_spool(request, spool_id, location)
    return clear_selection(JSONResponse({"spool_id": spool_id, "location": location}))


@app.post("/api/selection/clear")
def cancel_selection(request: Request, spool_id: int = Body(embed=True, gt=0)):
    require_selection(request, spool_id)
    return clear_selection(JSONResponse({"ok": True}))


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    current_spool_id = selected_spool_id(request)
    current_spool_markup = (
        f'<span id="currentSelection" class="chip">Selected spool: <strong>{current_spool_id}</strong></span>' if current_spool_id else ""
    )
    body = f"""
    <main class="stack">
      <section class="panel hero">
        <div class="summary">
          <span class="chip">Tap or scan</span>
          {current_spool_markup}
        </div>
        <div>
          <h1>Select a spool, then choose its destination</h1>
          <p class="muted">Scan a tag through Spoolman or use a spool QR. Then move or store the selected spool using a destination button or bin QR.</p>
          {f'<p id="continueSelection"><a class="button" href="/selected">Continue with spool {current_spool_id}</a></p>' if current_spool_id else ""}
        </div>
      </section>

      <section class="panel stack">
        <h2>Scan an NFC / RFID tag</h2>
        <p class="muted">Use a reader that enters the hardware UID, or paste a UID from a reader app. Spoolman decides which spool it identifies.</p>
        <form id="tagScanForm" class="stack">
          <label>Tag UID
            <input id="tagUid" class="input" required maxlength="128" autocomplete="off" spellcheck="false" placeholder="04:A2:B3:C4:D5:E6:F7" />
          </label>
          <label>Reader ID (optional)
            <input id="tagReaderId" class="input" maxlength="64" autocomplete="off" placeholder="desk-reader" />
          </label>
          <button id="submitTagScan" class="button" type="submit">Find spool in Spoolman</button>
        </form>
        <div class="toolbar">
          <button id="readNfc" class="button" type="button" hidden>Read tag with this phone</button>
          <button id="stopNfc" class="button" type="button" hidden>Stop reading</button>
        </div>
        <p id="tagScanStatus" role="status" aria-live="polite"></p>
        <p class="muted">Keyboard readers: focus Tag UID and send the hex UID followed by Enter. iPhone Safari needs a reader or companion app to supply the UID; it cannot read a blank tag directly.</p>
        <p><a href="{escape(SPOOLMAN_BASE, quote=True)}" target="_blank" rel="noreferrer">Link or reassign tags in Spoolman</a></p>
      </section>

      <section class="panel scanner-wrap">
        <h2>Scan a Spoolman QR</h2>
        <p class="muted">Scan a Spoolman QR such as <code>web+spoolman:s-42</code> or a SpoolBud spool link to choose a destination.</p>
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
    <script>{HOME_SCAN_PAGE_SCRIPT}{TAG_SCAN_PAGE_SCRIPT}</script>
    """
    return render_page("Home", body, request=request, active_nav="home")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "spoolman_base": SPOOLMAN_BASE}


async def render_selected_spool(spool_id: int) -> HTMLResponse:
    spool_details_markup = ""
    spool_details_notice = ""
    try:
        spool = await fetch_spoolman_spool(spool_id)
    except httpx.HTTPError:
        spool = {}
        spool_details_notice = (
            '<p class="muted">SpoolBud selected this spool, but could not load its details from Spoolman right now.</p>'
        )

    if spool:
        spool_details_markup = render_spool_cards([spool], compact=True)

    body = f"""
    <main class="stack">
      <section class="panel">
        <h1 id="selectedHeading">Spool {spool_id} selected</h1>
        <div id="spoolDetails">{spool_details_markup}{spool_details_notice}</div>
        <p><a href="{escape(spool_url(spool_id), quote=True)}" target="_blank" rel="noreferrer">Open this spool in Spoolman</a></p>
        <p id="moveComplete" hidden><a class="button" href="/">Move another spool</a></p>
      </section>

      <div id="selectionActions" class="stack" data-spool-id="{spool_id}">
      <section class="panel stack">
        <h2>Choose a destination</h2>
        <p class="muted">Move or store this spool by choosing a location below or scanning its bin QR. A location change does not load a printer.</p>
        <p id="destinationStatus" class="muted" role="status">Loading destinations...</p>
        <p id="moveStatus" role="status" aria-live="polite"></p>
        <form id="destinationForm" class="stack">
          <label>Find or enter a destination
            <input id="destinationSearch" class="input" type="search" required maxlength="200" placeholder="F-001 or PRINTER-1" />
          </label>
          <button class="button" type="submit">Move to entered destination</button>
        </form>
        <div id="destinations" class="grid destination-grid"></div>
        <button id="cancelSelection" class="button" type="button">Cancel selection</button>
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
      </div>
    </main>
    <script>{SCAN_PAGE_SCRIPT}</script>
    """
    response = render_page("Spool Selected", body)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/selected")
async def selected_spool_page(request: Request):
    spool_id = selected_spool_id(request)
    if spool_id is None:
        return render_page("Select a spool", '<main class="panel"><h1>No spool selected</h1><p><a href="/">Scan a tag or spool QR to begin.</a></p></main>', status_code=409)
    return await render_selected_spool(spool_id)


@app.get("/scan")
async def scan(request: Request, value: str, stay: str | None = Query(default=None)):
    spool_id = extract_spool_id(value)
    if not spool_id:
        raise HTTPException(status_code=400, detail="Could not identify a spool from this QR value.")
    response = (await render_selected_spool(spool_id) if wants_scan_stay(stay)
                else RedirectResponse(url=spool_url(spool_id), status_code=302))
    return set_selection(response, spool_id)


@app.get("/select/{spool_id}")
def select_spool(spool_id: int):
    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    return set_selection(response, spool_id)


@app.get("/bin/{location:path}")
async def set_location(location: str, request: Request, stay: str | None = None, spool_id: int | None = Query(default=None, gt=0)):
    normalized_location = normalize_location(location)
    if spool_id is not None:
        try:
            require_selection(request, spool_id)
        except HTTPException as exc:
            return render_move_error(request, exc)
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
          <p>Resolve a spool tag through Spoolman or scan a spool QR first to update its location.</p>
        </main>
        """
        return render_page(f"Bin {normalized_location}", body, request=request)

    try:
        normalized_location = await move_selected_spool(request, spool_id, normalized_location)
    except HTTPException as exc:
        return render_move_error(request, exc)

    if wants_scan_stay(stay):
        body = f"""<main class="panel">
          <h1>Spool {spool_id} moved to {escape(normalized_location)}</h1>
          <p><a class="button" href="/">Move another spool</a></p>
          <p><a href="{escape(spool_url(spool_id), quote=True)}">Open in Spoolman</a></p>
        </main>"""
        response = render_page("Spool moved", body)
    else:
        response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    return clear_selection(response)


def render_move_error(request: Request, exc: HTTPException) -> HTMLResponse:
    body = f"""<main class="panel">
      <h1>Move not confirmed</h1><p>{escape(str(exc.detail))}</p>
      <p><a href="/">Return to SpoolBud</a></p>
    </main>"""
    return render_page("Move not confirmed", body, request=request, status_code=exc.status_code)


@app.get("/status", response_class=JSONResponse)
def status(request: Request) -> dict[str, object]:
    spool_id = selected_spool_id(request)
    return {
        "selected_spool_id": spool_id,
        "selected_spool_url": spool_url(spool_id) if spool_id else None,
    }


@app.get("/api/bins", response_class=JSONResponse)
async def api_bins(source: str = Query(default="default", pattern="^(default|spoolman|all)$")):
    if source == "all":
        bins = set(configured_bins())
        warning = None
        try:
            bins.update(await fetch_spoolman_locations())
        except httpx.HTTPError:
            warning = "Could not load locations from Spoolman. Showing configured/default destinations."
        return {"source": "all", "bins": sorted(bins), "warning": warning}
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

    by_id = {spool["id"]: spool for spool in spools if isinstance(spool.get("id"), int) and spool["id"] > 0}
    summaries = [
        {"id": spool_id, "description": spool_summary(by_id[spool_id]),
         "color_hex": spool_color_hex(by_id[spool_id]), "locations": sorted(spool_location_values(by_id[spool_id]))}
        for spool_id in sorted(by_id)
    ]
    return {"source": "spoolman", "spool_ids": sorted(by_id), "spools": summaries}

@app.get("/qr.svg")
def qr_svg(value: str = Query(min_length=1, max_length=2048)) -> Response:
    return Response(render_qr_svg(value), media_type="image/svg+xml")


@app.get("/bins", response_class=HTMLResponse)
def bins_page(request: Request) -> HTMLResponse:
    body = f"""
    <main class="stack">
      <section class="panel">
        <h1>Bin QR Generator</h1>
        <p class="muted">Prepare QR labels for storage locations. Load configured shortcuts and used Spoolman locations, or enter names below.</p>
        <p class="muted">Spoolman owns the stored location. Local shortcuts only help choose a destination. Opening a bin QR with a selected spool moves it there.</p>
      </section>

      <section class="panel stack">
        <div class="toolbar">
          <label style="flex: 1 1 24rem;">
            <div class="muted">Public SpoolBud base URL</div>
            <input id="publicBase" class="input" value="" />
          </label>
          <button id="loadDefault" class="button" type="button">Load defaults</button>
          <button id="loadSpoolman" class="button" type="button">Load destinations</button>
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
        <p>Create each physical spool in <a href="{escape(SPOOLMAN_BASE, quote=True)}" target="_blank" rel="noreferrer">Spoolman</a>, then load the list below to prepare compatibility QR labels.</p>
        <p class="muted">For NFC/RFID, use the spool’s Tags section in Spoolman to link its hardware UID. No data needs to be written to the tag. SpoolBud resolves tag associations through Spoolman.</p>
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
            <option value="full-url">Full SpoolBud /scan URL</option>
            <option value="spoolman">Spoolman scanner payload (web+spoolman)</option>
          </select>
        </label>

        <label>
          <div class="muted">Public SpoolBud base URL (for full URL QR labels)</div>
          <input id="spoolPublicBase" class="input" value="" />
        </label>

        <label>
          <input id="includeStayFlag" type="checkbox" checked /> Include <code>&amp;stay=1</code> in full URL QR labels
        </label>

        <label>
          <div class="muted">Spool IDs or Spoolman spool URLs, one per line</div>
          <textarea id="spools" class="input" placeholder="42&#10;108&#10;256"></textarea>
        </label>

        <div id="spoolStatus" class="muted"></div>
        <label>Find a spool by ID, material, color, or location
          <input id="spoolSearch" class="input" type="search" placeholder="Search loaded labels" />
        </label>
        <div id="spoolGrid" class="grid"></div>
      </section>
    </main>
    <script>{{script}}</script>
    """.replace("{script}", SPOOLS_PAGE_SCRIPT)
    return render_page("Spool Labels", body, request=request, active_nav="spools")

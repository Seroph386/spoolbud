"""Reusable HTML page and spool components."""

from __future__ import annotations

import re
from html import escape
from typing import Any

from fastapi.responses import HTMLResponse

from spoolbud.rendering.assets import BASE_STYLES, COMMON_SCRIPT, THEME_SCRIPT
from spoolbud.services.bins import spool_location_values


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
    return " / ".join(unique_details) if unique_details else "No extra material details from Spoolman"


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
    current_spool_id: int | None,
    spoolman_base: str,
    active_nav: str = "home",
    status_code: int = 200,
) -> HTMLResponse:
    nav_links = [
        nav_link("Home", "/", active=active_nav == "home"),
        nav_link("Bin Labels", "/bins", active=active_nav == "bins"),
        nav_link("Spool Labels", "/spools", active=active_nav == "spools"),
    ]
    if current_spool_id is not None:
        nav_links.append(nav_link(f"Spool {current_spool_id}", f"{spoolman_base}/spool/show/{current_spool_id}", external=True))
    nav_links.append(nav_link("Spoolman", spoolman_base, external=True))

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


def render_spool_cards(spools: list[dict[str, Any]], *, spoolman_base: str, compact: bool = False) -> str:
    cards: list[str] = []
    for spool in spools:
        spool_id = spool.get("id", "?")
        link_markup = ""
        color_markup = ""
        if isinstance(spool_id, int) and not compact:
            link_markup = (
                f'<p><a href="{escape(f"{spoolman_base}/spool/show/{spool_id}", quote=True)}" '
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

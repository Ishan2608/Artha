"""
config.py — Frontend configuration

Single source of truth for:
  - Backend API base URL and all endpoint paths
  - App-level settings (page title, layout, etc.)
  - Theme color tokens (mirrored in main.css via CSS variables)

To point the frontend at a different backend, change BASE_URL only.
"""

import os

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL: str = os.getenv("ARTHA_API_URL", "http://localhost:8000")


class Endpoints:
    """All backend route URLs derived from BASE_URL."""

    # Auth
    REGISTER      = f"{BASE_URL}/auth/register"
    LOGIN         = f"{BASE_URL}/auth/login"
    ME            = f"{BASE_URL}/auth/me"

    # Chat
    CHAT          = f"{BASE_URL}/chat"
    CHAT_HISTORY  = f"{BASE_URL}/chat/history"

    # Files
    UPLOAD        = f"{BASE_URL}/upload"
    FILES         = f"{BASE_URL}/files"

    # Misc
    CONTEXT       = f"{BASE_URL}/context"
    HEALTH        = f"{BASE_URL}/health"


# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────

class AppConfig:
    PAGE_TITLE   = "Artha · AI Financial Analyst"
    PAGE_ICON    = "⬡"
    LAYOUT       = "wide"
    VERSION      = "2.0.0"

    # File upload constraints (must match backend ALLOWED_EXTENSIONS)
    ALLOWED_EXTENSIONS = ["pdf", "docx", "doc", "xlsx", "xls", "csv", "txt", "ppt", "pptx"]
    MAX_UPLOAD_MB      = 50

    # How many recent messages to show before "load more"
    MESSAGES_PER_PAGE  = 100

    # Request timeout (seconds)
    REQUEST_TIMEOUT    = 120


# ─────────────────────────────────────────────────────────────────────────────
# THEME  (kept in sync with CSS variables in styles/main.css)
# ─────────────────────────────────────────────────────────────────────────────

class Theme:
    # Backgrounds
    BG_DEEP      = "#04050a"
    BG_BASE      = "#080b12"
    BG_SURFACE   = "#0e1119"
    BG_CARD      = "#12151f"
    BG_CARD_2    = "#181b27"

    # Borders
    BORDER       = "#1c2035"
    BORDER_GLOW  = "#00c9b140"

    # Accents
    TEAL         = "#00c9b1"   # Artha brand / AI messages
    TEAL_DIM     = "#00c9b130"
    AMBER        = "#f0a500"   # User messages / CTAs
    AMBER_DIM    = "#f0a50025"
    ROSE         = "#ff5e7d"   # Errors / destructive actions

    # Text
    TEXT         = "#dde1ee"
    TEXT_MUTED   = "#4a5068"
    TEXT_DIM     = "#7a84a0"

    # Chart palette
    CHART_COLORS = ["#00c9b1", "#f0a500", "#7c6aff", "#ff5e7d", "#3dd68c", "#f4d03f"]

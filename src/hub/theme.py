"""
Celsius AI — UI palette.

Visual language mixes:
  Gemini  → violet/purple primary, sky-blue secondary
  Claude  → warm amber accent
  ChatGPT → deep-dark background, teal-green success

Import this from any hub module to keep colors consistent.
"""

# ── Colours ───────────────────────────────────────────────────────────────────
BG         = "#0d0d14"   # Main window background
SURFACE    = "#13131e"   # Panel / toolbar background
CARD       = "#1a1a2e"   # Card / LabelFrame fill
BORDER     = "#252540"   # Subtle border

PRIMARY    = "#7c3aed"   # Gemini violet/purple
PRI_LIGHT  = "#a78bfa"   # Lighter purple — hover, selected text
PRI_DARK   = "#6d28d9"   # Darker purple — pressed

SECONDARY  = "#0ea5e9"   # Sky blue (Gemini secondary)

AMBER      = "#f59e0b"   # Claude warm amber — warnings / restart
GREEN      = "#10b981"   # ChatGPT teal-green — success / start
RED        = "#ef4444"   # Danger / stop

TEXT       = "#e2e8f0"   # Primary text
TEXT_MUTED = "#64748b"   # Secondary / hint text
TEXT_DIM   = "#94a3b8"   # Dimmed / placeholder

# ── Convenience dict (for code that prefers dict access) ─────────────────────
PALETTE: dict = {
    "bg":         BG,
    "surface":    SURFACE,
    "card":       CARD,
    "border":     BORDER,
    "primary":    PRIMARY,
    "pri_light":  PRI_LIGHT,
    "pri_dark":   PRI_DARK,
    "secondary":  SECONDARY,
    "amber":      AMBER,
    "green":      GREEN,
    "red":        RED,
    "text":       TEXT,
    "text_muted": TEXT_MUTED,
    "text_dim":   TEXT_DIM,
}

# ── Typography ────────────────────────────────────────────────────────────────
FONT       = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_SM    = ("Segoe UI", 9)
FONT_SM_B  = ("Segoe UI", 9, "bold")
FONT_LG    = ("Segoe UI", 14, "bold")
FONT_HERO  = ("Segoe UI", 22, "bold")
FONT_MONO  = ("Consolas", 10)

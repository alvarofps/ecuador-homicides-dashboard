"""Shared pieces for the three dashboards: data access, FT-style look and bilingual helpers.

Data access
-----------
By default the apps read the marts from Snowflake using the `snowflake` gateway in the
project's config.yaml (the same settings SQLMesh and scripts/load_raw.py use).

Environment variables (all optional):
  DW_BACKEND   snowflake (default) | duckdb
  DW_CONFIG    path to config.yaml                     (default: ../config.yaml)
  DW_GATEWAY   gateway name in config.yaml             (default: snowflake)
  DW_SCHEMA    schema holding the marts                (default: MARTS; e.g. MARTS__DEV for `sqlmesh plan dev`)
  DW_DUCKDB    DuckDB file when DW_BACKEND=duckdb      (default: ../local_dw.duckdb)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

# ---------------------------------------------------------------------------
# Look: FT-inspired palette (validated for colour-blind separation and 3:1 contrast on the paper tone)
# ---------------------------------------------------------------------------
PAPER = "#FFF1E5"
WHEAT = "#F2DFCE"
INK = "#33302E"
MUTED = "#66605C"
GRID = "#E6D9CE"
OXFORD = "#0F5499"
CLARET = "#990F3D"
SERIES = ["#0F5499", "#990F3D", "#00989A", "#C8641A", "#7D4CB3", "#4E8A2A"]  # fixed order, never cycled
SEQUENTIAL = ["#F7E4D6", "#EFC1AE", "#DE8C86", "#C25267", "#990F3D", "#5E0B26"]  # one hue, light -> dark

FONT_SANS = "'Source Sans 3', 'Helvetica Neue', Arial, sans-serif"
FONT_SERIF = "'Source Serif 4', Georgia, 'Times New Roman', serif"

SOURCE_MDI = "Fuente / Source: Ministerio del Interior (MDI-DINASED), homicidios intencionales"
SOURCE_INEC = "Población / Population: INEC, Estimaciones y Proyecciones de Población, Revisión 2024"

# ---------------------------------------------------------------------------
# Bilingual labels for coded values
# ---------------------------------------------------------------------------
CRIME_LABELS = {
    "TODOS": "Todos / All",
    "ASESINATO": "Asesinato / Aggravated murder",
    "HOMICIDIO": "Homicidio / Homicide",
    "FEMICIDIO": "Femicidio / Femicide",
    "SICARIATO": "Sicariato / Contract killing",
}
CRIME_ORDER = ["ASESINATO", "HOMICIDIO", "FEMICIDIO", "SICARIATO"]

SEX_LABELS = {"HOMBRE": "Hombres / Men", "MUJER": "Mujeres / Women", "NO DETERMINADO": "No determinado / Unknown", "SIN_DATO": "Sin dato / No data"}

LIFE_STAGE_ORDER = ["NIÑEZ (0-11)", "ADOLESCENCIA (12-17)", "JUVENTUD (18-29)", "ADULTEZ (30-64)", "ADULTO MAYOR (65+)", "SIN_DATO"]
LIFE_STAGE_LABELS = {
    "NIÑEZ (0-11)": "Niñez / Children 0–11",
    "ADOLESCENCIA (12-17)": "Adolescencia / Teens 12–17",
    "JUVENTUD (18-29)": "Juventud / Young adults 18–29",
    "ADULTEZ (30-64)": "Adultez / Adults 30–64",
    "ADULTO MAYOR (65+)": "Adulto mayor / Older adults 65+",
    "SIN_DATO": "Sin dato / Unknown age",
}

WEAPON_LABELS = {
    "ARMA DE FUEGO": "Arma de fuego / Firearm",
    "ARMA BLANCA": "Arma blanca / Knife or blade",
    "ARMA CONTUNDENTE": "Arma contundente / Blunt object",
    "CONSTRICTORA": "Constrictora / Strangulation",
    "SUSTANCIAS": "Sustancias / Substances",
    "OTROS": "Otros / Other",
}


def label(mapping: dict, value) -> str:
    return mapping.get(value, str(value).title() if isinstance(value, str) else str(value))


_PLACE_FIXES = {"Sto Dgo De Los Tsáchilas": "Santo Domingo", "Santo Domingo De Los Tsáchilas": "Santo Domingo"}


def place(name: str) -> str:
    """Title-case an upper-case place name and shorten the one very long province name."""
    if not isinstance(name, str):
        return name
    t = name.title()
    for word in (" De ", " Del ", " La ", " Las ", " Los ", " El ", " Y "):
        t = t.replace(word, word.lower())
    return _PLACE_FIXES.get(name.title(), t)


def fmt_int(n) -> str:
    """Thousands with a thin space, readable in Spanish and English alike (45 497)."""
    if n is None or pd.isna(n):
        return "–"
    return f"{int(round(n)):,}".replace(",", " ")


def fmt_rate(x, digits: int = 1) -> str:
    if x is None or pd.isna(x):
        return "–"
    return f"{x:.{digits}f}"


# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------
CSS = f"""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {{ background: {PAPER}; color: {INK}; }}
[data-testid="stHeader"] {{ background: {PAPER}; }}
[data-testid="stSidebar"] {{ background: {WHEAT}; }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button {{ font-family: {FONT_SANS}; }}
.block-container {{ max-width: 1180px; padding-top: 3.4rem; }}

h1, h2, h3, .ft-title {{ font-family: {FONT_SERIF}; color: {INK}; letter-spacing: -0.005em; }}
.ft-kicker {{ font-family: {FONT_SANS}; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em;
              text-transform: uppercase; color: {CLARET}; margin-bottom: 0.15rem; }}
.ft-title {{ font-size: 2.35rem; font-weight: 600; line-height: 1.12; margin: 0 0 0.35rem; text-wrap: balance; }}
.ft-title-en {{ font-family: {FONT_SERIF}; font-size: 1.35rem; color: {MUTED}; font-weight: 500; margin: 0 0 0.9rem; }}
.ft-standfirst {{ font-size: 1.12rem; line-height: 1.5; color: {INK}; max-width: 72ch; margin: 0 0 0.2rem; }}
.ft-standfirst.en {{ color: {MUTED}; font-size: 1.02rem; }}
.ft-rule {{ border: 0; border-top: 4px solid {INK}; width: 60px; margin: 1.2rem 0 0.8rem; }}

.ft-section {{ font-family: {FONT_SERIF}; font-size: 1.45rem; font-weight: 600; margin: 1.8rem 0 0.1rem;
               padding-top: 0.9rem; border-top: 1px solid {INK}; }}
.ft-section-en {{ font-family: {FONT_SANS}; font-size: 0.98rem; color: {MUTED}; margin: 0 0 0.6rem; }}

.ft-explain {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.4rem 1.6rem;
               font-size: 0.95rem; line-height: 1.5; margin: 0.2rem 0 0.8rem; }}
.ft-explain p {{ margin: 0; }}
.ft-explain .lang {{ font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: {CLARET}; margin-right: 0.35rem; }}
.ft-explain .en {{ color: {MUTED}; }}

.ft-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0 1.4rem; margin: 0.6rem 0 0.4rem; }}
.ft-kpi {{ border-top: 1px solid {INK}; padding-top: 0.45rem; }}
.ft-kpi .v {{ font-family: {FONT_SERIF}; font-size: 2.1rem; font-weight: 600; line-height: 1.1; font-variant-numeric: tabular-nums; }}
.ft-kpi .v small {{ font-size: 1rem; color: {MUTED}; font-weight: 500; }}
.ft-kpi .l {{ font-size: 0.9rem; line-height: 1.35; }}
.ft-kpi .l .en {{ color: {MUTED}; display: block; }}

.ft-source {{ font-size: 0.8rem; color: {MUTED}; margin: -0.3rem 0 1.0rem; line-height: 1.4; }}
.ft-note {{ font-size: 0.85rem; color: {MUTED}; border-left: 3px solid {CLARET}; padding-left: 0.6rem; margin: 0.6rem 0; }}

[data-testid="stMetricValue"] {{ font-family: {FONT_SERIF}; }}
.stTabs [data-baseweb="tab"] {{ font-family: {FONT_SANS}; font-weight: 600; }}
</style>
"""


def setup_page(page_title: str) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    enable_chart_theme()


def header(kicker: str, title_es: str, title_en: str, standfirst_es: str, standfirst_en: str) -> None:
    st.markdown(
        f"""<div class="ft-kicker">{kicker}</div>
<h1 class="ft-title">{title_es}</h1>
<div class="ft-title-en">{title_en}</div>
<p class="ft-standfirst">{standfirst_es}</p>
<p class="ft-standfirst en">{standfirst_en}</p>
<hr class="ft-rule">""",
        unsafe_allow_html=True,
    )


def section(title_es: str, title_en: str) -> None:
    st.markdown(f'<div class="ft-section">{title_es}</div><div class="ft-section-en">{title_en}</div>', unsafe_allow_html=True)


def explain(es: str, en: str) -> None:
    st.markdown(
        f'<div class="ft-explain"><p><span class="lang">ES</span>{es}</p><p class="en"><span class="lang">EN</span>{en}</p></div>',
        unsafe_allow_html=True,
    )


def kpis(items: list[tuple[str, str, str]]) -> None:
    """items: (value_html, label_es, label_en)."""
    cells = "".join(
        f'<div class="ft-kpi"><div class="v">{v}</div><div class="l">{es}<span class="en">{en}</span></div></div>' for v, es, en in items
    )
    st.markdown(f'<div class="ft-kpis">{cells}</div>', unsafe_allow_html=True)


def source(*lines: str) -> None:
    st.markdown('<div class="ft-source">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)


def note(es: str, en: str) -> None:
    st.markdown(f'<div class="ft-note">{es}<br><span style="font-style:italic">{en}</span></div>', unsafe_allow_html=True)


def show_chart(chart) -> None:
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:  # older Streamlit
        st.altair_chart(chart, use_container_width=True)


def show_table(df: pd.DataFrame, int_cols: list | None = None, **kwargs) -> None:
    """Show a table; columns in int_cols get thin-space thousands separators."""
    if int_cols:
        df = df.style.format({col: fmt_int for col in int_cols})
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


# ---------------------------------------------------------------------------
# Altair theme
# ---------------------------------------------------------------------------
def _ft_theme() -> dict:
    return {
        "config": {
            "background": PAPER,
            "font": "Source Sans 3",
            "view": {"stroke": None},
            "padding": {"left": 24, "right": 44, "top": 8, "bottom": 4},
            "title": {"font": "Source Sans 3", "fontSize": 15, "fontWeight": 600, "color": INK, "anchor": "start",
                      "subtitleColor": MUTED, "subtitleFontSize": 13, "offset": 10},
            "axis": {"labelColor": MUTED, "labelFontSize": 12, "titleColor": MUTED, "titleFontSize": 12, "titleFontWeight": 400,
                     "domainColor": INK, "tickColor": INK, "gridColor": GRID, "gridWidth": 1},
            "axisX": {"grid": False, "tickSize": 4, "labelAngle": 0},
            "axisY": {"domain": False, "ticks": False, "labelPadding": 6, "grid": True, "labelLimit": 220},
            "axisBand": {"grid": False},
            "legend": {"orient": "top", "direction": "horizontal", "labelColor": INK, "labelFontSize": 12, "titleColor": MUTED,
                       "titleFontSize": 12, "titleFontWeight": 400, "symbolType": "square", "symbolSize": 120,
                       "labelLimit": 300, "columnPadding": 24, "rowPadding": 6},
            "range": {"category": SERIES, "ramp": SEQUENTIAL, "heatmap": SEQUENTIAL},
            "line": {"strokeWidth": 2.25},
            "bar": {"cornerRadiusEnd": 2},
            "point": {"size": 60, "filled": True},
        }
    }


def enable_chart_theme() -> None:
    try:  # Altair >= 5.5
        alt.theme.register("ft_paper", enable=True)(_ft_theme)
    except AttributeError:  # Altair 5.0 - 5.4
        alt.themes.register("ft_paper", _ft_theme)
        alt.themes.enable("ft_paper")


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
def _backend() -> str:
    return os.environ.get("DW_BACKEND", "snowflake").lower()


@st.cache_data(ttl=3600, show_spinner="Cargando datos / Loading data…")
def load_mart(table: str) -> pd.DataFrame:
    schema = os.environ.get("DW_SCHEMA", "MARTS")
    conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))
    df = conn.query(f"SELECT * FROM ECUADOR_DEATHS_DB.{schema}.{table}")
    df.columns = [c.lower() for c in df.columns]
    return df


def get_mart(table: str) -> pd.DataFrame:
    """Load a mart or stop the page with a clear bilingual error."""
    try:
        return load_mart(table)
    except Exception as exc:  # noqa: BLE001 - shown to the user
        st.error(
            f"No se pudo leer **{table}**. / Could not read **{table}**.\n\n`{exc}`\n\n"
            "Revise la conexión en config.yaml o use DW_BACKEND=duckdb para probar en local. / "
            "Check the connection in config.yaml, or set DW_BACKEND=duckdb to try it locally."
        )
        st.stop()

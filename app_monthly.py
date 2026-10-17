"""Homicidios mes a mes / Homicides month by month  -  reads MARTS.HOMICIDES_MONTHLY.

Run:  streamlit run app_monthly.py
"""
import altair as alt
import pandas as pd
import streamlit as st

import common as c

c.setup_page("Homicidios mes a mes")

df = c.get_mart("HOMICIDES_MONTHLY")
df["month_start_date"] = pd.to_datetime(df["month_start_date"])
df["crime_label"] = df["crime_type"].map(lambda v: c.label(c.CRIME_LABELS, v))
df["weapon_label"] = df["weapon_category"].map(lambda v: c.label(c.WEAPON_LABELS, v))
df["province_name"] = df["province_name"].map(c.place)
df["canton_name"] = df["canton_name"].map(c.place)

last_month = df["month_start_date"].max()
first_year, last_year = int(df["year"].min()), int(df["year"].max())

c.header(
    "Ecuador · Homicidios intencionales",
    "Cómo creció la violencia homicida en Ecuador, mes a mes",
    "How homicidal violence grew in Ecuador, month by month",
    f"Víctimas de homicidio intencional registradas por la Policía (DINASED) desde enero de {first_year} hasta "
    f"{last_month:%m/%Y}. Use los filtros de la izquierda para acotar por territorio, tipo de delito, arma o perfil de la víctima.",
    f"Victims of intentional homicide recorded by the police (DINASED) from January {first_year} to {last_month:%m/%Y}. "
    "Use the filters on the left to narrow down by territory, crime type, weapon or victim profile.",
)

# --------------------------------------------------------------------------- filters
with st.sidebar:
    st.markdown("### Filtros / Filters")
    years = st.slider("Años / Years", first_year, last_year, (first_year, last_year), key="years")
    regions = st.multiselect("Región / Region", sorted(df["natural_region"].dropna().unique()), key="regions")
    prov_options = sorted(df.loc[df["natural_region"].isin(regions) if regions else slice(None), "province_name"].unique())
    provinces = st.multiselect("Provincia / Province", prov_options, key="provinces")
    crimes = st.multiselect("Tipo de delito / Crime type", c.CRIME_ORDER, format_func=lambda v: c.CRIME_LABELS[v], key="crimes")
    weapons = st.multiselect("Arma / Weapon", sorted(df["weapon_category"].unique()), format_func=lambda v: c.label(c.WEAPON_LABELS, v), key="weapons")
    sexes = st.multiselect("Sexo / Sex", sorted(df["sex"].unique()), format_func=lambda v: c.label(c.SEX_LABELS, v), key="sexes")
    stages = st.multiselect("Etapa de vida / Life stage", [s for s in c.LIFE_STAGE_ORDER if s in set(df["life_stage"])],
                            format_func=lambda v: c.LIFE_STAGE_LABELS.get(v, v), key="stages")
    st.caption("Vacío = todos. / Empty = all.")

f = df[df["year"].between(*years)]
for col, chosen in [("natural_region", regions), ("province_name", provinces), ("crime_type", crimes),
                    ("weapon_category", weapons), ("sex", sexes), ("life_stage", stages)]:
    if chosen:
        f = f[f[col].isin(chosen)]

if f.empty:
    st.info("No hay víctimas con esta combinación de filtros. / No victims match these filters.")
    st.stop()

# --------------------------------------------------------------------------- headline numbers
monthly = f.groupby("month_start_date", as_index=False)["victims"].sum()
all_months = pd.date_range(f["month_start_date"].min(), last_month, freq="MS")
monthly = monthly.set_index("month_start_date").reindex(all_months, fill_value=0).rename_axis("month_start_date").reset_index()
monthly["rolling12"] = monthly["victims"].rolling(12, min_periods=12).mean()

last12 = monthly.tail(12)["victims"].sum()
prev12 = monthly.iloc[-24:-12]["victims"].sum() if len(monthly) >= 24 else None
change = (last12 / prev12 - 1) * 100 if prev12 else None
firearm_share = f.loc[f["weapon_category"] == "ARMA DE FUEGO", "victims"].sum() / f["victims"].sum() * 100
peak = monthly.loc[monthly["victims"].idxmax()]

c.kpis([
    (c.fmt_int(f["victims"].sum()), "víctimas en la selección", "victims in the selection"),
    (c.fmt_int(last12) + (f' <small>{change:+.0f}%</small>' if change is not None else ""),
     "en los últimos 12 meses, frente a los 12 anteriores", "in the last 12 months, vs the previous 12"),
    (f"{firearm_share:.0f}%", "murieron por arma de fuego", "were killed with a firearm"),
    (f'{c.fmt_int(peak["victims"])} <small>{peak["month_start_date"]:%m/%Y}</small>', "el peor mes", "the worst month"),
])

# --------------------------------------------------------------------------- 1. monthly trend
c.section("La tendencia", "The trend")
c.explain(
    "La línea fina muestra cada mes; la gruesa es el promedio de los últimos 12 meses, que suaviza la estacionalidad. "
    "Las víctimas se mantuvieron estables hasta 2020 y se multiplicaron a partir de 2021.",
    "The thin line shows each month; the thick line is the 12-month rolling average, which smooths out seasonality. "
    "Victims held steady until 2020 and multiplied from 2021 onwards.",
)
long = monthly.melt("month_start_date", ["victims", "rolling12"], var_name="serie", value_name="value").dropna()
long["serie"] = long["serie"].map({"victims": "Mensual / Monthly", "rolling12": "Promedio 12 meses / 12-month average"})
trend = (
    alt.Chart(long)
    .mark_line()
    .encode(
        x=alt.X("month_start_date:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")),
        y=alt.Y("value:Q", title=None, axis=alt.Axis(orient="right")),
        color=alt.Color("serie:N", title=None, scale=alt.Scale(range=["#B3A496", c.CLARET],
                                                                     domain=["Mensual / Monthly", "Promedio 12 meses / 12-month average"])),
        strokeWidth=alt.StrokeWidth("serie:N", legend=None, scale=alt.Scale(domain=["Mensual / Monthly", "Promedio 12 meses / 12-month average"], range=[1.25, 3])),
        tooltip=[alt.Tooltip("month_start_date:T", title="Mes / Month", format="%m/%Y"),
                 alt.Tooltip("serie:N", title="Serie"), alt.Tooltip("value:Q", title="Víctimas / Victims", format=",.0f")],
    )
    .properties(height=340, title=alt.TitleParams("Víctimas de homicidio intencional por mes", subtitle="Intentional-homicide victims per month · víctimas por mes / victims per month"))
)
c.show_chart(trend.interactive(bind_y=False))
c.source(c.SOURCE_MDI)

# --------------------------------------------------------------------------- 2. by crime type
c.section("Qué tipo de delito", "Which type of crime")
c.explain(
    "El Código Penal (COIP) clasifica cada muerte. <b>Asesinato</b> es un homicidio con agravantes (indefensión, ensañamiento…); "
    "<b>femicidio</b>, el asesinato de una mujer por razones de género; <b>sicariato</b>, el asesinato por encargo y pago. "
    "El asesinato explica casi todo el aumento.",
    "The penal code (COIP) classifies each death. <b>Asesinato</b> is homicide with aggravating circumstances; "
    "<b>femicidio</b> is the killing of a woman because of her gender; <b>sicariato</b> is killing for hire. "
    "Aggravated murder accounts for almost all of the increase.",
)
by_type = f.groupby(["year", "crime_type", "crime_label"], as_index=False)["victims"].sum()
by_type["order"] = by_type["crime_type"].map({k: i for i, k in enumerate(c.CRIME_ORDER)})
crime_domain = [c.CRIME_LABELS[k] for k in c.CRIME_ORDER]
stack = (
    alt.Chart(by_type)
    .mark_bar(stroke=c.PAPER, strokeWidth=1)
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("sum(victims):Q", title=None, axis=alt.Axis(orient="right")),
        color=alt.Color("crime_label:N", title=None, scale=alt.Scale(domain=crime_domain, range=c.SERIES[:4]), legend=alt.Legend(columns=2)),
        order=alt.Order("order:Q", sort="ascending"),
        tooltip=[alt.Tooltip("year:O", title="Año / Year"), alt.Tooltip("crime_label:N", title="Delito / Crime"),
                 alt.Tooltip("sum(victims):Q", title="Víctimas / Victims", format=",.0f")],
    )
    .properties(height=360, title=alt.TitleParams("Víctimas por año y tipo de delito", subtitle="Victims per year by crime type · número de víctimas / number of victims"))
)
c.show_chart(stack)
if last_year in by_type["year"].values and last_month.month < 12:
    c.note(f"{last_year} incluye solo enero–{last_month:%m}. No es comparable con años completos.",
           f"{last_year} covers January–{last_month:%m} only, so it is not comparable with full years.")
c.source(c.SOURCE_MDI)

# --------------------------------------------------------------------------- 3. weapons
c.section("Con qué armas", "With which weapons")
c.explain(
    "Proporción de víctimas según el arma usada. El peso de las armas de fuego creció con la ola de violencia.",
    "Share of victims by the weapon used. Firearms took a growing share as the wave of violence grew.",
)
by_weapon = f.groupby(["year", "weapon_category", "weapon_label"], as_index=False)["victims"].sum()
weapon_order = by_weapon.groupby("weapon_label")["victims"].sum().sort_values(ascending=False).index.tolist()
weapons_chart = (
    alt.Chart(by_weapon)
    .mark_bar(stroke=c.PAPER, strokeWidth=1)
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("sum(victims):Q", stack="normalize", title=None, axis=alt.Axis(format="%", orient="right")),
        color=alt.Color("weapon_label:N", title=None, scale=alt.Scale(domain=weapon_order, range=c.SERIES[: len(weapon_order)]),
                        legend=alt.Legend(columns=3)),
        order=alt.Order("weapon_label:N"),
        tooltip=[alt.Tooltip("year:O", title="Año / Year"), alt.Tooltip("weapon_label:N", title="Arma / Weapon"),
                 alt.Tooltip("sum(victims):Q", title="Víctimas / Victims", format=",.0f")],
    )
    .properties(height=360, title=alt.TitleParams("Víctimas según el arma", subtitle="Victims by weapon · % de víctimas de cada año / % of each year's victims"))
)
c.show_chart(weapons_chart)
c.source(c.SOURCE_MDI)

# --------------------------------------------------------------------------- 4. cantons
c.section("Dónde", "Where")
c.explain(
    "Los 15 cantones con más víctimas en la selección. Son cifras absolutas: los cantones más poblados aparecen arriba. "
    "Para comparar el riesgo entre territorios, vea las tasas por 100.000 habitantes en la app de tasas.",
    "The 15 cantons with the most victims in the selection. These are absolute counts, so the most populous cantons rank high. "
    "To compare risk between places, see the rates per 100,000 people in the rates app.",
)
cant = (f.groupby(["canton_name", "province_name"], as_index=False)["victims"].sum()
          .sort_values("victims", ascending=False).head(15))
cant["place"] = cant["canton_name"] + " (" + cant["province_name"] + ")"
bars = (
    alt.Chart(cant)
    .mark_bar(color=c.OXFORD)
    .encode(
        y=alt.Y("place:N", sort="-x", title=None, scale=alt.Scale(paddingInner=0.3), axis=alt.Axis(labelLimit=240)),
        x=alt.X("victims:Q", title=None, scale=alt.Scale(domain=[0, float(cant["victims"].max()) * 1.12], nice=False),
                axis=alt.Axis(grid=True, orient="top", tickCount=5, format="~s")),
        tooltip=[alt.Tooltip("place:N", title="Cantón / Canton"), alt.Tooltip("victims:Q", title="Víctimas / Victims", format=",.0f")],
    )
)
text = bars.mark_text(align="left", dx=4, color=c.INK, fontSize=12).encode(text=alt.Text("victims:Q", format=",.0f"))
c.show_chart((bars + text).properties(height=alt.Step(24), title=alt.TitleParams("Cantones con más víctimas", subtitle="Cantons with the most victims · número de víctimas / number of victims")))
c.source(c.SOURCE_MDI)

# --------------------------------------------------------------------------- 5. who
c.section("Quiénes son las víctimas", "Who the victims are")
c.explain(
    "Víctimas por sexo y etapa de vida en la selección. La gran mayoría son hombres jóvenes y adultos.",
    "Victims by sex and life stage in the selection. The large majority are young and adult men.",
)
who = f.groupby(["sex", "life_stage"], as_index=False)["victims"].sum()
pivot = (who.pivot(index="life_stage", columns="sex", values="victims").fillna(0).astype(int)
           .reindex([s for s in c.LIFE_STAGE_ORDER if s in set(who["life_stage"])]))
pivot.index = [c.LIFE_STAGE_LABELS.get(i, i) for i in pivot.index]
pivot.columns = [c.label(c.SEX_LABELS, s) for s in pivot.columns]
pivot["Total"] = pivot.sum(axis=1)
c.show_table(pivot.reset_index().rename(columns={"index": "Etapa de vida / Life stage"}), int_cols=list(pivot.columns))
c.source(c.SOURCE_MDI)

with st.expander("Ver datos mensuales / See the monthly data"):
    out = monthly.rename(columns={"month_start_date": "Mes / Month", "victims": "Víctimas / Victims", "rolling12": "Promedio 12m / 12m avg"})
    c.show_table(out, int_cols=["Víctimas / Victims"])

st.markdown(
    '<p class="ft-source">Datos: MARTS.HOMICIDES_MONTHLY. Una fila por víctima en origen; incluye homicidio, asesinato, femicidio y sicariato. '
    "/ Data: MARTS.HOMICIDES_MONTHLY. One row per victim at source; covers homicide, aggravated murder, femicide and contract killing.</p>",
    unsafe_allow_html=True,
)

"""Quién corre más riesgo / Who is most at risk  -  reads MARTS.HOMICIDE_RATES_BY_SEX_AGE.

Run:  streamlit run app_sex_age.py
"""
import altair as alt
import pandas as pd
import streamlit as st

import common as c

c.setup_page("Riesgo por sexo y edad")

df = c.get_mart("HOMICIDE_RATES_BY_SEX_AGE")
df["geo_name"] = df["geo_name"].map(c.place)
df["stage_label"] = df["life_stage"].map(lambda v: c.LIFE_STAGE_LABELS.get(v, v))
df["sex_label"] = df["sex"].map(lambda v: c.label(c.SEX_LABELS, v))
STAGES = [s for s in c.LIFE_STAGE_ORDER if s in set(df["life_stage"])]
STAGE_LABELS = [c.LIFE_STAGE_LABELS[s] for s in STAGES]
SEX_DOMAIN = [c.SEX_LABELS["HOMBRE"], c.SEX_LABELS["MUJER"]]
SEX_RANGE = [c.OXFORD, c.CLARET]

years_all = sorted(df["year"].unique())
latest = int(max(years_all))
months_latest = int(df.loc[df["year"] == latest, "months_covered"].max())
last_full = int(max(df.loc[df["months_covered"] == 12, "year"]))

c.header(
    "Ecuador · Riesgo por sexo y edad",
    "Los hombres jóvenes son las principales víctimas de la violencia homicida",
    "Young men are the main victims of homicidal violence",
    "Tasas de homicidio por cada 100.000 personas del mismo sexo y etapa de vida. Al dividir entre la población de cada grupo se "
    "compara el riesgo real, no solo el número de víctimas.",
    "Homicide rates per 100,000 people of the same sex and life stage. Dividing by each group's population compares actual risk, "
    "not just the number of victims.",
)

# --------------------------------------------------------------------------- controls
g1, g2, g3 = st.columns([2, 2, 2])
with g1:
    geo_options = ["EC"] + sorted(df.loc[df["geo_level"] == "PROVINCIA", "geo_code"].unique(),
                                  key=lambda code: df.loc[df["geo_code"] == code, "geo_name"].iloc[0])
    geo_names = df.drop_duplicates("geo_code").set_index("geo_code")["geo_name"]
    geo = st.selectbox("Territorio / Area", geo_options, format_func=lambda g: "Ecuador (nacional / national)" if g == "EC" else geo_names[g], key="geo")
with g2:
    year = st.select_slider("Año / Year", options=[int(y) for y in years_all], value=last_full, key="year")
with g3:
    annualise = st.toggle(f"Anualizar {latest} / Annualise {latest}", value=True, key="annualise",
                          help=f"{latest} cubre enero–{months_latest:02d}. / {latest} covers January–{months_latest:02d}.")

rate_col = "rate_per_100k_annualised" if annualise else "rate_per_100k"
d = df[df["geo_code"] == geo].copy()
d["rate"] = d[rate_col]
place_es = "Ecuador" if geo == "EC" else geo_names[geo]
yd = d[d["year"] == year]

# --------------------------------------------------------------------------- headline numbers
top = yd.sort_values("rate", ascending=False).iloc[0]
men = yd[yd["sex"] == "HOMBRE"]
women = yd[yd["sex"] == "MUJER"]
men_rate = men["victims"].sum() / men["population"].sum() * 100_000
women_rate = women["victims"].sum() / women["population"].sum() * 100_000
if annualise and year == latest:
    factor = 12 / months_latest
    men_rate, women_rate = men_rate * factor, women_rate * factor
ratio = men_rate / women_rate if women_rate else None
share_young_men = yd.loc[(yd["sex"] == "HOMBRE") & (yd["life_stage"].isin(["JUVENTUD (18-29)", "ADULTEZ (30-64)"])), "victims"].sum() / max(yd["victims"].sum(), 1) * 100

c.kpis([
    (c.fmt_rate(top["rate"]), f"tasa del grupo de mayor riesgo: {top['stage_label'].split(' / ')[0].lower()}, {top['sex_label'].split(' / ')[0].lower()}",
     f"rate for the highest-risk group: {top['stage_label'].split(' / ')[1]}, {top['sex_label'].split(' / ')[1].lower()}"),
    (c.fmt_rate(men_rate), "tasa de los hombres", "rate for men"),
    (c.fmt_rate(women_rate), "tasa de las mujeres", "rate for women"),
    ((f"×{ratio:.0f}" if ratio else "–"), "riesgo de los hombres frente a las mujeres", "men's risk compared with women's"),
])

# --------------------------------------------------------------------------- 1. profile for the year
c.section(f"El perfil del riesgo en {year}", f"The risk profile in {year}")
c.explain(
    f"Tasa por 100.000 personas de cada grupo en {place_es}. Las barras azules son hombres; las granates, mujeres. "
    f"En {year}, el {share_young_men:.0f}% de las víctimas con sexo y edad conocidos fueron hombres de 18 a 64 años.",
    f"Rate per 100,000 people in each group in {place_es}. Blue bars are men; claret bars are women. "
    f"In {year}, {share_young_men:.0f}% of victims with known sex and age were men aged 18 to 64.",
)
bars = alt.Chart(yd).mark_bar(width={"band": 0.42}, stroke=c.PAPER, strokeWidth=1).encode(
    x=alt.X("stage_label:N", sort=STAGE_LABELS, title=None, axis=alt.Axis(labelLimit=200, labelAngle=0,
                                                                         labelExpr="split(datum.label, ' / ')")),
    xOffset=alt.XOffset("sex_label:N", sort=SEX_DOMAIN),
    y=alt.Y("rate:Q", title=None, axis=alt.Axis(orient="right")),
    color=alt.Color("sex_label:N", title=None, scale=alt.Scale(domain=SEX_DOMAIN, range=SEX_RANGE)),
    tooltip=[alt.Tooltip("stage_label:N", title="Etapa / Life stage"), alt.Tooltip("sex_label:N", title="Sexo / Sex"),
             alt.Tooltip("rate:Q", title="Tasa / Rate", format=".1f"), alt.Tooltip("victims:Q", title="Víctimas / Victims", format=",.0f"),
             alt.Tooltip("population:Q", title="Población / Population", format=",.0f")],
)
vals = bars.mark_text(dy=-7, fontSize=11).encode(text=alt.Text("rate:Q", format=".0f"), color=alt.value(c.INK))
c.show_chart((bars + vals).properties(height=360, title=alt.TitleParams(f"Tasa por sexo y etapa de vida, {place_es}, {year}",
                                                                          subtitle=f"Rate by sex and life stage, {year} · por 100.000 personas / per 100,000 people")))
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

# --------------------------------------------------------------------------- 2. trend by life stage
c.section("Cómo cambió con los años", "How it changed over time")
c.explain(
    "Evolución de la tasa de cada etapa de vida, por separado para hombres y mujeres. Las escalas verticales son distintas: "
    "el riesgo de los hombres es muy superior.",
    "The rate for each life stage over time, separately for men and women. The vertical scales differ, because men's risk is far higher.",
)
d_plot = d.assign(partial=d["months_covered"] < 12)


def trend(sex: str, title_es: str, title_en: str):
    sub = d_plot[d_plot["sex"] == sex]
    base = alt.Chart(sub).encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("rate:Q", title=None, axis=alt.Axis(orient="right")),
        color=alt.Color("stage_label:N", title=None, sort=STAGE_LABELS,
                        scale=alt.Scale(domain=STAGE_LABELS, range=c.SERIES[: len(STAGE_LABELS)]),
                        legend=alt.Legend(orient="bottom", columns=2)),
        tooltip=[alt.Tooltip("year:O", title="Año / Year"), alt.Tooltip("stage_label:N", title="Etapa / Life stage"),
                 alt.Tooltip("rate:Q", title="Tasa / Rate", format=".1f"), alt.Tooltip("victims:Q", title="Víctimas / Victims", format=",.0f")],
    )
    full_pts = base.transform_filter("datum.partial == false").mark_point(size=36, filled=True)
    partial_pts = base.transform_filter("datum.partial == true").mark_point(size=48, filled=False, fill=c.PAPER, strokeWidth=2)
    return (base.mark_line() + full_pts + partial_pts).properties(height=420, title=alt.TitleParams(title_es, subtitle=title_en))


t1, t2 = st.columns(2)
with t1:
    c.show_chart(trend("HOMBRE", "Hombres", "Men · por 100.000 hombres / per 100,000 men"))
with t2:
    c.show_chart(trend("MUJER", "Mujeres", "Women · por 100.000 mujeres / per 100,000 women"))
c.note(f"Punto hueco: {latest} incompleto (enero–{months_latest:02d})" + (", anualizado." if annualise else ", sin anualizar."),
       f"Hollow point: {latest} is a partial year (January–{months_latest:02d})" + (", annualised." if annualise else ", not annualised."))
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

# --------------------------------------------------------------------------- 3. heatmap for men
c.section("Dónde se concentra el riesgo", "Where the risk is concentrated")
c.explain(
    "Tasa de los hombres por etapa de vida y año: cuanto más oscura la celda, mayor el riesgo. Muestra cómo el aumento golpeó "
    "sobre todo a los jóvenes de 18 a 29 años.",
    "Men's rate by life stage and year: the darker the cell, the higher the risk. It shows how the rise hit young men aged 18 to 29 hardest.",
)
heat = alt.Chart(d_plot[d_plot["sex"] == "HOMBRE"]).mark_rect(stroke=c.PAPER, strokeWidth=1).encode(
    x=alt.X("year:O", title=None, axis=alt.Axis(orient="top", domain=False, ticks=False)),
    y=alt.Y("stage_label:N", sort=STAGE_LABELS, title=None, axis=alt.Axis(labelExpr="split(datum.label, ' / ')", labelLimit=180)),
    color=alt.Color("rate:Q", title="Por 100.000 / per 100,000", scale=alt.Scale(range=c.SEQUENTIAL),
                    legend=alt.Legend(orient="top", gradientLength=260)),
    tooltip=[alt.Tooltip("stage_label:N", title="Etapa / Life stage"), alt.Tooltip("year:O", title="Año / Year"),
             alt.Tooltip("rate:Q", title="Tasa / Rate", format=".1f")],
)
txt = alt.Chart(d_plot[d_plot["sex"] == "HOMBRE"]).mark_text(fontSize=11).encode(
    x="year:O", y=alt.Y("stage_label:N", sort=STAGE_LABELS), text=alt.Text("rate:Q", format=".0f"),
    color=alt.condition("datum.rate > 100", alt.value(c.PAPER), alt.value(c.INK)),
)
c.show_chart((heat + txt).properties(height=420, title=alt.TitleParams(f"Hombres: tasa por etapa de vida, {place_es}",
                                                                         subtitle="Men: rate by life stage · por 100.000 / per 100,000")))
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

c.note(
    "Este análisis excluye a las víctimas cuyo sexo es «no determinado» o cuya edad se desconoce (alrededor del 2% del total), "
    "porque no pueden asignarse a ningún grupo de población.",
    "This analysis leaves out victims whose sex is recorded as undetermined or whose age is unknown (about 2% of the total), "
    "because they cannot be assigned to a population group.",
)
with st.expander("Ver los datos / See the data"):
    out = d[["year", "sex_label", "stage_label", "victims", "population", "rate"]].rename(columns={
        "year": "Año / Year", "sex_label": "Sexo / Sex", "stage_label": "Etapa / Life stage", "victims": "Víctimas / Victims",
        "population": "Población / Population", "rate": "Tasa / Rate"})
    c.show_table(out.sort_values(["Año / Year", "Sexo / Sex"]), int_cols=["Víctimas / Victims", "Población / Population"])
st.markdown(
    '<p class="ft-source">Datos: MARTS.HOMICIDE_RATES_BY_SEX_AGE. / Data: MARTS.HOMICIDE_RATES_BY_SEX_AGE.</p>',
    unsafe_allow_html=True,
)

"""Tasas de homicidio / Homicide rates  -  reads MARTS.HOMICIDE_RATES_ANNUAL.

Run:  streamlit run app_rates.py
"""
import altair as alt
import pandas as pd
import streamlit as st

import common as c

c.setup_page("Tasas de homicidio")

df = c.get_mart("HOMICIDE_RATES_ANNUAL")
df["geo_name"] = df["geo_name"].map(c.place)
years_all = sorted(df["year"].unique())
latest = int(max(years_all))
months_latest = int(df.loc[df["year"] == latest, "months_covered"].max())
full_years = sorted(df.loc[df["months_covered"] == 12, "year"].unique())
last_full = int(max(full_years))

_all = df[(df["geo_level"] == "NACIONAL") & (df["crime_type"] == "TODOS") & (df["months_covered"] == 12)].set_index("year")["rate_per_100k"]
_low_y, _high_y = int(_all.idxmin()), int(_all.idxmax())
_x = _all.max() / _all.min()
c.header(
    "Ecuador · Tasas por 100.000 habitantes",
    f"La tasa de homicidios de Ecuador se multiplicó por {_x:.0f} entre {_low_y} y {_high_y}",
    f"Ecuador's homicide rate rose {_x:.0f}-fold between {_low_y} and {_high_y}",
    "La tasa de homicidios divide las víctimas de cada año entre la población del territorio y la expresa por cada 100.000 "
    "habitantes. Así se pueden comparar años y territorios de distinto tamaño.",
    "The homicide rate divides each year's victims by the population of the place and expresses it per 100,000 people, "
    "so years and places of different sizes can be compared.",
)

# --------------------------------------------------------------------------- controls
col_a, col_b = st.columns([3, 2])
with col_a:
    crime = st.radio("Tipo de delito / Crime type", ["TODOS"] + c.CRIME_ORDER, format_func=lambda v: c.CRIME_LABELS[v],
                     horizontal=True, key="crime")
with col_b:
    annualise = st.toggle(f"Anualizar {latest} (ene–{months_latest:02d}) / Annualise {latest}", value=True, key="annualise",
                          help="Escala el año incompleto a 12 meses suponiendo el mismo ritmo. / Scales the partial year to 12 months at the same pace.")

per_women = crime == "FEMICIDIO"
rate_col = ("rate_per_100k_women" if per_women else "rate_per_100k") + ("_annualised" if annualise else "")
denom_es = "mujeres" if per_women else "habitantes"
denom_en = "women" if per_women else "people"
d = df[df["crime_type"] == crime].copy()
d["rate"] = d[rate_col]
nat = d[d["geo_level"] == "NACIONAL"].sort_values("year")

if per_women:
    c.note("Para el femicidio la tasa se calcula sobre la población de mujeres, como es la norma internacional.",
           "For femicide the rate is calculated per 100,000 women, as is the international convention.")

# --------------------------------------------------------------------------- headline numbers
def nat_rate(y):
    s = nat.loc[nat["year"] == y, "rate"]
    return float(s.iloc[0]) if len(s) else None

low_year = int(nat.loc[nat["year"].isin(full_years)].sort_values("rate").iloc[0]["year"])
r_last_full, r_low, r_latest = nat_rate(last_full), nat_rate(low_year), nat_rate(latest)
times = r_last_full / r_low if r_low else None
c.kpis([
    (c.fmt_rate(r_last_full), f"víctimas por 100.000 {denom_es} en {last_full}", f"victims per 100,000 {denom_en} in {last_full}"),
    (c.fmt_rate(r_low) + f" <small>{low_year}</small>", "la tasa más baja del periodo", "the lowest rate in the period"),
    ((f"×{times:.1f}" if times else "–"), f"{last_full} frente a {low_year}", f"{last_full} compared with {low_year}"),
    (c.fmt_rate(r_latest) + f" <small>{latest}{'*' if annualise else ''}</small>",
     f"{latest}, enero–{months_latest:02d}" + (" anualizado" if annualise else ""),
     f"{latest}, January–{months_latest:02d}" + (", annualised" if annualise else "")),
])

# --------------------------------------------------------------------------- 1. national trend
c.section("La tasa nacional", "The national rate")
c.explain(
    f"Víctimas por cada 100.000 {denom_es}. La tasa más baja fue {c.fmt_rate(r_low)} en {low_year}; en {last_full} llegó a {c.fmt_rate(r_last_full)}. "
    + f"El punto hueco de {latest} es un año incompleto" + (", anualizado." if annualise else ", sin anualizar."),
    f"Victims per 100,000 {denom_en}. The lowest rate was {c.fmt_rate(r_low)} in {low_year}; in {last_full} it reached {c.fmt_rate(r_last_full)}. "
    + f"The hollow {latest} point is a partial year" + (", annualised." if annualise else ", not annualised."),
)
nat_plot = nat.assign(partial=nat["months_covered"] < 12)
base = alt.Chart(nat_plot).encode(
    x=alt.X("year:O", title=None),
    y=alt.Y("rate:Q", title=None, axis=alt.Axis(orient="right")),
    tooltip=[alt.Tooltip("year:O", title="Año / Year"), alt.Tooltip("rate:Q", title="Tasa / Rate", format=".1f"),
             alt.Tooltip("victims:Q", title="Víctimas / Victims", format=",.0f"),
             alt.Tooltip("population:Q", title="Población / Population", format=",.0f")],
)
line_full = base.transform_filter("datum.partial == false").mark_line(color=c.CLARET)
line_partial = base.transform_filter(f"datum.year >= {last_full}").mark_line(color=c.CLARET, strokeDash=[4, 3])
pts = base.transform_filter("datum.partial == false").mark_point(size=70, color=c.CLARET, filled=True) \
    + base.transform_filter("datum.partial == true").mark_point(size=80, color=c.CLARET, filled=False, fill=c.PAPER, strokeWidth=2)
labels = base.transform_filter(f"datum.year == {last_full} || datum.year == {latest} || datum.year == {low_year}") \
    .mark_text(dy=-12, color=c.INK, fontSize=12, fontWeight=600).encode(text=alt.Text("rate:Q", format=".1f"))
c.show_chart((line_full + line_partial + pts + labels).properties(
    height=340, title=alt.TitleParams(
        ("Tasa de homicidios intencionales" if crime == "TODOS" else f"Tasa de {c.CRIME_LABELS[crime].split(' / ')[0].lower()}") + f" por 100.000 {denom_es}",
        subtitle=("Intentional-homicide" if crime == "TODOS" else c.CRIME_LABELS[crime].split(' / ')[1]) + f" rate per 100,000 {denom_en}")))
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

# --------------------------------------------------------------------------- 2. province ranking
c.section("Las provincias", "The provinces")
c.explain(
    "Tasa de cada provincia en el año elegido; la línea vertical marca la tasa nacional. "
    "En los últimos años las provincias de la Costa concentran las tasas más altas.",
    "Each province's rate in the chosen year; the vertical line marks the national rate. "
    "In recent years the coastal provinces have had the highest rates.",
)
year = st.select_slider("Año / Year", options=[int(y) for y in years_all], value=last_full, key="prov_year")
prov = d[(d["geo_level"] == "PROVINCIA") & (d["year"] == year)].dropna(subset=["rate"]).sort_values("rate", ascending=False)
nat_y = nat_rate(year)
bars = alt.Chart(prov).mark_bar(color=c.OXFORD).encode(
    y=alt.Y("geo_name:N", sort="-x", title=None, scale=alt.Scale(paddingInner=0.3), axis=alt.Axis(labelLimit=220)),
    x=alt.X("rate:Q", title=None, scale=alt.Scale(domain=[0, float(prov["rate"].max()) * 1.1], nice=False), axis=alt.Axis(grid=True, orient="top", tickCount=6)),
    tooltip=[alt.Tooltip("geo_name:N", title="Provincia / Province"), alt.Tooltip("rate:Q", title="Tasa / Rate", format=".1f"),
             alt.Tooltip("victims:Q", title="Víctimas / Victims", format=",.0f"),
             alt.Tooltip("population:Q", title="Población / Population", format=",.0f")],
)
vals = bars.mark_text(align="left", dx=4, color=c.INK, fontSize=11).encode(text=alt.Text("rate:Q", format=".1f"))
layers = bars + vals
if nat_y is not None:
    rule = alt.Chart(pd.DataFrame({"x": [nat_y], "t": [f"Ecuador {nat_y:.1f}"]}))
    layers = layers + rule.mark_rule(color=c.CLARET, strokeWidth=2).encode(x="x:Q") \
        + rule.mark_text(align="left", dx=4, dy=-8, color=c.CLARET, fontWeight=600, fontSize=12).encode(x="x:Q", y=alt.value(0), text="t:N")
c.show_chart(layers.properties(height=alt.Step(22),
                               title=alt.TitleParams(f"Tasa por provincia, {year}",
                                                     subtitle=f"Rate by province, {year} · por 100.000 {denom_es} / per 100,000 {denom_en}")))
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

# --------------------------------------------------------------------------- 3. heatmap
c.section("Cómo se extendió la violencia", "How the violence spread")
c.explain(
    "Cada celda es la tasa de una provincia en un año: cuanto más oscura, más alta. Permite ver cuándo y dónde empezó el aumento "
    "y cómo se fue extendiendo.",
    "Each cell is one province's rate in one year: the darker, the higher. It shows when and where the rise began and how it spread.",
)
heat = d[d["geo_level"] == "PROVINCIA"].dropna(subset=["rate"])
order = heat[heat["year"] == last_full].sort_values("rate", ascending=False)["geo_name"].tolist()
heatmap = alt.Chart(heat).mark_rect(stroke=c.PAPER, strokeWidth=1).encode(
    x=alt.X("year:O", title=None, axis=alt.Axis(orient="top", domain=False, ticks=False)),
    y=alt.Y("geo_name:N", sort=order, title=None, axis=alt.Axis(labelLimit=240)),
    color=alt.Color("rate:Q", title=f"Por 100.000 / per 100,000",
                    scale=alt.Scale(range=c.SEQUENTIAL, type="sqrt"), legend=alt.Legend(orient="top", gradientLength=260)),
    tooltip=[alt.Tooltip("geo_name:N", title="Provincia / Province"), alt.Tooltip("year:O", title="Año / Year"),
             alt.Tooltip("rate:Q", title="Tasa / Rate", format=".1f"), alt.Tooltip("victims:Q", title="Víctimas / Victims", format=",.0f")],
)
c.show_chart(heatmap.properties(height=alt.Step(22),
                                title=alt.TitleParams("Tasa por provincia y año", subtitle=f"Rate by province and year · ordenado por / sorted by {last_full}")))
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

# --------------------------------------------------------------------------- 4. cantons
c.section("Los cantones", "The cantons")
c.explain(
    "En cantones pequeños unas pocas muertes cambian mucho la tasa, por eso puede fijar una población mínima. "
    "Ordenado de mayor a menor tasa.",
    "In small cantons a handful of deaths swings the rate a lot, so you can set a minimum population. Sorted from highest rate down.",
)
cc1, cc2 = st.columns([1, 1])
with cc1:
    c_year = st.selectbox("Año / Year", [int(y) for y in reversed(years_all)], index=list(reversed(years_all)).index(last_full), key="cant_year")
with cc2:
    min_pop = st.select_slider("Población mínima / Minimum population", options=[0, 10_000, 25_000, 50_000, 100_000, 250_000],
                               value=50_000, format_func=c.fmt_int, key="min_pop")
cant = d[(d["geo_level"] == "CANTON") & (d["year"] == c_year)].dropna(subset=["rate"])
pop_col = "population_women" if per_women else "population"
cant = cant[cant[pop_col] >= min_pop].sort_values("rate", ascending=False)
province_of = df[df["geo_level"] == "PROVINCIA"][["geo_code", "geo_name"]].drop_duplicates().set_index("geo_code")["geo_name"]
cant["Provincia / Province"] = cant["geo_code"].str[:2].map(province_of)
table = cant.rename(columns={"geo_name": "Cantón / Canton", "rate": f"Tasa / Rate (×100k {denom_en})",
                             "victims": "Víctimas / Victims", pop_col: "Población / Population"})[
    ["Cantón / Canton", "Provincia / Province", f"Tasa / Rate (×100k {denom_en})", "Víctimas / Victims", "Población / Population"]]
rate_name = f"Tasa / Rate (×100k {denom_en})"
c.show_table(
    table,
    height=420,
    column_config={
        rate_name: st.column_config.ProgressColumn(rate_name, format="%.1f", min_value=0,
                                                   max_value=float(table[rate_name].max() or 1)),
        "Víctimas / Victims": st.column_config.NumberColumn(format="%d"),
        "Población / Population": st.column_config.NumberColumn(format="%d"),
    },
)
c.source(c.SOURCE_MDI, c.SOURCE_INEC)

st.markdown(
    '<p class="ft-source">Datos: MARTS.HOMICIDE_RATES_ANNUAL. Población a 30 de junio de cada año. '
    "/ Data: MARTS.HOMICIDE_RATES_ANNUAL. Population at 30 June of each year.</p>",
    unsafe_allow_html=True,
)

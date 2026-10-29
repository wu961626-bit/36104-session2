"""Gold stock-transfer monitor — desktop build.

Run:  python ingest.py --synthetic   (once, or --all for live data)
      streamlit run app.py

Design contract (reasoning in the companion notebook):
  - solid = reported, dashed = estimated; one colour per country everywhere
  - the same event rules on every time axis; labels only on the dominant charts
  - one bordered region (the KPI strip); whitespace does all other grouping
  - one dominant chart per tab: P1 carries Declared, P4 carries Inferred
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

import design as dz

DATA = Path(__file__).parent / "data"

st.set_page_config(page_title="Gold stock-transfer monitor",
                   layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- chrome/css --
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400;1,6..72,500&family=Archivo:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, p, li {
  font-family: 'Archivo', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}
.stApp { background: #fbfbf8; color: #1c1c18; }
.block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 3rem; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

h1 { font-family: 'Newsreader', serif; font-weight: 500; letter-spacing: -.01em;
     font-size: 2.5rem; margin-bottom: 0; }
h3 { font-family: 'Newsreader', serif; font-style: italic; font-weight: 500;
     font-size: 1.35rem; margin-bottom: 0; }
.stCaption, [data-testid="stCaptionContainer"] { color: #8c8c84; }

/* tabs: underline grammar, gold for the active page */
.stTabs [data-baseweb="tab-list"] { gap: 30px; border-bottom: 1px solid #ecece5; }
.stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 500; color: #8c8c84;
  padding: 6px 0 10px; background: none; }
.stTabs [aria-selected="true"] { color: #1c1c18; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #a3780a; height: 2px; }
.stTabs [data-baseweb="tab-border"] { background-color: transparent; }

/* KPI strip: the only bordered region on the page */
.kpis { border: 1.5px solid #1c1c18; border-radius: 3px;
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 0 26px;
  padding: 14px 18px 10px; margin: 6px 0 4px; }
.kpi .l { font-size: 11px; color: #8c8c84; line-height: 1.25; }
.kpi .v { font-size: 20px; font-weight: 600; margin-top: 1px; }
.kpi .v small { font-size: 11.5px; font-weight: 500; color: #8c8c84; margin-left: 4px; }
.kpi svg { display: block; margin-top: 4px; }

.grammar { font-size: 12.5px; color: #8c8c84; margin: 2px 0 10px; }
.grammar b { color: #1c1c18; font-weight: 500; }
.masthead { display: flex; justify-content: space-between; align-items: baseline; }
.masthead .d { color: #8c8c84; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------- plotly theme --
pio.templates["ledger"] = go.layout.Template(layout=dict(
    paper_bgcolor=dz.PAPER, plot_bgcolor=dz.PAPER,
    font=dict(family="Archivo, system-ui, sans-serif", color=dz.INK, size=13),
    margin=dict(l=10, r=64, t=34, b=10), showlegend=False,
    xaxis=dict(showgrid=False, ticks="outside", tickcolor=dz.GHOST,
               linecolor=dz.GHOST),
    yaxis=dict(gridcolor="#efefe8", zeroline=False, side="right",
               tickformat=","),
    hoverlabel=dict(bgcolor=dz.PAPER, bordercolor=dz.GHOST,
                    font=dict(family="Archivo, system-ui, sans-serif",
                              color=dz.INK, size=12)),
))
pio.templates.default = "ledger"

# ------------------------------------------------------------------ loading --
@st.cache_data(ttl=3600)
def load(name: str, dates=("date",)) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv", parse_dates=list(dates))

try:
    price = load("price")
    etf = load("etf")
    declared = load("declared")
    gap = load("gap", dates=("quarter_end",))
    swiss = load("swiss")
except FileNotFoundError:
    st.error("No data found. Run `python ingest.py --synthetic` first.")
    st.stop()

asof = {"price": price.date.max(), "etf": etf.date.max(),
        "declared": declared.date.max(), "gap": gap.quarter_end.max(),
        "swiss": swiss.date.max()}
fmt = lambda t: pd.Timestamp(t).strftime("%b %y")

# --------------------------------------------------------------- helpers -----
def events(fig, label: bool):
    for i, (d, t) in enumerate(dz.EVENTS):
        fig.add_vline(x=d, line_color=dz.GHOST, line_width=1)
        if label:
            fig.add_annotation(x=d, y=1.03 + 0.075 * (i % 2), yref="paper",
                               text=t, showarrow=False,
                               font=dict(size=11, color=dz.FAINT))

def endlabel(fig, x, y, text, color=dz.FAINT):
    fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left",
                       xshift=8, font=dict(size=12, color=color))

def chart(fig, h):
    fig.update_layout(height=h)
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})

def spark(vals, color, w=76, h=20):
    lo, hi = min(vals), max(vals) + 1e-9
    pts = " ".join(f"{2 + (w-4)*i/(len(vals)-1):.1f},"
                   f"{h-2 - (h-4)*(v-lo)/(hi-lo):.1f}" for i, v in enumerate(vals))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="1.6" stroke-linejoin="round"/></svg>')

# ------------------------------------------------------------- derived nums --
t12 = (declared[declared.date > asof["declared"] - pd.DateOffset(months=12)]
       .groupby("country").net_purchases_t.sum().sort_values(ascending=False))
top_buy, top_sell = t12.index[0], t12.index[-1]
east_m = (swiss[swiss.destination.isin(["China + HK", "India", "Turkey"])]
          .groupby("date").tonnes.sum())
all_last = swiss[swiss.date == asof["swiss"]].tonnes.sum()
gap_res = (gap.wgc_estimate_t - gap.imf_reported_t)
p_now, p_prev = price.price_usd_oz.iloc[-1], price.price_usd_oz.iloc[-2]
e_now, e_prev = etf.tonnes.iloc[-1], etf.tonnes.iloc[-2]
china12 = declared[declared.country == top_buy].net_purchases_t.tail(12)
russia12 = declared[declared.country == top_sell].net_purchases_t.tail(12)

# ----------------------------------------------------------------- masthead --
st.markdown(f"""
<div class="masthead"><h1>Gold stock-transfer monitor</h1>
<span class="d">{pd.Timestamp(asof['price']).strftime('%A %d %B %Y')}</span></div>
""", unsafe_allow_html=True)
st.caption("Who holds the stock, and which way it is moving.")
st.warning("PRACTICE DATA: all values are synthetic course data, not current market observations.")

KPIS = [
    ("price, $/oz", f"{p_now:,.0f}", f"{p_now/p_prev-1:+.1%} m/m",
     spark(price.price_usd_oz.tail(12).tolist(), dz.GOLD)),
    ("GLD + IAU", f"{e_now:,.0f} t", f"{e_now-e_prev:+.0f} t m/m",
     spark(etf.tonnes.tail(12).tolist(), dz.hue("West"))),
    ("gap, latest qtr", f"+{gap_res.iloc[-1]:,.0f} t", "unreported",
     spark(gap_res.tail(8).tolist(), dz.GOLD)),
    ("top buyer, 12m", top_buy, f"+{t12.iloc[0]:,.0f} t",
     spark(china12.tolist(), dz.hue(top_buy))),
    ("top seller, 12m", top_sell, f"{t12.iloc[-1]:,.0f} t",
     spark(russia12.tolist(), dz.hue(top_sell))),
    (f"Swiss → east, {fmt(asof['swiss'])}", f"{east_m.iloc[-1]:,.0f} t",
     f"of {all_last:,.0f} t out",
     spark(east_m.tail(12).tolist(), dz.hue("China"))),
]
tiles = "".join(f'<div class="kpi"><div class="l">{l}</div>'
                f'<div class="v">{v}<small>{s}</small></div>{sp}</div>'
                for l, v, s, sp in KPIS)
st.markdown(f'<div class="kpis">{tiles}</div>', unsafe_allow_html=True)
st.markdown('<p class="grammar"><b>Solid</b> marks reported series, '
            '<b>dashed</b> marks estimates. Each country keeps one colour on '
            'every panel.</p>', unsafe_allow_html=True)

tabD, tabI = st.tabs(["Declared", "Inferred"])

# ============================================================== DECLARED =====
with tabD:
    st.subheader("Price and its opportunity cost")
    st.caption(f"Has the price detached from real yields, and by how much? — "
               f"as of {fmt(asof['price'])}")
    f = go.Figure()
    f.add_trace(go.Scatter(x=price.date, y=price.yield_implied_usd_oz,
        name="yield-implied", mode="lines",
        line=dict(color=dz.INK, width=1.3, dash=dz.DASH)))
    f.add_trace(go.Scatter(x=price.date, y=price.price_usd_oz, name="price",
        mode="lines", line=dict(color=dz.GOLD, width=2.6),
        fill="tonexty", fillcolor="rgba(163,120,10,.13)"))
    events(f, label=True)
    endlabel(f, price.date.iloc[-1], p_now, f"<b>{p_now:,.0f}</b> $/oz", dz.GOLD)
    endlabel(f, price.date.iloc[-1], price.yield_implied_usd_oz.iloc[-1], "implied")
    f.update_layout(hovermode="x unified")
    chart(f, 430)
    st.caption("Shaded wedge: actual price over the pre-2022 yield-implied "
               "level — the premium a yield-indifferent buyer pays.")

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Western investor holdings")
        st.caption(f"Is the yield-sensitive holder buying this move or "
                   f"selling into it? — as of {fmt(asof['etf'])}")
        f = go.Figure(go.Scatter(x=etf.date, y=etf.tonnes, mode="lines",
            line=dict(color=dz.hue("West"), width=2.4)))
        events(f, label=False)
        endlabel(f, etf.date.iloc[-1], e_now, f"<b>{e_now:,.0f}</b> t",
                 dz.hue("West"))
        chart(f, 330)
    with right:
        st.subheader("Declared official sector")
        st.caption(f"Trailing 12-month reported change — IMF, "
                   f"{fmt(asof['declared'])}")
        s = t12.sort_values()
        f = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h",
            marker_color=[dz.hue(c) for c in s.index],
            text=[f"{v:+,.0f}" for v in s.values], textposition="outside",
            textfont=dict(size=11, color=dz.FAINT), cliponaxis=False))
        f.update_xaxes(title="tonnes", showgrid=False)
        f.update_yaxes(side="left", gridcolor=dz.PAPER)
        chart(f, 330)

    with st.expander("12-month detail per bank"):
        d12 = declared[declared.date > asof["declared"] -
                       pd.DateOffset(months=12)].copy()
        order = t12.index.tolist()
        fig = px.bar(d12, x="date", y="net_purchases_t", facet_col="country",
                     facet_col_wrap=5, category_orders={"country": order},
                     color="country",
                     color_discrete_map={c: dz.hue(c) for c in order},
                     facet_row_spacing=.10, facet_col_spacing=.03)
        fig.update_yaxes(matches=None, title=None, side="left")
        fig.update_xaxes(title=None, showticklabels=False)
        fig.for_each_annotation(lambda a:
            a.update(text=a.text.split("=")[-1], font=dict(size=12)))
        chart(fig, 520)

# ============================================================== INFERRED =====
with tabI:
    st.subheader("The gap")
    st.caption(f"How much official buying goes unreported each quarter? — "
               f"{gap.quarter_end.iloc[-1].to_period('Q')}")
    f = go.Figure()
    f.add_trace(go.Scatter(x=gap.quarter_end, y=gap.imf_reported_t,
        mode="lines", line=dict(width=0), hoverinfo="skip"))
    f.add_trace(go.Scatter(x=gap.quarter_end, y=gap.wgc_estimate_t,
        name="WGC estimate", mode="lines",
        line=dict(color=dz.INK, width=1.6, dash=dz.DASH),
        fill="tonexty", fillcolor="rgba(163,120,10,.16)"))
    f.add_trace(go.Bar(x=gap.quarter_end, y=gap.imf_reported_t,
        name="reported to IMF", marker_color=dz.INK, opacity=.85))
    events(f, label=True)
    endlabel(f, gap.quarter_end.iloc[-1], gap.wgc_estimate_t.iloc[-1],
             f"WGC <b>{gap.wgc_estimate_t.iloc[-1]:,.0f}</b> t")
    endlabel(f, gap.quarter_end.iloc[-1], gap.imf_reported_t.iloc[-1],
             f"IMF <b>{gap.imf_reported_t.iloc[-1]:,.0f}</b> t")
    f.update_yaxes(title="tonnes / quarter")
    chart(f, 430)
    st.caption("Bars: purchases reported to the IMF. Dashed: World Gold "
               "Council estimate of actual official demand. Shaded: the "
               "unreported residual.")

    st.subheader("Physical flow west to east")
    st.caption(f"Where are the bars going, and is the float being "
               f"replenished? — Swiss customs, {fmt(asof['swiss'])}")
    f = go.Figure()
    for dest in ["other", "UAE + Gulf", "UK + US", "Turkey", "India",
                 "China + HK"]:
        d = swiss[swiss.destination == dest]
        f.add_trace(go.Scatter(x=d.date, y=d.tonnes, name=dest,
            stackgroup="flow", mode="none", fillcolor=dz.hue(dest),
            hovertemplate=f"{dest}: %{{y:.0f}} t<extra></extra>"))
    events(f, label=False)
    show_repl = st.toggle("show mine replenishment")
    if show_repl:
        f.add_hline(y=dz.MINE_TOTAL_TPM,
            line=dict(color=dz.INK, width=1.2, dash="dash"),
            annotation_text="all mine supply ≈ 300 t/mo",
            annotation_position="top left")
        f.add_hline(y=dz.MINE_WESTERN_TPM,
            line=dict(color=dz.INK, width=1.2, dash="dot"),
            annotation_text="enters Western circuit ≈ 200 t/mo",
            annotation_position="bottom left")
    f.update_yaxes(title="tonnes / month", range=[0, 330])
    f.update_layout(showlegend=True, legend=dict(orientation="h", y=1.06,
        x=0, font=dict(size=12)), hovermode="x unified")
    chart(f, 400)
    if show_repl:
        st.caption("Output above the lower line drains the Western float "
                   "faster than the ground refills it. The space between the "
                   "lines is mine supply born outside the circuit (China, "
                   "Russia, Uzbekistan, Kazakhstan).")

st.caption("Sources when live: COMEX front-month futures (GC=F), FRED DFII10, "
           "GLD and IAU daily bar lists, IMF International Financial "
           "Statistics, World Gold Council Gold Demand Trends, Swiss-Impex "
           "tariff heading 7108. Event rules: Feb 22 reserve freeze, Jun 22 "
           "G7 import ban, Jun 25 Iran war, Nov 25 CBR sales begin, May 26 "
           "escalation.")


with tabD:
    st.subheader("Compare buying and selling over the same months")
    st.caption("Question: which countries bought or sold most, and when did that activity happen? All values are synthetic course data.")
    available_dates = sorted(declared.date.unique())
    start, end = st.select_slider("Comparison period", options=available_dates,
        value=(available_dates[max(0,len(available_dates)-12)], available_dates[-1]),
        format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"))
    countries = st.multiselect("Countries to compare", sorted(declared.country.unique()),
        default=[c for c in ["China", "Russia"] if c in declared.country.unique()])
    period = declared[declared.date.between(start,end)]
    if not countries:
        st.info("Choose at least one country to display its monthly activity.")
    else:
        selected = period[period.country.isin(countries)]
        totals = period.groupby("country").net_purchases_t.sum().sort_values()
        ranking = px.bar(x=totals.values,y=totals.index,orientation="h",
            labels={"x":"Net purchases (tonnes)","y":"Country"},
            title="All countries: net purchases in the selected period (sample data)")
        ranking.update_traces(marker_color=[dz.hue(c) for c in totals.index])
        ranking.update_yaxes(side="left")
        ranking.add_vline(x=0,line_color="#555555")
        st.plotly_chart(ranking,use_container_width=True)
        monthly = px.bar(selected,x="date",y="net_purchases_t",color="country",
            barmode="group",color_discrete_map={c:dz.hue(c) for c in countries},
            labels={"date":"Month","net_purchases_t":"Net purchases (tonnes)","country":"Country"},
            title="Selected countries: monthly buying and selling (sample data)")
        monthly.update_layout(showlegend=True,hovermode="x unified")
        monthly.add_hline(y=0,line_color="#555555")
        st.plotly_chart(monthly,use_container_width=True)
        st.caption(f"Both charts use {pd.Timestamp(start):%b %Y} to {pd.Timestamp(end):%b %Y}. Positive = net buying; negative = net selling. Missing observations are not replaced with zero.")
        st.download_button("Download selected observations",selected.to_csv(index=False),
            "gold_selected_sample_data.csv","text/csv")

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta
import json, openai    # pip install openai  (only needed if you use narrative)
import numpy as np
import os

openai.api_key = os.getenv("OPENAI_API_KEY") 

# -----------------------------------------------------------------
# 1. Metric engine (same pure functions we wrote earlier)
# -----------------------------------------------------------------
def totals(df):
    dep = df[df.amount > 0]
    wd  = df[df.amount < 0]
    return {
        "deposits":     {"count": len(dep), "value": dep.amount.sum()},
        "withdrawals":  {"count": len(wd),  "value": abs(wd.amount.sum())},
    }

def hourly(df):
    return (
        df.assign(hour=df.tx_datetime.dt.hour)
          .groupby("hour")["amount"].size()
          .reindex(range(24), fill_value=0)
    )

def dom_intl(df, home="ZA"):
    g = df.assign(dom=df.counterparty_country_code.eq(home)) \
          .groupby("dom")["amount"].agg(["count","sum"])
    def row(flag): 
        if flag in g.index: return dict(count=int(g.loc[flag,"count"]),
                                        value=float(abs(g.loc[flag,"sum"])))
        else:               return dict(count=0,value=0.0)
    return {"domestic": row(True), "international": row(False)}

def extremes(df):
    dep = df[df.amount > 0].nlargest(1,"amount")
    wd  = df[df.amount < 0].nsmallest(1,"amount")
    return {"largest_deposit": dep, "largest_withdrawal": wd}

def channel_mix(df):
    return (df.groupby("channel")["amount"]
              .agg(count="size",value="sum")
              .abs()
              .sort_values("value",ascending=False)
              .reset_index())

# -----------------------------------------------------------------
# 2. Spotlight rules (deterministic)
# -----------------------------------------------------------------
def spotlights(df_win, df_hist):
    out = {}
    # hourly burst
    win_max = df_win.tx_datetime.dt.hour.value_counts().max()
    hist_start = df_win.tx_datetime.max() - timedelta(days=90)
    hist_med = df_hist[df_hist.tx_datetime>=hist_start] \
                  .tx_datetime.dt.hour.value_counts().median()
    out["burst"] = {"flag": win_max / max(hist_med,1) > 3,
                    "score": win_max / max(hist_med,1)}
    # imbalance
    dep = df_win[df_win.amount>0].amount.sum()
    wd  = abs(df_win[df_win.amount<0].amount.sum())
    out["imbalance"] = {"flag": wd/dep > 1.2 if dep else True,
                        "ratio": wd/dep if dep else float("inf")}
    return out

# -----------------------------------------------------------------
# 3. (Optional) LLM narrative writer
# -----------------------------------------------------------------
def narrative(metrics, spots):
    json_payload = json.dumps(
        {"metrics": metrics, "spotlights": spots},
        default=to_builtin,          # <-- new
        indent=2
    )
    
    prompt = f"""You are an AML analyst. Using the JSON below, write
    a 4-bullet executive summary (≤120 words) highlighting anomalies.
    JSON:
    {json.dumps({"metrics":metrics,"spotlights":spots}, indent=2)}"""
    chat = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,max_tokens=200)
    return chat.choices[0].message.content.strip()


def to_builtin(obj):
    """Convert NumPy scalars (int64, float64, bool_) to builtin Python types."""
    if isinstance(obj, (np.generic,)):        # covers all NumPy scalar subclasses
        return obj.item()
    raise TypeError                          # let json.dumps handle other cases


# -----------------------------------------------------------------
# 4. Streamlit UI
# -----------------------------------------------------------------
st.set_page_config(page_title="AML QuickLook", layout="wide")
st.title("AML QuickLook Dashboard")

uploaded = st.sidebar.file_uploader("Upload CSV", type="csv")
if not uploaded:
    st.info("👈 Drop the synthetic CSV to begin")
    st.stop()

df = pd.read_csv(uploaded, parse_dates=["tx_datetime"])
df.sort_values("tx_datetime", inplace=True)

# sidebar window picker
win = st.sidebar.date_input(
    "Date window",
    (df.tx_datetime.min().date(), df.tx_datetime.max().date()),
    format="YYYY-MM-DD")
start, end = pd.to_datetime(win[0]), pd.to_datetime(win[1]) + timedelta(days=1) - timedelta(seconds=1)
dfw = df[(df.tx_datetime>=start) & (df.tx_datetime<=end)]

# KPIs
kpi = totals(dfw); dom = dom_intl(dfw)
row = st.columns(4)
row[0].metric("Deposits (ZAR)", f"R{kpi['deposits']['value']:,.0f}", f"{kpi['deposits']['count']} tx")
row[1].metric("Withdrawals (ZAR)", f"R{kpi['withdrawals']['value']:,.0f}",
                                   f"{kpi['withdrawals']['count']} tx")
row[2].metric("Domestic tx", dom['domestic']['count'],
                              f"R{dom['domestic']['value']:,.0f}")
row[3].metric("International tx", dom['international']['count'],
                                   f"R{dom['international']['value']:,.0f}")

# Spotlights (simple pills)
spots = spotlights(dfw, df)
pill = lambda flag: ("✅ OK","🟡 Check","🔴 Alert")[1 if flag else 0] if isinstance(flag,bool) else flag
st.write(f"**Burst flag**: {pill(spots['burst']['flag'])} &nbsp;&nbsp; "
         f"**Imbalance flag**: {pill(spots['imbalance']['flag'])}")

# Charts
h = hourly(dfw)
st.plotly_chart(px.bar(x=h.index,y=h.values,labels={"x":"Hour","y":"Tx count"},
                       title="Transactions per Hour"), use_container_width=True)

dom_df = pd.DataFrame([
    {"group":"Domestic","value":dom['domestic']['value']},
    {"group":"International","value":dom['international']['value']}])
st.plotly_chart(px.pie(dom_df, names="group", values="value",
                       title="Domestic vs International (value)"), use_container_width=True)

st.plotly_chart(px.bar(channel_mix(dfw),
                       x="channel", y="value", text="count",
                       title="Channel mix (value)"),
                use_container_width=True)

# Extremes table
st.subheader("Largest single deposit & withdrawal")
ex = extremes(dfw)
st.dataframe(pd.concat([ex['largest_deposit'], ex['largest_withdrawal']])
               .reset_index(drop=True))

# Optional narrative
if openai.api_key and st.checkbox("Generate analyst note"):
    note = narrative({"totals":kpi,"domestic_split":dom}, spots)
    st.info(note)

st.caption("Powered by Streamlit • Data stays in-memory; nothing uploaded elsewhere.")

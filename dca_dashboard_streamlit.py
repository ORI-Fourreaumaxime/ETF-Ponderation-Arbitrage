# -*- coding: utf-8 -*-
"""
Dashboard DCA ETF avec allocation DCA pour 50% d'actions,
utilisant un shift automatique pour sous-pondérer les scores négatifs,
et affichant pour chaque indice sa carte complète (graphique, badges, allocation et points).
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred
from typing import Tuple

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Dashboard DCA ETF", layout="wide", initial_sidebar_state="expanded")

# --- CONSTANTES ---
etfs = {
    'S&P500': 'SPY',
    'NASDAQ100': 'QQQ',
    'CAC40': '^FCHI',
    'EURO STOXX50': 'FEZ',
    'EURO STOXX600 TECH': 'EXV3.DE',
    'NIKKEI 225': '^N225',
    'WORLD': 'VT',
    'EMERGING': 'EEM'
}
timeframes = {
    'Hebdo': 7,
    'Mensuel': 30,
    'Trimestriel': 90,
    'Annuel': 365,
    '5 ans': 365 * 5
}
macro_series = {
    'CAPE10': 'CAPE',
    'Fed Funds Rate': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'
}

# --- FONCTIONS UTILES ---
def pct_change(s: pd.Series) -> float:
    return float((s.iloc[-1] / s.iloc[-2] - 1) * 100) if len(s) > 1 else 0.0

def score_and_style(diff: float, threshold_pct: float) -> Tuple[float, str, str]:
    t = threshold_pct / 100.0
    if diff <= -t:
        return 1.0,  '↑', 'green'
    elif diff <= 0:
        return 0.5, '↗', '#c8e6c9'
    elif diff < t:
        return -0.5,'↘','orange'
    else:
        return -1.0,'↓','crimson'

# --- SIDEBAR ---
st.sidebar.header("Paramètres de stratégie DCA")
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
threshold_pct = st.sidebar.slider("Seuil déviation (%)", 1, 20, 10, 1)
debug = st.sidebar.checkbox("Afficher debug")
use_container_cards = st.sidebar.checkbox(
    "Version st.container/st.metric", value=False
)

# --- DONNÉES ---
@st.cache_data
def load_prices() -> pd.DataFrame:
    end = datetime.today()
    max_w = max(timeframes.values())
    trading_days = 252
    est_days = int(max_w / trading_days * 365 * 1.1)
    start = end - timedelta(days=est_days)
    df = pd.DataFrame()
    for name, ticker in etfs.items():
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            df[name] = data.get('Adj Close', data.get('Close', pd.Series(dtype=float)))
        except:
            df[name] = pd.Series(dtype=float)
    return df

@st.cache_data
def load_macro() -> pd.DataFrame:
    api_key = st.secrets.get('FRED_API_KEY', '')
    if not api_key:
        return pd.DataFrame()
    fred = Fred(api_key=api_key)
    end = datetime.today()
    start = end - timedelta(days=365*6)
    df = pd.DataFrame()
    for label, code in macro_series.items():
        try:
            df[label] = fred.get_series(code, start, end)
        except:
            df[label] = pd.Series(dtype=float)
    return df

# --- CALCUL SCORES BRUTS ---
prices = load_prices()
raw_scores = {}
for name, series in prices.items():
    s = series.dropna()
    if len(s) < 1:
        raw_scores[name] = 0.0
        continue
    last = s.iloc[-1]
    score = sum(
        score_and_style((last - s.tail(w).mean()) / s.tail(w).mean(), threshold_pct)[0]
        for w in timeframes.values() if len(s) >= w
    )
    raw_scores[name] = score

# --- SHIFT & ALLOCATION DCA ---
min_score = min(raw_scores.values())
shift = -min_score if min_score < 0 else 0.0
adj_scores = {k: v + shift for k, v in raw_scores.items()}
sum_adj = sum(adj_scores.values()) or 1.0
allocations = {k: (v / sum_adj * 50) for k, v in adj_scores.items()}

# --- SIDEBAR ALLOCATION ---
st.sidebar.header("Allocation DCA (50% actions)")
for name, pct in allocations.items():
    st.sidebar.markdown(f"**{name}:** {pct:.1f}%")
    if debug:
        st.sidebar.write(
            f"raw={raw_scores[name]:+.2f}, shift={shift:.2f}, adj={adj_scores[name]:+.2f}"
        )

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")
cols = st.columns(2)
macro_df = load_macro()
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue
    last = data.iloc[-1]
    delta = deltas.get(name, 0.0)
    perf_color = 'green' if delta >= 0 else 'crimson'

    # Calcul des poids par timeframe
    weights = {}
    for lbl, w in timeframes.items():
        if len(data) >= w:
            m = data.tail(w).mean()
            diff = (last - m) / m
            wt, _, _ = score_and_style(diff, threshold_pct)
            weights[lbl] = wt
        else:
            weights[lbl] = None



    key = f"win_{name}"
    if key not in st.session_state:
        st.session_state[key] = 'Annuel'
    period = timeframes[st.session_state[key]]
    df_plot = data.tail(period)
    fig = px.line(df_plot, height=200)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    alloc = allocations.get(name, 0)
    color = 'green' if alloc >= 40 else 'gold' if alloc >= 20 else 'crimson'

    items = []
    for lbl in macro_series:
        if lbl in macro_df and not macro_df[lbl].dropna().empty:
            val = macro_df[lbl].dropna().iloc[-1]
            items.append(f"<li>{lbl}: {val:.2f}</li>")
        else:
            items.append(f"<li>{lbl}: N/A</li>")
    half = len(items)//2 + len(items)%2
    macro_html = (
        "<div style='display:flex;gap:20px;'><ul style='margin:0;padding-left:16px'>"
        f"{''.join(items[:half])}</ul><ul style='margin:0;padding-left:16px'>{''.join(items[half:])}</ul></div>"
    )

    with cols[idx % 2]:
        if use_container_cards:
            target = st.container(border=True)
            target.markdown(
                f"<div style='height:4px;background:{color};margin:-10px -10px 10px -10px;border-radius:4px 4px 0 0'></div>",
                unsafe_allow_html=True,
            )
            target.subheader(name)
            target.metric("Dernier cours", f"{last:.2f}", delta=f"{delta:+.2f}%")
        else:
            st.markdown(
                "<div style='border:2px solid #1f77b4; border-radius:6px; padding:12px; margin:6px;'>",
                unsafe_allow_html=True,
            )
            target = st
            target.markdown(
                f"<h4>{name}: {last:.2f} <span style='color:{perf_color}'>{delta:+.2f}%</span></h4>",
                unsafe_allow_html=True,
            )

        target.plotly_chart(fig, use_container_width=True)

        badge_cols = target.columns(len(timeframes))
        for i, (lbl, w) in enumerate(timeframes.items()):
            if len(data) >= w:
                m = data.tail(w).mean()
                diff = (last - m) / m
                _, arrow, bg = score_and_style(diff, threshold_pct)
                tooltip = f"Moyenne {lbl}: {m:.2f}"
            else:
                arrow, bg, tooltip = '↓', 'crimson', 'N/A'
            with badge_cols[i]:
                if st.button(f"{lbl} {arrow}", key=f"{name}_{lbl}"):
                    st.session_state[key] = lbl
                st.markdown(
                    f"<span title='{tooltip}' style='background:{bg};color:white;padding:4px;border-radius:4px;font-size:12px;'>{lbl} {arrow}</span>",
                    unsafe_allow_html=True,
                )

        pts = ", ".join(
            f"{lbl}:{weights[lbl]:+0.1f}" for lbl in timeframes if weights[lbl] is not None
        )
        target.markdown(
            f"<div style='font-size:12px;'>Points: {pts}</div>", unsafe_allow_html=True
        )
        target.markdown(
            f"<div style='text-align:right;color:#ff7f0e;'>Allocation DCA: {alloc:.1f}%</div>",
            unsafe_allow_html=True,
        )
        target.markdown(macro_html, unsafe_allow_html=True)

        if not use_container_cards:
            target.markdown("</div>", unsafe_allow_html=True)

# Clé FRED
if macro_df.empty:
    st.warning("🔑 Clé FRED_API_KEY manquante.")

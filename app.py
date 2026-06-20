"""
Streamlit dashboard for TASE index analysis.

Run with:
    streamlit run app.py
"""

import csv
import io
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from analytics import (
    TRADING_DAYS,
    compute_metrics,
    monte_carlo_forecast,
    to_price_series,
)
from scraper import DEFAULT_INDEX_ID, fetch_tase_data

INDEX_NAMES = {
    142: 'ת"א-35',
    137: 'ת"א-90',
    146: 'ת"א-125',
    640: "תל-גוב כללי",
    641: "תל-גוב שקלי",
    642: "תל-גוב צמודות",
    643: "תל-גוב קצר",
    645: "תל-גוב צמודות 0-2",
    646: "תל-גוב צמודות 2-5",
    647: "תל-גוב צמודות 5+",
    648: "תל-בונד כללי",
    649: "תל-בונד שקלי",
    650: "תל-בונד צמודות",
}

st.set_page_config(page_title="TASE Index Dashboard", page_icon="📈", layout="wide")
st.title("📈 TASE Index Dashboard")
st.caption("בחר מדד וטווח תאריכים — תוצג סטיית תקן שנתית, תשואה, downside 5% ותחזית.")


# ---------------------------------------------------------------- selection ----
today = date.today()
default_start = today - timedelta(days=365)

with st.sidebar:
    st.header("בחירת נייר")

    labels = {f'{name}  ({oid})': oid for oid, name in INDEX_NAMES.items()}
    labels["אחר (הזן מזהה ידנית)…"] = None
    choice = st.selectbox("מדד / נייר", list(labels.keys()), index=0)
    selected_id = labels[choice]
    if selected_id is None:
        selected_id = st.number_input(
            "מזהה מדד (Index ID)", min_value=1, value=DEFAULT_INDEX_ID, step=1
        )
    index_id = int(selected_id)

    from_date = st.date_input("מתאריך", value=default_start, format="DD/MM/YYYY")
    to_date = st.date_input("עד תאריך", value=today, format="DD/MM/YYYY")

    fetch = st.button("טען נתונים", type="primary", use_container_width=True)


def _load_data(index_id: int, from_date: date, to_date: date):
    progress = st.progress(0.0, text="מתחיל…")

    def on_progress(msg: str, frac):
        progress.progress(min(max(frac or 0.0, 0.0), 1.0), text=msg)

    try:
        items = fetch_tase_data(
            from_date=from_date.strftime("%d/%m/%Y"),
            to_date=to_date.strftime("%d/%m/%Y"),
            index_id=index_id,
            progress_cb=on_progress,
        )
    except requests.RequestException as exc:
        progress.empty()
        st.error(f"שגיאת רשת בעת שליפת הנתונים: {exc}")
        return None
    progress.empty()
    return items


if fetch:
    if from_date > to_date:
        st.error("תאריך ההתחלה חייב להיות לפני תאריך הסיום.")
        st.stop()
    items = _load_data(index_id, from_date, to_date)
    if items is not None:
        st.session_state["items"] = items
        st.session_state["meta"] = {
            "index_id": index_id,
            "name": INDEX_NAMES.get(index_id, str(index_id)),
            "from": from_date,
            "to": to_date,
        }


# ---------------------------------------------------------------- dashboard ----
items = st.session_state.get("items")
meta = st.session_state.get("meta")

if not items:
    st.info("בחר נייר וטווח תאריכים בסרגל הצד ולחץ **טען נתונים**.")
    st.stop()

prices = to_price_series(items)
metrics = compute_metrics(prices)

if metrics is None:
    st.warning(
        f"לא התקבלו מספיק נתונים עבור מדד {meta['index_id']}. "
        "בדוק את המזהה ב-[market.tase.co.il](https://market.tase.co.il)."
    )
    st.stop()

st.subheader(f"{meta['name']}  ·  מדד {meta['index_id']}")
st.caption(
    f"{metrics.n_obs} ימי מסחר · {metrics.start:%d/%m/%Y}–{metrics.end:%d/%m/%Y} "
    f"· מחיר אחרון {metrics.last_price:,.2f}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("סטיית תקן מגולמת שנתית", f"{metrics.annual_vol * 100:.2f}%")
c2.metric(
    "תשואה (בתקופה)",
    f"{metrics.period_return * 100:.2f}%",
    help=f"תשואה שנתית מגולמת: {metrics.annual_return * 100:.2f}%",
)
c3.metric(
    "Downside 5% (יומי)",
    f"-{metrics.daily_var_5 * 100:.2f}%",
    help="VaR היסטורי: ההפסד היומי שנחצה רק ב-5% מהימים.",
)
c4.metric("Downside 5% (שנתי)", f"-{metrics.annual_var_5 * 100:.2f}%")

st.line_chart(prices.rename("מחיר סגירה"), height=280)


# ---------------------------------------------------------------- forecast ----
st.divider()
st.subheader("🔮 תחזית (Monte Carlo · GBM)")

fc1, fc2 = st.columns([1, 3])
with fc1:
    horizon = st.number_input(
        "אופק חיזוי (ימי מסחר קדימה)",
        min_value=1,
        max_value=TRADING_DAYS * 3,
        value=21,
        step=1,
        help="מספר ימי המסחר שתרצה לחזות קדימה.",
    )
    n_sims = st.select_slider(
        "מספר סימולציות", options=[500, 1000, 2000, 5000, 10000], value=2000
    )

forecast = monte_carlo_forecast(prices, horizon=int(horizon), n_sims=int(n_sims))

if forecast is None:
    st.warning("אין מספיק נתונים לחישוב תחזית.")
    st.stop()

with fc1:
    st.metric("מחיר צפוי (חציון)", f"{forecast.exp_price:,.2f}")
    st.metric(
        "תשואה צפויה",
        f"{forecast.exp_return * 100:+.2f}%",
    )
    st.metric(
        "Downside 5% לאופק",
        f"{forecast.downside_5_return * 100:.2f}%",
        help=(
            f"ב-5% מהתרחישים המחיר יורד אל {forecast.downside_5_price:,.2f} או פחות "
            f"בתום {forecast.horizon} ימי מסחר."
        ),
    )

with fc2:
    hist_tail = prices.tail(min(len(prices), 90))
    chart_df = pd.DataFrame(index=hist_tail.index.union(forecast.dates))
    chart_df["היסטוריה"] = hist_tail
    chart_df.loc[forecast.dates, "תחזית (חציון)"] = forecast.median
    chart_df.loc[forecast.dates, "אחוזון 5%"] = forecast.p5
    chart_df.loc[forecast.dates, "אחוזון 95%"] = forecast.p95
    st.line_chart(chart_df, height=380)

st.caption(
    "המודל מניח שתשואות יומיות (log) מתפלגות נורמלית לפי הממוצע וסטיית התקן ההיסטוריים, "
    "ומדמה מסלולי מחיר עתידיים. אחוזון 5%–95% הם רצועת אי-הוודאות; אחוזון 5% הוא ה-downside."
)


# ---------------------------------------------------------------- raw data ----
st.divider()
with st.expander("📄 נתונים גולמיים והורדת CSV"):
    st.dataframe(items, use_container_width=True)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(items[0].keys()))
    writer.writeheader()
    writer.writerows(items)
    filename = (
        f"tase_{meta['index_id']}_{meta['from']:%Y%m%d}_{meta['to']:%Y%m%d}"
        f"_{len(items)}rows.csv"
    )
    st.download_button(
        "⬇️ הורד CSV",
        data=buf.getvalue().encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )

import json
import os

import pandas as pd
import streamlit as st

from src.classify import classify_message, CATEGORIES
from src.extract import extract_items
from src.sensitive import scan_message

st.set_page_config(page_title="Message Intelligence Demo", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "messages.csv")
MANDATORY_PATH = os.path.join(os.path.dirname(__file__), "data", "mandatory_demo_ids.csv")


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["message"] = df["message"].astype(str)
    df = df.sort_values("timestamp").reset_index(drop=True)

    rows = []
    all_items = []
    all_sensitive = []
    for _, row in df.iterrows():
        mid, ts, sender, text = row["message_id"], row["timestamp"], row["sender"], row["message"]
        category, confidence, reason, rule = classify_message(text)
        rows.append({
            "message_id": mid, "timestamp": ts, "sender": sender, "message": text,
            "category": category, "confidence": confidence, "reason": reason,
        })
        for _, item in extract_items(text):
            item = dict(item)
            item["source_message_id"] = mid
            all_items.append(item)
        all_sensitive.extend(scan_message(mid, text))

    return pd.DataFrame(rows), all_items, all_sensitive


def load_mandatory_ids():
    if os.path.exists(MANDATORY_PATH):
        m = pd.read_csv(MANDATORY_PATH, encoding="utf-8-sig")
        return m["message_id"].tolist()
    return []


st.title("Message Intelligence Demo")
st.caption(
    "Rule-based classification, task/event extraction, and sensitive-information "
    "detection over the 900-message dataset. All processing runs locally in this "
    "app; no message text is sent to any external service."
)

if not os.path.exists(DATA_PATH):
    st.error(
        "data/messages.csv not found. This dataset is intentionally excluded from "
        "the public GitHub repo per the assignment rules -- place it in data/ "
        "before running or deploying this app."
    )
    st.stop()

df, items, sensitive_findings = load_data()
mandatory_ids = load_mandatory_ids()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Classification", "Tasks & Events", "Sensitive Information", "Mandatory Demo IDs"]
)

with tab1:
    st.subheader("Message Classification")
    c1, c2 = st.columns([1, 2])
    with c1:
        counts = df["category"].value_counts().reindex(CATEGORIES).fillna(0).astype(int)
        st.bar_chart(counts)
    with c2:
        cat_filter = st.multiselect("Filter by category", CATEGORIES, default=CATEGORIES)
        search = st.text_input("Search message text or ID")
        view = df[df["category"].isin(cat_filter)]
        if search:
            view = view[
                view["message_id"].str.contains(search, case=False)
                | view["message"].str.contains(search, case=False)
            ]
        st.dataframe(
            view[["message_id", "sender", "category", "confidence", "message", "reason"]],
            use_container_width=True, height=420,
        )

with tab2:
    st.subheader("Extracted Tasks & Events")
    items_df = pd.DataFrame(items)
    if not items_df.empty:
        item_type = st.radio("Type", ["all", "task", "event"], horizontal=True)
        v = items_df if item_type == "all" else items_df[items_df["type"] == item_type]
        st.dataframe(v, use_container_width=True, height=420)
        st.caption(
            f"{len(items_df)} items extracted total "
            f"({(items_df['date'].isna()).sum()} with unresolved date, per the "
            f"'do not guess missing information' rule)."
        )
    else:
        st.info("No items extracted.")

with tab3:
    st.subheader("Sensitive Information Detection")
    sens_df = pd.DataFrame(sensitive_findings)
    if not sens_df.empty:
        risk_filter = st.multiselect(
            "Filter by risk", sorted(sens_df["risk"].unique()),
            default=sorted(sens_df["risk"].unique()),
        )
        st.dataframe(
            sens_df[sens_df["risk"].isin(risk_filter)][
                ["message_id", "sensitivity_type", "risk", "masked_text", "recommended_action"]
            ],
            use_container_width=True, height=420,
        )
        st.caption(
            "All values shown are masked. Raw sensitive values are never written "
            "to logs, screenshots, or stored output in this app."
        )
    else:
        st.info("No sensitive information detected.")

with tab4:
    st.subheader("Mandatory Demo Message IDs")
    if mandatory_ids:
        mand_df = df[df["message_id"].isin(mandatory_ids)].copy()
        mand_df["extracted_items"] = mand_df["message_id"].apply(
            lambda mid: json.dumps(
                [i for i in items if i["source_message_id"] == mid], default=str
            )
        )
        mand_df["sensitive_flags"] = mand_df["message_id"].apply(
            lambda mid: ", ".join(
                s["sensitivity_type"] for s in sensitive_findings if s["message_id"] == mid
            )
        )
        st.dataframe(
            mand_df[["message_id", "category", "confidence", "message",
                     "extracted_items", "sensitive_flags"]],
            use_container_width=True, height=520,
        )
    else:
        st.warning("mandatory_demo_ids.csv not found in data/.")

st.divider()
st.caption(
    "Approach summary: the dataset is template-generated (~125 reusable core "
    "sentences), so classification, extraction, and sensitive detection all use "
    "explainable regex/keyword rules rather than a black-box model -- every "
    "output can be traced back to the exact rule that produced it. See README.md "
    "for the full methodology, assumptions, and limitations."
)

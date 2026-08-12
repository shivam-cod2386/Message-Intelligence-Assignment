import json
import os

import pandas as pd

from classify import classify_message
from extract import extract_items
from sensitive import scan_message

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "messages.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def run():
    df = pd.read_csv(DATA_PATH)
    df["message"] = df["message"].astype(str)
    # Rule: process messages in chronological order.
    df = df.sort_values("timestamp").reset_index(drop=True)

    classifications = []
    extracted_items = []
    sensitive_findings = []

    task_counter = 1
    event_counter = 1

    for _, row in df.iterrows():
        mid, ts, sender, text = row["message_id"], row["timestamp"], row["sender"], row["message"]

        category, confidence, reason, rule = classify_message(text)
        classifications.append({
            "message_id": mid,
            "timestamp": ts,
            "sender": sender,
            "category": category,
            "confidence": confidence,
            "reason": reason,
        })

        for rule_name, item in extract_items(text):
            if item["type"] == "task":
                item_id = f"TASK_{task_counter:03d}"
                task_counter += 1
            else:
                item_id = f"EVENT_{event_counter:03d}"
                event_counter += 1
            item_out = {
                "item_id": item_id,
                "type": item["type"],
                "title": item["title"],
                "date": item["date"],
                "time": item["time"],
                "person": item["person"],
                "priority": item["priority"],
                "source_message_id": mid,
            }
            if item["location"]:
                item_out["location"] = item["location"]
            if item["raw_time_expression"]:
                item_out["raw_time_expression"] = item["raw_time_expression"]
            extracted_items.append(item_out)

        sensitive_findings.extend(scan_message(mid, text))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "classifications.json"), "w") as f:
        json.dump(classifications, f, indent=2)
    with open(os.path.join(OUT_DIR, "tasks_and_events.json"), "w") as f:
        json.dump(extracted_items, f, indent=2)
    with open(os.path.join(OUT_DIR, "sensitive_report.json"), "w") as f:
        json.dump(sensitive_findings, f, indent=2)

    print(f"Messages processed:      {len(df)}")
    print(f"Classifications written: {len(classifications)}")
    print(f"Tasks/events extracted:  {len(extracted_items)}")
    print(f"Sensitive findings:      {len(sensitive_findings)}")
    print()
    print("Category breakdown:")
    print(pd.Series([c['category'] for c in classifications]).value_counts())


if __name__ == "__main__":
    run()

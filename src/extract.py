import re

DATE_RE = r"(\d{4}-\d{2}-\d{2})"
TIME_RE = r"(\d{1,2}:\d{2})"

_EXTRACTORS = []


def _extractor(name, pattern, builder, flags=re.IGNORECASE):
    _EXTRACTORS.append((name, re.compile(pattern, flags), builder))


def _mk(item_type, title, date=None, time=None, person=None, priority="medium",
        location=None, raw_time_expression=None):
    return {
        "type": item_type,
        "title": title.strip().rstrip(".").strip(),
        "date": date,
        "time": time,
        "person": person,
        "priority": priority,
        "location": location,
        "raw_time_expression": raw_time_expression,
    }


# ---- Meeting / Event templates -------------------------------------------
_extractor(
    "calendar_update",
    r"Calendar update:\s*([^,]+),\s*" + DATE_RE + r" at " + TIME_RE + r",\s*([^.]+)\.",
    lambda m: _mk("event", m.group(1), date=m.group(2), time=m.group(3),
                  location=m.group(4).strip(), priority="medium"),
)
_extractor(
    "reminder_event",
    r"Reminder:\s*(.+?) happens on\s*" + DATE_RE + r" at " + TIME_RE + r" in ([^.]+)\.",
    lambda m: _mk("event", m.group(1), date=m.group(2), time=m.group(3),
                  location=m.group(4).strip(), priority="medium"),
)
_extractor(
    "please_join",
    r"Please join the (.+?) on\s*" + DATE_RE + r",\s*" + TIME_RE + r" at ([^.]+)\.",
    lambda m: _mk("event", m.group(1), date=m.group(2), time=m.group(3),
                  location=m.group(4).strip(), priority="medium"),
)
_extractor(
    "scheduled_for",
    r"The (.+?) is scheduled for\s*" + DATE_RE + r" at " + TIME_RE + r" in ([^.]+)\.",
    lambda m: _mk("event", m.group(1), date=m.group(2), time=m.group(3),
                  location=m.group(4).strip(), priority="medium"),
)
_extractor(
    "are_you_available",
    r"Are you available for the (.+?) at\s*" + TIME_RE + r" on\s*" + DATE_RE + r"\? Location: ([^.]+)\.",
    lambda m: _mk("event", m.group(1), date=m.group(3), time=m.group(2),
                  location=m.group(4).strip(), priority="medium"),
)
_extractor(
    "meet_vague",
    r"Let us meet sometime next week\.",
    lambda m: _mk("event", "meet with sender", date=None, time=None,
                  priority="low", raw_time_expression="sometime next week"),
)
_extractor(
    "review_vague",
    r"The review could be Friday afternoon\.",
    lambda m: _mk("event", "review", date=None, time=None,
                  priority="low", raw_time_expression="Friday afternoon"),
)

# ---- Action Required templates --------------------------------------------
_extractor(
    "can_you_before",
    r"Can you (.+?) before\s*" + DATE_RE + r"\?",
    lambda m: _mk("task", m.group(1), date=m.group(2), priority="high"),
)
_extractor(
    "dont_forget",
    r"Don't forget to (.+?); deadline is\s*" + DATE_RE + r"\.",
    lambda m: _mk("task", m.group(1), date=m.group(2), priority="high"),
)
_extractor(
    "i_need_you_to",
    r"I need you to (.+?) by\s*" + DATE_RE + r"\.",
    lambda m: _mk("task", m.group(1), date=m.group(2), priority="high"),
)
_extractor(
    "please_call",
    r"Please call (\w+) when you are free\.",
    lambda m: _mk("task", "call " + m.group(1), date=None, person=m.group(1),
                  priority="low", raw_time_expression="when you are free"),
)
_extractor(
    "please_verb_by",
    r"Please (complete|confirm|reply to|submit) (.+?) by\s*" + DATE_RE + r"\.",
    lambda m: _mk("task", m.group(1) + " " + m.group(2), date=m.group(3), priority="high"),
)
_extractor(
    "is_due_on",
    r"(Complete|Prepare|Send|Share) (.+?) is due on\s*" + DATE_RE + r"\.",
    lambda m: _mk("task", m.group(1) + " " + m.group(2), date=m.group(3), priority="high"),
)
_extractor(
    "could_you_send",
    r"Could you send it soon\?",
    lambda m: _mk("task", "send it", date=None, priority="low",
                  raw_time_expression="soon"),
)
_extractor(
    "review_file",
    r"review the file before the meeting\.",
    lambda m: _mk("task", "review the file", date=None, priority="medium",
                  raw_time_expression="before the meeting"),
)


def extract_items(text: str):
    """Return a list of extracted task/event dicts for one message (usually 0 or 1)."""
    items = []
    for name, pattern, builder in _EXTRACTORS:
        match = pattern.search(text)
        if match:
            items.append((name, builder(match)))
    return items


if __name__ == "__main__":
    import pandas as pd
    import sys
    sys.path.insert(0, "/home/claude/kastack/src")
    from classify import classify_message

    df = pd.read_csv("/home/claude/kastack/data/messages.csv")
    df["message"] = df["message"].astype(str)
    cats = df["message"].apply(classify_message)
    df["category"] = [c[0] for c in cats]

    relevant = df[df["category"].isin(["Action Required", "Meeting or Event"])]
    n_extracted = 0
    n_missed = 0
    misses = []
    for _, row in relevant.iterrows():
        items = extract_items(row["message"])
        if items:
            n_extracted += 1
        else:
            n_missed += 1
            misses.append(row["message"])
    print("Action/Meeting messages:", len(relevant))
    print("Extracted at least one item:", n_extracted)
    print("Missed (no extractor matched):", n_missed)
    for m in sorted(set(misses)):
        print("  MISS:", m)

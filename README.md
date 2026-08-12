# Message Intelligence Assignment

A local, explainable pipeline that classifies 900 chronological messages,
extracts tasks/events, and detects + masks sensitive information — plus a
Streamlit demo app.

## Live demo
- Cloud-hosted app: `<ADD_YOUR_DEPLOYED_URL_HERE>`
- Video walkthrough: `<ADD_YOUR_LOOM_LINK_HERE>`

## Repo layout
```
src/
  classify.py    # Part 1 — message classification
  extract.py     # Part 2 — task/event extraction
  sensitive.py   # Part 3 — sensitive information detection & masking
  pipeline.py    # runs all three over messages.csv, writes JSON outputs
app.py           # Streamlit demo (classification / extraction / sensitive / mandatory IDs)
outputs/         # generated JSON (classifications.json, tasks_and_events.json, sensitive_report.json)
data/            # messages.csv + mandatory_demo_ids.csv go here locally (NOT committed — see .gitignore)
```

## How to run locally
```bash
pip install -r requirements.txt
# place messages.csv and mandatory_demo_ids.csv in data/
python3 src/pipeline.py      # generates outputs/*.json
streamlit run app.py         # interactive demo
```

## Approach

### Why rule-based, not a trained ML model
No labelled training data was provided, and the assignment explicitly
forbids fabricating results or relying entirely on external AI APIs.
Inspecting the dataset shows it is generated from a small, closed set of
**~125 reusable "core" message templates**, each wrapped in one of a dozen
filler prefixes ("For today:", "Just checking—", "Hi,", "FYI:", etc.) that
carry no category information themselves. Given that, a transparent
regex/keyword rule engine is both more accurate and far more explainable
than a model trained on synthetic/self-labelled data — every single output
can be traced back to the exact rule and regex group that produced it,
satisfying the "you must understand and explain everything submitted"
requirement. This is a deliberate design choice, not a shortcut, and is
demonstrated in the video.

### Part 1 — Classification (`src/classify.py`)
An ordered list of regex rules is checked per message; the first match
wins. Priority order (high → low): **Sensitive Information → Promotional →
Meeting or Event → Action Required → Personal Information → General
Information (default fallback)**.

Every classification carries a `reason` string. Messages that don't match
any specific rule fall back to **General Information** with a lower
confidence score (0.55) and an explicit "no strong pattern matched"
reason — never a silent or fabricated guess.

**Confidence scoring:** 0.95 for a direct, unambiguous template match;
0.55–0.8 for messages we judged genuinely ambiguous (see "Uncertain cases"
below); 0.55 for the unmatched fallback.

**Design decision — overlap between "Personal Information" and "Sensitive
Information":** messages containing a directly exploitable secret (OTP,
password, access token, card number, bank account number, recovery code,
government-style ID number) are classified **Sensitive Information** in
Part 1, since the security risk dominates. Messages that are personal but
not a usable credential by themselves (home address, phone number,
personal preferences) are classified **Personal Information** in Part 1,
but are *also* picked up by the dedicated Part 3 sensitive-data scan,
because an address or phone number is still private and worth masking
even though it isn't the message's defining "category."

### Part 2 — Task & Event Extraction (`src/extract.py`)
Runs only conceptually over messages that read as a task, reminder,
meeting, or event (in practice: everything classified as Action Required
or Meeting or Event). Each known template family has its own regex that
captures title / date / time / location directly from the matched groups
— nothing is inferred beyond what the regex captures.

**"Do not guess missing information" is followed literally.** Two
templates reference genuinely vague timing ("Let us meet **sometime next
week**", "The review could be **Friday afternoon**"). For these, `date`
and `time` are stored as `null`, and the original vague phrase is kept in
a `raw_time_expression` field so a human can resolve it manually — we
never invent a calendar date for a relative expression.

**Priority heuristic** (simple, disclosed, not a strong claim): `high` for
Action Required items with an explicit deadline date, `medium` for
Meeting/Event items with a resolved date + time, `low` for anything with
an unresolved date/time.

Coverage check: every message classified as Action Required or Meeting or
Event produced at least one extracted item (400/400) in local testing.

### Part 3 — Sensitive Information Detection (`src/sensitive.py`)
Regex detectors for the sensitivity types the assignment names explicitly:
OTP, password, authentication token, payment card number, bank account
number, and personal identification number/private address/contact
details. **One addition, clearly disclosed:** health information (e.g. a
message stating a private test result) — not in the assignment's example
list, but obviously private data, so we flag it as its own
`health_information` type at medium risk rather than silently dropping it
or treating it identically to a password.

**Masking:** only the sensitive value inside the sentence is replaced with
a fixed-length mask (`******`); the surrounding sentence is preserved so a
reviewer can still see the message's context, matching the assignment's
own example format. A unit check (`src/sensitive.py`, run as a script)
confirms no findings ever leave an unmasked value in `masked_text`.

**Risk levels:** `high` = directly exploitable credential (OTP, password,
token, card number, bank account number, recovery code, ID number).
`medium` = private personal data that is not a usable credential by
itself (address, phone number, health detail).

**Recommended actions** used: `do_not_store` (credentials, tokens,
financial identifiers, health detail) and `ask_for_confirmation` (address,
phone number — plausible to sometimes need for legitimate logistics, so a
confirmation step is safer than either processing silently or refusing
outright). We never recommend sending sensitive values to an external
service.

## Uncertain / borderline cases (disclosed, not hidden)
These are deliberately called out in the video as required:

1. **"You may like our new student plan."** (sent by a named person, not
   the `Promotions` sender, and with no promo code) — classified
   **Promotional** at 0.65 confidence based on marketing phrasing similar
   to other promotional templates. **General Information** is a
   reasonable alternative reading; disclosed as such.
2. **"The review could be Friday afternoon."** — classified **Meeting or
   Event** at 0.7 confidence; date/time left `null` because "Friday
   afternoon" is a relative day name, not a resolvable date, and "could
   be" signals it isn't confirmed.
3. **"Let us meet sometime next week."** — same treatment: classified as
   an event with `date: null`, `raw_time_expression: "sometime next
   week"`.
4. **"The report may be needed tomorrow."** — classified **General
   Information** rather than Action Required, because "may be needed" is
   a possibility, not a direct request/instruction to the reader.

## Assumptions
- No labelled ground truth was provided, so "correctness" here means
  internal consistency and explainability against the observed templates,
  not agreement with a hidden answer key.
- `person` in extracted tasks/events is only populated when a name is
  explicitly addressed in an imperative context (e.g. "Please call
  **Maya**"); the message `sender` field is not treated as the task's
  `person`, since the assignment schema example uses `person` for someone
  *referenced* in the task, not the sender.
- Timestamps in `messages.csv` are treated as already chronological
  (verified by sorting on load) rather than re-derived from message
  content.

## Limitations & possible improvements
- The regex rules are tuned to this dataset's ~125 templates. A
  production system handling free-form, human-written messages would need
  a more general fallback (e.g. lightweight local embeddings) behind the
  same rule-first architecture, so genuinely novel phrasing degrades
  gracefully instead of always landing in the General Information default.
- Priority scoring is a simple three-level heuristic based on
  deadline-resolution, not urgency language or sender role — a real system
  could weight sender importance or explicit urgency words ("urgent",
  "ASAP").
- Sensitive-value detection is pattern-based; it would miss sensitive data
  expressed in a format not seen in this dataset (e.g. a differently
  formatted phone number). A production system would likely combine this
  with a broader PII-detection library as a second pass.

## AI-tool usage disclosure
This solution (classification rules, extraction regexes, sensitive-data
detectors, pipeline, Streamlit app, and this README) was developed with
the assistance of an AI coding assistant (Claude), based on direct
inspection of the actual dataset's message templates. All logic was
reviewed, tested against the full 900-message dataset, and is understood
and can be explained line-by-line, per the assignment's requirement. No
message content was sent to any external AI service or API as part of the
classification/extraction/detection pipeline itself — all processing is
local Python regex/rule logic with zero external calls.

## Rules compliance checklist
- [x] Individual assignment — solved directly, not shared.
- [x] Messages processed in chronological order (`pipeline.py` sorts by timestamp).
- [x] No invented dates/people/deadlines/events — unresolved fields are `null`.
- [x] Every classification/extraction decision carries a `reason`.
- [x] Sensitive values are always masked before being written to any output file.
- [x] Dataset (`messages.csv`, `mandatory_demo_ids.csv`) excluded from the public repo via `.gitignore`.
- [x] No raw message text sent to any external AI service.

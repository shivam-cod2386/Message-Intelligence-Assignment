import re

CATEGORIES = [
    "Action Required",
    "Meeting or Event",
    "Personal Information",
    "General Information",
    "Promotional",
    "Sensitive Information",
]

# Each rule: (name, compiled_regex, category, reason, confidence)
_RULES = []


def _rule(name, pattern, category, reason, confidence=0.95, flags=re.IGNORECASE):
    _RULES.append((name, re.compile(pattern, flags), category, reason, confidence))


# ---------------------------------------------------------------- SENSITIVE
_rule("otp", r"\bOTP\b",
      "Sensitive Information",
      "Message contains a one-time password (OTP) value.")
_rule("password", r"\bpassword\b",
      "Sensitive Information",
      "Message contains a plaintext password / login credential.")
_rule("access_token", r"\baccess token\b|tok_demo",
      "Sensitive Information",
      "Message contains an authentication/access token.")
_rule("card_number", r"\bcard number\b",
      "Sensitive Information",
      "Message contains a payment card number.")
_rule("bank_account", r"\bbank account number\b",
      "Sensitive Information",
      "Message contains a bank account number.")
_rule("recovery_code", r"\baccount recovery code\b",
      "Sensitive Information",
      "Message contains an account recovery code.")
_rule("id_number", r"\bidentification number\b",
      "Sensitive Information",
      "Message contains a personal identification number.")

# ---------------------------------------------------------------- PROMOTIONAL
_rule("promo_code", r"\buse code\s+[A-Z0-9]+\b",
      "Promotional",
      "Message advertises a discount/offer and includes a promo code.")
_rule("promo_softsell", r"you may like our new .* plan",
      "Promotional",
      "Message uses marketing/soft-sell phrasing ('you may like our new "
      "... plan') similar to other promotional templates, even though it "
      "has no promo code attached. Treated as Promotional with medium "
      "confidence; General Information is a reasonable alternative reading.",
      confidence=0.65)

# ---------------------------------------------------------------- MEETING / EVENT
_rule("calendar_update", r"\bcalendar update\s*:",
      "Meeting or Event",
      "Message is an explicit calendar update naming an event, date and time.")
_rule("reminder_event", r"\breminder\s*:\s*[\w\- ]+ happens on",
      "Meeting or Event",
      "Message is a reminder about an event with a fixed date and time.")
_rule("scheduled_for", r"\bis scheduled for\b",
      "Meeting or Event",
      "Message states that a meeting/discussion is scheduled with a date and time.")
_rule("please_join", r"\bplease join the\b",
      "Meeting or Event",
      "Message invites the reader to a workshop/orientation/session with a date and time.")
_rule("are_you_available", r"\bare you available for\b",
      "Meeting or Event",
      "Message asks about availability for a specific scheduled event.")
_rule("lets_meet_vague", r"\blet us meet sometime\b",
      "Meeting or Event",
      "Message proposes a meeting, but the timing is vague/unresolved "
      "('sometime next week') rather than a fixed date.",
      confidence=0.8)
_rule("review_could_be", r"\bthe review could be\b",
      "Meeting or Event",
      "Message tentatively mentions a review session, but the date is a "
      "relative day name ('Friday afternoon') with the word 'could', so "
      "timing is uncertain rather than confirmed.",
      confidence=0.7)

# ---------------------------------------------------------------- ACTION REQUIRED
_rule("can_you_before", r"\bcan you .* before\b",
      "Action Required",
      "Message directly asks the reader to complete a task by a deadline.")
_rule("dont_forget", r"\bdon't forget to\b",
      "Action Required",
      "Message is a direct reminder to perform a task, with a deadline.")
_rule("i_need_you_to", r"\bi need you to\b",
      "Action Required",
      "Message directly assigns a task to the reader with a deadline.")
_rule("please_verb_deadline", r"\bplease (call|complete|confirm|reply|submit)\b",
      "Action Required",
      "Message is a direct request/instruction addressed to the reader.")
_rule("is_due_on", r"\bis due on\b",
      "Action Required",
      "Message names a deliverable with an explicit due date.")
_rule("could_you_send", r"\bcould you send it soon\b",
      "Action Required",
      "Message directly requests the reader to send something.")
_rule("review_file", r"\breview the file before the meeting\b",
      "Action Required",
      "Message instructs the reader to review something before a meeting.")

# ---------------------------------------------------------------- PERSONAL INFORMATION
_rule("for_my_profile", r"\bfor my profile\b",
      "Personal Information",
      "Message shares a personal/biographical fact for a user profile.")
_rule("personal_note", r"\bpersonal note\s*:",
      "Personal Information",
      "Message is explicitly labelled as a personal note about the sender.")
_rule("remember_that", r"\bremember that\b",
      "Personal Information",
      "Message shares a personal preference the reader is asked to remember.")
_rule("preference_bare",
      r"\bi (drink coffee|prefer morning|prefer evening|prefer receiving|use dark mode|might prefer)\b"
      r"|\bmy t-shirt size\b",
      "Personal Information",
      "Message states a personal preference about the sender (optionally "
      "introduced by filler such as 'Just so you know,').")
_rule("home_address", r"\bmy home address is\b",
      "Personal Information",
      "Message shares the sender's home address (also flagged separately "
      "as sensitive/private data in Part 3).")
_rule("contact_number", r"\byou can contact me on\b",
      "Personal Information",
      "Message shares the sender's contact number (also flagged separately "
      "as sensitive/private data in Part 3).")
_rule("health_info", r"\bmy recent test result says\b",
      "Personal Information",
      "Message shares a personal health-related fact about the sender. "
      "Not in the assignment's example sensitivity list, but flagged as an "
      "additional 'health_information' type in Part 3 since it is clearly "
      "private data.")

_FALLBACK_REASON = (
    "No strong category-specific pattern matched; classified as General "
    "Information by default because the message reads as a plain factual "
    "statement/announcement rather than a request, invite, secret, "
    "promotion, or personal disclosure."
)


def classify_message(text: str):
    """Return (category, confidence, reason, matched_rule) for one message."""
    for name, pattern, category, reason, confidence in _RULES:
        if pattern.search(text):
            return category, confidence, reason, name
    return "General Information", 0.55, _FALLBACK_REASON, "fallback_default"


if __name__ == "__main__":
    import pandas as pd

    df = pd.read_csv("/home/claude/kastack/data/messages.csv")
    df["message"] = df["message"].astype(str)
    results = df["message"].apply(classify_message)
    df["category"], df["confidence"], df["reason"], df["rule"] = zip(*results)
    print(df["category"].value_counts())
    print()
    print("Unmatched (fallback) count:", (df["rule"] == "fallback_default").sum())
    print(df[df["rule"] == "fallback_default"]["message"].drop_duplicates().to_string())

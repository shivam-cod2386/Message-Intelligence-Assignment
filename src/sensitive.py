import re

_MASK = "******"

_DETECTORS = []


def _detector(name, pattern, value_group, sensitivity_type, risk, action, flags=re.IGNORECASE):
    _DETECTORS.append((name, re.compile(pattern, flags), value_group, sensitivity_type, risk, action))


_detector("otp", r"Your OTP is ([\d\-]+)\. It expires",
          1, "one_time_password", "high", "do_not_store")
_detector("password", r"Use password (\S+) to sign in",
          1, "password", "high", "do_not_store")
_detector("access_token", r"temporary access token is (\S+?)\.",
          1, "authentication_token", "high", "do_not_store")
_detector("card_number", r"My card number is ([\d \-]+)\.",
          1, "payment_card_number", "high", "do_not_store")
_detector("bank_account", r"bank account number ([\d\-]+)\.",
          1, "bank_account_number", "high", "do_not_store")
_detector("recovery_code", r"account recovery code is ([\w\-]+)\.",
          1, "account_recovery_code", "high", "do_not_store")
_detector("id_number", r"identification number is ([\w\-]+)\.",
          1, "personal_identification_number", "high", "do_not_store")
_detector("home_address", r"home address is ([^.]+)\.",
          1, "private_address", "medium", "ask_for_confirmation")
_detector("contact_number", r"contact me on ([\d \-]+)\.",
          1, "private_contact_number", "medium", "ask_for_confirmation")
_detector("health_info", r"test result says ([^.]+)\.",
          1, "health_information", "medium", "do_not_store")


def scan_message(message_id: str, text: str):
    """Return a list of sensitive-info findings for one message (usually 0 or 1)."""
    findings = []
    for name, pattern, group, s_type, risk, action in _DETECTORS:
        match = pattern.search(text)
        if match:
            value = match.group(group)
            masked_text = text[:match.start(group)] + _MASK + text[match.end(group):]
            findings.append({
                "message_id": message_id,
                "sensitivity_type": s_type,
                "risk": risk,
                "masked_text": masked_text,
                "recommended_action": action,
                "detector": name,
            })
    return findings


if __name__ == "__main__":
    import pandas as pd

    df = pd.read_csv("/home/claude/kastack/data/messages.csv")
    df["message"] = df["message"].astype(str)
    total = 0
    by_type = {}
    for _, row in df.iterrows():
        findings = scan_message(row["message_id"], row["message"])
        for f in findings:
            total += 1
            by_type[f["sensitivity_type"]] = by_type.get(f["sensitivity_type"], 0) + 1
            assert "*" * 3 in f["masked_text"], f"Unmasked value leaked: {f}"
    print("Total sensitive findings:", total)
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")

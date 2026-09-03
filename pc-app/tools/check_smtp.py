#!/usr/bin/env python3
"""Test the SMTP credentials on their own, without the rest of the app.

A failed alert could be the credentials, the app, or the network. This talks to
the mail server directly and reports exactly what it says, so you know which.
It authenticates but sends nothing.

    python tools/check_smtp.py

Never prints the password -- only its length and whether it looks like a Google
app password.
"""

from __future__ import annotations

import smtplib
import ssl
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402


def main() -> int:
    print("Configuration")
    print(f"  host     : {settings.smtp_host}:{settings.smtp_port}")
    print(f"  user     : {settings.smtp_user}")
    print(f"  from     : {settings.alert_from or '(falls back to user)'}")

    pw = settings.smtp_password
    shape = "16 lowercase letters" if len(pw) == 16 and pw.isalpha() and pw.islower() else "NOT the usual shape"
    print(f"  password : {len(pw)} characters, {shape}")

    if not settings.smtp_configured:
        print("\nFAIL: SMTP_HOST, SMTP_USER and SMTP_PASSWORD must all be set in pc-app/.env")
        return 1

    if settings.smtp_host.endswith("gmail.com") and shape.startswith("NOT"):
        print("\nNOTE: Google app passwords are exactly 16 lowercase letters, no")
        print("      digits or symbols. A normal account password will always be")
        print("      rejected for SMTP, whatever else is configured correctly.")

    print("\nConnecting...")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            print("  connected")
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            print("  TLS established")
            smtp.login(settings.smtp_user, settings.smtp_password)
            print("  authenticated")
    except smtplib.SMTPAuthenticationError as exc:
        print(f"\nFAIL: the server rejected the credentials\n  {exc.smtp_code} {exc.smtp_error!r}")
        print("\nThe connection and TLS worked, so this is the account or the")
        print("password, not the network and not this application. In order of")
        print("likelihood:")
        print("  1. The app password belongs to a different Google account. The")
        print("     app-passwords page generates for whichever account is active,")
        print("     which is easy to get wrong when signed into several.")
        print("  2. The account is too new. Google restricts SMTP on freshly")
        print("     created accounts, sometimes for a day or more.")
        print("  3. 2-Step Verification was turned off, which revokes every app")
        print("     password silently.")
        print("  4. A mistyped character. Regenerate and paste again.")
        print("\nTo tell them apart, try an established personal account with its")
        print("own freshly generated app password. If that authenticates, the")
        print("problem is the other account rather than anything here.")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAIL: {type(exc).__name__}: {exc}")
        print("\nThis one is the connection rather than the credentials -- check")
        print("the host and port, and whether the network blocks outbound 587.")
        return 1

    print("\nOK: the credentials work. Alerts will send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

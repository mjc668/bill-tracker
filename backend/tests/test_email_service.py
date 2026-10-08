"""Unit tests for app/services/email.py — mocks smtplib.SMTP."""

import smtplib
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.email import (
    send_monthly_summary_email,
    send_password_reset_email,
    send_reminder_email,
)

_BASE = dict(
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_user="user@example.com",
    smtp_password="secret",
    from_addr="reminders@example.com",
    to_addr="user@example.com",
    bill_name="Internet",
    due_date=date(2026, 6, 17),
    amount=Decimal("99.99"),
    currency="PLN",
)


def _call(**overrides):
    return {**_BASE, **overrides}


@patch("app.services.email.smtplib.SMTP")
def test_starttls_login_send_quit_sequence(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reminder_email(**_call(kind="upcoming", language="en"))

    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user@example.com", "secret")
    smtp_instance.send_message.assert_called_once()


@patch("app.services.email.smtplib.SMTP")
def test_no_login_when_smtp_user_is_none(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reminder_email(
        **_call(smtp_user=None, smtp_password=None, kind="upcoming", language="en")
    )

    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_not_called()
    smtp_instance.send_message.assert_called_once()


_SUBJECT_CASES = [
    ("2_days_before", "en", "Reminder: Internet due in 2 days (99.99 PLN)"),
    ("2_days_before", "pl", "Przypomnienie: Internet płatne za 2 dni (99.99 PLN)"),
    ("2_days_before", "de", "Erinnerung: Internet fällig in 2 Tagen (99.99 PLN)"),
    ("upcoming", "en", "Reminder: Internet due tomorrow (99.99 PLN)"),
    ("upcoming", "pl", "Przypomnienie: Internet płatne jutro (99.99 PLN)"),
    ("upcoming", "de", "Erinnerung: Internet fällig morgen (99.99 PLN)"),
    ("on_day", "en", "Due today: Internet (99.99 PLN)"),
    ("on_day", "pl", "Płatne dziś: Internet (99.99 PLN)"),
    ("on_day", "de", "Heute fällig: Internet (99.99 PLN)"),
    ("1_day_after", "en", "Overdue: Internet was due yesterday (99.99 PLN)"),
    ("1_day_after", "pl", "Zaległość: Internet było płatne wczoraj (99.99 PLN)"),
    ("1_day_after", "de", "Überfällig: Internet war gestern fällig (99.99 PLN)"),
]


@pytest.mark.parametrize("kind,language,expected_subject", _SUBJECT_CASES)
@patch("app.services.email.smtplib.SMTP")
def test_subject_combinations(mock_smtp_cls, kind, language, expected_subject):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reminder_email(**_call(kind=kind, language=language))

    sent_msg = smtp_instance.send_message.call_args[0][0]
    assert sent_msg["Subject"] == expected_subject


@patch("app.services.email.smtplib.SMTP")
def test_unknown_language_falls_back_to_english(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reminder_email(**_call(kind="upcoming", language="xx"))

    sent_msg = smtp_instance.send_message.call_args[0][0]
    assert sent_msg["Subject"] == "Reminder: Internet due tomorrow (99.99 PLN)"


@patch("app.services.email.smtplib.SMTP")
def test_reminder_body_contains_bill_name_amount_due_date(mock_smtp_cls):
    """HTML body must contain the bill name, amount, and due date — blank template vars fail here."""
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reminder_email(**_call(kind="upcoming", language="en"))

    msg = smtp_instance.send_message.call_args[0][0]
    # EmailMessage may be multipart or plain; walk covers both
    body = "".join(
        part.get_payload(decode=True).decode()
        for part in msg.walk()
        if part.get_content_type() in ("text/html", "text/plain")
        and not part.get_content_disposition()
    )
    assert "Internet" in body
    assert "99.99" in body
    assert "2026-06-17" in body or "June 17" in body or "17" in body


@patch("app.services.email.smtplib.SMTP")
def test_reminder_body_on_day_kind_contains_bill_details(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reminder_email(**_call(kind="on_day", language="en"))

    msg = smtp_instance.send_message.call_args[0][0]
    body = "".join(
        part.get_payload(decode=True).decode()
        for part in msg.walk()
        if part.get_content_type() in ("text/html", "text/plain")
        and not part.get_content_disposition()
    )
    assert "Internet" in body
    assert "PLN" in body


# ---------------------------------------------------------------------------
# Monthly summary email tests
# ---------------------------------------------------------------------------

_SUMMARY_BASE = dict(
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_user="user@example.com",
    smtp_password="secret",
    from_addr="reminders@example.com",
    to_addr="user@example.com",
    month_label="June 2026",
    language="en",
)

_PAID_ROW = {
    "name": "Internet",
    "due_date": "2026-06-10",
    "amount": Decimal("99.99"),
    "paid_amount": Decimal("99.99"),
    "currency": "PLN",
    "paid_at": datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
}

_UNPAID_ROW = {
    "name": "Netflix",
    "due_date": "2026-06-20",
    "amount": Decimal("45.00"),
    "currency": "PLN",
}


@patch("app.services.email.smtplib.SMTP")
def test_monthly_summary_sends_html_email(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_monthly_summary_email(
        **_SUMMARY_BASE,
        paid_rows=[_PAID_ROW],
        unpaid_rows=[_UNPAID_ROW],
    )

    smtp_instance.send_message.assert_called_once()
    msg = smtp_instance.send_message.call_args[0][0]
    assert msg["Subject"] == "Monthly summary for June 2026 — Hearthbill"
    # EmailMessage with add_alternative is multipart
    assert msg.is_multipart()
    html_part = next(
        (p for p in msg.walk() if p.get_content_type() == "text/html"), None
    )
    assert html_part is not None
    html = html_part.get_payload(decode=True).decode()
    assert "Internet" in html
    assert "Netflix" in html


@patch("app.services.email.smtplib.SMTP")
def test_monthly_summary_mismatch_shows_both_amounts(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    mismatch_row = {**_PAID_ROW, "paid_amount": Decimal("95.00")}
    send_monthly_summary_email(
        **_SUMMARY_BASE,
        paid_rows=[mismatch_row],
        unpaid_rows=[],
    )

    msg = smtp_instance.send_message.call_args[0][0]
    html_part = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    html = html_part.get_payload(decode=True).decode()
    assert "95.00" in html
    assert "99.99" in html  # expected amount also shown


@patch("app.services.email.smtplib.SMTP")
def test_monthly_summary_empty_paid_section(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_monthly_summary_email(
        **_SUMMARY_BASE,
        paid_rows=[],
        unpaid_rows=[_UNPAID_ROW],
    )

    msg = smtp_instance.send_message.call_args[0][0]
    html_part = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    html = html_part.get_payload(decode=True).decode()
    assert "No payments were marked as paid this month" in html
    assert "Netflix" in html


@patch("app.services.email.smtplib.SMTP")
def test_monthly_summary_escapes_user_controlled_currency(mock_smtp_cls):
    """A malicious currency string is HTML-escaped in the summary email."""
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    row = {**_UNPAID_ROW, "currency": '<script>alert("x")</script>'}
    send_monthly_summary_email(
        **_SUMMARY_BASE,
        paid_rows=[],
        unpaid_rows=[row],
    )

    msg = smtp_instance.send_message.call_args[0][0]
    html_part = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    html = html_part.get_payload(decode=True).decode()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    "language,expected_subject",
    [
        ("en", "Monthly summary for June 2026 — Hearthbill"),
        ("pl", "Miesięczne podsumowanie za June 2026 — Hearthbill"),
        ("de", "Monatliche Zusammenfassung für June 2026 — Hearthbill"),
    ],
)
@patch("app.services.email.smtplib.SMTP")
def test_monthly_summary_multilingual_subject(
    mock_smtp_cls, language, expected_subject
):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_monthly_summary_email(
        **{**_SUMMARY_BASE, "language": language},
        paid_rows=[],
        unpaid_rows=[],
    )

    msg = smtp_instance.send_message.call_args[0][0]
    assert msg["Subject"] == expected_subject


@patch("app.services.email.smtplib.SMTP")
def test_monthly_summary_unknown_language_falls_back_to_english(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_monthly_summary_email(
        **{**_SUMMARY_BASE, "language": "xx"},
        paid_rows=[],
        unpaid_rows=[],
    )

    msg = smtp_instance.send_message.call_args[0][0]
    assert msg["Subject"] == "Monthly summary for June 2026 — Hearthbill"


# ---------------------------------------------------------------------------
# Password reset email tests
# ---------------------------------------------------------------------------

_RESET_BASE = dict(
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_user="user@example.com",
    smtp_password="secret",
    smtp_use_tls=True,
    from_addr="noreply@example.com",
    to_addr="target@example.com",
    reset_url="http://localhost:3010/reset-password?token=abc123",
    language="en",
)


@patch("app.services.email.smtplib.SMTP")
def test_reset_email_starttls_login_send_sequence(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_password_reset_email(**_RESET_BASE)

    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user@example.com", "secret")
    smtp_instance.send_message.assert_called_once()


@patch("app.services.email.smtplib.SMTP")
def test_reset_email_no_login_when_smtp_user_is_none(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_password_reset_email(
        **{**_RESET_BASE, "smtp_user": None, "smtp_password": None}
    )

    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_not_called()
    smtp_instance.send_message.assert_called_once()


@pytest.mark.parametrize(
    "language,expected_subject",
    [
        ("en", "Reset your Hearthbill password"),
        ("pl", "Zresetuj hasło Hearthbill"),
        ("de", "Hearthbill Passwort zurücksetzen"),
    ],
)
@patch("app.services.email.smtplib.SMTP")
def test_reset_email_subject_per_language(mock_smtp_cls, language, expected_subject):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_password_reset_email(**{**_RESET_BASE, "language": language})

    msg = smtp_instance.send_message.call_args[0][0]
    assert msg["Subject"] == expected_subject


@patch("app.services.email.smtplib.SMTP")
def test_reset_email_body_contains_reset_url(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    reset_url = "http://localhost:3010/reset-password?token=my-special-token"
    send_password_reset_email(**{**_RESET_BASE, "reset_url": reset_url})

    msg = smtp_instance.send_message.call_args[0][0]
    body = msg.get_payload(decode=True).decode()
    assert reset_url in body


@patch("app.services.email.smtplib.SMTP")
def test_reset_email_unknown_language_falls_back_to_english(mock_smtp_cls):
    smtp_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=smtp_instance)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_password_reset_email(**{**_RESET_BASE, "language": "xx"})

    msg = smtp_instance.send_message.call_args[0][0]
    assert msg["Subject"] == "Reset your Hearthbill password"

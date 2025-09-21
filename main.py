#!/usr/bin/env python3
"""
main.py

Email automation: read CSV of HR contacts, render a personalized cold email,
attach resume.pdf, and send via Gmail SMTP (smtp.gmail.com:587).

Default: dry-run mode (prints messages & attachments but does NOT send).
To actually send, run with --send.

Functions:
 - read_csv()
 - validate_row()
 - render_template()
 - send_email()
 - main()

Security:
 - Credentials must be provided via environment variables:
     GMAIL_USER, GMAIL_APP_PASS
 - Do NOT hardcode credentials.
"""

import argparse
import csv
import os
import re
import sys
import time
import json
import logging
from typing import Dict, List, Tuple, Optional
from email.message import EmailMessage
import smtplib
import socket
from datetime import datetime
from pathlib import Path
from copy import deepcopy

# Optional dependency: pandas (can be helpful for larger CSVs)
try:
    import pandas as pd  # type: ignore
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False

# ---------------------------
# Configuration defaults
# ---------------------------
DEFAULT_CSV_PATH = "sample_hr.csv"
DEFAULT_RESUME_PATH = "resume.pdf"
DEFAULT_LOG_PATH = "send_log.csv"
DEFAULT_TEMPLATE_PATH = "email_template.txt"
DEFAULT_CONFIG_JSON = "config.example.json"

# Basic email regex for validation
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

# Setup logging (console + file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("email_automation")

# ---------------------------
# Utility functions
# ---------------------------

# def read_csv(path: str) -> List[Dict[str, str]]:
#     """
#     Read CSV and return list of dict rows. Tries pandas if available (preserves types).
#     Expects header row with columns at least: SNo, Name, Email, Title, Company
#     """
#     if not os.path.exists(path):
#         raise FileNotFoundError(f"CSV file not found: {path}")

#     logger.info(f"Reading CSV: {path}")
#     rows = []
#     if HAS_PANDAS:
#         df = pd.read_csv(path, dtype=str).fillna("")
#         for _, r in df.iterrows():
#             rows.append({k: ("" if pd.isna(v) else str(v)) for k, v in r.items()})
#     else:
#         with open(path, newline='', encoding='utf-8') as f:
#             reader = csv.DictReader(f)
#             for r in reader:
#                 # convert None to empty string
#                 rows.append({k: (v if v is not None else "") for k, v in r.items()})
#     logger.info(f"Found {len(rows)} rows in CSV")
#     return rows

def read_csv(path: str) -> List[Dict[str, str]]:
    """
    Robust reader: normalizes tabs -> commas, removes trailing spaces after commas in header,
    then uses csv.DictReader with utf-8-sig. Keeps fallback parsing if needed.
    """
    import io
    import re
    from csv import DictReader, Sniffer

    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV file not found: {path}")

    logger.info(f"Reading CSV: {path}")

    # Read raw text and normalize common issues:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        raw = f.read()

    # Normalize tabs => commas
    normalized = raw.replace("\t", ",")

    # Replace comma + many spaces => single comma
    normalized = re.sub(r",\s+", ",", normalized)

    # Optionally write to a temporary StringIO for parsing
    from io import StringIO
    sio = StringIO(normalized)

    # Let csv.Sniffer guess delimiter (should be comma now)
    sample = normalized[:8192]
    delimiter = ","
    try:
        from csv import Sniffer
        dialect = Sniffer().sniff(sample)
        delimiter = dialect.delimiter
        logger.info(f"csv.Sniffer detected delimiter: '{delimiter}'")
    except Exception:
        logger.warning("csv.Sniffer could not detect delimiter; defaulting to comma")

    # Use DictReader on normalized content
    sio.seek(0)
    reader = DictReader(sio, delimiter=delimiter)
    # Normalize headers
    if reader.fieldnames:
        reader.fieldnames = [fn.strip().replace("\ufeff", "") for fn in reader.fieldnames]
        logger.info(f"CSV headers (normalized): {reader.fieldnames}")

    rows = []
    for r in reader:
        normalized_row = { (k.strip().replace("\ufeff","") if k else ""): (v.strip() if v is not None else "") for k, v in r.items() }
        rows.append(normalized_row)

    logger.info(f"Found {len(rows)} rows in CSV (after normalization)")
    return rows


def validate_row(row: Dict[str, str], required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate a single CSV row.
    Returns (is_valid, errors)
    """
    errors = []
    for field in required_fields:
        if field not in row or str(row[field]).strip() == "":
            errors.append(f"Missing required field '{field}'")
    # email validation
    email = str(row.get("Email", "")).strip()
    if email == "":
        errors.append("Email is empty")
    elif not EMAIL_REGEX.match(email):
        errors.append(f"Invalid email address: '{email}'")
    return (len(errors) == 0, errors)

def render_template(template: str, row: Dict[str, str]) -> Tuple[str, str]:
    """
    Render the subject and body from the given template using placeholders.
    Template format (simple):
      Subject: {Subject line with placeholders}
      
      {Body with placeholders}
    If the template doesn't have 'Subject:' on the first line, use a default subject.
    Returns (subject, body)
    """
    # Build a safe mapping for placeholders (so missing keys produce empty string)
    safe_row = {k: v for k, v in row.items()}
    # Common placeholders fallback
    for k in ["Name", "Title", "Company", "SNo"]:
        safe_row.setdefault(k, "")

    # If template starts with "Subject:" we parse it
    lines = template.splitlines()
    subject = None
    body = template
    if lines and lines[0].lower().startswith("subject:"):
        subject_line = lines[0][len("subject:"):].strip()
        subject = subject_line.format(**safe_row)
        body = "\n".join(lines[1:]).lstrip()
    else:
        # no explicit subject: use a default
        subject = f"Hello {safe_row.get('Name','')} — Opportunity to connect"

    try:
        body_rendered = body.format(**safe_row)
    except KeyError as e:
        missing = e.args[0]
        logger.warning(f"Template placeholder '{missing}' missing in row; replacing with empty string")
        # Do a safer replace by creating a format map that returns empty for missing keys
        class DefaultDict(dict):
            def __missing__(self, key):
                return ""
        body_rendered = body.format_map(DefaultDict(**safe_row))
    return subject, body_rendered

def load_template(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        logger.info("Template file not found; using built-in default template")
        return (
            "Subject: Connecting about potential opportunities at {Company}\n\n"
            "Hello {Name},\n\n"
            "I hope you're doing well. I'm reaching out because I'm interested in roles"
            " at {Company} that match my background. I saw your profile as {Title} "
            "and thought you'd be the best person to connect with.\n\n"
            "A quick snapshot: I'm a software engineer with experience in Java, Python and cloud technologies.\n\n"
            "I've attached my resume for your review. If appropriate, I'd appreciate 10-15 minutes of your time for a quick chat.\n\n"
            "Thanks,\n"
            "Your Name\n"
            "Email: your.email@example.com\n"
        )

# ---------------------------
# Email sending logic
# ---------------------------

def attach_file_to_message(msg: EmailMessage, filepath: str):
    """
    Attach a binary file to EmailMessage.
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"Attachment not found: {filepath}")
    with open(p, "rb") as f:
        data = f.read()
    maintype = "application"
    subtype = "octet-stream"
    # attempt to set subtype by extension for better compatibility
    if p.suffix.lower() == ".pdf":
        subtype = "pdf"
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)

def send_email(
    gmail_user: str,
    gmail_app_pass: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    dry_run: bool = True,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    max_retries: int = 3,
    retry_backoff: float = 2.0
) -> Tuple[bool, str]:
    """
    Build and (optionally) send an email message via Gmail SMTP.
    Returns (success, message)
    If dry_run=True, does not open SMTP connection but validates everything and prints a preview.
    """
    msg = EmailMessage()
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Attach the resume if present
    if attachment_path:
        try:
            attach_file_to_message(msg, attachment_path)
        except Exception as e:
            return (False, f"Attachment error: {e}")

    # Dry-run: show preview & return
    if dry_run:
        logger.info("----- DRY RUN: EMAIL PREVIEW -----")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        truncated_body = (body[:1000] + "...") if len(body) > 1000 else body
        logger.info(f"Body (first 1000 chars):\n{truncated_body}")
        if attachment_path:
            logger.info(f"Attachment: {attachment_path} (exists: {os.path.exists(attachment_path)})")
        logger.info("----- END PREVIEW -----")
        return (True, "dry-run previewed")

    # Live send: connect to SMTP, with simple retry/backoff
    attempt = 0
    while attempt < max_retries:
        try:
            logger.info(f"Connecting to SMTP {smtp_host}:{smtp_port} (attempt {attempt+1})")
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(gmail_user, gmail_app_pass)
                server.send_message(msg)
            return (True, "sent")
        except (smtplib.SMTPException, socket.error) as e:
            attempt += 1
            if attempt >= max_retries:
                logger.exception("SMTP send failed after retries")
                return (False, f"smtp error after {attempt} attempts: {e}")
            sleep_for = retry_backoff ** attempt
            logger.warning(f"Transient SMTP error: {e}. Retrying in {sleep_for}s...")
            time.sleep(sleep_for)
        except Exception as e:
            logger.exception("Unexpected error during SMTP send")
            return (False, f"unexpected error: {e}")
    return (False, "max retries reached")

# ---------------------------
# Main orchestration
# ---------------------------

def write_log_row(log_path: str, row: Dict[str, str], status: str, message: str):
    """
    Append a row to a CSV log (create file with header if not exists).
    Columns: timestamp, SNo, Name, Email, Company, Title, status, message
    """
    header = ["timestamp", "SNo", "Name", "Email", "Company", "Title", "status", "message"]
    exists = os.path.exists(log_path)
    with open(log_path, "a", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        out = {
            "timestamp": datetime.utcnow().isoformat(),
            "SNo": row.get("SNo", ""),
            "Name": row.get("Name", ""),
            "Email": row.get("Email", ""),
            "Company": row.get("Company", ""),
            "Title": row.get("Title", ""),
            "status": status,
            "message": message
        }
        writer.writerow(out)

def main():
    parser = argparse.ArgumentParser(description="Personalized cold-email sender (Gmail SMTP).")
    parser.add_argument("--csv", "-c", default=DEFAULT_CSV_PATH, help="Path to CSV with contacts")
    parser.add_argument("--resume", "-r", default=DEFAULT_RESUME_PATH, help="Path to resume file to attach")
    parser.add_argument("--template", "-t", default=DEFAULT_TEMPLATE_PATH, help="Path to email template file (optional)")
    parser.add_argument("--send", action="store_true", help="Actually send emails. Default is dry-run (safe).")
    parser.add_argument("--emails-per-minute", type=float, default=20.0, help="Rate limit (emails per minute). Default 20.")
    parser.add_argument("--log", default=DEFAULT_LOG_PATH, help="Path to CSV log file for results")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries for SMTP transient errors")
    parser.add_argument("--config", default=DEFAULT_CONFIG_JSON, help="Optional JSON config path (example provided)")
    args = parser.parse_args()

    # Load environment credentials
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_app_pass = os.environ.get("GMAIL_APP_PASS")
    if args.send:
        if not gmail_user or not gmail_app_pass:
            logger.error("GMAIL_USER and GMAIL_APP_PASS must be set in environment to send emails. Aborting.")
            sys.exit(1)
        else:
            logger.info("Credentials found in environment; live sending enabled.")
    else:
        logger.info("Dry-run mode: no emails will be sent. Use --send to enable live sending (requires credentials).")

    # Load template
    template_text = load_template(args.template)

    # Read CSV
    try:
        rows = read_csv(args.csv)
    except Exception as e:
        logger.exception(f"Failed reading CSV: {e}")
        sys.exit(1)

    required_fields = ["SNo", "Name", "Email", "Title", "Company"]
    total = 0
    sent_count = 0
    failed_count = 0
    skipped_count = 0

    # Rate limiting interval
    emails_per_minute = max(args.emails_per_minute, 0.1)
    interval = 60.0 / emails_per_minute

    logger.info(f"Rate limit: {emails_per_minute} emails/min => {interval:.2f}s between messages")

    for raw_row in rows:
        total += 1
        row = deepcopy(raw_row)  # avoid mutating original
        is_valid, errors = validate_row(row, required_fields)
        if not is_valid:
            skipped_count += 1
            reason = "; ".join(errors)
            logger.warning(f"Skipping row SNo={row.get('SNo','')} Email={row.get('Email','')}: {reason}")
            write_log_row(args.log, row, status="skipped", message=reason)
            continue

        # Render template
        subject, body = render_template(template_text, row)

        # Print a short preview first
        logger.info(f"Preparing message for {row.get('Email')} (SNo {row.get('SNo')})")

        success, message = send_email(
            gmail_user=gmail_user or "dry-run@example.com",
            gmail_app_pass=gmail_app_pass or "",
            to_email=row["Email"],
            subject=subject,
            body=body,
            attachment_path=args.resume if os.path.exists(args.resume) else None,
            dry_run=(not args.send),
            max_retries=args.max_retries
        )

        if success:
            if args.send:
                sent_count += 1
                logger.info(f"Sent to {row['Email']}")
                write_log_row(args.log, row, status="sent", message=message)
            else:
                # dry-run: success just means previewed
                logger.info(f"Dry-run previewed for {row['Email']}")
                write_log_row(args.log, row, status="previewed", message=message)
        else:
            failed_count += 1
            logger.error(f"Failed to send to {row['Email']}: {message}")
            write_log_row(args.log, row, status="failed", message=message)

        # Rate limit between messages
        if total < len(rows):
            logger.debug(f"Sleeping for {interval:.2f}s for rate limiting")
            time.sleep(interval)

    # Summary
    logger.info("------ SUMMARY ------")
    logger.info(f"Total rows processed: {total}")
    logger.info(f"Sent: {sent_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"Log written to: {args.log}")
    logger.info("---------------------")

if __name__ == "__main__":
    main()

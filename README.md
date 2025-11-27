#  Cold Email Automation Tool

A robust Python-based automation tool for sending personalized cold emails with attachments to HR contacts, recruiters, or hiring managers. Built with Gmail SMTP, featuring intelligent CSV parsing, dynamic template rendering, rate limiting, and comprehensive logging.

---

##  Key Features

- ** Personalized Templates**: Dynamically replace placeholders like `{Name}`, `{Company}`, `{Title}`, and `{SNo}` in both subject and body
- ** Safe by Default (Dry-Run Mode)**: Preview emails before sending. Validates CSV, renders templates, and displays a preview without connecting to SMTP
- ** Intelligent CSV Parsing**: 
  - Automatically detects delimiters (comma, tab, whitespace)
  - Uses `csv.Sniffer` for detection with fallback parsing
  - Handles BOM markers, extra whitespace, and normalization
  - Works with `pandas` if installed, falls back to native `csv` module
- ** Attachment Support**: Automatically attaches files (e.g., resume.pdf) to every email
- ** Rate Limiting**: Configurable delay between emails to avoid triggering Gmail's sending limits or spam filters
- ** Detailed Logging**: 
  - Console output with timestamps
  - CSV log file with status for each email (Sent, Failed, Skipped, Previewed)
  - Tracks Name, Email, Company, Title, error messages, and timestamps
- ** Secure Credentials**: Uses environment variables only (no hardcoded passwords)
- ** SMTP Retry Logic**: Automatic retry with exponential backoff for transient network errors
- ** HTML + Plain Text**: Sends emails in both formats with friendly sender name

---

##  Project Structure

```
email-automation/
├── main.py                      # Core automation script (612 lines)
├── email_template.txt           # Sample email template #1
├── new_email_template.txt       # Sample email template #2 (alternate)
├── hr_list.csv                  # Large contact list (1296 rows)
├── sample_hr.csv                # Small sample for testing (7 rows)
├── send_log.csv                 # Generated log file (output)
├── README.md                    # This file
└── .gitattributes               # Git configuration
```

---

##  Setup Guide

### 1. Prerequisites

- **Python 3.7+** installed on your system
- **A Gmail account** (any Gmail address works)
- **Gmail App Password** (not your regular Gmail password)
- **A resume or file to attach** (optional but recommended)

### 2. Generate Gmail App Password

Google no longer supports "Less Secure Apps." You must create an **App Password**:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)
3. Return to Security settings and search for **"App Passwords"**
4. Select **"Mail"** and **"Other (custom name)"**
5. Enter `Email Automation` as the custom name
6. Google will generate a 16-character password like: `abcd efgh ijkl mnop`
7. **Copy this password** (you'll need it for environment variables)

### 3. Installation

Clone or download the repository:

```bash
git clone https://github.com/Subhasis19/email-automation.git
cd email-automation
```

(Optional) Install `pandas` for better CSV handling on large files:

```bash
pip install pandas
```

> Note: The script runs fine without pandas; it's optional for optimization.

### 4. Configure Environment Variables

** Never hardcode credentials in the script.** Always use environment variables.

#### Windows (PowerShell) - Recommended

```powershell
$env:GMAIL_USER="your.email@gmail.com"
$env:GMAIL_APP_PASS="abcd efgh ijkl mnop"
```

#### Windows (Command Prompt)

```cmd
set GMAIL_USER=your.email@gmail.com
set GMAIL_APP_PASS=abcd efgh ijkl mnop
```

#### macOS / Linux

```bash
export GMAIL_USER="your.email@gmail.com"
export GMAIL_APP_PASS="abcd efgh ijkl mnop"
```

**To make these permanent** (macOS/Linux), add to `~/.bashrc` or `~/.zshrc`.

### 5. Prepare Your Data

#### CSV File Format

Your CSV must have these headers (case-sensitive): `SNo`, `Name`, `Email`, `Title`, `Company`

Example (`sample_hr.csv`):

```csv
SNo,Name,Email,Title,Company
1,John Smith,john@example.com,Head of Talent,ExampleCorp
2,Jane Doe,jane@example.com,Technical Recruiter,TechCorp
3,Bob Wilson,bob@example.com,HR Manager,InnovateTech
```

The CSV parser:
- Automatically detects comma or tab delimiters
- Strips extra whitespace
- Handles UTF-8 BOM markers
- Validates required fields (skips incomplete rows)

#### Email Template Format

Create a text file (e.g., `email_template.txt`) with:
- **Line 1**: `Subject: {Your subject with placeholders}`
- **Lines 2+**: Email body (plain text, can use HTML-like breaks)

Example (`new_email_template.txt`):

```
Subject: Quick question about {Company} — {Name}

Hello {Name},

I hope you're doing well. I came across your profile and wanted to reach out 
regarding potential opportunities at {Company}.

I'm a Computer Science graduate with hands-on experience in Software Development 
and skills in Java, JavaScript, SQL, and Cloud Computing.

I've attached my resume for your kind review. If possible, I'd appreciate 
a brief 10–15 minute conversation.

Warm regards,
Subhasis Samantasinghar
Email: subhasissamantasinghar1@gmail.com
```

**Available placeholders:**
- `{SNo}` — Row number from CSV
- `{Name}` — Contact name
- `{Email}` — Contact email
- `{Title}` — Job title
- `{Company}` — Company name

#### File to Attach

Ensure your attachment exists:

```bash
ls resume.pdf   # macOS/Linux
dir resume.pdf  # Windows
```

---

##  Usage Guide

### Dry-Run Mode (Preview) — START HERE!

By default, the script previews emails without sending:

```bash
python main.py --csv sample_hr.csv --resume resume.pdf --template new_email_template.txt
```

**Output:**
- Console preview of each email (first 1000 characters)
- Log file created with status "previewed"
- No SMTP connection; no emails sent
- Safe to test multiple times

### Live Sending

Once you're confident, enable sending with `--send`:

```bash
python main.py --send --csv hr_list.csv --resume resume.pdf --template new_email_template.txt
```

**Output:**
- Connects to Gmail SMTP (`smtp.gmail.com:587`)
- Authenticates with your App Password
- Sends personalized emails with attachments
- Creates/appends to `send_log.csv` with status "sent" or "failed"

### Custom Rate Limiting

Default: 20 emails/minute (3-second interval). Adjust with `--emails-per-minute`:

```bash
# Send 5 emails per minute (safer for large campaigns)
python main.py --send --csv hr_list.csv --emails-per-minute 5

# Send 1 email per minute (very conservative)
python main.py --send --csv hr_list.csv --emails-per-minute 1

# Send 60 emails per minute (aggressive; NOT recommended)
python main.py --send --csv hr_list.csv --emails-per-minute 60
```

### Common Commands

| Purpose | Command |
|---------|---------|
| **Test with sample data** | `python main.py --csv sample_hr.csv` |
| **Dry-run with full list** | `python main.py --csv hr_list.csv` |
| **Live send (slow & safe)** | `python main.py --send --csv hr_list.csv --emails-per-minute 5` |
| **Check log** | `cat send_log.csv` (or open in Excel) |
| **Resume interrupted campaign** | `python main.py --send --csv hr_list.csv` (continues from next row) |

---

##  Command-Line Options

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--csv` | `-c` | str | `hr_list.csv` | Path to contact list CSV |
| `--resume` | `-r` | str | `resume.pdf` | Path to file to attach |
| `--template` | `-t` | str | `new_email_template.txt` | Path to email template |
| `--send` | — | bool | False | Enable live sending (dry-run by default) |
| `--emails-per-minute` | — | float | 20.0 | Rate limit (emails per minute) |
| `--log` | — | str | `send_log.csv` | Path to output log file |
| `--max-retries` | — | int | 3 | SMTP retry attempts for transient errors |
| `--config` | — | str | `config.example.json` | (Optional) JSON config file path |

### Example: Full Configuration

```bash
python main.py \
  --csv hr_list.csv \
  --resume resume.pdf \
  --template new_email_template.txt \
  --send \
  --emails-per-minute 10 \
  --log my_campaign_log.csv \
  --max-retries 5
```

---

## 📋 Log File Format

After running, `send_log.csv` contains:

| Column | Example | Possible Values |
|--------|---------|-----------------|
| `timestamp` | `2025-11-27T14:32:45.123456` | ISO 8601 format |
| `SNo` | `1` | Row number from CSV |
| `Name` | `John Smith` | Contact name |
| `Email` | `john@example.com` | Contact email |
| `Company` | `ExampleCorp` | Company name |
| `Title` | `Head of Talent` | Job title |
| `status` | `sent` | `sent`, `failed`, `skipped`, `previewed` |
| `message` | `"SMTP 250 OK"` | Status details or error message |

### Log Status Meanings

- **`sent`** — Email successfully handed off to Gmail SMTP (doesn't guarantee delivery)
- **`failed`** — SMTP error (auth failed, network error, etc.)
- **`skipped`** — Row missing required data (Name, Email, Title, Company, or invalid email format)
- **`previewed`** — Email previewed in dry-run mode (not sent)

---

##  Important Notes & Best Practices

### Gmail Sending Limits

- **Free Gmail**: ~500 emails/day limit
- **Exceeding the limit**: Account locked for 24 hours
- **Recommended**: Send 50-100 emails/day to stay safe

### Spam Filters

- **Identical emails**: Trigger spam filters. Customize `{Company}` and `{Name}` in templates
- **Attachments**: Large files increase spam risk. Keep resumes under 2MB
- **Rate limiting**: Critical. Don't send >30 emails/minute
- **Warm-up**: Start with 10 emails/day for first week

### Authentication Issues

If you get `SMTPAuthenticationError`:
1. Verify `GMAIL_USER` and `GMAIL_APP_PASS` are set correctly
2. Ensure you're using an **App Password**, not your Gmail password
3. Check that 2-Step Verification is enabled on your Google Account
4. Try generating a new App Password

### Network Errors

The script automatically retries transient errors (timeouts, connection resets) with exponential backoff:
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds

### CSV Parsing Issues

If your CSV isn't parsing correctly:
1. Check for UTF-8 BOM markers (use "Save as UTF-8" in Excel)
2. Ensure headers are in row 1: `SNo,Name,Email,Title,Company`
3. Test with `sample_hr.csv` first
4. The script logs the detected delimiter: check console output

---

##  Troubleshooting

### "GMAIL_USER and GMAIL_APP_PASS must be set in environment"

**Solution**: Set environment variables before running the script:

**PowerShell:**
```powershell
$env:GMAIL_USER="your.email@gmail.com"
$env:GMAIL_APP_PASS="abcd efgh ijkl mnop"
python main.py --send --csv hr_list.csv
```

**Command Prompt:**
```cmd
set GMAIL_USER=your.email@gmail.com
set GMAIL_APP_PASS=abcd efgh ijkl mnop
python main.py --send --csv hr_list.csv
```

### "CSV file not found"

**Solution**: Provide the correct path:

```bash
python main.py --csv /full/path/to/hr_list.csv
```

Or ensure the CSV is in the same directory as `main.py`.

### "Attachment not found"

**Solution**: Verify the file exists:

```bash
ls resume.pdf        # macOS/Linux
dir resume.pdf       # Windows
```

Or use a relative path:

```bash
python main.py --resume ./resume.pdf --csv hr_list.csv
```

### "Invalid email address: john@example"

**Reason**: The email is malformed.

**Solution**: Fix the CSV and re-run.

### "SMTP error after 3 attempts: [Errno 110] Connection timed out"

**Reason**: Network issue or Gmail blocking the connection.

**Solutions**:
- Increase retry attempts: `--max-retries 5`
- Reduce rate limit: `--emails-per-minute 5`
- Try again later (Gmail might be throttling)
- Check your internet connection

### "SMTPAuthenticationError: invalid username or password"

**Solution**:
1. Double-check your App Password (it's 16 characters with spaces)
2. Verify it's an App Password, not your Gmail password
3. Generate a new App Password in Google Account settings

---

##  Security Best Practices

1. **Never commit credentials** to Git:
   ```bash
   echo "GMAIL_USER=..." >> .bashrc  # Add to shell profile, not files
   ```

2. **Use `.gitignore`** to exclude sensitive files:
   ```
   send_log.csv
   .env
   config.json
   resume.pdf
   ```

3. **Rotate App Passwords** periodically in Google Account settings

4. **Use a dedicated Gmail account** for automation (consider a separate email)

5. **Monitor logs** for suspicious activity:
   ```bash
   tail -f send_log.csv
   ```

---

##  Code Overview

### Main Functions

| Function | Purpose |
|----------|---------|
| `read_csv()` | Robust CSV parsing with delimiter detection |
| `validate_row()` | Validates required fields and email format |
| `render_template()` | Replaces placeholders with row data |
| `load_template()` | Loads template from file or uses built-in default |
| `send_email()` | Builds MIME message and sends via SMTP |
| `attach_file_to_message()` | Attaches binary files to email |
| `write_log_row()` | Appends result to CSV log |
| `main()` | Orchestrates CSV reading, validation, rendering, and sending |

### Key Implementation Details

- **Email Format**: Sends MIME multipart with plain text + HTML alternatives
- **Rate Limiting**: Uses `time.sleep()` between emails
- **SMTP Retry**: Exponential backoff (2^attempt seconds)
- **Logging**: Console output with timestamps + CSV log file
- **Validation**: Regex email check + required field verification

---

##  Example Workflow

1. **Prepare files:**
   ```bash
   # Ensure these exist
   ls main.py sample_hr.csv resume.pdf new_email_template.txt
   ```

2. **Set credentials (PowerShell):**
   ```powershell
   $env:GMAIL_USER="subhasissamantasinghar1@gmail.com"
   $env:GMAIL_APP_PASS="abcd efgh ijkl mnop"
   ```

3. **Dry-run with sample data:**
   ```bash
   python main.py --csv sample_hr.csv --resume resume.pdf --template new_email_template.txt
   ```

4. **Review console output** for email previews

5. **Check `send_log.csv`** for status

6. **If good, send 5 emails as a test:**
   ```bash
   python main.py --send --csv sample_hr.csv --emails-per-minute 5
   ```

7. **Check email accounts** to verify delivery

8. **Send full campaign (slow):**
   ```bash
   python main.py --send --csv hr_list.csv --emails-per-minute 5
   ```

9. **Monitor progress:**
   ```bash
   tail -f send_log.csv  # Watch log updates in real-time
   ```

---

##  Advanced Usage

### Resume Interrupted Campaign

If the script crashes or you stop it mid-sending:

```bash
# Simply run again; it appends to send_log.csv
# (You may want to filter CSV to remove already-sent rows)
python main.py --send --csv hr_list.csv
```

### Filter Already-Sent Contacts

Use pandas or your preferred tool:

```python
import pandas as pd

log = pd.read_csv("send_log.csv")
sent_emails = log[log["status"] == "sent"]["Email"].tolist()

df = pd.read_csv("hr_list.csv")
remaining = df[~df["Email"].isin(sent_emails)]
remaining.to_csv("hr_list_remaining.csv", index=False)
```

Then run with the new CSV:

```bash
python main.py --send --csv hr_list_remaining.csv --emails-per-minute 5
```

### Multiple Campaigns

Create separate templates and CSVs:

```bash
python main.py --send --csv cohort_1.csv --template template_1.txt --log log_cohort_1.csv
python main.py --send --csv cohort_2.csv --template template_2.txt --log log_cohort_2.csv
```

---

##  License

This project is provided as-is. Use responsibly and respect email recipients' preferences.

---

##  Contributing

Found a bug? Have a feature request? Submit an issue or PR on [GitHub](https://github.com/Subhasis19/email-automation).

---

##  Contact

**Author:** Subhasis Samantasinghar  
**Email:** asubhasis2002@gmail.com  
**LinkedIn:** https://www.linkedin.com/in/subhasis-samantasinghar/

---

**Happy emailing! 🚀**
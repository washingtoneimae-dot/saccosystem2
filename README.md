# SACCO Member Statement System

Automated SACCO member statement generation, Excel export, and email delivery.

**Zero pip packages.** Pure Python stdlib + Himalaya CLI for email.

---

## Quick Start

### Linux / WSL
```bash
git clone https://github.com/YOUR_USER/sacco-system.git
cd sacco-system
bash install.sh
sacco
# Open http://127.0.0.1:9150/dashboard
```

### Windows
```
Unzip → double-click SACCO.bat → browser opens at http://127.0.0.1:9160/dashboard
```

---

## Architecture

```
Browser ──► api_server.py ──► sacco.db (SQLite)
                │
                ├── compute.py       ← Running balances + auto-interest
                ├── generate_xlsx.py ← Excel (.xlsx) in Norken SACCO format
                ├── render.py        ← HTML email body
                ├── dashboard_template.html ← UI (designer-friendly)
                └── dashboard.js     ← Frontend logic
```

Email is sent via **Himalaya CLI** → Gmail SMTP (app password auth).

---

## Requirements

| Dependency | Minimum | Check |
|------------|---------|-------|
| Python | 3.7+ | `python3 --version` |
| Himalaya CLI | 1.0+ | `himalaya --version` (for email only) |

No pip packages needed. Everything uses Python's standard library.

---

## Features

### Dashboard
- **Add Transaction** — contribution, loan disbursement, loan repayment, share purchase, registration, refund
- **Add Member** — with DOB, joined date, member number
- **Members Table** — click name to view/edit transactions
- **Edit/Delete** — members and individual transactions
- **Send Statements** — emails all members with Excel attachments (background)
- **Download ZIP** — download all statements as `.xlsx` files (no email)
- **Email Settings** — configure sender, app password, interest rate from UI
- **Test Email** — verify credentials work before sending
- **Activity Log** — view last activity timestamps
- **Close System** — shuts down the server remotely

### Auto Interest Calculation
- Monthly interest = `interest_rate% × outstanding loan balance`
- Interest is **added to the loan balance** each month
- Rate configurable in Settings (default 1%, validated 0-100)
- No manual `interest_charge` transaction needed

### Excel Statements
- Matches Norken SACCO format (from original Excel)
- Running totals: Total Deposit, Loan Balance, Total Interest
- Month names (e.g. "Dec 2021") instead of Excel serial dates
- Number format: `#,##0.00` for comma display
- Column layout: MONTH, Total pay, SHARE, REG., Refund, Contribution, Total Deposit, Loan granted, Loan repaid, Loan Balance, Interest/mo, Total interest

---

## File Structure

| File | What it does | Designer-safe? |
|------|-------------|----------------|
| `api_server.py` | HTTP server, routes, DB ops, email, template loading | ❌ |
| `compute.py` | Running balance + interest calculation per member | ❌ |
| `render.py` | HTML email body with member summary | ❌ |
| `generate_xlsx.py` | Norken-format Excel via raw ZIP/XML | ❌ |
| `dashboard_template.html` | All HTML + CSS | ✅ Edit freely |
| `dashboard.js` | All frontend JavaScript | ✅ Edit freely |
| `SACCO.bat` | Windows: double-click to start | ❌ |
| `sacco.ps1` | Windows: PowerShell start | ❌ |
| `sacco-stop.ps1` | Windows: PowerShell stop | ❌ |
| `install.sh` | Linux: deps check + command install | ❌ |
| `sacco.db` | SQLite database (auto-created if missing) | ❌ |

### For Designers
Edit `dashboard_template.html` and `dashboard.js` only. Keep these intact:
- `{member_opts}`, `{member_table}`, `{type_opts}`, `{today}` — dynamic placeholders
- `{settings.get('...')}` — settings value placeholders
- Element `id`s referenced in `dashboard.js`
- `onclick` handler names

---

## API Endpoints

All POST to `http://127.0.0.1:9150/` (WSL) or `9160` (Windows):

| Endpoint | Purpose |
|----------|---------|
| `/add_member` | Create member |
| `/add_tx` | Add transaction |
| `/member_tx` | List member's transactions |
| `/edit_member` | Update member field |
| `/edit_tx` | Update transaction |
| `/delete_member` | Remove member + all their data |
| `/delete_tx` | Remove single transaction |
| `/compute_all` | Get all members' statement data |
| `/generate_statement` | Generate single Excel |
| `/download_all_statements` | Download ZIP of all Excel files |
| `/send_all_statements` | Email statements (background) |
| `/get_settings` | Get all settings |
| `/update_settings` | Save settings |
| `/get_activity` | Last activity timestamps |
| `/check_registration` | Check if member has registration |
| `/test_email_settings` | Send test email |
| `/shutdown` | Stop the server |

---

## Database

Auto-created on first run. Tables:

- **members** — id, name, email, phone, member_number, joined_date, dob
- **transactions** — id, member_id, date, type, amount, description
- **statements_sent** — log of sent emails
- **settings** — key/value config (sender, interest rate, etc.)

---

## Security

- SQL queries use parameterized `?` placeholders (no injection)
- Shell commands use list args (no shell injection)
- HTML output escapes `<script>` etc. via `html.escape()`
- Interest rate validated as number between 0-100
- Only accessible on localhost (127.0.0.1)

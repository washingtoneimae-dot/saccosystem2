#!/usr/bin/env python3
"""SACCO API server — serves dashboard, handles DB operations, generates Excel, sends email."""
import json, uuid, sys, os, subprocess, tempfile, base64, traceback, html
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import sqlite3

DB = os.path.join(os.path.dirname(__file__) or '.', 'sacco.db')

def _ensure_schema(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            member_number TEXT UNIQUE,
            joined_date TEXT, dob TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL REFERENCES members(id),
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            evidence_path TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_transactions_member ON transactions(member_id, date);
        CREATE TABLE IF NOT EXISTS statements_sent (
            id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL REFERENCES members(id),
            sent_date TEXT NOT NULL DEFAULT (datetime('now')),
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
    ''')
    # Seed default settings (INSERT OR IGNORE preserves user changes)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    defaults = [
        ('sender_name', 'Norken SACCO'),
        ('sender_email', 'name@gmail.com'),
        ('gmail_app_password', ''),
        ('society_name', 'NORKEN SACCO SOCIETY LIMITED'),
        ('account_type', 'MEMBER PERSONAL ACCOUNT'),
        ('interest_rate', '1'),
    ]
    conn.executemany(
        'INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)',
        [(k, v, now) for k, v in defaults]
    )
    conn.commit()

class Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _html(self, content, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(content.encode())

    def _binary(self, data, filename, mime='application/zip'):
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _connect(self):
        conn = sqlite3.connect(DB, timeout=10)
        conn.row_factory = sqlite3.Row
        _ensure_schema(conn)
        return conn

    def do_GET(self):
        try:
            if self.path == '/dashboard':
                self._html(self._dashboard_html())
            elif self.path == '/':
                self._html('<html><body><h1>SACCO API Server</h1><p><a href="/dashboard">Dashboard</a></p></body></html>')
            elif self.path == '/dashboard.js':
                with open(os.path.join(os.path.dirname(__file__) or '.', 'dashboard.js'), encoding='utf-8') as f:
                    js = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/javascript')
                self.send_header('Content-Length', str(len(js.encode())))
                self.end_headers()
                self.wfile.write(js.encode())
            elif self.path.startswith('/download_evidence'):
                self._download_evidence()
            elif self.path == '/download_all_statements':
                self._download_all_statements()
            else:
                self._json({'error': 'not found'}, 404)
        except Exception as e:
            self._json({'error': str(e), 'traceback': traceback.format_exc()}, 500)

    def do_POST(self):
        try:
            cl = int(self.headers.get('Content-Length', 0))
            raw_body = {}
            if cl > 0:
                raw = self.rfile.read(cl)
                raw_body = json.loads(raw) if raw else {}
            body = raw_body.get('body', raw_body) if isinstance(raw_body, dict) else raw_body

            routes = {
                '/compute_all': lambda: self._compute_all(),
                '/get_members': lambda: self._get_members(),
                '/render_members': lambda: self._get_members(),
                '/add_tx': lambda: self._add_tx(body),
                '/edit_member': lambda: self._edit_member(body),
                '/add_member': lambda: self._add_member(body),
                '/member_tx': lambda: self._member_tx(body),
                '/check_registration': lambda: self._check_registration(body),
                '/delete_tx': lambda: self._delete_tx(body),
                '/upload_evidence': lambda: self._upload_evidence(body),
                '/edit_tx': lambda: self._edit_tx(body),
                '/delete_member': lambda: self._delete_member(body),
                '/log_statement': lambda: self._log_statement(body),
                '/send_email': lambda: self._send_email(body),
                '/generate_statement': lambda: self._generate_statement(body),
                '/send_email_with_attachment': lambda: self._send_email_with_attachment(body),
                '/send_all_statements': lambda: self._send_all_statements(),
                '/get_settings': lambda: self._get_settings(),
                '/get_activity': lambda: self._get_activity(),
                '/update_settings': lambda: self._update_settings(body),
                '/test_email_settings': lambda: self._test_email_settings(body),
                '/shutdown': lambda: self._shutdown(),
            }
            handler = routes.get(self.path)
            if handler:
                self._json(handler())
            else:
                self._json({'error': 'not found'}, 404)
        except Exception as e:
            self._json({'error': str(e), 'traceback': traceback.format_exc()}, 500)

    def _get_members(self):
        conn = self._connect()
        members = [dict(r) for r in conn.execute('SELECT * FROM members ORDER BY member_number')]
        conn.close()
        rows = ''
        for m in members:
            rows += f'<tr><td style="padding:4px 8px;border-bottom:1px solid #eee;">{m["name"]}</td><td>{m.get("member_number","")}</td><td>{m.get("email","")}</td></tr>'
        return {'html': rows, 'count': len(members)}

    def _add_tx(self, body):
        mid, date, tx_type, amt = body['member_id'], body['date'], body['type'], float(body['amount'])
        desc = body.get('description', '')
        evidence = body.get('evidence_path', '')
        conn = self._connect()
        tx_id = str(uuid.uuid4())
        conn.execute('INSERT INTO transactions (id,member_id,date,type,amount,description,evidence_path) VALUES (?,?,?,?,?,?,?)', (tx_id, mid, date, tx_type, amt, desc, evidence))
        conn.commit(); conn.close()
        return {'status':'ok', 'tx_id':tx_id, 'member_id':mid, 'type':tx_type, 'amount':amt}

    def _edit_member(self, body):
        mid, field, value = body['member_id'], body['field'], body['value']
        allowed = {'name','email','phone','member_number','dob'}
        if field not in allowed:
            return {'status':'error','message':f'Invalid: {field}'}
        conn = self._connect()
        conn.execute(f'UPDATE members SET {field}=? WHERE id=?', (value, mid))
        conn.commit(); conn.close()
        return {'status':'ok', 'member_id':mid, 'field':field, 'value':value}

    def _add_member(self, body):
        mid, name = body['member_id'], body['name']
        email, phone = body.get('email',''), body.get('phone','')
        num = body.get('member_number','')
        joined = body.get('joined_date', datetime.now().strftime('%Y-%m-%d'))
        dob = body.get('dob', '')
        conn = self._connect()
        conn.execute('INSERT INTO members (id,name,email,phone,member_number,joined_date,dob) VALUES (?,?,?,?,?,?,?)', (mid, name, email, phone, num, joined, dob))
        conn.commit(); conn.close()
        return {'status':'ok','member_id':mid}

    def _member_tx(self, body):
        mid = body['member_id']
        tx_type = body.get('filter_type', '')
        amt_min = body.get('filter_amt_min', '')
        amt_max = body.get('filter_amt_max', '')
        date_from = body.get('filter_date_from', '')
        date_to = body.get('filter_date_to', '')
        query = 'SELECT * FROM transactions WHERE member_id=?'
        params = [mid]
        if tx_type:
            query += ' AND type=?'
            params.append(tx_type)
        if amt_min:
            query += ' AND amount>=?'
            params.append(float(amt_min))
        if amt_max:
            query += ' AND amount<=?'
            params.append(float(amt_max))
        if date_from:
            query += ' AND date>=?'
            params.append(date_from)
        if date_to:
            query += ' AND date<=?'
            params.append(date_to)
        query += ' ORDER BY date DESC'
        conn = self._connect()
        txs = [dict(r) for r in conn.execute(query, params)]
        conn.close()
        rows = ''
        for tx in txs:
            pdf_icon = ''
            if tx['type'] == 'loan_disbursement':
                pdf_icon = f' <a href="/download_evidence?tx_id={tx["id"]}" style="text-decoration:none;" title="Download evidence PDF">📄</a>'
            rows += f'<tr id="txrow-{tx["id"]}"><td>{tx["date"]}</td><td>{tx["type"]}</td><td style="text-align:right;">KES {tx["amount"]:,.0f}</td><td><button class="edit-btn" onclick="editTx(\'{tx["id"]}\',\'{tx["date"]}\',\'{tx["type"]}\',\'{tx["amount"]}\',\'{tx.get("description","")}\')">Edit</button>{pdf_icon}</td></tr>'
        return {'html':rows, 'member_id':mid, 'count':len(txs)}

    def _check_registration(self, body):
        mid = body.get('member_id', '')
        conn = self._connect()
        count = conn.execute("SELECT COUNT(*) FROM transactions WHERE member_id=? AND type='registration'", (mid,)).fetchone()[0]
        conn.close()
        return {'has_registration': count > 0, 'count': count}

    def _delete_tx(self, body):
        conn = self._connect()
        conn.execute('DELETE FROM transactions WHERE id=?', (body['tx_id'],))
        conn.commit(); conn.close()
        return {'status':'ok','deleted':True}

    def _edit_tx(self, body):
        tx_id = body['tx_id']
        conn = self._connect()
        updates = []
        vals = []
        for field in ['date', 'type', 'amount', 'description']:
            if field in body:
                updates.append(f'{field}=?')
                vals.append(body[field])
        if updates:
            vals.append(tx_id)
            conn.execute(f'UPDATE transactions SET {",".join(updates)} WHERE id=?', vals)
            conn.commit()
        conn.close()
        return {'status':'ok', 'tx_id':tx_id}

    def _delete_member(self, body):
        mid = body['member_id']
        conn = self._connect()
        conn.execute('DELETE FROM transactions WHERE member_id=?', (mid,))
        conn.execute('DELETE FROM statements_sent WHERE member_id=?', (mid,))
        conn.execute('DELETE FROM members WHERE id=?', (mid,))
        conn.commit()
        conn.close()
        return {'status':'ok', 'deleted': mid}

    def _get_settings(self):
        conn = self._connect()
        rows = conn.execute('SELECT key, value FROM settings ORDER BY key').fetchall()
        conn.close()
        return {r['key']: r['value'] for r in rows}

    def _get_activity(self):
        conn = self._connect()
        last_tx = conn.execute('SELECT MAX(created_at) FROM transactions').fetchone()[0]
        last_member = conn.execute('SELECT MAX(created_at) FROM members').fetchone()[0]
        last_sent = conn.execute('SELECT MAX(sent_date) FROM statements_sent').fetchone()[0]
        last_settings = conn.execute('SELECT MAX(updated_at) FROM settings').fetchone()[0]
        tx_count = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        member_count = conn.execute('SELECT COUNT(*) FROM members').fetchone()[0]
        sent_count = conn.execute('SELECT COUNT(*) FROM statements_sent').fetchone()[0]
        conn.close()
        return {
            'last_transaction': last_tx or 'Never',
            'last_member': last_member or 'Never',
            'last_statement_sent': last_sent or 'Never',
            'last_settings_update': last_settings or 'Never',
            'total_transactions': tx_count,
            'total_members': member_count,
            'total_statements_sent': sent_count,
        }

    def _update_settings(self, body):
        # Validate interest_rate
        if 'interest_rate' in body:
            try:
                rate = float(body['interest_rate'])
                if rate < 0 or rate > 100:
                    return {'status': 'error', 'message': 'Interest rate must be between 0 and 100'}
            except (ValueError, TypeError):
                return {'status': 'error', 'message': 'Interest rate must be a number'}
        conn = self._connect()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for key, value in body.items():
            conn.execute('INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, str(value), now))
        conn.commit()
        conn.close()
        
        # If email settings changed, update the Himalaya config
        if any(k in body for k in ['sender_email', 'sender_name', 'gmail_app_password']):
            self._write_himalaya_config(body)
        
        return {'status': 'ok'}

    def _write_himalaya_config(self, updates):
        """Write the Himalaya email config file from current settings + provided updates."""
        conn = self._connect()
        rows = dict(conn.execute('SELECT key, value FROM settings').fetchall())
        conn.close()
        # Merge with updates (so we use the latest values even before they're saved)
        for k, v in updates.items():
            rows[k] = str(v)
        
        email = rows.get('sender_email', 'washingtoneimae@gmail.com')
        name = rows.get('sender_name', 'SACCO')
        password = rows.get('gmail_app_password', '')
        
        config = f'''[accounts.personal]
email = "{email}"
display-name = "{name}"
default = true

backend.type = "imap"
backend.host = "imap.gmail.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "{email}"
backend.auth.type = "password"
backend.auth.cmd = "echo {password}"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.gmail.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "{email}"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "echo {password}"

folder.aliases.inbox = "INBOX"
folder.aliases.sent = "[Gmail]/Sent Mail"
folder.aliases.drafts = "[Gmail]/Drafts"
folder.aliases.trash = "[Gmail]/Trash"
'''
        try:
            os.makedirs(os.path.expanduser('~/.config/himalaya'), exist_ok=True)
            with open(os.path.expanduser('~/.config/himalaya/config.toml'), 'w') as f:
                f.write(config)
        except Exception as e:
            print(f'Warning: could not write Himalaya config: {e}')

    def _upload_evidence(self, body):
        tx_id = body.get('tx_id', '')
        b64_data = body.get('file_data', '')
        if not tx_id or not b64_data:
            return {'status': 'error', 'message': 'Missing tx_id or file_data'}
        ev_dir = os.path.join(os.path.dirname(__file__) or '.', 'evidence')
        os.makedirs(ev_dir, exist_ok=True)
        filepath = os.path.join(ev_dir, f'{tx_id}.pdf')
        try:
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(b64_data))
            conn = self._connect()
            # Store relative path so it works if folder is moved
            rel_path = f'evidence/{tx_id}.pdf'
            conn.execute('UPDATE transactions SET evidence_path=? WHERE id=?', (rel_path, tx_id))
            conn.commit()
            conn.close()
            return {'status': 'ok', 'path': filepath}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _download_evidence(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        tx_id = params.get('tx_id', [None])[0]
        if not tx_id:
            self._json({'error': 'Missing tx_id'}, 400)
            return
        conn = self._connect()
        row = conn.execute('SELECT evidence_path FROM transactions WHERE id=?', (tx_id,)).fetchone()
        conn.close()
        if not row or not row['evidence_path']:
            self._json({'error': 'No evidence file found'}, 404)
            return
        # Resolve relative path
        ev_path = row['evidence_path']
        if not os.path.isabs(ev_path):
            ev_path = os.path.join(os.path.dirname(__file__) or '.', ev_path)
        if not os.path.exists(ev_path):
            self._json({'error': 'No evidence file found'}, 404)
            return
        with open(ev_path, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'application/pdf')
        self.send_header('Content-Disposition', f'attachment; filename="evidence_{tx_id}.pdf"')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _log_statement(self, body):
        mid = body['member_id']
        ps = body.get('period_start','2021-01-01')
        pe = body.get('period_end','2026-06-30')
        conn = self._connect()
        conn.execute('INSERT INTO statements_sent (id,member_id,sent_date,period_start,period_end) VALUES (?,?,datetime("now"),?,?)', (str(uuid.uuid4()), mid, ps, pe))
        conn.commit(); conn.close()
        return {'status':'ok'}

    def _get_sender(self):
        """Return (sender_name, sender_email) from settings."""
        conn = self._connect()
        name = conn.execute("SELECT value FROM settings WHERE key='sender_name'").fetchone()
        email = conn.execute("SELECT value FROM settings WHERE key='sender_email'").fetchone()
        conn.close()
        return (name['value'] if name else 'SACCO', email['value'] if email else 'sacco@localhost')

    def _test_email_settings(self, body):
        """Send a test email to verify settings work."""
        sname, semail = self._get_sender()
        to = body.get('to', semail)
        if not to:
            return {'status': 'error', 'message': 'No recipient email'}
        test_body = f'<div style="font-family:Arial;padding:20px;"><h2>Test Email</h2><p>This is a test from the SACCO system.</p><p><strong>Sender:</strong> {sname} &lt;{semail}&gt;</p><p>If you received this, your email settings are working.</p></div>'
        raw = f'From: {sname} <{semail}>\r\nTo: {to}\r\nSubject: SACCO Email Test\r\nMIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n{test_body}'
        import tempfile, subprocess
        tmp = os.path.join(tempfile.gettempdir(), 'sacco_test_email.eml')
        with open(tmp, 'w') as f: f.write(raw)
        try:
            r = subprocess.run(['himalaya', 'message', 'send'], input=raw, text=True, capture_output=True, timeout=30)
            try: os.unlink(tmp)
            except: pass
            if r.returncode == 0:
                return {'status': 'ok', 'sent_to': to, 'sender': semail}
            else:
                err = r.stderr.strip() or r.stdout.strip() or f'exit code {r.returncode}'
                return {'status': 'error', 'message': err}
        except Exception as e:
            try: os.unlink(tmp)
            except: pass
            return {'status': 'error', 'message': str(e)}

    def _send_email(self, body):
        email = body.get('email','')
        html = body.get('html_body','')
        subj = body.get('subject','Statement')
        mid = body.get('member_id','')
        sname, semail = self._get_sender()
        raw = f'From: {sname} <{semail}>\r\nTo: {email}\r\nSubject: {subj}\r\nMIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n{html}'
        tmp = os.path.join(tempfile.gettempdir(), f'sacco_{mid}.eml')
        with open(tmp,'w') as f: f.write(raw)
        try:
            r = subprocess.run(['himalaya','message','send'], input=raw, text=True, capture_output=True, timeout=30)
            try: os.unlink(tmp)
            except: pass
            if r.returncode == 0:
                return {'status':'ok','sent':True,'to':email}
            else:
                err = r.stderr.strip() or r.stdout.strip() or f'exit {r.returncode}'
                return {'status':'error','message':err, 'to':email}
        except Exception as e:
            try: os.unlink(tmp)
            except: pass
            return {'status':'error','message':str(e)}

    def _generate_statement(self, body):
        sys.path.insert(0, os.path.dirname(__file__) or '.')
        from compute import compute_statement
        from generate_xlsx import generate_xlsx
        member_id = body.get('member_id', 'm001')
        data = compute_statement(member_id)
        if not data:
            return {'status': 'error', 'message': 'Member not found'}
        # Get DOB from database
        conn = self._connect()
        dob_row = conn.execute("SELECT dob FROM members WHERE id=?", (member_id,)).fetchone()
        dob = dob_row['dob'] if dob_row and dob_row['dob'] else ''
        conn.close()
        out = os.path.join(tempfile.gettempdir(), f'sacco_statement_{member_id}.xlsx')
        generate_xlsx(data['member']['name'], data['member']['member_number'], data['rows'], data['summary'], out, dob)
        return {
            'status': 'ok', 'xlsx_path': out, 'member_id': member_id,
            'email': data['member']['email'], 'name': data['member']['name'],
            'member_number': data['member']['member_number'],
            'subject': f"Your SACCO Account Statement - {datetime.now().strftime('%B %Y')}",
            'savings_balance': data['summary']['current_savings'],
            'loan_balance': data['summary']['current_loan'],
        }

    def _send_email_with_attachment(self, body):
        xlsx_path = body.get('xlsx_path', '')
        if not xlsx_path or not os.path.exists(xlsx_path):
            return self._send_email(body)
        email = body.get('email','')
        html = body.get('html_body','')
        subj = body.get('subject','Statement')
        mid = body.get('member_id','')
        sname, semail = self._get_sender()
        with open(xlsx_path, 'rb') as f:
            xlsx_b64 = base64.b64encode(f.read()).decode()
        mime = f'''From: {sname} <{semail}>
To: {email}
Subject: {subj}
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="=_sacco_boundary_"

--=_sacco_boundary_
Content-Type: text/html; charset=UTF-8

{html}
--=_sacco_boundary_
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="SACCO_Statement_{mid}.xlsx"
Content-Transfer-Encoding: base64

{xlsx_b64}
--=_sacco_boundary_--'''
        tmp = os.path.join(tempfile.gettempdir(), f'sacco_{mid}.eml')
        with open(tmp,'w') as f: f.write(mime)
        try:
            subprocess.run(['himalaya','message','send'], input=mime, text=True, capture_output=True, timeout=30)
            try: os.unlink(tmp); os.unlink(xlsx_path)
            except: pass
            return {'status':'ok','sent':True,'to':email}
        except Exception as e:
            try: os.unlink(tmp)
            except: pass
            return {'status':'error','message':str(e)}

    def _send_all_statements(self):
        """Send Excel statements to all members (runs in background for large lists)."""
        import threading
        results = self._compute_all()
        # Count total members from DB for the message (compute_all skips empty accounts)
        conn = self._connect()
        total_db = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        conn.close()
        total = len(results)
        
        def _send():
            for m in results:
                if not m.get('email'):
                    continue
                try:
                    gen = self._generate_statement({'member_id': m['member_id']})
                    if gen.get('status') != 'ok':
                        continue
                    body = {
                        'xlsx_path': gen['xlsx_path'], 'email': m['email'],
                        'html_body': m['html_body'], 'subject': m['subject'],
                        'member_id': m['member_id'],
                    }
                    email_result = self._send_email_with_attachment(body)
                    if email_result.get('sent'):
                        self._log_statement({'member_id': m['member_id']})
                except:
                    pass
        
        t = threading.Thread(target=_send, daemon=True)
        t.start()
        return {'status': 'started', 'message': f'Sending statements to {total} of {total_db} members in background'}

    def _download_all_statements(self):
        """Generate zip of all member statements and serve as download."""
        import io, zipfile
        results = self._compute_all()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for m in results:
                gen = self._generate_statement({'member_id': m['member_id']})
                if gen.get('status') != 'ok':
                    continue
                xlsx_path = gen['xlsx_path']
                if os.path.exists(xlsx_path):
                    safe_name = m['name'].replace(' ', '_').replace('/', '_')
                    z.write(xlsx_path, f'{safe_name}_statement.xlsx')
                    try: os.unlink(xlsx_path)
                    except: pass
        data = buf.getvalue()
        self._binary(data, 'sacco_statements.zip')

    def _compute_all(self):
        sys.path.insert(0, os.path.dirname(__file__) or '.')
        from compute import compute_statement
        from render import render_statement_html
        conn = self._connect()
        members = [dict(r) for r in conn.execute('SELECT * FROM members ORDER BY member_number')]
        conn.close()
        results = []
        for m in members:
            data = compute_statement(m['id'])
            if not data: continue
            html = render_statement_html(data)
            results.append({
                'email': data['member']['email'], 'name': data['member']['name'],
                'member_id': m['id'], 'member_number': data['member']['member_number'],
                'html_body': html,
                'subject': f"Your SACCO Account Statement - {datetime.now().strftime('%B %Y')}",
                'savings_balance': data['summary']['current_savings'],
                'loan_balance': data['summary']['current_loan'],
            })
        return results

    def _dashboard_html(self):
        conn = self._connect()
        members = [dict(r) for r in conn.execute('SELECT * FROM members ORDER BY member_number')]
        settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
        conn.close()
        settings = {r['key']: r['value'] for r in settings_rows}
        def h(val): return html.escape(str(val)).replace("'", "&#39;")
        member_opts = ''
        member_table = ''
        for m in members:
            member_opts += f'<option value="{m["id"]}">{h(m["name"])} (#{h(m.get("member_number",""))})</option>'
            member_table += f'<tr><td><a href="#" onclick="viewTx(\'{m["id"]}\',\'{m["name"]}\');return false;" style="color:#2980b9;text-decoration:none;">{m["name"]}</a></td><td>{m.get("member_number","")}</td><td>{m.get("email","")}</td><td>{m.get("phone","")}</td><td><button class="edit-btn" onclick="editMember(\'{m["id"]}\',\'{m["name"]}\',\'{m.get("email","")}\',\'{m.get("phone","")}\',\'{m.get("member_number","")}\')">Edit</button> <button class="del-btn" onclick="deleteMember(\'{m["id"]}\',\'{m["name"]}\')">Delete</button></td></tr>'
        tx_types = ['contribution','loan_disbursement','loan_repayment','share_purchase','registration','refund']
        type_opts = ''.join(f'<option value="{t}">{t.replace("_"," ").title()}</option>' for t in tx_types)
        today = datetime.now().strftime('%Y-%m-%d')
        # Load template from file
        with open(os.path.join(os.path.dirname(__file__) or '.', 'dashboard_template.html'), encoding='utf-8') as f:
            template = f.read()
        # Substitute placeholders
        template = template.replace('{member_opts}', member_opts)
        template = template.replace('{member_table}', member_table)
        template = template.replace('{type_opts}', type_opts)
        template = template.replace('{today}', today)
        template = template.replace("{settings.get('sender_name','Norke SACCO')}", html.escape(settings.get('sender_name', 'Norke SACCO')))
        template = template.replace("{settings.get('sender_email','')}", html.escape(settings.get('sender_email', '')))
        template = template.replace("{settings.get('society_name','NORKEN SACCO SOCIETY LIMITED')}", html.escape(settings.get('society_name', 'NORKEN SACCO SOCIETY LIMITED')))
        template = template.replace("{settings.get('account_type','MEMBER PERSONAL ACCOUNT')}", html.escape(settings.get('account_type', 'MEMBER PERSONAL ACCOUNT')))
        template = template.replace("{settings.get('gmail_app_password','')}", settings.get('gmail_app_password', ''))
        template = template.replace("{settings.get('sender_email','')}", html.escape(settings.get('sender_email', '')))
        template = template.replace("{settings.get('interest_rate','1')}", html.escape(settings.get('interest_rate', '1')))
        return template

    def log_message(self, *a): pass

    def _shutdown(self):
        """Stop the server immediately."""
        import threading
        t = threading.Thread(target=lambda: (self._json({'status':'ok','message':'Shutting down'}), os._exit(0)), daemon=True)
        t.start()

if __name__ == '__main__':
    port = int(os.environ.get("SACCO_PORT", "9160"))
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'SACCO API on http://127.0.0.1:{port}')
    server.serve_forever()

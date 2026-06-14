"""Statement computation from transaction log."""
import sqlite3, os
from collections import defaultdict

DB = os.path.join(os.path.dirname(__file__) or '.', 'sacco.db')


def compute_statement(member_id):
    """Compute running-balance statement for a member.

    Returns:
        dict with member info, monthly rows with running balances, and summary.
    """
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM members WHERE id=?', (member_id,))
    member_row = c.fetchone()
    if not member_row:
        conn.close()
        return None
    member = dict(member_row)

    c.execute(
        'SELECT * FROM transactions WHERE member_id=? ORDER BY date, rowid',
        (member_id,),
    )
    txs = [dict(r) for r in c.fetchall()]
    conn.close()

    # Group by month
    months = defaultdict(
        lambda: {
            'contribution': 0,
            'loan_disbursement': 0,
            'loan_repayment': 0,
            'interest_charge': 0,
            'share_purchase': 0,
            'registration': 0,
            'refund': 0,
            'total_pay': 0,
        }
    )

    for tx in txs:
        month_key = tx['date'][:7]
        months[month_key][tx['type']] += tx['amount']

    # Build rows with running balances
    savings_balance = 0.0
    loan_balance = 0.0
    total_interest_paid = 0.0
    rows = []

    # Get interest rate from settings
    conn2 = sqlite3.connect(DB)
    rate_row = conn2.execute("SELECT value FROM settings WHERE key='interest_rate'").fetchone()
    interest_rate = float(rate_row[0]) / 100.0 if rate_row else 0.01
    # Safety: fallback to 1% if value is invalid
    if interest_rate <= 0 or interest_rate > 1:
        interest_rate = 0.01
    conn2.close()

    for month_key in sorted(months.keys()):
        m = months[month_key]
        
        # Auto-calculate interest on loan balance, then add it to loan
        interest = round(loan_balance * interest_rate, 2)
        if interest > 0:
            loan_balance += interest
            total_interest_paid += interest
        
        savings_balance += m['contribution'] + m['refund']
        loan_balance += m['loan_disbursement'] - m['loan_repayment']
        
        rows.append(
            {
                'month': month_key,
                'contribution': m['contribution'],
                'savings_balance': round(savings_balance, 2),
                'loan_disbursed': m['loan_disbursement'],
                'loan_repaid': m['loan_repayment'],
                'loan_balance': round(loan_balance, 2),
                'interest_charged': interest,
                'total_interest_paid': round(total_interest_paid, 2),
                'total_pay': m['total_pay'],
                'shares': m['share_purchase'],
                'registration': m['registration'],
                'refund': m['refund'],
            }
        )

    if not rows:
        return None

    return {
        'member': member,
        'rows': rows,
        'summary': {
            'total_contributions': sum(r['contribution'] for r in rows),
            'current_savings': round(savings_balance, 2),
            'current_loan': round(loan_balance, 2),
            'total_interest': round(total_interest_paid, 2),
            'month_count': len(rows),
        },
    }

"""HTML email renderer for SACCO member statements."""


def render_statement_html(data):
    """Generate HTML email body from compute_statement() output."""
    member = data['member']
    rows = data['rows']
    summary = data['summary']

    # Last 6 months for the detail table
    month_rows = ''
    for r in rows[-6:]:
        month_rows += f"""
        <tr>
            <td style="padding: 6px 10px; border-bottom: 1px solid #eee;">{r['month']}</td>
            <td style="padding: 6px 10px; text-align: right; border-bottom: 1px solid #eee;">{r['contribution']:,.0f}</td>
            <td style="padding: 6px 10px; text-align: right; border-bottom: 1px solid #eee;">{r['savings_balance']:,.2f}</td>
            <td style="padding: 6px 10px; text-align: right; border-bottom: 1px solid #eee;">{r['loan_repaid']:,.0f}</td>
            <td style="padding: 6px 10px; text-align: right; border-bottom: 1px solid #eee;">{r['loan_balance']:,.2f}</td>
            <td style="padding: 6px 10px; text-align: right; border-bottom: 1px solid #eee;">{r['interest_charged']:,.0f}</td>
        </tr>"""

    html = f"""<div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #1a5276; margin: 0;">NORKEN SACCO SOCIETY LIMITED</h2>
            <p style="color: #7f8c8d; margin: 4px 0;">MEMBER PERSONAL ACCOUNT</p>
        </div>

        <table style="width: 100%; margin-bottom: 20px;">
            <tr><td style="padding: 4px 0; color: #555;">NAME:</td><td><strong>{member['name']}</strong></td></tr>
            <tr><td style="padding: 4px 0; color: #555;">M/NUMBER:</td><td>{member['member_number']}</td></tr>
        </table>

        <h3 style="color: #1a5276; border-bottom: 2px solid #2980b9; padding-bottom: 6px;">Recent Activity (Last 6 Months)</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <tr style="background: #2980b9; color: white;">
                <th style="padding: 8px 10px; text-align: left;">Month</th>
                <th style="padding: 8px 10px; text-align: right;">Contribution</th>
                <th style="padding: 8px 10px; text-align: right;">Savings Bal</th>
                <th style="padding: 8px 10px; text-align: right;">Loan Repaid</th>
                <th style="padding: 8px 10px; text-align: right;">Loan Bal</th>
                <th style="padding: 8px 10px; text-align: right;">Interest</th>
            </tr>
            {month_rows}
        </table>

        <h3 style="color: #1a5276; border-bottom: 2px solid #2980b9; padding-bottom: 6px; margin-top: 24px;">Account Summary</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr style="background: #eaf2f8;"><td style="padding: 8px;">Total Contributions</td><td style="padding: 8px; text-align: right;"><strong>KES {summary['total_contributions']:,.0f}</strong></td></tr>
            <tr><td style="padding: 8px;">Current Savings Balance</td><td style="padding: 8px; text-align: right;"><strong>KES {summary['current_savings']:,.2f}</strong></td></tr>
            <tr style="background: #eaf2f8;"><td style="padding: 8px;">Outstanding Loan</td><td style="padding: 8px; text-align: right;"><strong>KES {summary['current_loan']:,.2f}</strong></td></tr>
            <tr><td style="padding: 8px;">Total Interest Paid</td><td style="padding: 8px; text-align: right;"><strong>KES {summary['total_interest']:,.2f}</strong></td></tr>
        </table>

        <p style="color: #95a5a6; font-size: 11px; margin-top: 30px; text-align: center;">
            This is an automated statement. For inquiries, contact your SACCO office.
        </p>
    </div>"""

    return html

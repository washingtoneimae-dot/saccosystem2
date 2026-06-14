#!/usr/bin/env python3
"""Generate an xlsx matching the exact Norken SACCO statement format."""
import sys, os, io, zipfile, xml.etree.ElementTree as ET
from datetime import datetime

def generate_xlsx(member_name, member_number, rows, summary, output_path, dob=''):
    if not dob:
        dob = 'N/A'
    # Collect shared strings
    ss_pool = [
        'NORKEN SACCO SOCIETY LIMITED', 'MEMBER PERSONAL ACCOUNT',
        'SHARES/REG. UPDATE', 'SAVINGS UPDATE', 'LOAN UPDATE', 'INTEREST UPDATE',
        'MONTH', 'Total pay to society', 'SHARE', 'REG.',
        'Refund', 'Monthly Contribution', 'Total Deposit',
        'Loan granted', 'Loan repaid', 'Loan Balance',
        'Interest per month', 'Total interest paid',
        'Balance b/f',
        f'NAME;{member_name}', f'M/NUMBER:{member_number}', f'D.O.B.; {dob}',
    ]
    
    savings_running = 0.0
    loan_running = 0.0
    interest_running = 0.0
    deposit_running = 0.0
    
    row_data = []
    for r in rows:
        month_str = r['month']
        try:
            y, m = month_str.split('-')
            dt = datetime(int(y), int(m), 1)
            month_display = dt.strftime('%b %Y')
        except:
            month_display = month_str
        
        contrib = r.get('contribution', 0)
        total_pay = r.get('total_pay', 0)
        shares = r.get('shares', 0)
        reg = r.get('registration', 0)
        refund = r.get('refund', 0)
        loan_disb = r.get('loan_disbursed', 0)
        loan_repay = r.get('loan_repaid', 0)
        interest = r.get('interest_charged', 0)
        
        deposit_running += contrib + refund
        savings_running += contrib + refund
        loan_running += loan_disb - loan_repay
        interest_running += interest
        
        rd = {
            'month_display': month_display,
            'total_pay': total_pay,
            'shares': shares,
            'reg': reg,
            'refund': refund,
            'contrib': contrib,
            'deposit': round(deposit_running, 2),
            'loan_disb': loan_disb,
            'loan_repay': loan_repay,
            'loan_bal': round(loan_running, 2),
            'interest': interest,
            'interest_total': round(interest_running, 2),
        }
        row_data.append(rd)
        
        for val in [month_display, str(int(total_pay)) if total_pay else '',
                     str(int(shares)) if shares else '', str(int(reg)) if reg else '',
                     str(int(refund)) if refund else '', str(int(contrib)) if contrib else '',
                     str(rd['deposit']), str(int(loan_disb)) if loan_disb else '',
                     str(int(loan_repay)) if loan_repay else '', str(rd['loan_bal']),
                     str(int(interest)) if interest else '', str(rd['interest_total'])]:
            if val and val not in ss_pool:
                ss_pool.append(val)
    
    # Deduplicate strings
    seen = set()
    uniq = []
    idx = {}
    for s in ss_pool:
        if s not in seen:
            seen.add(s)
            idx[s] = len(uniq)
            uniq.append(s)
    
    def si(s):
        return idx.get(s, 0)
    
    def esc(s):
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    def scell(ref, s):
        return f'<c r="{ref}" t="s"><v>{si(s)}</v></c>'
    
    def mcell(ref, v):
        """Money cell with comma formatting."""
        return f'<c r="{ref}" s="1"><v>{float(v):.2f}</v></c>'
    
    # Shared strings XML
    si_items = ''
    for s in uniq:
        si_items += f'<si><t>{esc(s)}</t></si>'
    si_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(uniq)}" uniqueCount="{len(uniq)}">{si_items}</sst>'
    
    rows_xml = ''
    
    # Row 1: Society name
    rows_xml += f'<row r="1">{scell("A1","NORKEN SACCO SOCIETY LIMITED")}</row>'
    # Row 2: Account type
    rows_xml += f'<row r="2">{scell("A2","MEMBER PERSONAL ACCOUNT")}</row>'
    # Row 3: Name
    rows_xml += f'<row r="3">{scell("A3",f"NAME;{member_name}")}</row>'
    # Row 4: Member number
    rows_xml += f'<row r="4">{scell("A4",f"M/NUMBER:{member_number}")}</row>'
    # Row 5: DOB
    rows_xml += f'<row r="5">{scell("A5",f"D.O.B.; {dob}")}</row>'
    # Row 6: Section headers
    rows_xml += f'<row r="6">{scell("D6","SHARES/REG. UPDATE")}{scell("G6","SAVINGS UPDATE")}{scell("K6","LOAN UPDATE")}{scell("O6","INTEREST UPDATE")}</row>'
    # Row 7: Column headers
    h7 = [('A','MONTH'),('B','Total pay to society'),('D','SHARE'),('E','REG.'),
          ('G','Refund'),('H','Monthly Contribution'),('I','Total Deposit'),
          ('K','Loan granted'),('L','Loan repaid'),('M','Loan Balance'),
          ('O','Interest per month'),('P','Total interest paid')]
    hrow = '<row r="7">'
    for col, text in h7:
        hrow += scell(f'{col}7', text)
    hrow += '</row>'
    rows_xml += hrow
    
    # Row 8: Balance b/f
    rows_xml += f'<row r="8">{scell("A8","Balance b/f")}{mcell("I8",0)}{mcell("M8",0)}</row>'
    
    # Data rows
    for ridx, rd in enumerate(row_data):
        rn = ridx + 9
        row = f'<row r="{rn}">'
        row += scell(f'A{rn}', rd['month_display'])
        if rd['total_pay']:
            row += mcell(f'B{rn}', rd['total_pay'])
        if rd['shares']:
            row += mcell(f'D{rn}', rd['shares'])
        if rd['reg']:
            row += mcell(f'E{rn}', rd['reg'])
        if rd['refund']:
            row += mcell(f'G{rn}', rd['refund'])
        if rd['contrib']:
            row += mcell(f'H{rn}', rd['contrib'])
        row += mcell(f'I{rn}', rd['deposit'])
        if rd['loan_disb']:
            row += mcell(f'K{rn}', rd['loan_disb'])
        if rd['loan_repay']:
            row += mcell(f'L{rn}', rd['loan_repay'])
        row += mcell(f'M{rn}', rd['loan_bal'])
        if rd['interest']:
            row += mcell(f'O{rn}', rd['interest'])
        row += mcell(f'P{rn}', rd['interest_total'])
        row += '</row>'
        rows_xml += row
    
    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetViews><sheetView tabSelected="1" workbookViewId="0"><pane ySplit="8" topLeftCell="A9" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<cols><col min="1" max="1" width="12"/><col min="2" max="2" width="18"/><col min="4" max="5" width="8"/><col min="7" max="9" width="16"/><col min="11" max="13" width="16"/><col min="15" max="16" width="18"/></cols>
<sheetData>{rows_xml}</sheetData></worksheet>'''
    
    # Build xlsx zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>')
        z.writestr('_rels/.rels',
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
        z.writestr('xl/workbook.xml',
            '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Statement" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml)
        z.writestr('xl/sharedStrings.xml', si_xml)
        z.writestr('xl/styles.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<numFmts count="1">'
            '<numFmt numFmtId="164" formatCode="#,##0.00"/>'
            '</numFmts>'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
            '</cellXfs>'
            '</styleSheet>')
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(buf.getvalue())
    return output_path


if __name__ == '__main__':
    import json
    data = json.loads(sys.stdin.read())
    result = generate_xlsx(data['member_name'], data['member_number'],
                          data['rows'], data['summary'], data['output_path'])
    print(json.dumps({'path': result, 'size': os.path.getsize(result)}))

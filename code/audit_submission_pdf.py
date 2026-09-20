"""Check the built submission, including actual font sizes and extracted tables.

Run with: uv run --with pymupdf python code/audit_submission_pdf.py
The build log must come from the PDF being checked.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pymupdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', default='paper/main.pdf')
    parser.add_argument('--log', default='paper/main.log')
    parser.add_argument('--out', default='paper/rewrite-validation/pdf-audit.json')
    args = parser.parse_args()
    pdf, log = Path(args.pdf), Path(args.log)
    tex = Path('paper/main.tex').read_text()
    document = pymupdf.open(pdf)
    pages = [page.get_text() for page in document]
    spans = [span for page in document for block in page.get_text('dict')['blocks']
             if 'lines' in block for line in block['lines'] for span in line['spans']
             if span['text'].strip()]
    fonts = subprocess.check_output(['pdffonts', str(pdf)], text=True)
    extracted = subprocess.check_output(['pdftotext', str(pdf), '-'], text=True)
    layout = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    url = 'github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty'
    url_lines = [line.strip() for line in extracted.splitlines() if url in line]
    layout_lines = [line.strip() for line in layout.splitlines() if url in line]
    warnings = log.read_text()
    ack = [n + 1 for n, text in enumerate(pages) if 'ACKNOWLEDGMENT' in text]
    ethics = [n + 1 for n, text in enumerate(pages) if 'COMPLIANCE WITH ETHICAL STANDARDS' in text]
    minimum = min(span['size'] for span in spans)
    overfull = len(re.findall(r'Overfull \\[hv]box', warnings))
    undefined = len(re.findall(r'(?:Reference|Citation).*undefined|undefined references|undefined citations', warnings))
    type3 = fonts.count('Type 3')
    assert len(document) == 5
    assert overfull == undefined == type3 == 0
    assert minimum >= 9
    assert ack == ethics == [4]
    assert 'Anthropic Claude and OpenAI Codex' in pages[3]
    assert len(url_lines) == len(layout_lines) == 1
    assert url_lines[0] == url + '.'
    assert 'REFERENCES' in pages[4][:40]
    assert not any(word in pages[4] for word in ('ACKNOWLEDGMENT', 'ETHICAL STANDARDS', 'DISCUSSION AND CONCLUSION'))
    assert all('REFERENCES' not in p for p in pages[:4])
    # Inspect the PDF, not just the source: every numeric table row must survive.
    def normalize(value):
        value = value.replace('\u2212', '-').replace('\u2013', '--').replace('\u2192', '->')
        return re.sub(r'\s+', '', value)
    pdf_text = normalize(''.join(pages))
    checked_rows = {}
    tables = []
    for number, match in enumerate(re.finditer(r'\\begin\{table\}.*?\\end\{table\}', tex, re.S), 1):
        table = match.group()
        label = re.search(r'\\label\{([^}]+)\}', table).group(1)
        rows = [line.strip() for line in table.splitlines() if line.rstrip().endswith(r'\\')]
        numeric = [row for row in rows if '&' in row and re.search(r'\d', row)]
        for row in numeric:
            rendered = row.replace(r'\%', '%').replace(r'\to', '->')
            rendered = rendered.replace('$', '').replace('&', '').replace(r'\\', '')
            assert normalize(rendered) in pdf_text, (label, row)
        checked_rows[label] = len(numeric)
        tables.append({'number': number, 'label': label, 'rows_tex': rows})
    assert checked_rows == {'tab:eers': 32, 'tab:influence': 3, 'tab:arms': 3, 'tab:sign': 4, 'tab:spoof': 4}
    # SpoofCeleb's six categorical rows have no digits; verify those separately.
    for table in tables:
        if table['label'] == 'tab:spoof':
            for row in table['rows_tex']:
                if re.search(r' & [YN] &', row):
                    assert normalize(row.replace('&', '').replace(r'\\', '')) in pdf_text
    result = {
        'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
        'tex_sha256': hashlib.sha256(tex.encode()).hexdigest(),
        'page_count': len(document), 'overfull_boxes': overfull,
        'undefined_reference_or_citation_warnings': undefined,
        'minimum_font_size_points': minimum, 'type3_fonts': type3,
        'acknowledgment_page': ack, 'ethics_page': ethics,
        'page5_references_only': True, 'extracted_url_line': url_lines[0],
        'layout_extracted_url_line': layout_lines[0],
        'artifact_commit': re.search(r'Artifact version \\texttt\{([0-9a-f]{40})\}', tex).group(1),
        'pdf_numeric_table_rows_checked': checked_rows,
        'pdf_spoofceleb_categorical_rows_checked': 6,
        'tables_as_built': tables,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS — PDF: 5 pages, references only on page 5; acknowledgment and ethics on page 4; '
          f'0 overfull boxes, 0 undefined citations/references, 0 Type 3 fonts; minimum font {minimum:.6f} pt.')
    print('PASS — all five tables survive PDF extraction; URL intact on one line: ' + url_lines[0])


if __name__ == '__main__':
    main()

"""Rebuild questions.js from the study-manual PDF.  Usage: python3 tools/extract.py Study_Manual_AR.pdf
Correct answer = the option set in a Bold font. Requires: pip install pymupdf pillow"""
import sys, re, json, io, unicodedata, pymupdf
from PIL import Image
pdf = sys.argv[1] if len(sys.argv) > 1 else 'Study_Manual_AR.pdf'
# Motorbike (74-100) and heavy-vehicle / trailer (36-48, 52-56, 71-73) questions are excluded: car-driver exam only.
EXCLUDE = set(range(36,49)) | set(range(52,57)) | {71,72,73} | set(range(74,101))
SWAP = str.maketrans('()', ')(')
def norm(s):
    s = unicodedata.normalize('NFKC', s).translate(SWAP)
    s = re.sub(r'([،؟:])(?=[\u0621-\u064A])', r'\1 ', s)
    return re.sub(r'\s+', ' ', s).strip()
d = pymupdf.open(pdf)
rows, pending = [], []          # rows: dict(id,cat,q,lines[(y,x,text,bold)],imgs)
def span_text(s, gap=1.6):
    out, prev = '', None
    for c in s['chars']:
        ch = c['c']
        if prev and ch != ' ' and prev['c'] != ' ' and ord(ch) >= 0xFB50 and ord(prev['c']) >= 0xFB50 and prev['bbox'][0] - c['bbox'][2] > gap: out += ' '
        out += ch; prev = c
    return out
def lines_to_opts(lines):
    lines.sort(key=lambda l: (l[0], -l[1]))
    ln = []                      # merge spans on the same visual line
    for y, x, t, b in lines:
        if ln and abs(ln[-1]['y'] - y) < 4: ln[-1]['t'].append(t); ln[-1]['b'] |= b
        else: ln.append({'y': y, 't': [t], 'b': b})
    opts = []
    for l in ln:
        txt = ' '.join(l['t'])
        if opts and l['y'] - opts[-1]['y'] <= 16: opts[-1]['t'] += ' ' + txt; opts[-1]['b'] |= l['b']; opts[-1]['y'] = l['y']
        else: opts.append({'y': l['y'], 't': txt, 'b': l['b']})
    return [(norm(o['t']), o['b']) for o in opts]
for pn, p in enumerate(d):
    tb = p.find_tables().tables[0]
    qrows = sorted([r.bbox for r in tb.rows if r.bbox[2] > 500 and r.bbox[3] - r.bbox[1] > 12], key=lambda b: b[1])
    if qrows and tb.bbox[3] - qrows[-1][3] > 12: qrows.append((55, qrows[-1][3], 540, tb.bbox[3]))
    spans = [s for b in p.get_text('rawdict')['blocks'] if b['type'] == 0 for l in b['lines'] for s in l['spans'] if span_text(s).strip()]
    for s in spans: s['text'] = span_text(s)
    spans = [s for s in spans if not re.search(r'Page \d+ of|about:blank|\d+/\d+/\d{4}', s['text'])]
    imgs = p.get_image_info(xrefs=True)
    qrows.insert(0, (55, 0, 540, qrows[0][1]))   # area above the first row: continuation and/or a split row
    first = 0
    for (x0, y0, x1, y1) in qrows:
        r = {'id': None, 'cat': None, 'q': [], 'lines': [], 'imgs': [], 'page': pn}
        for s in spans:
            bx0, by0, bx1, by1 = s['bbox']; cy = (by0 + by1) / 2
            if not (y0 <= cy < y1): continue
            t = s['text']
            if bx0 > 512 and re.fullmatch(r'\d+', t.strip()): r['id'] = int(t); continue
            if bx0 >= 255:
                m = re.match(r'(Law|Safety|Signs)(.*)', t.strip())
                if m: r['cat'] = m.group(1); t = m.group(2)
                if t.strip(): r['q'].append((by0, -bx0, t))
            else: r['lines'].append((by0, bx0, t, 'Bold' in s['font']))
        for im in imgs:
            bx0, by0, bx1, by1 = im['bbox']
            if x0 + 200 < bx0 < 500 and y0 <= (by0 + by1) / 2 < y1:
                r['imgs'].append(im['xref'])
        if r['id']: rows.append(r)
        elif rows: rows[-1]['lines'] += [(1e4 + y, x, t, b) for y, x, t, b in r['lines']]
out, seen, stats = [], set(), {'noimg': [], 'skipped': []}
for r in rows:
    r['q'].sort(); q = norm(' '.join(t for _, _, t in r['q']))
    opts = lines_to_opts([(y if y < 1e4 else y, x, t, b) for y, x, t, b in r['lines']])
    # continuation lines (y>=1e4) belong to the last option
    if r['id'] in EXCLUDE or r['cat'] is None: continue
    nb = sum(b for _, b in opts)
    if len(opts) < 2 or nb != 1 or 'اختر كافة' in q:
        stats['skipped'].append((r['id'], len(opts), nb)); continue
    item = {'id': r['id'], 'cat': r['cat'].lower(), 'q': q or 'ماذا تعني هذه الإشارة؟', 'o': [t for t, _ in opts], 'a': [b for _, b in opts].index(True)}
    if r['cat'] == 'Signs':
        if not r['imgs']: stats['noimg'].append(r['id']); continue
        pix = pymupdf.Pixmap(d, r['imgs'][0]); 
        if pix.n - pix.alpha >= 4 or pix.alpha: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB'); im.thumbnail((200, 200))
        im.save(f'img/s{r["id"]}.webp', 'WEBP', quality=85); item['img'] = f'img/s{r["id"]}.webp'
    key = (item['q'], tuple(sorted(item['o'])), item.get('img'))
    if r['cat'] != 'Signs' and key in seen: continue
    seen.add(key); out.append(item)
open('questions.js', 'w', encoding='utf-8').write('window.QUESTIONS=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';')
from collections import Counter
print(Counter(i['cat'] for i in out), 'total', len(out)); print(stats)
if len(sys.argv) > 2:
    for r in rows:
        if r['id'] in map(int, sys.argv[2:]): print(r['id'], r['page'], [(round(y), round(x), b, norm(t)[:30]) for y, x, t, b in sorted(r['lines'])])

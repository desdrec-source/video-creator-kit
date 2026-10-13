"""Rebuild the binary assets (TTF fonts, placeholder logo) from packed/*.b64.NN, checking each SHA-256."""
import base64, hashlib, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
man = json.load(open(os.path.join(ROOT, 'packed', 'manifest.json')))
for m in man:
    out = os.path.join(ROOT, m['out'])
    if os.path.exists(out) and '--force' not in sys.argv:
        print('ok  ', m['out']); continue
    b = base64.b64decode(''.join(open(os.path.join(ROOT, p)).read() for p in m['parts']))
    if hashlib.sha256(b).hexdigest() != m['sha256']: sys.exit('checksum mismatch: ' + m['packed'])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(b)
    print('made', m['out'])

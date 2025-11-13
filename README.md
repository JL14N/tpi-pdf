Project: PDF CSRF/XSS Demo — Vulnerable vs Isolated+POST

This repository contains a minimal teaching demo for the TPI proposal: a vulnerable web app that can be exploited via a PDF containing an actionable link, and a secure variant that prevents the attack by requiring state changes via POST and serving PDFs from an isolated origin with a strict CSP.

What is included
- `vulnerable_server.py`: Insecure demo (port 5000). Accepts a GET on `/admin/change-email` and changes the stored `admin_email` without authentication or CSRF protection.
- `secure_server.py`: Secure demo (port 5001). The same UI but `/admin/change-email` requires POST; the app also sets a strict `Content-Security-Policy` header and serves PDFs from the isolated upload folder.
- `app.py`: legacy/sample app containing other PDF examples (kept for reference).
- `templates/`: Shared HTML templates used by both servers.
- `uploads/` and `uploads_isolated/`: storage for uploaded PDFs (vulnerable vs isolated).
- `admin_state.json`: small JSON file storing the current `admin_email` used for the demo.

Quick start
1. Create a virtualenv and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Start the vulnerable server (port 5000):
```bash
python3 vulnerable_server.py
```
3. In another terminal start the secure/isolation server (port 5001):
```bash
python3 secure_server.py
```

Demo endpoints
- `http://127.0.0.1:5000/sample_csrf_link` — Returns a PDF that contains a clickable link to `http://127.0.0.1:5000/admin/change-email?email=attacker%40evil.example`. Opening and clicking the link will change `admin_state.json` because the vulnerable server accepts GET.
- `http://127.0.0.1:5001/sample_csrf_link` — Returns a similar PDF pointing to the secure server's `/admin/change-email`. Clicking it will NOT succeed because the secure server rejects GET (405) and requires a POST.

How to test quickly
- Vulnerable server:
  - Open `http://127.0.0.1:5000/sample_csrf_link` in your browser (it will render a PDF with a link). Click it and observe the response text that indicates the email changed.
  - Inspect `admin_state.json` to verify the change.
- Secure server:
  - Open `http://127.0.0.1:5001/sample_csrf_link` and click the link — you should get `405 Method Not Allowed` because the server only accepts POST for state changes.

Notes and teaching points
- This demo intentionally simplifies authentication and state handling to make the vulnerability visible in a lab environment.
- The primary lesson is architectural: moving potentially dangerous content to an isolated origin (different port/host) and disallowing state changes via GET greatly reduces the attack surface.

Warning
- Do not expose these demo servers to the public internet. They are intentionally insecure for teaching purposes.

If you want, puedo añadir instrucciones para generar un PDF físico (archivo) en el repo o un pequeño script que automatice los pasos de la demo.

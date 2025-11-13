from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, make_response, session
from werkzeug.utils import secure_filename
import os, json
from io import BytesIO
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader
from functools import wraps
from PIL import Image, ImageDraw, ImageFont

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
STATE_FILE = os.path.join(os.path.dirname(__file__), 'admin_state.json')
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'secure-demo-secret'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
THUMB_DIR = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs')
os.makedirs(THUMB_DIR, exist_ok=True)



def load_state():
    if not os.path.exists(STATE_FILE):
        state = {'admin_email': 'admin@bank.local'}
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
        return state
    with open(STATE_FILE, 'r') as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


# Ensure admin email resets to default on server start
save_state({'admin_email': 'admin@bank.local'})


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_thumbnail(pdf_path, thumb_path, title=None):
    try:
        text = None
        try:
            reader = PdfReader(pdf_path)
            if reader.pages:
                raw = reader.pages[0].extract_text() or ''
                text = raw.strip().replace('\n', ' ')[:300]
        except Exception:
            text = None
        if not text and title:
            text = title
        if not text:
            text = os.path.basename(pdf_path)
        W, H = 400, 520
        img = Image.new('RGB', (W, H), color=(250, 250, 250))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('DejaVuSans.ttf', 14)
            title_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 16)
        except Exception:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        draw.rectangle([8, 8, W-8, 120], fill=(230, 230, 230))
        draw.text((16, 14), os.path.basename(pdf_path), fill=(30, 30, 30), font=title_font)
        y = 140
        lines = []
        words = text.split(' ')
        line = ''
        for w in words:
            if len(line) + len(w) + 1 > 50:
                lines.append(line)
                line = w
            else:
                line = (line + ' ' + w).strip()
        if line:
            lines.append(line)
        for l in lines[:12]:
            draw.text((16, y), l, fill=(60, 60, 60), font=font)
            y += 18
        img.save(thumb_path)
        return True
    except Exception:
        return False


def require_login(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped


@app.after_request
def set_csp(response):
    # Strict CSP for the isolated origin
    # Allow inline styles for this demo (templates use inline <style> blocks).
    # In a production setup prefer nonces or external stylesheet with proper hashes instead.
    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
    return response


@app.route('/')
@require_login
def index():
    state = load_state()
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    last = files[-1] if files else None
    role = session.get('role')
    user = session.get('user')
    # prepare slots for template (always pass a list of 5 entries)
    slots = []
    for i in range(1, 6):
        fname = f'slot{i}.pdf'
        path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        slots.append(fname if os.path.exists(path) else None)

    # compute available thumbnails (relative paths like 'thumbs/slot1.png')
    thumbs_available = set()
    try:
        for n in os.listdir(THUMB_DIR):
            thumbs_available.add('thumbs/' + n)
    except Exception:
        pass

    return render_template('index.html', filename=last, admin_email=state.get('admin_email'), role=role, user=user, slots=slots, thumbs_available=thumbs_available, theme='secure')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == 'attacker' and pwd == 'attacker':
            session['user'] = 'attacker'
            session['role'] = 'attacker'
            return redirect(url_for('manage'))
        if user == 'admin' and pwd == 'admin':
            session['user'] = 'admin'
            session['role'] = 'admin'
            return redirect(url_for('index'))
        flash('Credenciales inválidas')
    return render_template('login.html', theme='secure')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/manage')
@require_login
def manage():
    if session.get('role') != 'attacker':
        flash('Acceso denegado')
        return redirect(url_for('index'))
    slots = []
    for i in range(1, 6):
        fname = f'slot{i}.pdf'
        path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        slots.append({'slot': i, 'filename': fname if os.path.exists(path) else None})
    # compute available thumbnails
    thumbs_available = set()
    try:
        for n in os.listdir(THUMB_DIR):
            thumbs_available.add('thumbs/' + n)
    except Exception:
        pass
    return render_template('manage.html', slots=slots, thumbs_available=thumbs_available, theme='secure')


@app.route('/manage/upload', methods=['POST'])
@require_login
def manage_upload():
    if session.get('role') != 'attacker':
        return 'Forbidden', 403
    slot = int(request.form.get('slot', '0'))
    if slot < 1 or slot > 5:
        return 'Bad slot', 400
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('manage'))
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = f'slot{slot}.pdf'
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        thumb_name = f'slot{slot}.png'
        thumb_path = os.path.join(THUMB_DIR, thumb_name)
        try:
            create_thumbnail(path, thumb_path, title=filename)
        except Exception:
            pass
        flash(f'Subido en slot {slot}', 'success')
    else:
        flash('Tipo de archivo no permitido')
    return redirect(url_for('manage'))


@app.route('/manage/delete')
@require_login
def manage_delete():
    if session.get('role') != 'attacker':
        return 'Forbidden', 403
    try:
        slot = int(request.args.get('slot', '0'))
    except Exception:
        return 'Bad slot', 400
    if slot < 1 or slot > 5:
        return 'Bad slot', 400
    filename = f'slot{slot}.pdf'
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        os.remove(path)
        flash(f'Slot {slot} eliminado', 'success')
    return redirect(url_for('manage'))


@app.route('/upload', methods=['POST'])
def upload():
    # attacker must be logged in to upload
    if not session.get('user'):
        return redirect(url_for('login'))
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
            except Exception:
                pass
        file.save(path)
        # create thumbnail
        thumb_name = os.path.splitext(filename)[0] + '.png'
        thumb_path = os.path.join(THUMB_DIR, thumb_name)
        try:
            create_thumbnail(path, thumb_path, title=filename)
        except Exception:
            pass
        flash('PDF cargado correctamente (aislado)', 'success')
        return redirect(url_for('index'))
    else:
        flash('Tipo de archivo no permitido')
        return redirect(url_for('index'))


@app.route('/isolated/view/<path:filename>')
def isolated_view(filename):
    # Serve the uploaded PDF from the isolated origin. CSP header set in after_request.
    if not session.get('user'):
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Compatibility endpoint used by templates
    if not session.get('user'):
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/sample_csrf_link')
@require_login
def sample_csrf_link():
    # Generate a PDF containing a visible link that performs a GET to change admin email on this origin.
    # In the secure server this will NOT work because the change endpoint requires POST.
    buf = BytesIO()
    p = canvas.Canvas(buf)
    p.drawString(100, 750, 'Documento de prueba - Enlace CSRF (aislado)')
    p.drawString(100, 730, 'Haga clic en el enlace (GET) — en el servidor seguro esto no cambia el email.')
    link = 'http://127.0.0.1:5000/admin/change-email?email=attacker%40evil.example'
    p.drawString(100, 700, 'Click aquí:')
    p.linkURL(link, (160, 688, 460, 708), relative=0)
    p.drawString(160, 700, link)
    p.showPage()
    p.save()
    buf.seek(0)
    return (buf.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline; filename="sample_csrf_link.pdf"'
    })


@app.route('/sample_risky')
@require_login
def sample_risky():
    # Backwards-compatible route referenced by the shared template.
    # Redirect to the CSRF-link sample (which demonstrates the difference between GET and POST handling).
    from flask import redirect
    return redirect(url_for('sample_csrf_link'))


@app.route('/admin/change-email', methods=['GET', 'POST'])
@require_login
def admin_change_email():
    # Only allow role 'admin' to change the administrative email.
    if session.get('role') != 'admin':
        return 'Forbidden', 403

    if request.method == 'GET':
        # render form for admin
        state = load_state()
        return render_template('change_email.html', current=state.get('admin_email'), theme='secure')

    # POST: change via form
    email = request.form.get('email')
    if not email:
        flash('Falta email')
        return redirect(url_for('admin_change_email'))
    state = load_state()
    old = state.get('admin_email')
    state['admin_email'] = email
    save_state(state)
    flash(f'Admin email cambiado de {old} a {email}', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)

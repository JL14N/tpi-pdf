from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'dev-secret-for-demo'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def pdf_has_risk(filepath):
    """Very small heuristic: check the raw bytes for the trigger phrase.
    This is intentionally simple for the demo. In a real app you'd parse the PDF content.
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read().lower()
            if b'riesgo de seguridad' in data:
                return True
    except Exception:
        pass
    return False


@app.route('/')
def index():
    # Show the upload form and (if present) the last uploaded file
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    last = files[-1] if files else None
    return render_template('index.html', filename=last)


@app.route('/upload', methods=['POST'])
def upload():
    # Single file input named 'file'
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
        # remove existing files to enforce single-upload behavior
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
            except Exception:
                pass
        file.save(path)
        if pdf_has_risk(path):
            flash('Riesgo de Seguridad', 'danger')
        else:
            flash('PDF cargado correctamente', 'success')
        return redirect(url_for('index'))
    else:
        flash('Tipo de archivo no permitido')
        return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/sample-risky')
def sample_risky():
    # Create a simple PDF in-memory with reportlab
    buf = BytesIO()
    p = canvas.Canvas(buf)
    p.drawString(100, 750, 'Documento de prueba - Riesgo de Seguridad')
    p.drawString(100, 730, 'Este PDF contiene la frase que debe activar la alerta: Riesgo de Seguridad')
    p.showPage()
    p.save()
    buf.seek(0)

    # Read it with PyPDF2 and inject JavaScript as an OpenAction in the Catalog
    reader = PdfReader(buf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # JavaScript payload (the user's proof-of-concept)
    # Use a triple-quoted string to avoid escaping hell
    js = '''app.alert({
    cMsg: "¡Vulnerabilidad XSS/Ejecución de Script Demostrada! (Documento.domain: " + document.domain + ") - ¡Las credenciales han sido robadas!",
    cTitle: "Alerta de Seguridad TPI"
});'''

    # PyPDF2: add JS and set OpenAction
    writer.add_js(js)

    out_buf = BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)

    return (out_buf.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline; filename="sample_risky.pdf"'
    })


@app.route('/sample-risky-download')
def sample_risky_download():
    # Same PDF but force download so user can open it externally (e.g., Acrobat Reader)
    buf = BytesIO()
    p = canvas.Canvas(buf)
    p.drawString(100, 750, 'Documento de prueba - Riesgo de Seguridad')
    p.drawString(100, 730, 'Este PDF contiene la frase que debe activar la alerta: Riesgo de Seguridad')
    p.showPage()
    p.save()
    buf.seek(0)

    reader = PdfReader(buf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    js = '''app.alert({
    cMsg: "¡Vulnerabilidad XSS/Ejecución de Script Demostrada! (Documento.domain: " + document.domain + ") - ¡Las credenciales han sido robadas!",
    cTitle: "Alerta de Seguridad TPI"
});'''
    writer.add_js(js)

    out_buf = BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)

    return (out_buf.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="sample_risky.pdf"'
    })


@app.route('/simulate-payload')
def simulate_payload():
    # Render a safe HTML page that simulates the alert the PDF would show.
    return render_template('simulate.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)

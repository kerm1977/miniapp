# notas.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from PIL import Image as PILImage # Importar Pillow para JPG
import os

# Importar db y el modelo Nota desde models.py
from models import db, Nota # Asegúrate de que esta importación sea correcta
from flask_wtf.csrf import generate_csrf # ¡IMPORTANTE: Importar generate_csrf!

notas_bp = Blueprint('notas', __name__, template_folder='templates')

# Formulario para Notas
class NotaForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    descripcion = TextAreaField('Descripción', validators=[DataRequired()])
    submit = SubmitField('Guardar Nota')

# Función para generar colores pastel aleatorios
def generate_pastel_color():
    # Genera un color pastel en formato hexadecimal
    r = int((255 + (datetime.now().microsecond % 100)) / 2)
    g = int((255 + (datetime.now().microsecond % 100) + 50) / 2)
    b = int((255 + (datetime.now().microsecond % 100) + 100) / 2)
    return f'#{r:02x}{g:02x}{b:02x}'

# Rutas para el CRUD de Notas

@notas_bp.route('/ver_notas')
@login_required
def ver_notas():
    # Obtiene todas las notas del usuario actual, ordenadas por fecha de creación descendente
    notas = Nota.query.filter_by(usuario_id=current_user.id).order_by(Nota.fecha_creacion.desc()).all()
    pastel_color = generate_pastel_color() # Genera un color pastel para el fondo
    # ¡IMPORTANTE: Pasar generate_csrf a la plantilla!
    return render_template('ver_notas.html', notas=notas, pastel_color=pastel_color, generate_csrf=generate_csrf)

@notas_bp.route('/crear_nota', methods=['GET', 'POST'])
@login_required
def crear_nota():
    form = NotaForm()
    if form.validate_on_submit():
        # Crea una nueva nota con los datos del formulario y la fecha actual
        nueva_nota = Nota(
            usuario_id=current_user.id,
            titulo=form.titulo.data,
            descripcion=form.descripcion.data,
            fecha_creacion=datetime.utcnow() # La fecha se coloca automáticamente
        )
        db.session.add(nueva_nota)
        db.session.commit()
        flash('¡Nota creada exitosamente!', 'success')
        return redirect(url_for('notas.ver_notas'))
    pastel_color = generate_pastel_color() # Genera un color pastel para el fondo
    return render_template('crear_notas.html', form=form, pastel_color=pastel_color, generate_csrf=generate_csrf) # Pasar generate_csrf aquí también

@notas_bp.route('/editar_nota/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_nota(id):
    # Busca la nota por ID y usuario actual
    nota = Nota.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = NotaForm(obj=nota) # Pre-llena el formulario con los datos de la nota

    if form.validate_on_submit():
        # Actualiza los datos de la nota
        nota.titulo = form.titulo.data
        nota.descripcion = form.descripcion.data
        db.session.commit()
        flash('¡Nota actualizada exitosamente!', 'success')
        return redirect(url_for('notas.ver_notas'))
    pastel_color = generate_pastel_color() # Genera un color pastel para el fondo
    return render_template('editar_notas.html', form=form, nota=nota, pastel_color=pastel_color, generate_csrf=generate_csrf) # Pasar generate_csrf aquí también

@notas_bp.route('/borrar_nota/<int:id>', methods=['POST'])
@login_required
def borrar_nota(id):
    # Busca y borra la nota
    nota = Nota.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if nota:
        db.session.delete(nota)
        db.session.commit()
        flash('¡Nota borrada exitosamente!', 'success')
    else:
        flash('Error al intentar borrar la nota.', 'danger')
    return redirect(url_for('notas.ver_notas'))

# Función para exportar nota a PDF
@notas_bp.route('/exportar_nota_pdf/<int:id>')
@login_required
def exportar_nota_pdf(id):
    nota = Nota.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Estilo para el título de la nota
    styles.add(ParagraphStyle(name='NotaTitle', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    # Estilo para la fecha
    styles.add(ParagraphStyle(name='NotaDate', fontSize=10, leading=12, alignment=TA_RIGHT, spaceAfter=10, textColor='#666666'))
    # Estilo para la descripción
    styles.add(ParagraphStyle(name='NotaDescription', fontSize=12, leading=14, spaceAfter=10))

    story = []

    # Título de la nota
    story.append(Paragraph(nota.titulo, styles['NotaTitle']))
    # Fecha de creación
    story.append(Paragraph(f"Fecha de Creación: {nota.fecha_creacion.strftime('%d-%m-%Y %H:%M')}", styles['NotaDate']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(nota.descripcion, styles['NotaDescription']))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'nota_{nota.titulo}.pdf'
    )

# Función para exportar nota a JPG (usando Pillow y html2canvas en el frontend)
# Esta función es para el backend, pero el proceso de JPG se maneja en el frontend
# y luego se envía una imagen ya generada o se renderiza en el navegador.
# Si necesitas generar JPG en el backend, tendrías que usar librerías como imgkit (requiere wkhtmltopdf)
# o Pillow para manipular imágenes si la descripción es texto plano.
# Dado que el editor WYSIWYG genera HTML, la exportación a JPG desde el backend sería compleja.
# La solución más común es usar html2canvas en el frontend como ya lo tienes en editar_notas.html.
# Por lo tanto, no se necesita una ruta de backend para exportar a JPG si ya se hace en el frontend.

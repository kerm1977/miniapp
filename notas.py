# notas.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from PIL import Image as PILImage # Importar Pillow para JPG
import os
import re # Importar el módulo de expresiones regulares
from bs4 import BeautifulSoup # Importar BeautifulSoup para parsear HTML

# Importar db y los modelos Nota y User desde models.py
from models import db, Nota, User # ¡CORRECCIÓN AQUÍ: Agregado 'User'!
from flask_wtf.csrf import generate_csrf
from reportlab.lib.units import inch
from flask import send_file

notas_bp = Blueprint('notas', __name__, template_folder='templates')

# Formulario para Notas
class NotaForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    descripcion = TextAreaField('Descripción', validators=[DataRequired()])
    submit = SubmitField('Guardar Nota')

# Función para generar colores pastel aleatorios
def generate_pastel_color():
    """Genera un color pastel aleatorio en formato hexadecimal."""
    import random
    r = random.randint(200, 255)
    g = random.randint(200, 255)
    b = random.randint(200, 255)
    return f"#{r:02x}{g:02x}{b:02x}"

# Rutas de notas
@notas_bp.route('/ver_notas')
@login_required
def ver_notas():
    pastel_color = generate_pastel_color()
    # Asegúrate de que solo se muestran las notas del usuario actual
    user_notes = Nota.query.filter_by(usuario_id=current_user.id).order_by(Nota.fecha_creacion.desc()).all()
    # Generar un token CSRF para el botón de eliminar, si es necesario, o manejarlo con un formulario separado
    csrf_token = generate_csrf()
    return render_template('ver_notas.html', user_notes=user_notes, pastel_color=pastel_color, csrf_token=csrf_token)

@notas_bp.route('/crear_nota', methods=['GET', 'POST'])
@login_required
def crear_nota():
    form = NotaForm()
    pastel_color = generate_pastel_color()
    if form.validate_on_submit():
        # La descripción ya viene como HTML del frontend
        new_note = Nota(
            titulo=form.titulo.data,
            descripcion=form.descripcion.data, # Guardar el HTML directamente
            usuario_id=current_user.id
        )
        db.session.add(new_note)
        db.session.commit()
        flash('¡Nota creada exitosamente!', 'success')
        return redirect(url_for('notas.ver_notas'))
    return render_template('crear_notas.html', form=form, pastel_color=pastel_color, csrf_token=generate_csrf())

@notas_bp.route('/editar_nota/<int:nota_id>', methods=['GET', 'POST'])
@login_required
def editar_nota(nota_id):
    note_to_edit = Nota.query.get_or_404(nota_id)

    # Asegurarse de que el usuario actual es el propietario de la nota
    if note_to_edit.usuario_id != current_user.id:
        flash('No tienes permiso para editar esta nota.', 'danger')
        return redirect(url_for('notas.ver_notas'))

    form = NotaForm(obj=note_to_edit) # Pre-llenar el formulario con los datos de la nota existente
    pastel_color = generate_pastel_color()

    if form.validate_on_submit():
        note_to_edit.titulo = form.titulo.data
        note_to_edit.descripcion = form.descripcion.data # Actualizar con el HTML del editor
        db.session.commit()
        flash('¡Nota actualizada exitosamente!', 'success')
        return redirect(url_for('notas.ver_notas'))
    
    # Cuando se carga la página por primera vez (GET request),
    # el 'descripcion' del formulario se llena con el contenido de la DB,
    # y luego en el HTML se renderiza con |safe
    return render_template('editar_notas.html', form=form, nota=note_to_edit, pastel_color=pastel_color, csrf_token=generate_csrf())


@notas_bp.route('/eliminar_nota/<int:nota_id>', methods=['POST'])
@login_required
def eliminar_nota(nota_id):
    note_to_delete = Nota.query.get_or_404(nota_id)

    # Asegurarse de que el usuario actual es el propietario de la nota
    if note_to_delete.usuario_id != current_user.id:
        flash('No tienes permiso para eliminar esta nota.', 'danger')
        return redirect(url_for('notas.ver_notas'))

    db.session.delete(note_to_delete)
    db.session.commit()
    flash('¡Nota eliminada exitosamente!', 'success')
    return redirect(url_for('notas.ver_notas'))

@notas_bp.route('/notas/<int:nota_id>')
@login_required
def notas_detail(nota_id):
    pastel_color = generate_pastel_color()
    nota = Nota.query.get_or_404(nota_id)
    if nota.usuario_id != current_user.id:
        flash('No tienes permiso para ver esta nota.', 'danger')
        return redirect(url_for('notas.ver_notas'))
    
    csrf_token = generate_csrf()
    return render_template('notas_detail.html', nota=nota, pastel_color=pastel_color, csrf_token=csrf_token)


@notas_bp.route('/exportar_pdf/<int:nota_id>')
@login_required
def exportar_pdf(nota_id):
    nota = Nota.query.get_or_404(nota_id)

    if nota.usuario_id != current_user.id:
        flash('No tienes permiso para exportar esta nota.', 'danger')
        return redirect(url_for('notas.ver_notas'))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Estilos personalizados para la nota
    styles.add(ParagraphStyle(name='NotaTitle', fontName='Helvetica-Bold', fontSize=24, spaceAfter=14, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='NotaMeta', fontName='Helvetica', fontSize=10, textColor='#666666', spaceAfter=12, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='NotaDescription', fontName='Helvetica', fontSize=12, leading=16, spaceAfter=6, alignment=TA_JUSTIFY))

    # Título
    story.append(Paragraph(nota.titulo, styles['NotaTitle']))
    
    # Metadatos
    story.append(Paragraph(f"Creada por: {nota.usuario.username} el {nota.fecha_creacion.strftime('%d/%m/%Y a las %H:%M')}", styles['NotaMeta']))
    story.append(Spacer(1, 0.2 * inch))

    # Transformar los elementos de la lista de checkboxes para PDF
    def transform_checkbox_items_for_pdf(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for ul in soup.find_all('ul', class_='checkbox-list'):
            for li in ul.find_all('li'):
                checkbox = li.find('input', type='checkbox')
                
                # Encontrar el elemento de texto (span o s)
                text_element = li.find('span') or li.find('s')
                
                if checkbox and text_element:
                    item_text = text_element.get_text()
                    # Si el checkbox está marcado o el texto está tachado (se asume que si está tachado, el checkbox está marcado)
                    if checkbox.has_attr('checked') or text_element.name == 's':
                        li.string = f"[X] {item_text}"
                    else:
                        li.string = f"[ ] {item_text}"
                    # Eliminar el checkbox y el span/s original para dejar solo el texto transformado
                    if checkbox:
                        checkbox.decompose()
                    if text_element:
                        text_element.decompose()
        return str(soup)

    transformed_description = transform_checkbox_items_for_pdf(nota.descripcion)

    # Limpiar comentarios HTML antes de pasar a ReportLab (no es estrictamente necesario, pero es buena práctica)
    cleaned_description = re.sub(r'<!--.*?-->', '', transformed_description, flags=re.DOTALL)
    # Normalizar <br> a <br/> para compatibilidad XML si es necesario (ReportLab suele preferir esto)
    cleaned_description = cleaned_description.replace('<br>', '<br/>')

    # Ahora ReportLab puede usar el HTML transformado para renderizar la descripción.
    # El `allowXML=1` es crucial para que ReportLab interprete las etiquetas HTML.
    story.append(Paragraph(cleaned_description, styles['NotaDescription'], encoding='utf-8'))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'nota_{nota.titulo}.pdf'
    )

# La función de exportar a JPG se maneja completamente en el frontend con html2canvas.
# No se necesita una ruta de backend para generar el JPG en este caso.

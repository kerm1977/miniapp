from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import io # Importar io para BytesIO
import html.parser # Importar para el parser HTML
import re # Importar para expresiones regulares

# Importar para generación de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportlabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# Importar para generación de JPG desde PDF
from PIL import Image as PILImage # Importar Pillow para convertir a JPG
import fitz # Importar PyMuPDF para manejar PDFs (necesario para convertir a JPG)


# Importar generate_csrf para pasar el token a las plantillas
from flask_wtf.csrf import generate_csrf # Importar generate_csrf

# Importar db y el modelo Info desde models.py
from models import db, Info, User # Asegúrate de importar User también si es necesario para relaciones

# Crear un Blueprint para el módulo Info
info_bp = Blueprint('info', __name__, template_folder='templates')

# --- Formularios ---
class InfoForm(FlaskForm):
    """
    Formulario para crear y editar elementos de información.
    Incluye campos para imagen, título y un editor de texto enriquecido.
    La fecha de creación se genera automáticamente en el modelo.
    """
    imagen = FileField('Subir y visualizar imagen', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Solo se permiten imágenes (jpg, jpeg, png, gif).'), Optional()])
    titulo = StringField('Título', validators=[DataRequired()])
    # El campo de contenido se llenará desde el editor de texto HTML
    contenido = TextAreaField('Contenido', validators=[DataRequired()])
    submit = SubmitField('Guardar')

# --- Funciones Auxiliares ---
def allowed_file(filename):
    """Verifica si la extensión del archivo es una imagen permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --- Conversor HTML a ReportLab-compatible ---
class ReportLabHTMLConverter(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = []
        self.in_p = False # Para gestionar el cierre de párrafos
        self.current_tag = [] # Para manejar anidamientos simples

    def handle_starttag(self, tag, attrs):
        # Tratar <div> como <p> para ReportLab
        if tag == 'div':
            if self.in_p: # Si ya estamos en un párrafo, cerrarlo
                self.output.append('</p>')
            self.output.append('<p>')
            self.in_p = True
        elif tag == 'p':
            if self.in_p: # Si ya estamos en un párrafo, cerrarlo
                self.output.append('</p>')
            self.output.append('<p>')
            self.in_p = True
        elif tag == 'br':
            self.output.append('<br/>') # ReportLab prefiere <br/>
        elif tag in ['b', 'strong']:
            self.output.append('<b>')
            self.current_tag.append('b')
        elif tag in ['i', 'em']:
            self.output.append('<i>')
            self.current_tag.append('i')
        elif tag == 'u':
            self.output.append('<u>')
            self.current_tag.append('u')
        elif tag == 'a':
            href = dict(attrs).get('href', '#')
            self.output.append(f'<a href="{href}">')
            self.current_tag.append('a')
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.in_p: self.output.append('</p>')
            # ReportLab Paragraph no tiene estilos de encabezado nativos para HTML simple.
            # Se tratará como un párrafo en negrita.
            self.output.append('<p><b>')
            self.in_p = True
            self.current_tag.append('h') # Marcador para cerrar negrita y p
        elif tag == 'ul':
            if self.in_p: self.output.append('</p>') # Cierra párrafo si estaba abierto
            self.output.append('<ul>')
            self.in_p = False # Las listas no son párrafos simples
            self.current_tag.append('ul')
        elif tag == 'ol':
            if self.in_p: self.output.append('</p>')
            self.output.append('<ol>')
            self.in_p = False
            self.current_tag.append('ol')
        elif tag == 'li':
            self.output.append('<li>')
            self.current_tag.append('li')
        elif tag == 'img':
            # Ignorar etiquetas de imagen aquí, ya que se manejan por separado en PDF
            pass


    def handle_endtag(self, tag):
        if tag == 'div':
            if self.in_p: # Solo cerrar si se abrió un párrafo por el div
                self.output.append('</p>')
                self.in_p = False
        elif tag == 'p':
            self.output.append('</p>')
            self.in_p = False
        elif tag in ['b', 'strong']:
            if self.current_tag and self.current_tag[-1] == 'b': self.output.append('</b>'); self.current_tag.pop()
        elif tag in ['i', 'em']:
            if self.current_tag and self.current_tag[-1] == 'i': self.output.append('</i>'); self.current_tag.pop()
        elif tag == 'u':
            if self.current_tag and self.current_tag[-1] == 'u': self.output.append('</u>'); self.current_tag.pop()
        elif tag == 'a':
            if self.current_tag and self.current_tag[-1] == 'a': self.output.append('</a>'); self.current_tag.pop()
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.current_tag and self.current_tag[-1] == 'h': self.output.append('</b></p>'); self.current_tag.pop()
            self.in_p = False
        elif tag == 'ul':
            if self.current_tag and self.current_tag[-1] == 'ul': self.output.append('</ul>'); self.current_tag.pop()
        elif tag == 'ol':
            if self.current_tag and self.current_tag[-1] == 'ol': self.output.append('</ol>'); self.current_tag.pop()
        elif tag == 'li':
            if self.current_tag and self.current_tag[-1] == 'li': self.output.append('</li>'); self.current_tag.pop()


    def handle_data(self, data):
        self.output.append(html.unescape(data)) # Desescapar entidades HTML

    def handle_entityref(self, name):
        self.output.append(f'&{name};')

    def handle_charref(self, name):
        self.output.append(f'&#{name};')

    def get_output(self):
        # Asegurar que cualquier párrafo o etiqueta de bloque abierta sea cerrada
        if self.in_p:
            self.output.append('</p>')
        
        # Unir todas las partes y limpiar posibles espacios en blanco excesivos
        final_output = "".join(self.output)
        # Reemplazar múltiples <br/> seguidos con un solo <br/>
        final_output = re.sub(r'(<br/>\s*){2,}', '<br/>', final_output)
        # Eliminar <p><br/></p> que son párrafos vacíos
        final_output = re.sub(r'<p>\s*<br/>\s*</p>', '', final_output)
        # Eliminar párrafos vacíos
        final_output = re.sub(r'<p>\s*</p>', '', final_output)

        return final_output.strip() # Eliminar espacios en blanco al inicio/final

def convert_html_for_reportlab(html_content):
    parser = ReportLabHTMLConverter()
    parser.feed(html_content)
    parser.close()
    return parser.get_output()

# --- Rutas ---

@info_bp.route('/ver_info')
@login_required
def ver_info():
    """
    Muestra una lista de todos los elementos de información creados por el usuario actual.
    """
    info_items = Info.query.filter_by(usuario_id=current_user.id).order_by(Info.fecha_creacion.desc()).all()
    return render_template('ver_info.html', info_items=info_items, generate_csrf=generate_csrf)

@info_bp.route('/crear_info', methods=['GET', 'POST'])
@login_required
def crear_info():
    """
    Permite al usuario crear un nuevo elemento de información.
    Soporta la subida de imágenes y el uso de un editor de texto.
    """
    form = InfoForm()
    if form.validate_on_submit():
        imagen_filename = None
        if form.imagen.data:
            if allowed_file(form.imagen.data.filename):
                filename = secure_filename(form.imagen.data.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                filepath = os.path.join(upload_folder, filename)
                form.imagen.data.save(filepath)
                imagen_filename = filename
            else:
                flash('Tipo de archivo de imagen no permitido.', 'danger')
                return render_template('crear_info.html', form=form, generate_csrf=generate_csrf)

        new_info = Info(
            usuario_id=current_user.id,
            imagen_filename=imagen_filename,
            titulo=form.titulo.data,
            contenido=request.form.get('contenido'),
            fecha_creacion=datetime.utcnow()
        )
        db.session.add(new_info)
        db.session.commit()
        flash('¡Información creada exitosamente!', 'success')
        return redirect(url_for('info.ver_info'))
    return render_template('crear_info.html', form=form, generate_csrf=generate_csrf)

@info_bp.route('/editar_info/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_info(id):
    """
    Permite editar un elemento de información existente.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = InfoForm(obj=info_item)

    if form.validate_on_submit():
        if form.imagen.data:
            if allowed_file(form.imagen.data.filename):
                if info_item.imagen_filename and info_item.imagen_filename != form.imagen.data.filename:
                    old_image_path = os.path.join(current_app.root_path, 'static', 'uploads', info_item.imagen_filename)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                filename = secure_filename(form.imagen.data.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                filepath = os.path.join(upload_folder, filename)
                form.imagen.data.save(filepath)
                info_item.imagen_filename = filename
            else:
                flash('Tipo de archivo de imagen no permitido.', 'danger')
                return render_template('editar_info.html', form=form, info_item=info_item, generate_csrf=generate_csrf)

        info_item.titulo = form.titulo.data
        updated_content = request.form.get('contenido')
        if updated_content is not None:
            info_item.contenido = updated_content
        else:
            flash('El contenido no puede estar vacío.', 'danger')
            return render_template('editar_info.html', form=form, info_item=info_item, generate_csrf=generate_csrf)

        db.session.commit()
        flash('¡Información actualizada exitosamente!', 'success')
        return redirect(url_for('info.ver_info'))
    
    if request.method == 'GET':
        form.contenido.data = info_item.contenido 

    return render_template('editar_info.html', form=form, info_item=info_item, generate_csrf=generate_csrf)

@info_bp.route('/detalle_info/<int:id>')
@login_required
def detalle_info(id):
    """
    Muestra los detalles de un elemento de información específico.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    return render_template('detalle_info.html', info_item=info_item, generate_csrf=generate_csrf)

@info_bp.route('/borrar_info/<int:id>', methods=['POST'])
@login_required
def borrar_info(id):
    """
    Borra un elemento de información.
    También elimina la imagen asociada si existe.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if info_item:
        if info_item.imagen_filename:
            image_path = os.path.join(current_app.root_path, 'static', 'uploads', info_item.imagen_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(info_item)
        db.session.commit()
        flash('¡Información borrada exitosamente!', 'success')
    else:
        flash('Error al intentar borrar la información.', 'danger')
    return redirect(url_for('info.ver_info'))

@info_bp.route('/exportar_pdf_info/<int:id>')
@login_required
def exportar_pdf_info(id):
    """
    Exporta el detalle de una información a PDF.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Definir estilos antes de su uso
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['h1'],
        alignment=TA_CENTER,
        spaceAfter=14
    )
    date_style = ParagraphStyle(
        name='DateStyle',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=12
    )
    content_style = ParagraphStyle( # Definición de content_style movida al inicio
        name='ContentStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        spaceAfter=6
    )

    story.append(Paragraph(info_item.titulo, title_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"Creado el: {info_item.fecha_creacion.strftime('%d-%m-%Y %H:%M')}", date_style))
    story.append(Spacer(1, 0.2 * inch))

    # Imagen si existe
    if info_item.imagen_filename:
        image_path = os.path.join(current_app.root_path, 'static', 'uploads', info_item.imagen_filename)
        if os.path.exists(image_path):
            try:
                img = ImageReader(image_path)
                img_width, img_height = img.getSize()
                max_width = letter[0] - 2 * inch
                
                if img_width > max_width:
                    scale_factor = max_width / img_width
                    img_width = max_width
                    img_height *= scale_factor
                
                max_height = letter[1] / 3
                if img_height > max_height:
                    scale_factor = max_height / img_height
                    img_height = max_height
                    img_width *= scale_factor


                story.append(ReportlabImage(image_path, width=img_width, height=img_height))
                story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                flash(f"Error al incluir la imagen en el PDF: {e}", "danger")
                print(f"Error al incluir la imagen en el PDF: {e}")

    # Contenido (descripción) - Usar el conversor HTML
    reportlab_compatible_html = convert_html_for_reportlab(info_item.contenido)
    story.append(Paragraph(reportlab_compatible_html, content_style))
    story.append(Spacer(1, 0.5 * inch))


    try:
        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"informacion_{info_item.titulo}.pdf", mimetype='application/pdf')
    except Exception as e:
        flash(f"Error al generar el PDF: {e}", "danger")
        print(f"Error al generar el PDF: {e}")
        return redirect(url_for('info.detalle_info', id=id))

@info_bp.route('/exportar_jpg_info/<int:id>')
@login_required
def exportar_jpg_info(id):
    """
    Exporta el detalle de una información a JPG (convirtiendo el PDF generado).
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    # Primero, genera el PDF en memoria
    buffer_pdf = io.BytesIO()
    doc_pdf = SimpleDocTemplate(buffer_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Definir estilos antes de su uso
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['h1'],
        alignment=TA_CENTER,
        spaceAfter=14
    )
    date_style = ParagraphStyle(
        name='DateStyle',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=12
    )
    content_style = ParagraphStyle( # Definición de content_style movida al inicio
        name='ContentStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        spaceAfter=6
    )

    story.append(Paragraph(info_item.titulo, title_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"Creado el: {info_item.fecha_creacion.strftime('%d-%m-%Y %H:%M')}", date_style))
    story.append(Spacer(1, 0.2 * inch))

    # Imagen si existe
    if info_item.imagen_filename:
        image_path = os.path.join(current_app.root_path, 'static', 'uploads', info_item.imagen_filename)
        if os.path.exists(image_path):
            try:
                img = ImageReader(image_path)
                img_width, img_height = img.getSize()
                max_width = letter[0] - 2 * inch 
                if img_width > max_width:
                    scale_factor = max_width / img_width
                    img_width = max_width
                    img_height *= scale_factor
                max_height = letter[1] / 3
                if img_height > max_height:
                    scale_factor = max_height / img_height
                    img_height = max_height
                    img_width *= scale_factor

                story.append(ReportlabImage(image_path, width=img_width, height=img_height))
                story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                flash(f"Error al incluir la imagen en el PDF para JPG: {e}", "danger")
                print(f"Error al incluir la imagen en el PDF para JPG: {e}")

    # Contenido - Usar el conversor HTML
    reportlab_compatible_html = convert_html_for_reportlab(info_item.contenido)
    story.append(Paragraph(reportlab_compatible_html, content_style))
    story.append(Spacer(1, 0.5 * inch))

    try:
        doc_pdf.build(story)
        buffer_pdf.seek(0)

        # Usar PyMuPDF para convertir la primera página del PDF a JPG
        doc_fitz = fitz.open("pdf", buffer_pdf.read()) # Abrir desde el buffer del PDF
        page = doc_fitz[0] # Obtener la primera página
        
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Aumentar la resolución para mejor calidad

        img_buffer = io.BytesIO()
        # 'RGB' para asegurar compatibilidad con JPG, ya que pixmap puede ser RGBA
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples) 
        img.save(img_buffer, "JPEG", quality=90) # Ajustar calidad si es necesario
        img_buffer.seek(0)
        doc_fitz.close()
        
        filename = f"informacion_{info_item.titulo}.jpg"
        return send_file(img_buffer, as_attachment=True, download_name=filename, mimetype='image/jpeg')
    except Exception as e:
        flash(f"Error al convertir PDF a JPG: {e}. Asegúrese de tener PyMuPDF (fitz) y Pillow instalados.", "danger")
        print(f"Error al convertir PDF a JPG: {e}")
        return redirect(url_for('info.detalle_info', id=id))

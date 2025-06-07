from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file, g
from flask_login import login_required, current_user # <-- CORRECCIÓN AQUÍ: current_user se importa desde flask_login
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, FileField, TextAreaField, DecimalField, BooleanField
from wtforms.validators import DataRequired, Optional, Length, Regexp, NumberRange
from wtforms.widgets import DateInput
from flask_wtf.file import FileAllowed
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date
import json # Para manejar la lista de acompañantes
from io import BytesIO
import base64
import mimetypes
import urllib.parse # <-- IMPORTACIÓN AÑADIDA AQUÍ para quote_plus

# Importar db y los modelos desde models.py
from models import db, User, Contacto, GestorProyecto

# Para la generación de PDF/JPG/TXT (se usarán en fragmentos posteriores)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage # Renombrar para evitar conflicto con Image de ReportLab
import fitz # PyMuPDF - Requiere 'pip install pymupdf'

gestor_bp = Blueprint('gestor', __name__, template_folder='templates', static_folder='static')

# --- Rutas de Archivos para Gestor de Proyectos ---
UPLOAD_PROJECT_FOLDER = os.path.join('static', 'uploads', 'proyectos')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def configure_gestor_uploads(app):
    """Configura la carpeta de subida para las imágenes de proyectos."""
    app.config['UPLOAD_PROJECT_FOLDER'] = UPLOAD_PROJECT_FOLDER
    app.config['ALLOWED_IMAGE_EXTENSIONS_GESTOR'] = ALLOWED_IMAGE_EXTENSIONS
    if not os.path.exists(UPLOAD_PROJECT_FOLDER):
        os.makedirs(UPLOAD_PROJECT_FOLDER)
    print(f"Carpeta de subidas de proyectos configurada en: {UPLOAD_PROJECT_FOLDER}")


# --- Datos de Provincias y Cantones de Costa Rica ---
PROVINCIAS_CR = [
    ('Alajuela', 'Alajuela'),
    ('Cartago', 'Cartago'),
    ('Heredia', 'Heredia'),
    ('Limón', 'Limón'),
    ('Puntarenas', 'Puntarenas'),
    ('Guanacaste', 'Guanacaste'),
    ('San José', 'San José')
]

CANTONES_CR = {
    'Alajuela': [
        ('Alajuela', 'Alajuela'), ('San Ramón', 'San Ramón'), ('Grecia', 'Grecia'), 
        ('San Mateo', 'San Mateo'), ('Atenas', 'Atenas'), ('Naranjo', 'Naranjo'), 
        ('Palmares', 'Palmares'), ('Poás', 'Poás'), ('Orotina', 'Orotina'), 
        ('San Carlos', 'San Carlos'), ('Zarcero', 'Zarcero'), ('Sarchí', 'Sarchí'), 
        ('Upala', 'Upala'), ('Los Chiles', 'Los Chiles'), ('Guatuso', 'Guatuso'), 
        ('Río Cuarto', 'Río Cuarto')
    ],
    'Cartago': [
        ('Cartago', 'Cartago'), ('Paraíso', 'Paraíso'), ('La Unión', 'La Unión'), 
        ('Jiménez', 'Jiménez'), ('Turrialba', 'Turrialba'), ('Alvarado', 'Alvarado'), 
        ('Oreamuno', 'Oreamuno'), ('El Guarco', 'El Guarco')
    ],
    'Heredia': [
        ('Heredia', 'Heredia'), ('Barva', 'Barva'), ('Santo Domingo', 'Santo Domingo'), 
        ('Santa Bárbara', 'Santa Bárbara'), ('San Rafael', 'San Rafael'), ('San Isidro', 'San Isidro'), 
        ('Belén', 'Belén'), ('Flores', 'Flores'), ('San Pablo', 'San Pablo'), 
        ('Sarapiquí', 'Sarapiquí')
    ],
    'Limón': [
        ('Limón', 'Limón'), ('Pococí', 'Pococí'), ('Siquirres', 'Siquirres'), 
        ('Talamanca', 'Talamanca'), ('Matina', 'Matina'), ('Guácimo', 'Guácimo')
    ],
    'Puntarenas': [
        ('Puntarenas', 'Puntarenas'), ('Esparza', 'Esparza'), ('Buenos Aires', 'Buenos Aires'), 
        ('Montes de Oro', 'Montes de Oro'), ('Osa', 'Osa'), ('Quepos', 'Quepos'), 
        ('Golfito', 'Golfito'), ('Coto Brus', 'Coto Brus'), ('Parrita', 'Parrita'), 
        ('Corredores', 'Corredores'), ('Garabito', 'Garabito')
    ],
    'Guanacaste': [
        ('Liberia', 'Liberia'), ('Nicoya', 'Nicoya'), ('Santa Cruz', 'Santa Cruz'), 
        ('Bagaces', 'Bagaces'), ('Carrillo', 'Carrillo'), ('Cañas', 'Cañas'), 
        ('Abangares', 'Abangares'), ('Tilarán', 'Tilarán'), ('Nandayure', 'Nandayure'), 
        ('La Cruz', 'La Cruz'), ('Hojancha', 'Hojancha')
    ],
    'San José': [
        ('San José', 'San José'), ('Escazú', 'Escazú'), ('Desamparados', 'Desamparados'), 
        ('Puriscal', 'Puriscal'), ('Tarrazú', 'Tarrazú'), ('Aserrí', 'Aserrí'), 
        ('Mora', 'Mora'), ('Goicoechea', 'Goicoechea'), ('Santa Ana', 'Santa Ana'), 
        ('Alajuelita', 'Alajuelita'), ('Vázquez de Coronado', 'Vázquez de Coronado'), 
        ('Acosta', 'Acosta'), ('Tibás', 'Tibás'), ('Moravia', 'Moravia'), 
        ('Montes de Oca', 'Montes de Oca'), ('Turrubares', 'Turrubares'), 
        ('Dota', 'Dota'), ('Curridabat', 'Curridabat'), ('Pérez Zeledón', 'Pérez Zeledón'), 
        ('León Cortés Castro', 'León Cortés Castro')
    ]
}

# --- Formularios ---
class GestorProyectoForm(FlaskForm):
    nombre_proyecto = StringField('Nombre del Proyecto', validators=[DataRequired()])
    imagen_proyecto = FileField('Imagen del Proyecto', validators=[FileAllowed(ALLOWED_IMAGE_EXTENSIONS, 'Solo se permiten imágenes (png, jpg, jpeg, gif).'), Optional()])
    propuesta_por = SelectField('Propuesta Por', choices=[
        ('Kenneth Ruiz Matamoros', 'Kenneth Ruiz Matamoros'),
        ('Jenny Ceciliano Cordoba', 'Jenny Ceciliano Cordoba'),
        ('Invitado', 'Invitado')
    ], validators=[DataRequired()])
    nombre_invitado = StringField('Nombre del Invitado (si aplica)', validators=[Optional()])
    provincia = SelectField('Provincia', choices=PROVINCIAS_CR, validators=[DataRequired()])
    canton = SelectField('Cantón', choices=[], validators=[DataRequired()]) # Se llenará dinámicamente
    fecha_actividad_propuesta = StringField('Fecha de Actividad Propuesta (YYYY-MM-DD)', validators=[DataRequired()], widget=DateInput())
    dificultad = SelectField('Dificultad', choices=[
        ('Paseo', 'Paseo'),
        ('Básico', 'Básico'),
        ('Intermedio', 'Intermedio'),
        ('Dificil', 'Dificil'),
        ('Avanzado', 'Avanzado'),
        ('Técnico', 'Técnico')
    ], validators=[DataRequired()])
    acompanantes = SelectField('Acompañantes (selecciona uno o más)', choices=[], coerce=int, validators=[Optional()], render_kw={'multiple': True}) # Múltiples seleccionables
    transporte = SelectField('Transporte', choices=[
        ('Moto', 'Moto'),
        ('Auto', 'Auto'),
        ('Bus', 'Bus'),
        ('Buseta', 'Buseta')
    ], validators=[DataRequired()])
    transporte_adicional = SelectField('Transporte Adicional', choices=[
        ('No aplica', 'No aplica'),
        ('Acuatico', 'Acuático'),
        ('Aereo', 'Aéreo')
    ], default='No aplica', validators=[Optional()])
    precio_entrada = DecimalField('Precio Entrada (₡)', validators=[Optional(), NumberRange(min=0)], places=2, default=0.00)
    nombre_lugar = StringField('Nombre del Lugar', validators=[DataRequired()])
    contacto_lugar = StringField('Contacto del Lugar', validators=[Optional()])
    telefono_lugar = StringField('Teléfono del Lugar', validators=[Optional(), Regexp('^[0-9]+$', message='El teléfono debe contener solo dígitos.')])
    tipo_terreno = SelectField('Tipo de Terreno', choices=[
        ('Asfalto', 'Asfalto'),
        ('Lastre', 'Lastre'),
        ('Montaña', 'Montaña'),
        ('Arena', 'Arena')
    ], validators=[DataRequired()])
    mas_tipo_terreno = BooleanField('Indique si tiene más tipo de terreno')
    notas_adicionales = TextAreaField('Notas Adicionales', validators=[Optional()])
    submit = SubmitField('Guardar Proyecto')

    def __init__(self, *args, **kwargs):
        super(GestorProyectoForm, self).__init__(*args, **kwargs)
        if current_user and hasattr(current_user, 'id'):
            # Cargar cantones para la provincia por defecto (San José) o la primera en la lista
            default_province = self.provincia.data if self.provincia.data else PROVINCIAS_CR[0][0]
            self.canton.choices = CANTONES_CR.get(default_province, [])

            # Cargar acompañantes desde la base de datos (modelo Contacto)
            contacts = Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre).all()
            self.acompanantes.choices = [(c.id, f"{c.nombre} {c.primer_apellido or ''}") for c in contacts]
        else:
            self.canton.choices = []
            self.acompanantes.choices = []


# --- Rutas de API para Cantones ---
@gestor_bp.route('/get_cantones/<provincia>')
@login_required
def get_cantones(provincia):
    """Retorna los cantones para una provincia dada."""
    cantones = CANTONES_CR.get(provincia, [])
    return jsonify(cantones)

# --- Rutas del CRUD para Gestor de Proyectos ---

@gestor_bp.route('/ver_proyectos')
@login_required
def ver_proyectos():
    """Muestra una lista de todos los proyectos del usuario actual."""
    proyectos = GestorProyecto.query.filter_by(usuario_id=current_user.id).order_by(GestorProyecto.fecha_actividad_propuesta.desc()).all()
    
    # Para mostrar los nombres de los acompañantes en la vista
    for proyecto in proyectos:
        if proyecto.acompanantes:
            acompanantes_ids = json.loads(proyecto.acompanantes)
            # Asegura que acompanantes_ids sea siempre una lista, incluso si json.loads devuelve un solo entero
            if not isinstance(acompanantes_ids, list):
                acompanantes_ids = [acompanantes_ids]
            
            # Fetch full contact objects based on IDs
            proyecto.acompanantes_nombres = Contacto.query.filter(
                Contacto.id.in_(acompanantes_ids),
                Contacto.usuario_id == current_user.id
            ).all()
        else:
            proyecto.acompanantes_nombres = []

    return render_template('ver_gestor.html', proyectos=proyectos)

@gestor_bp.route('/crear_proyecto', methods=['GET', 'POST'])
@login_required
def crear_proyecto():
    form = GestorProyectoForm()
    
    if form.validate_on_submit():
        try:
            imagen_proyecto_filename = None
            if form.imagen_proyecto.data:
                filename = secure_filename(form.imagen_proyecto.data.filename)
                imagen_proyecto_filename = os.path.join(UPLOAD_PROJECT_FOLDER, filename)
                form.imagen_proyecto.data.save(imagen_proyecto_filename)
                
                # Almacenar solo el nombre del archivo o la ruta relativa si prefieres
                imagen_proyecto_filename = filename 

            fecha_actividad_propuesta_obj = datetime.strptime(form.fecha_actividad_propuesta.data, '%Y-%m-%d').date()

            # Convertir la lista de IDs de acompañantes a una cadena JSON
            acompanantes_json = json.dumps(form.acompanantes.data) if form.acompanantes.data else '[]'

            nuevo_proyecto = GestorProyecto(
                usuario_id=current_user.id,
                nombre_proyecto=form.nombre_proyecto.data,
                imagen_proyecto=imagen_proyecto_filename,
                propuesta_por=form.propuesta_por.data,
                nombre_invitado=form.nombre_invitado.data if form.propuesta_por.data == 'Invitado' else None,
                provincia=form.provincia.data,
                canton=form.canton.data,
                fecha_actividad_propuesta=fecha_actividad_propuesta_obj,
                dificultad=form.dificultad.data,
                acompanantes=acompanantes_json,
                transporte=form.transporte.data,
                transporte_adicional=form.transporte_adicional.data,
                precio_entrada=form.precio_entrada.data,
                nombre_lugar=form.nombre_lugar.data,
                contacto_lugar=form.contacto_lugar.data,
                telefono_lugar=form.telefono_lugar.data,
                tipo_terreno=form.tipo_terreno.data,
                mas_tipo_terreno=form.mas_tipo_terreno.data,
                notas_adicionales=form.notas_adicionales.data
            )
            db.session.add(nuevo_proyecto)
            db.session.commit()
            flash('¡Proyecto creado exitosamente!', 'success')
            return redirect(url_for('gestor.ver_proyectos'))
        except ValueError as e:
            flash(f'Error de formato en la fecha o datos numéricos: {e}. Asegúrese de usarYYYY-MM-DD.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al guardar el proyecto: {e}', 'danger')
    
    # Recargar opciones de cantones si la provincia está precargada (ej. después de un error de validación)
    if request.method == 'GET' and form.provincia.data:
        form.canton.choices = CANTONES_CR.get(form.provincia.data, [])
    elif request.method == 'POST' and form.provincia.data: # Si hubo un error POST, mantener cantones
         form.canton.choices = CANTONES_CR.get(form.provincia.data, [])

    return render_template('crear_gestor.html', form=form, CANTONES_CR=CANTONES_CR)

@gestor_bp.route('/editar_proyecto/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_proyecto(id):
    """Permite al usuario editar un proyecto existente."""
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = GestorProyectoForm(obj=proyecto)

    # Si es una petición GET, precargar los datos del proyecto en el formulario
    if request.method == 'GET':
        form.fecha_actividad_propuesta.data = proyecto.fecha_actividad_propuesta.strftime('%Y-%m-%d') if proyecto.fecha_actividad_propuesta else ''
        
        # Cargar los cantones correctos para la provincia del proyecto
        form.canton.choices = CANTONES_CR.get(proyecto.provincia, [])
        form.canton.data = proyecto.canton # Seleccionar el cantón actual del proyecto

        # Cargar acompañantes seleccionados
        if proyecto.acompanantes:
            form.acompanantes.data = json.loads(proyecto.acompanantes)
        else:
            form.acompanantes.data = []

    if form.validate_on_submit():
        try:
            # Manejo de la imagen de proyecto
            if form.imagen_proyecto.data: # Si se sube una nueva imagen
                # Eliminar la imagen anterior si existe
                if proyecto.imagen_proyecto and os.path.exists(os.path.join(UPLOAD_PROJECT_FOLDER, proyecto.imagen_proyecto)):
                    os.remove(os.path.join(UPLOAD_PROJECT_FOLDER, proyecto.imagen_proyecto))
                
                filename = secure_filename(form.imagen_proyecto.data.filename)
                filepath = os.path.join(UPLOAD_PROJECT_FOLDER, filename)
                form.imagen_proyecto.data.save(filepath)
                proyecto.imagen_proyecto = filename # Guardar solo el nombre del archivo
            # Si no se sube una nueva imagen, y el campo de imagen no está vacío, mantener la existente
            # Si el campo de imagen está vacío y antes había una, no se hace nada.
            # Si se desea eliminar la imagen sin subir una nueva, se necesitaría un checkbox adicional.

            proyecto.nombre_proyecto = form.nombre_proyecto.data
            proyecto.propuesta_por = form.propuesta_por.data
            proyecto.nombre_invitado = form.nombre_invitado.data if form.propuesta_por.data == 'Invitado' else None
            proyecto.provincia = form.provincia.data
            proyecto.canton = form.canton.data
            proyecto.fecha_actividad_propuesta = datetime.strptime(form.fecha_actividad_propuesta.data, '%Y-%m-%d').date()
            proyecto.dificultad = form.dificultad.data
            proyecto.acompanantes = json.dumps(form.acompanantes.data) if form.acompanantes.data else '[]'
            proyecto.transporte = form.transporte.data
            proyecto.transporte_adicional = form.transporte_adicional.data
            proyecto.precio_entrada = form.precio_entrada.data
            proyecto.nombre_lugar = form.nombre_lugar.data
            proyecto.contacto_lugar = form.contacto_lugar.data
            proyecto.telefono_lugar = form.telefono_lugar.data
            proyecto.tipo_terreno = form.tipo_terreno.data
            proyecto.mas_tipo_terreno = form.mas_tipo_terreno.data
            proyecto.notas_adicionales = form.notas_adicionales.data

            db.session.commit()
            flash('¡Proyecto actualizado exitosamente!', 'success')
            return redirect(url_for('gestor.ver_proyectos'))
        except ValueError as e:
            flash(f'Error de formato en la fecha o datos numéricos: {e}. Asegúrese de usarYYYY-MM-DD.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al actualizar el proyecto: {e}', 'danger')
    
    # Recargar opciones de cantones si la provincia está precargada (ej. después de un error de validación)
    if request.method == 'GET' and form.provincia.data:
        form.canton.choices = CANTONES_CR.get(form.provincia.data, [])
    elif request.method == 'POST' and form.provincia.data: # Si hubo un error POST, mantener cantones
         form.canton.choices = CANTONES_CR.get(form.provincia.data, [])

    return render_template('editar_gestor.html', form=form, proyecto=proyecto, CANTONES_CR=CANTONES_CR)

@gestor_bp.route('/borrar_proyecto/<int:id>', methods=['POST'])
@login_required
def borrar_proyecto(id):
    """Borra un proyecto existente."""
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if proyecto:
        # Eliminar la imagen asociada si existe
        if proyecto.imagen_proyecto and os.path.exists(os.path.join(UPLOAD_PROJECT_FOLDER, proyecto.imagen_proyecto)):
            os.remove(os.path.join(UPLOAD_PROJECT_FOLDER, proyecto.imagen_proyecto))
        
        db.session.delete(proyecto)
        db.session.commit()
        flash('¡Proyecto borrado exitosamente!', 'success')
    else:
        flash('Error al intentar borrar el proyecto.', 'danger')
    return redirect(url_for('gestor.ver_proyectos'))

@gestor_bp.route('/detalle_proyecto/<int:id>')
@login_required
def detalle_proyecto(id):
    """Muestra los detalles de un proyecto específico."""
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    
    acompanantes_data = []
    if proyecto.acompanantes:
        acompanantes_ids = json.loads(proyecto.acompanantes)
        # Asegura que acompanantes_ids sea siempre una lista
        if not isinstance(acompanantes_ids, list):
            acompanantes_ids = [acompanantes_ids]

        acompanantes_objetos = Contacto.query.filter(
            Contacto.id.in_(acompanantes_ids),
            Contacto.usuario_id == current_user.id
        ).all()
        acompanantes_data = [f"{c.nombre} {c.primer_apellido or ''}" for c in acompanantes_objetos]

    return render_template('detalle_gestor.html', proyecto=proyecto, acompanantes_data=acompanantes_data)

# --- Funciones de Exportación y WhatsApp (se añadirán en el siguiente fragmento) ---
# Se dejan aquí para mostrar que serán parte de gestor.py
@gestor_bp.route('/exportar_proyecto_pdf/<int:id>')
@login_required
def exportar_proyecto_pdf(id):
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados
    styles.add(ParagraphStyle(name='ProjectTitle', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold', textColor=colors.HexColor('#007bff')))
    styles.add(ParagraphStyle(name='DetailLabel', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#333333')))
    styles.add(ParagraphStyle(name='DetailValue', fontSize=10, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='NotesText', fontSize=10, leading=12, spaceBefore=6, spaceAfter=6, fontName='Helvetica'))
    
    story = []

    # Título del Proyecto
    story.append(Paragraph(f"Proyecto: {proyecto.nombre_proyecto}", styles['ProjectTitle']))
    story.append(Spacer(1, 0.2 * inch))

    # Imagen del Proyecto (si existe)
    if proyecto.imagen_proyecto:
        image_path = os.path.join(UPLOAD_PROJECT_FOLDER, proyecto.imagen_proyecto)
        if os.path.exists(image_path):
            try:
                img = Image(image_path)
                img_width = 3 * inch
                img_height = img_width * (img.drawHeight / img.drawWidth) # Mantener proporción
                img.drawWidth = img_width
                img.drawHeight = img_height
                story.append(img)
                story.append(Spacer(1, 0.1 * inch))
            except Exception as e:
                print(f"Error al cargar la imagen para PDF: {e}")
                story.append(Paragraph("<i>(Imagen no disponible)</i>", styles['DetailValue']))
    story.append(Spacer(1, 0.2 * inch))

    # Sección de Detalles del Proyecto
    story.append(Paragraph("Detalles del Proyecto", styles['SectionHeader']))
    details_data = [
        [Paragraph("<b>Propuesta Por:</b>", styles['DetailLabel']), Paragraph(proyecto.propuesta_por, styles['DetailValue'])],
        [Paragraph("<b>Nombre Invitado:</b>", styles['DetailLabel']), Paragraph(proyecto.nombre_invitado or 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Provincia:</b>", styles['DetailLabel']), Paragraph(proyecto.provincia, styles['DetailValue'])],
        [Paragraph("<b>Cantón:</b>", styles['DetailLabel']), Paragraph(proyecto.canton, styles['DetailValue'])],
        [Paragraph("<b>Fecha Actividad Propuesta:</b>", styles['DetailLabel']), Paragraph(proyecto.fecha_actividad_propuesta.strftime('%Y-%m-%d'), styles['DetailValue'])],
        [Paragraph("<b>Dificultad:</b>", styles['DetailLabel']), Paragraph(proyecto.dificultad, styles['DetailValue'])],
        [Paragraph("<b>Transporte:</b>", styles['DetailLabel']), Paragraph(proyecto.transporte, styles['DetailValue'])],
        [Paragraph("<b>Transporte Adicional:</b>", styles['DetailLabel']), Paragraph(proyecto.transporte_adicional, styles['DetailValue'])],
        [Paragraph("<b>Precio Entrada:</b>", styles['DetailLabel']), Paragraph(f"₡{proyecto.precio_entrada:,.2f}" if proyecto.precio_entrada is not None else 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Nombre del Lugar:</b>", styles['DetailLabel']), Paragraph(proyecto.nombre_lugar, styles['DetailValue'])],
        [Paragraph("<b>Contacto del Lugar:</b>", styles['DetailLabel']), Paragraph(proyecto.contacto_lugar or 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Teléfono del Lugar:</b>", styles['DetailLabel']), Paragraph(proyecto.telefono_lugar or 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Tipo de Terreno:</b>", styles['DetailLabel']), Paragraph(proyecto.tipo_terreno, styles['DetailValue'])],
        [Paragraph("<b>Más Tipo de Terreno:</b>", styles['DetailLabel']), Paragraph('Sí' if proyecto.mas_tipo_terreno else 'No', styles['DetailValue'])],
    ]
    details_table = Table(details_data, colWidths=[2.5 * inch, 5 * inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 0.2 * inch))

    # Sección de Acompañantes
    story.append(Paragraph("Acompañantes", styles['SectionHeader']))
    acompanantes_list = []
    if proyecto.acompanantes:
        acompanantes_ids = json.loads(proyecto.acompanantes)
        # Asegura que acompanantes_ids sea siempre una lista
        if not isinstance(acompanantes_ids, list):
            acompanantes_ids = [acompanantes_ids]
        acompanantes_objetos = Contacto.query.filter(
            Contacto.id.in_(acompanantes_ids),
            Contacto.usuario_id == current_user.id
        ).all()
        if acompanantes_objetos:
            for contacto in acompanantes_objetos:
                acompanantes_list.append([Paragraph(f"- {contacto.nombre} {contacto.primer_apellido or ''} ({contacto.movil or contacto.telefono or 'N/A'})", styles['DetailValue'])])
        else:
            acompanantes_list.append([Paragraph("No se han especificado acompañantes o no se encontraron.", styles['DetailValue'])])
    else:
        acompanantes_list.append([Paragraph("No se han especificado acompañantes.", styles['DetailValue'])])
    
    if acompanantes_list:
        acompanantes_table = Table(acompanantes_list, colWidths=[7.5 * inch])
        acompanantes_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(acompanantes_table)
    story.append(Spacer(1, 0.2 * inch))

    # Notas Adicionales
    if proyecto.notas_adicionales:
        story.append(Paragraph("Notas Adicionales", styles['SectionHeader']))
        story.append(Paragraph(proyecto.notas_adicionales, styles['NotesText']))
        story.append(Spacer(1, 0.2 * inch))

    # Fecha de Creación
    story.append(Paragraph(f"<i>Fecha de Creación: {proyecto.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}</i>", styles['DetailValue']))

    doc.build(story)
    buffer.seek(0)
    
    filename = f"proyecto_{proyecto.nombre_proyecto.replace(' ', '_').lower()}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@gestor_bp.route('/exportar_proyecto_jpg/<int:id>')
@login_required
def exportar_proyecto_jpg(id):
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    # Primero, generar el PDF en memoria
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados (duplicados de la función de PDF para asegurar independencia)
    styles.add(ParagraphStyle(name='ProjectTitle', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold', textColor=colors.HexColor('#007bff')))
    styles.add(ParagraphStyle(name='DetailLabel', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#333333')))
    styles.add(ParagraphStyle(name='DetailValue', fontSize=10, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='NotesText', fontSize=10, leading=12, spaceBefore=6, spaceAfter=6, fontName='Helvetica'))
    
    story = []

    # Título del Proyecto
    story.append(Paragraph(f"Proyecto: {proyecto.nombre_proyecto}", styles['ProjectTitle']))
    story.append(Spacer(1, 0.2 * inch))

    # Imagen del Proyecto (si existe)
    if proyecto.imagen_proyecto:
        image_path = os.path.join(UPLOAD_PROJECT_FOLDER, proyecto.imagen_proyecto)
        if os.path.exists(image_path):
            try:
                img = Image(image_path)
                img_width = 3 * inch
                img_height = img_width * (img.drawHeight / img.drawWidth) # Mantener proporción
                img.drawWidth = img_width
                img.drawHeight = img_height
                story.append(img)
                story.append(Spacer(1, 0.1 * inch))
            except Exception as e:
                print(f"Error al cargar la imagen para PDF (JPG): {e}")
                story.append(Paragraph("<i>(Imagen no disponible)</i>", styles['DetailValue']))
    story.append(Spacer(1, 0.2 * inch))

    # Sección de Detalles del Proyecto
    story.append(Paragraph("Detalles del Proyecto", styles['SectionHeader']))
    details_data = [
        [Paragraph("<b>Propuesta Por:</b>", styles['DetailLabel']), Paragraph(proyecto.propuesta_por, styles['DetailValue'])],
        [Paragraph("<b>Nombre Invitado:</b>", styles['DetailLabel']), Paragraph(proyecto.nombre_invitado or 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Provincia:</b>", styles['DetailLabel']), Paragraph(proyecto.provincia, styles['DetailValue'])],
        [Paragraph("<b>Cantón:</b>", styles['DetailLabel']), Paragraph(proyecto.canton, styles['DetailValue'])],
        [Paragraph("<b>Fecha Actividad Propuesta:</b>", styles['DetailLabel']), Paragraph(proyecto.fecha_actividad_propuesta.strftime('%Y-%m-%d'), styles['DetailValue'])],
        [Paragraph("<b>Dificultad:</b>", styles['DetailLabel']), Paragraph(proyecto.dificultad, styles['DetailValue'])],
        [Paragraph("<b>Transporte:</b>", styles['DetailLabel']), Paragraph(proyecto.transporte, styles['DetailValue'])],
        [Paragraph("<b>Transporte Adicional:</b>", styles['DetailLabel']), Paragraph(proyecto.transporte_adicional, styles['DetailValue'])],
        [Paragraph("<b>Precio Entrada:</b>", styles['DetailLabel']), Paragraph(f"₡{proyecto.precio_entrada:,.2f}" if proyecto.precio_entrada is not None else 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Nombre del Lugar:</b>", styles['DetailLabel']), Paragraph(proyecto.nombre_lugar, styles['DetailValue'])],
        [Paragraph("<b>Contacto del Lugar:</b>", styles['DetailLabel']), Paragraph(proyecto.contacto_lugar or 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Teléfono del Lugar:</b>", styles['DetailLabel']), Paragraph(proyecto.telefono_lugar or 'N/A', styles['DetailValue'])],
        [Paragraph("<b>Tipo de Terreno:</b>", styles['DetailLabel']), Paragraph(proyecto.tipo_terreno, styles['DetailValue'])],
        [Paragraph("<b>Más Tipo de Terreno:</b>", styles['DetailLabel']), Paragraph('Sí' if proyecto.mas_tipo_terreno else 'No', styles['DetailValue'])],
    ]
    details_table = Table(details_data, colWidths=[2.5 * inch, 5 * inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 0.2 * inch))

    # Sección de Acompañantes
    story.append(Paragraph("Acompañantes", styles['SectionHeader']))
    acompanantes_list = []
    if proyecto.acompanantes:
        acompanantes_ids = json.loads(proyecto.acompanantes)
        # Asegura que acompanantes_ids sea siempre una lista
        if not isinstance(acompanantes_ids, list):
            acompanantes_ids = [acompanantes_ids]
        acompanantes_objetos = Contacto.query.filter(
            Contacto.id.in_(acompanantes_ids),
            Contacto.usuario_id == current_user.id
        ).all()
        if acompanantes_objetos:
            for contacto in acompanantes_objetos:
                acompanantes_list.append([Paragraph(f"- {contacto.nombre} {contacto.primer_apellido or ''} ({contacto.movil or contacto.telefono or 'N/A'})", styles['DetailValue'])])
        else:
            acompanantes_list.append([Paragraph("No se han especificado acompañantes o no se encontraron.", styles['DetailValue'])])
    else:
        acompanantes_list.append([Paragraph("No se han especificado acompañantes.", styles['DetailValue'])])
    
    if acompanantes_list:
        acompanantes_table = Table(acompanantes_list, colWidths=[7.5 * inch])
        acompanantes_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(acompanantes_table)
    story.append(Spacer(1, 0.2 * inch))

    # Notas Adicionales
    if proyecto.notas_adicionales:
        story.append(Paragraph("Notas Adicionales", styles['SectionHeader']))
        story.append(Paragraph(proyecto.notas_adicionales, styles['NotesText']))
        story.append(Spacer(1, 0.2 * inch))

    # Fecha de Creación
    story.append(Paragraph(f"<i>Fecha de Creación: {proyecto.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}</i>", styles['DetailValue']))

    doc.build(story)
    pdf_buffer.seek(0)

    # Convertir el PDF a JPG usando PyMuPDF y Pillow
    try:
        doc_pdf = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        page = doc_pdf.load_page(0)  # Cargar la primera página
        
        # Aumentar la resolución para mejor calidad JPG (ej. 2x)
        zoom = 2
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_buffer = BytesIO()
        # 'RGB' para asegurar compatibilidad con JPG, ya que pixmap puede ser RGBA
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples) 
        img.save(img_buffer, "JPEG", quality=90) # Ajustar calidad si es necesario
        img_buffer.seek(0)
        doc_pdf.close()
        
        filename = f"proyecto_{proyecto.nombre_proyecto.replace(' ', '_').lower()}.jpg"
        return send_file(img_buffer, as_attachment=True, download_name=filename, mimetype='image/jpeg')
    except Exception as e:
        flash(f"Error al convertir PDF a JPG: {e}. Asegúrese de tener PyMuPDF (fitz) y Pillow instalados.", "danger")
        print(f"Error al convertir PDF a JPG: {e}")
        return redirect(url_for('gestor.detalle_proyecto', id=id))


@gestor_bp.route('/exportar_proyecto_txt/<int:id>')
@login_required
def exportar_proyecto_txt(id):
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    content = f"--- Detalles del Proyecto: {proyecto.nombre_proyecto} ---\n\n"
    content += f"Propuesta Por: {proyecto.propuesta_por}\n"
    if proyecto.nombre_invitado:
        content += f"Nombre del Invitado: {proyecto.nombre_invitado}\n"
    content += f"Provincia: {proyecto.provincia}\n"
    content += f"Cantón: {proyecto.canton}\n"
    content += f"Fecha de Actividad Propuesta: {proyecto.fecha_actividad_propuesta.strftime('%Y-%m-%d')}\n"
    content += f"Dificultad: {proyecto.dificultad}\n"
    content += f"Transporte: {proyecto.transporte}\n"
    content += f"Transporte Adicional: {proyecto.transporte_adicional}\n"
    content += f"Precio Entrada: ₡{proyecto.precio_entrada:,.2f}\n" if proyecto.precio_entrada is not None else "Precio Entrada: N/A\n"
    content += f"Nombre del Lugar: {proyecto.nombre_lugar}\n"
    content += f"Contacto del Lugar: {proyecto.contacto_lugar or 'N/A'}\n"
    content += f"Teléfono del Lugar: {proyecto.telefono_lugar or 'N/A'}\n"
    content += f"Tipo de Terreno: {proyecto.tipo_terreno}\n"
    content += f"Más Tipo de Terreno: {'Sí' if proyecto.mas_tipo_terreno else 'No'}\n"
    
    content += "\nAcompañantes:\n"
    if proyecto.acompanantes:
        acompanantes_ids = json.loads(proyecto.acompanantes)
        # Asegura que acompanantes_ids sea siempre una lista
        if not isinstance(acompanantes_ids, list):
            acompanantes_ids = [acompanantes_ids]
        acompanantes_objetos = Contacto.query.filter(
            Contacto.id.in_(acompanantes_ids),
            Contacto.usuario_id == current_user.id
        ).all()
        if acompanantes_objetos:
            for contacto in acompanantes_objetos:
                content += f"- {contacto.nombre} {contacto.primer_apellido or ''} ({contacto.movil or contacto.telefono or 'N/A'})\n"
        else:
            content += "  No se han especificado acompañantes o no se encontraron.\n"
    else:
        content += "  No se han especificado acompañantes.\n"

    if proyecto.notas_adicionales:
        content += f"\nNotas Adicionales:\n{proyecto.notas_adicionales}\n"

    content += f"\nFecha de Creación: {proyecto.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}\n"

    buffer = BytesIO(content.encode('utf-8'))
    filename = f"proyecto_{proyecto.nombre_proyecto.replace(' ', '_').lower()}.txt"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/plain')

@gestor_bp.route('/enviar_proyecto_whatsapp/<int:id>')
@login_required
def enviar_proyecto_whatsapp(id):
    proyecto = GestorProyecto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    # Prepara un mensaje de texto para WhatsApp
    message_parts = [
        f"¡Hola! Te comparto los detalles del proyecto '{proyecto.nombre_proyecto}':",
        f"🗓️ Fecha Propuesta: {proyecto.fecha_actividad_propuesta.strftime('%d/%m/%Y')}",
        f"📍 Lugar: {proyecto.nombre_lugar} ({proyecto.canton}, {proyecto.provincia})",
        f"⛰️ Dificultad: {proyecto.dificultad}",
        f"🚗 Transporte: {proyecto.transporte}"
    ]

    if proyecto.transporte_adicional != 'No aplica':
        message_parts[-1] += f" ({proyecto.transporte_adicional})"
    
    if proyecto.precio_entrada is not None and proyecto.precio_entrada > 0:
        message_parts.append(f"💰 Precio Entrada: ₡{proyecto.precio_entrada:,.2f}")
    
    if proyecto.acompanantes:
        acompanantes_ids = json.loads(proyecto.acompanantes)
        # Asegura que acompanantes_ids sea siempre una lista
        if not isinstance(acompanantes_ids, list):
            acompanantes_ids = [acompanantes_ids]
        acompanantes_objetos = Contacto.query.filter(
            Contacto.id.in_(acompanantes_ids),
            Contacto.usuario_id == current_user.id
        ).all()
        if acompanantes_objetos:
            acompanantes_nombres = [f"{c.nombre} {c.primer_apellido or ''}" for c in acompanantes_objetos]
            message_parts.append(f"👥 Acompañantes: {', '.join(acompanantes_nombres)}")
    
    if proyecto.notas_adicionales:
        message_parts.append(f"📝 Notas Adicionales: {proyecto.notas_adicionales}")
    
    # Unir las partes del mensaje con saltos de línea codificados para URL
    # y luego codificar todo el mensaje para la URL
    message = "\n".join(message_parts)
    whatsapp_url = f"https://wa.me/?text={urllib.parse.quote_plus(message)}"
    
    return redirect(whatsapp_url)

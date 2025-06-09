from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os

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

# --- Rutas ---

@info_bp.route('/ver_info')
@login_required
def ver_info():
    """
    Muestra una lista de todos los elementos de información creados por el usuario actual.
    """
    # Ordenar por fecha de creación descendente para ver los más recientes primero
    info_items = Info.query.filter_by(usuario_id=current_user.id).order_by(Info.fecha_creacion.desc()).all()
    # Asegúrate de pasar el token CSRF también aquí si otras acciones en ver_info.html lo necesitan
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
            # Guardar la imagen si se sube
            if allowed_file(form.imagen.data.filename):
                filename = secure_filename(form.imagen.data.filename)
                # Asegúrate de que la carpeta 'uploads' exista en 'static'
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                filepath = os.path.join(upload_folder, filename)
                form.imagen.data.save(filepath)
                imagen_filename = filename
            else:
                flash('Tipo de archivo de imagen no permitido.', 'danger')
                return render_template('crear_info.html', form=form, generate_csrf=generate_csrf) # Pasar generate_csrf

        # Crear el nuevo objeto Info
        new_info = Info(
            usuario_id=current_user.id,
            imagen_filename=imagen_filename,
            titulo=form.titulo.data,
            contenido=request.form.get('contenido'), # Obtener directamente del formulario HTML
            fecha_creacion=datetime.utcnow() # Autofecha
        )
        db.session.add(new_info)
        db.session.commit()
        flash('¡Información creada exitosamente!', 'success')
        return redirect(url_for('info.ver_info'))
    return render_template('crear_info.html', form=form, generate_csrf=generate_csrf) # Pasar generate_csrf

@info_bp.route('/editar_info/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_info(id):
    """
    Permite editar un elemento de información existente.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = InfoForm(obj=info_item)

    if form.validate_on_submit():
        # Manejar la actualización de la imagen
        if form.imagen.data:
            if allowed_file(form.imagen.data.filename):
                # Eliminar la imagen antigua si existe y es diferente a la nueva
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
                return render_template('editar_info.html', form=form, info_item=info_item, generate_csrf=generate_csrf) # Pasar generate_csrf

        info_item.titulo = form.titulo.data
        # CAMBIO CLAVE AQUÍ: Obtener el contenido directamente de request.form después de la validación
        updated_content = request.form.get('contenido')
        if updated_content is not None:
            info_item.contenido = updated_content
        else:
            # Esto se puede manejar con una validación de Flask-WTF si es obligatorio
            # o dejarlo como None si es opcional. Aquí se asume DataRequired()
            flash('El contenido no puede estar vacío.', 'danger')
            return render_template('editar_info.html', form=form, info_item=info_item, generate_csrf=generate_csrf)

        db.session.commit()
        flash('¡Información actualizada exitosamente!', 'success')
        return redirect(url_for('info.ver_info'))
    
    # Pre-llenar el editor de texto si es un GET request
    if request.method == 'GET':
        # La propiedad 'obj' de Flask-WTF ya debería haber pre-llenado form.titulo.data
        # Pero para el contenido, se pasa directamente a la plantilla para JavaScript
        form.contenido.data = info_item.contenido 

    return render_template('editar_info.html', form=form, info_item=info_item, generate_csrf=generate_csrf) # Pasar generate_csrf

@info_bp.route('/detalle_info/<int:id>')
@login_required
def detalle_info(id):
    """
    Muestra los detalles de un elemento de información específico.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    return render_template('detalle_info.html', info_item=info_item, generate_csrf=generate_csrf) # Pasar generate_csrf

@info_bp.route('/borrar_info/<int:id>', methods=['POST'])
@login_required
def borrar_info(id):
    """
    Borra un elemento de información.
    También elimina la imagen asociada si existe.
    """
    info_item = Info.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if info_item:
        # Eliminar la imagen asociada si existe
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


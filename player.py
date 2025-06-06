# player.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import db, ArchivoMultimedia # Importamos db y el nuevo modelo
from flask_wtf.csrf import generate_csrf # <-- Importar generate_csrf

# Creamos un Blueprint para el reproductor multimedia
player_bp = Blueprint('player', __name__, template_folder='templates')

# --- Formularios ---
class SubirArchivoForm(FlaskForm):
    """
    Formulario para subir nuevos archivos multimedia.
    Permite MP3, MP4, WMA, WMV, JPG, PNG, PDF.
    """
    nombre = StringField('Nombre del Archivo', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción (Opcional)')
    archivo = FileField('Seleccionar Archivo', validators=[
        FileAllowed(['mp3', 'mp4', 'wma', 'wmv', 'jpg', 'jpeg', 'png', 'pdf'],
                    'Solo se permiten archivos de audio (mp3, wma), video (mp4, wmv), imagen (jpg, jpeg, png) o PDF.')
    ])
    submit = SubmitField('Subir Archivo')

class EditarArchivoForm(FlaskForm):
    """
    Formulario para editar la información de un archivo multimedia existente.
    No permite cambiar el archivo en sí.
    """
    nombre = StringField('Nombre del Archivo', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción (Opcional)')
    submit = SubmitField('Guardar Cambios')

# --- Funciones Auxiliares ---
def allowed_file(filename):
    """
    Verifica si la extensión del archivo está permitida.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_MEDIA_EXTENSIONS']

# --- Rutas del CRUD y Reproducción ---

@player_bp.route('/ver_archivos')
@login_required
def ver_archivos():
    """
    Muestra una lista de todos los archivos multimedia subidos por el usuario actual.
    """
    # No necesitamos pasar 'archivos' aquí, ya que solo mostraremos los botones de categoría.
    return render_template('ver_archivos.html', generate_csrf=generate_csrf)

@player_bp.route('/subir_archivo', methods=['GET', 'POST'])
@login_required
def subir_archivo():
    """
    Permite al usuario subir un nuevo archivo multimedia.
    Guarda el archivo en la carpeta de subidas y registra su información en la base de datos.
    """
    form = SubirArchivoForm()
    if form.validate_on_submit():
        if 'archivo' not in request.files or not form.archivo.data:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('player.subir_archivo'))

        file = form.archivo.data
        if file.filename == '':
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('player.subir_archivo'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER'] # Carpeta de subidas ya configurada en app.py
            file_path = os.path.join(upload_folder, filename)

            try:
                file.save(file_path)

                # Determinar el tipo de archivo
                file_extension = filename.rsplit('.', 1)[1].lower()
                if file_extension in ['mp3', 'wma']:
                    tipo = 'audio'
                elif file_extension in ['mp4', 'wmv']:
                    tipo = 'video'
                elif file_extension in ['jpg', 'jpeg', 'png']:
                    tipo = 'imagen'
                elif file_extension == 'pdf':
                    tipo = 'pdf'
                # Considerar añadir 'txt' si lo necesitas en el futuro, pero no estaba en allowed_file inicialmente.
                # Para documentos, podrías agrupar pdf y txt si los permites.
                else:
                    tipo = 'desconocido'

                nuevo_archivo = ArchivoMultimedia(
                    usuario_id=current_user.id,
                    nombre_archivo=form.nombre.data,
                    ruta_archivo=os.path.join('uploads', filename), # Guardar la ruta relativa para usar en templates
                    tipo_archivo=tipo
                )
                db.session.add(nuevo_archivo)
                db.session.commit()
                flash('¡Archivo subido exitosamente!', 'success')
                # Redirigir a la vista general o a la vista detallada según el tipo subido
                return redirect(url_for('player.ver_archivos'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ocurrió un error al subir el archivo: {e}', 'danger')
        else:
            flash('Tipo de archivo no permitido.', 'danger')
    return render_template('crear_archivos.html', form=form)

@player_bp.route('/editar_archivo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_archivo(id):
    """
    Permite editar la información de un archivo multimedia (nombre, descripción).
    """
    archivo = ArchivoMultimedia.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = EditarArchivoForm(obj=archivo)
    if form.validate_on_submit():
        archivo.nombre_archivo = form.nombre.data
        # No hay campo de descripción en el modelo actual de ArchivoMultimedia
        # Si se quiere añadir, se debe actualizar el modelo primero.
        # archivo.descripcion = form.descripcion.data
        db.session.commit()
        flash('¡Archivo actualizado exitosamente!', 'success')
        return redirect(url_for('player.ver_archivos'))
    return render_template('editar_archivos.html', form=form, archivo=archivo)

@player_bp.route('/borrar_archivo/<int:id>', methods=['POST'])
@login_required
def borrar_archivo(id):
    """
    Borra un archivo multimedia de la base de datos y del sistema de archivos.
    """
    archivo = ArchivoMultimedia.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if archivo:
        try:
            # Construir la ruta absoluta del archivo para eliminarlo
            file_to_delete = os.path.join(current_app.root_path, 'static', archivo.ruta_archivo)
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)
            db.session.delete(archivo)
            db.session.commit()
            flash('¡Archivo borrado exitosamente!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al borrar el archivo: {e}', 'danger')
    else:
        flash('Error: Archivo no encontrado o no autorizado.', 'danger')
    return redirect(url_for('player.ver_archivos'))

@player_bp.route('/play_media/<int:id>')
@login_required
def play_media(id):
    """
    Reproduce un archivo multimedia (audio/video) o muestra una imagen.
    Para PDFs, redirige a una ruta específica.
    """
    archivo = ArchivoMultimedia.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if archivo.tipo_archivo == 'pdf':
        return redirect(url_for('player.abrir_pdf', id=archivo.id))
    
    # Obtener la ruta absoluta del archivo
    file_path = os.path.join(current_app.root_path, 'static', archivo.ruta_archivo)
    
    # Determinar el mimetype para send_file
    import mimetypes
    mimetype, _ = mimetypes.guess_type(file_path)
    if not mimetype:
        mimetype = 'application/octet-stream' # Tipo genérico si no se puede adivinar

    # Envía el archivo para ser reproducido/mostrado directamente por el navegador
    # as_attachment=False permite que el navegador intente mostrarlo en línea
    return send_file(file_path, mimetype=mimetype, as_attachment=False)


@player_bp.route('/abrir_pdf/<int:id>')
@login_required
def abrir_pdf(id):
    """
    Abre un archivo PDF en una nueva pestaña del navegador.
    """
    archivo = ArchivoMultimedia.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if archivo.tipo_archivo != 'pdf':
        flash('El archivo seleccionado no es un PDF.', 'danger')
        return redirect(url_for('player.ver_archivos'))

    file_path = os.path.join(current_app.root_path, 'static', archivo.ruta_archivo)
    return send_file(file_path, mimetype='application/pdf', as_attachment=False)

@player_bp.route('/archivos_detail/<string:tipo>')
@login_required
def archivos_detail(tipo):
    """
    Muestra una lista de archivos multimedia filtrados por tipo.
    """
    if tipo == 'documentos':
        # Agrupa PDF y otros tipos de documentos si los incluyes en allowed_file y el modelo.
        # Por ahora, solo PDFs. Si añades TXT, deberás actualizar `allowed_file` y la lógica de `subir_archivo`.
        archivos = ArchivoMultimedia.query.filter_by(usuario_id=current_user.id, tipo_archivo='pdf').order_by(ArchivoMultimedia.fecha_subida.desc()).all()
        titulo = 'Mis Documentos'
    elif tipo == 'audio':
        archivos = ArchivoMultimedia.query.filter_by(usuario_id=current_user.id, tipo_archivo='audio').order_by(ArchivoMultimedia.fecha_subida.desc()).all()
        titulo = 'Mi Música'
    elif tipo == 'video':
        archivos = ArchivoMultimedia.query.filter_by(usuario_id=current_user.id, tipo_archivo='video').order_by(ArchivoMultimedia.fecha_subida.desc()).all()
        titulo = 'Mis Videos'
    elif tipo == 'imagen':
        archivos = ArchivoMultimedia.query.filter_by(usuario_id=current_user.id, tipo_archivo='imagen').order_by(ArchivoMultimedia.fecha_subida.desc()).all()
        titulo = 'Mis Imágenes'
    else:
        flash('Tipo de archivo no válido.', 'danger')
        return redirect(url_for('player.ver_archivos'))
    
    return render_template('archivos_detail.html', archivos=archivos, titulo=titulo, generate_csrf=generate_csrf)
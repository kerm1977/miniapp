# lista_abonos.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, FileField, DecimalField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from wtforms.widgets import DateInput, TimeInput
from flask_wtf.file import FileAllowed
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, time

# Importar db y los modelos necesarios desde models.py
# ASEGÚRATE DE QUE ESTOS MODELOS ESTÁN DEFINIDOS SOLO EN models.py
from models import db, User, Contacto, ListaActividad, ContactoActividad, Abono 

# Crear un Blueprint para la lógica de abonos
abonos_bp = Blueprint('abonos', __name__, template_folder='templates', static_folder='static')

# --- Formularios ---
class ListaActividadForm(FlaskForm):
    avatar_actividad = FileField('Avatar de la Actividad', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif']), Optional()])
    nombre_actividad = StringField('Nombre de la actividad', validators=[DataRequired()])
    fecha_actividad = StringField('Fecha de la actividad (YYYY-MM-DD)', validators=[DataRequired()], widget=DateInput())
    precio_actividad = DecimalField('Precio de la actividad', validators=[DataRequired(), NumberRange(min=0)])
    capacidad_choices = [
        ('12', '12'), ('14', '14'), ('17', '17'), ('28', '28'), ('31', '31'),
        ('42', '42'), ('45', '45'), ('Mas de 45', 'Más de 45')
    ]
    capacidad = SelectField('Capacidad', choices=capacidad_choices, validators=[DataRequired()])
    dificultad_choices = [
        ('Iniciante', 'Iniciante'), ('Paseo', 'Paseo'), ('Basico', 'Básico'),
        ('Intermedio', 'Intermedio'), ('Avanzado', 'Avanzado'), ('Tecnico', 'Técnico')
    ]
    dificultad_actividad = SelectField('Dificultad de la actividad', choices=dificultad_choices, validators=[DataRequired()])
    hora_salida = StringField('Hora de Salida (HH:MM)', validators=[DataRequired()], widget=TimeInput())
    lugar_salida_choices = [
        ('Parque de Tres Ríos-Escuela', 'Parque de Tres Ríos-Escuela'),
        ('Parque de Tres Ríos-Cruz Roja', 'Parque de Tres Ríos-Cruz Roja'),
        ('Parque de Tres Ríos-Las Letras', 'Parque de Tres Ríos-Las Letras'),
        ('Plaza de Deportes San Diego', 'Plaza de Deportes San Diego'),
        ('Iglesia San Diego de Alcalá', 'Iglesia San Diego de Alcalá')
    ]
    lugar_salida = SelectField('Lugar de Salida', choices=lugar_salida_choices, validators=[DataRequired()])
    distancia = StringField('Distancia', validators=[Optional()])
    descripcion = TextAreaField('Descripción', validators=[Optional()])
    incluye = TextAreaField('Incluye', validators=[Optional()])
    instrucciones = TextAreaField('Instrucciones', validators=[Optional()])
    recomendaciones = TextAreaField('Recomendaciones', validators=[Optional()])
    submit = SubmitField('Guardar Actividad')

    def validate_fecha_actividad(self, field):
        try:
            datetime.strptime(field.data, '%Y-%m-%d')
        except ValueError:
            raise ValidationError('Formato de fecha inválido. Por favor, use YYYY-MM-DD.')

    def validate_hora_salida(self, field):
        try:
            datetime.strptime(field.data, '%H:%M').time()
        except ValueError:
            raise ValidationError('Formato de hora inválido. Por favor, use HH:MM.')

class ContactoActividadForm(FlaskForm):
    contacto_existente_id = SelectField('Seleccionar Contacto Existente', coerce=int, validators=[Optional()])
    nombre_manual = StringField('Nombre (si no está en Contactos)', validators=[Optional()])
    apellido_manual = StringField('Apellido (si no está en Contactos)', validators=[Optional()])
    telefono_manual = StringField('Teléfono (si no está en Contactos)', validators=[Optional()])
    submit = SubmitField('Agregar Contacto a la Lista')

    def __init__(self, *args, **kwargs):
        super(ContactoActividadForm, self).__init__(*args, **kwargs)
        # Asegurarse de que `current_user` y `id` existan antes de la consulta
        if current_user and hasattr(current_user, 'id'):
            contactos_usuario = Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre).all()
            self.contacto_existente_id.choices = [(0, '--- Seleccionar Contacto ---')] + \
                                                 [(c.id, f"{c.nombre} {c.primer_apellido or ''} {c.segundo_apellido or ''} - {c.movil or c.telefono}") for c in contactos_usuario]
        else:
            self.contacto_existente_id.choices = [(0, '--- No hay contactos disponibles ---')] # No hay usuario logueado o ID


class AbonoForm(FlaskForm):
    monto = DecimalField('Monto del Abono', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Registrar Abono')


# --- Rutas del Blueprint de Abonos ---

@abonos_bp.route('/crear_lista', methods=['GET', 'POST'])
@login_required
def crear_lista():
    form = ListaActividadForm()
    if form.validate_on_submit():
        try:
            avatar_filename = None
            if form.avatar_actividad.data:
                # Se asume que app.config['UPLOAD_FOLDER'] está configurado en app.py
                # y que la aplicación Flask se pasa al Blueprint o se accede globalmente.
                # Para este ejemplo, usaremos una ruta de placeholder.
                # En tu app.py real, deberías importar `current_app` y usar `current_app.config['UPLOAD_FOLDER']`
                # o pasar el `UPLOAD_FOLDER` al Blueprint si no lo tienes globalmente accesible.
                upload_folder = os.path.join(os.getcwd(), 'static', 'uploads') # Placeholder
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                avatar_filename = secure_filename(form.avatar_actividad.data.filename)
                avatar_path = os.path.join(upload_folder, avatar_filename)
                form.avatar_actividad.data.save(avatar_path)
            
            fecha_actividad_obj = datetime.strptime(form.fecha_actividad.data, '%Y-%m-%d').date()
            hora_salida_obj = datetime.strptime(form.hora_salida.data, '%H:%M').time()

            nueva_lista = ListaActividad(
                usuario_id=current_user.id,
                avatar_actividad=avatar_filename,
                nombre_actividad=form.nombre_actividad.data,
                fecha_actividad=fecha_actividad_obj,
                precio_actividad=form.precio_actividad.data,
                capacidad=form.capacidad.data,
                dificultad_actividad=form.dificultad_actividad.data,
                hora_salida=hora_salida_obj,
                lugar_salida=form.lugar_salida.data,
                distancia=form.distancia.data,
                descripcion=form.descripcion.data,
                incluye=form.incluye.data,
                instrucciones=form.instrucciones.data,
                recomendaciones=form.recomendaciones.data
            )
            db.session.add(nueva_lista)
            db.session.commit()
            flash('¡Lista de actividad creada exitosamente!', 'success')
            return redirect(url_for('abonos.ver_lista'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la lista de actividad: {e}', 'danger')
            print(f"Error al crear lista: {e}") # Para depuración
    return render_template('crear_lista.html', form=form)

@abonos_bp.route('/ver_lista')
@login_required
def ver_lista():
    listas = ListaActividad.query.filter_by(usuario_id=current_user.id).order_by(ListaActividad.fecha_actividad.desc()).all()
    return render_template('ver_lista.html', listas=listas)

@abonos_bp.route('/detalle_lista/<int:lista_id>', methods=['GET', 'POST'])
@login_required
def detalle_lista(lista_id):
    lista = ListaActividad.query.filter_by(id=lista_id, usuario_id=current_user.id).first_or_404()
    
    form_add_contact = ContactoActividadForm()
    # Recargar las opciones de contacto para el formulario en cada solicitud para asegurar que estén actualizadas
    if current_user and hasattr(current_user, 'id'):
        contactos_usuario = Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre).all()
        form_add_contact.contacto_existente_id.choices = [(0, '--- Seleccionar Contacto ---')] + \
                                                         [(c.id, f"{c.nombre} {c.primer_apellido or ''} {c.segundo_apellido or ''} - {c.movil or c.telefono}") for c in contactos_usuario]
    else:
        form_add_contact.contacto_existente_id.choices = [(0, '--- No hay contactos disponibles ---')]

    form_abono = AbonoForm() # Formulario para agregar abonos

    if request.method == 'POST':
        if form_add_contact.submit.data and form_add_contact.validate_on_submit():
            contacto_id = form_add_contact.contacto_existente_id.data
            nombre_manual = form_add_contact.nombre_manual.data
            apellido_manual = form_add_contact.apellido_manual.data
            telefono_manual = form_add_contact.telefono_manual.data

            if contacto_id != 0: # Si se seleccionó un contacto existente
                # Verificar si el contacto ya está en la lista de esta actividad
                if ContactoActividad.query.filter_by(lista_actividad_id=lista.id, contacto_id=contacto_id).first():
                    flash('Este contacto ya ha sido añadido a esta lista.', 'warning')
                else:
                    nuevo_contacto_actividad = ContactoActividad(
                        lista_actividad_id=lista.id,
                        contacto_id=contacto_id,
                        estado='Pendiente'
                    )
                    db.session.add(nuevo_contacto_actividad)
                    db.session.commit()
                    flash('Contacto añadido exitosamente a la lista!', 'success')
            elif nombre_manual and telefono_manual: # Si se añadió manualmente
                # Verificar si el contacto manual ya existe con el mismo nombre y teléfono para esta actividad
                if ContactoActividad.query.filter_by(
                    lista_actividad_id=lista.id,
                    nombre_manual=nombre_manual,
                    telefono_manual=telefono_manual
                ).first():
                    flash('Este contacto manual ya ha sido añadido a esta lista.', 'warning')
                else:
                    nuevo_contacto_actividad = ContactoActividad(
                        lista_actividad_id=lista.id,
                        nombre_manual=nombre_manual,
                        apellido_manual=apellido_manual,
                        telefono_manual=telefono_manual,
                        estado='Pendiente'
                    )
                    db.session.add(nuevo_contacto_actividad)
                    db.session.commit()
                    flash('Contacto manual añadido exitosamente a la lista!', 'success')
            else:
                flash('Por favor, selecciona un contacto existente o introduce los datos de un contacto manual.', 'danger')
            return redirect(url_for('abonos.detalle_lista', lista_id=lista_id))
        
        # Lógica para agregar abono (se agregó la validación del form_abono.submit.data)
        if form_abono.submit.data and form_abono.validate_on_submit():
            contacto_actividad_id = request.form.get('contacto_actividad_id_for_abono') # Obtener el ID del contacto al que se le agrega el abono
            monto_abono = form_abono.monto.data
            
            contacto_actividad = ContactoActividad.query.get(contacto_actividad_id)
            if contacto_actividad and contacto_actividad.lista_actividad.usuario_id == current_user.id:
                nuevo_abono = Abono(
                    contacto_actividad_id=contacto_actividad.id,
                    monto_abono=monto_abono 
                )
                db.session.add(nuevo_abono)
                db.session.commit()
                flash('Abono registrado exitosamente!', 'success')
            else:
                flash('Error: Contacto de actividad no encontrado o no autorizado.', 'danger')
            return redirect(url_for('abonos.detalle_lista', lista_id=lista_id))

    # Obtener contactos para la lista (incluyendo los manuales)
    contactos_en_lista = ContactoActividad.query.filter_by(lista_actividad_id=lista.id).all()
    
    return render_template(
        'detalle_lista.html',
        lista=lista,
        form_add_contact=form_add_contact,
        form_abono=form_abono,
        contactos_en_lista=contactos_en_lista
    )

@abonos_bp.route('/editar_lista/<int:lista_id>', methods=['GET', 'POST'])
@login_required
def editar_lista(lista_id):
    lista = ListaActividad.query.filter_by(id=lista_id, usuario_id=current_user.id).first_or_404()
    form = ListaActividadForm(obj=lista) # Pre-rellena el formulario con los datos existentes

    if request.method == 'GET':
        form.fecha_actividad.data = lista.fecha_actividad.strftime('%Y-%m-%d')
        form.hora_salida.data = lista.hora_salida.strftime('%H:%M')
        # El precio ya se pre-rellena con obj=lista para DecimalField

    if form.validate_on_submit():
        try:
            if form.avatar_actividad.data:
                # Eliminar el avatar antiguo si existe y es diferente al nuevo
                if lista.avatar_actividad and os.path.exists(os.path.join(abonos_bp.static_folder, 'uploads', lista.avatar_actividad)):
                    os.remove(os.path.join(abonos_bp.static_folder, 'uploads', lista.avatar_actividad))
                
                # Guardar el nuevo avatar
                upload_folder = os.path.join(os.getcwd(), 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                avatar_filename = secure_filename(form.avatar_actividad.data.filename)
                avatar_path = os.path.join(upload_folder, avatar_filename)
                form.avatar_actividad.data.save(avatar_path)
                lista.avatar_actividad = avatar_filename # Actualizar la ruta en el modelo

            lista.nombre_actividad = form.nombre_actividad.data
            lista.fecha_actividad = datetime.strptime(form.fecha_actividad.data, '%Y-%m-%d').date()
            lista.precio_actividad = form.precio_actividad.data
            lista.capacidad = form.capacidad.data
            lista.dificultad_actividad = form.dificultad_actividad.data
            lista.hora_salida = datetime.strptime(form.hora_salida.data, '%H:%M').time()
            lista.lugar_salida = form.lugar_salida.data
            lista.distancia = form.distancia.data
            lista.descripcion = form.descripcion.data
            lista.incluye = form.incluye.data
            lista.instrucciones = form.instrucciones.data # Corregido: antes faltaba asignar
            lista.recomendaciones = form.recomendaciones.data
            
            db.session.commit()
            flash('¡Lista de actividad actualizada exitosamente!', 'success')
            return redirect(url_for('abonos.ver_lista'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la lista de actividad: {e}', 'danger')
            print(f"Error al actualizar lista: {e}")
    return render_template('edita_lista.html', form=form, lista=lista)

@abonos_bp.route('/borrar_lista/<int:lista_id>', methods=['POST'])
@login_required
def borrar_lista(lista_id):
    lista = ListaActividad.query.filter_by(id=lista_id, usuario_id=current_user.id).first_or_404()
    if lista:
        # Eliminar el avatar si existe
        if lista.avatar_actividad and os.path.exists(os.path.join(abonos_bp.static_folder, 'uploads', lista.avatar_actividad)):
            os.remove(os.path.join(abonos_bp.static_folder, 'uploads', lista.avatar_actividad))
        
        db.session.delete(lista)
        db.session.commit()
        flash('¡Lista de actividad y todos sus contactos/abonos borrados exitosamente!', 'success')
    else:
        flash('Error al intentar borrar la lista de actividad.', 'danger')
    return redirect(url_for('abonos.ver_lista'))

@abonos_bp.route('/borrar_contacto_lista/<int:contacto_actividad_id>', methods=['POST'])
@login_required
def borrar_contacto_lista(contacto_actividad_id):
    contacto_en_lista = ContactoActividad.query.get_or_404(contacto_actividad_id)
    lista_id = contacto_en_lista.lista_actividad_id

    # Asegurarse de que el usuario actual sea el propietario de la lista
    if contacto_en_lista.lista_actividad.usuario_id != current_user.id:
        flash('No tienes permiso para borrar este contacto.', 'danger')
        return redirect(url_for('abonos.detalle_lista', lista_id=lista_id))

    db.session.delete(contacto_en_lista)
    db.session.commit()
    flash('Contacto eliminado de la lista exitosamente.', 'success')
    return redirect(url_for('abonos.detalle_lista', lista_id=lista_id))

@abonos_bp.route('/actualizar_estado_contacto/<int:contacto_actividad_id>', methods=['POST'])
@login_required
def actualizar_estado_contacto(contacto_actividad_id):
    contacto_en_lista = ContactoActividad.query.get_or_404(contacto_actividad_id)
    lista_id = contacto_en_lista.lista_actividad_id

    # Asegurarse de que el usuario actual sea el propietario de la lista
    if contacto_en_lista.lista_actividad.usuario_id != current_user.id:
        return jsonify({'success': False, 'message': 'No autorizado para actualizar este contacto.'}), 403

    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ['Pendiente', 'Reservado', 'Cancelado']:
        contacto_en_lista.estado = nuevo_estado
        db.session.commit()
        return jsonify({'success': True, 'message': 'Estado actualizado.'})
    return jsonify({'success': False, 'message': 'Estado inválido.'}), 400

@abonos_bp.route('/ver_detalle_contacto_abonos/<int:contacto_actividad_id>', methods=['GET', 'POST']) # AÑADIDO 'POST' AQUÍ
@login_required
def ver_detalle_contacto_abonos(contacto_actividad_id):
    contacto_actividad = ContactoActividad.query.get_or_404(contacto_actividad_id)

    # Asegurarse de que el usuario actual sea el propietario de la lista
    if contacto_actividad.lista_actividad.usuario_id != current_user.id:
        flash('No tienes permiso para ver los detalles de este contacto.', 'danger')
        return redirect(url_for('abonos.ver_lista')) # O a la lista de actividades

    form_abono = AbonoForm()

    # Lógica para agregar abono cuando se envía el formulario desde esta misma página
    if request.method == 'POST' and form_abono.validate_on_submit():
        monto_abono = form_abono.monto.data
        
        nuevo_abono = Abono(
            contacto_actividad_id=contacto_actividad.id,
            monto_abono=monto_abono 
        )
        db.session.add(nuevo_abono)
        db.session.commit()
        flash('Abono registrado exitosamente!', 'success')
        # Redirigir para evitar reenvío de formulario y actualizar la página
        return redirect(url_for('abonos.ver_detalle_contacto_abonos', contacto_actividad_id=contacto_actividad.id))


    # Obtener el total de abonos para este contacto (se recalcula después de posible POST)
    total_abonado = sum(abono.monto_abono for abono in contacto_actividad.abonos) 
    
    # Obtener el precio total de la actividad asociada
    precio_total_actividad = contacto_actividad.lista_actividad.precio_actividad

    # Calcular el saldo pendiente
    saldo_pendiente = precio_total_actividad - total_abonado

    return render_template(
        'detalle_contacto_abonos.html',
        contacto_actividad=contacto_actividad,
        total_abonado=total_abonado,
        precio_total_actividad=precio_total_actividad,
        saldo_pendiente=saldo_pendiente,
        form_abono=form_abono
    )

@abonos_bp.route('/eliminar_abono/<int:abono_id>', methods=['POST'])
@login_required
def eliminar_abono(abono_id):
    abono = Abono.query.get_or_404(abono_id)
    contacto_actividad_id = abono.contacto_actividad_id
    
    # Verificar que el usuario actual sea el propietario de la actividad a través del contacto_actividad y la lista_actividad
    if abono.contacto_actividad.lista_actividad.usuario_id != current_user.id:
        flash('No tienes permiso para eliminar este abono.', 'danger')
        return redirect(url_for('abonos.ver_detalle_contacto_abonos', contacto_actividad_id=contacto_actividad_id))

    db.session.delete(abono)
    db.session.commit()
    flash('Abono eliminado exitosamente.', 'success')
    return redirect(url_for('abonos.ver_detalle_contacto_abonos', contacto_actividad_id=contacto_actividad_id))

# Función para configurar la carpeta de subidas (llamada desde app.py)
def configure_abonos_uploads(app_instance):
    # Asegúrate de que esta carpeta exista y sea accesible
    # Se recomienda que esta sea la misma que app.config['UPLOAD_FOLDER']
    upload_folder = os.path.join(app_instance.root_path, 'static', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    # Puedes guardar la ruta en el Blueprint para fácil acceso si es necesario
    abonos_bp.static_folder = os.path.join(app_instance.root_path, 'static')

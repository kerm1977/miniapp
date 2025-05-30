from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, FileField, TextAreaField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, Optional, NumberRange
from flask_wtf.csrf import generate_csrf
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date, time
from flask_migrate import Migrate
import io
from io import BytesIO
import vobject
import base64
import mimetypes
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
import numpy
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Importar db y los modelos desde models.py
# Asegúrate de que 'Evento' esté importado aquí junto con los demás.
from models import db, User, Contacto, Event, Factura, Evento # Añadir Evento

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'uploads') # Cambiado a 'uploads' para ser más genérico
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegurarse de que la carpeta de subidas exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Inicializar db con la aplicación
db.init_app(app)

migrate = Migrate(app, db)

# Extensiones permitidas para subidas (imágenes y PDF para flyers)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'} 

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."


def is_authenticated(self):
    return True


# FORMS
class RegistrationForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    cedula = StringField('Cédula', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired(), Regexp('^[0-9]+$'), Length(min=8, max=10, message='El teléfono debe tener entre 8 y 10 dígitos')])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    image = FileField('Imagen de Usuario', validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Solo se permiten imágenes png, jpg, jpeg o gif.')])
    submit = SubmitField('Registrarse')

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar sesión')

class EditUserForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    cedula = StringField('Cédula', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired(), Regexp('^[0-9]+$'), Length(min=8, max=10, message='El teléfono debe tener entre 8 y 10 dígitos')])
    submit = SubmitField('Guardar Cambios')

class UpdateProfileImageForm(FlaskForm):
    image = FileField('Nueva Imagen de Perfil', validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Solo se permiten imágenes png, jpg, jpeg o gif.')])
    submit = SubmitField('Actualizar Imagen')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class SearchForm(FlaskForm):
    search_term = StringField('Buscar Contacto', validators=[DataRequired()])
    submit = SubmitField('Buscar')

class ContactoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()], render_kw={"class": "rounded-pill"})
    primer_apellido = StringField('Primer Apellido', render_kw={"class": "rounded-pill"})
    segundo_apellido = StringField('Segundo Apellido', render_kw={"class": "rounded-pill"})
    telefono = StringField('Teléfono', validators=[DataRequired()], render_kw={"class": "rounded-pill"})
    movil = StringField('Móvil', render_kw={"class": "rounded-pill"})
    email = StringField('Email', render_kw={"class": "rounded-pill"})
    direccion = StringField('Dirección', render_kw={"class": "rounded-pill"})
    actividades_choices = [
        ('', 'Seleccionar Actividad'),
        ('La Tribu', 'La Tribu'),
        ('Senderista', 'Senderista'),
        ('Enfermería', 'Enfermería'),
        ('Cocina', 'Cocina'),
        ('Confección y Diseño', 'Confección y Diseño'),
        ('Restaurante', 'Restaurante'),
        ('Transporte Terrestre', 'Transporte Terrestre'),
        ('Transporte Acuatico', 'Transporte Acuatico'),
        ('Transporte Aereo', 'Transporte Aereo'),
        ('Migración', 'Migración'),
        ('Parque Nacional', 'Parque Nacional'),
        ('Refugio Silvestre', 'Refugio Silvestre'),
        ('Centro de Atracción', 'Centro de Atracción'),
        ('Lugar para Caminata', 'Lugar para Caminata'),
        ('Acarreo', 'Acarreo'),
        ('Oficina de trámite', 'Oficina de trámite'),
        ('Primeros Auxilios', 'Primeros Auxilios'),
        ('Farmacia', 'Farmacia'),
        ('Taller', 'Taller'),
        ('Abobado', 'Abobado'),
        ('Mensajero', 'Mensajero'),
        ('Tienda', 'Tienda'),
        ('Polizas', 'Polizas'),
        ('Aerolínea', 'Aerolínea'),
        ('Guía', 'Guía'),
        ('Banco', 'Banco'),
        ('Otros', 'Otros (especifique)')
    ]
    tipo_actividad = SelectField('Actividad', choices=actividades_choices, render_kw={"class": "rounded-pill"})
    nota = TextAreaField('Nota', render_kw={"class": "rounded-pill"})
    direccion_mapa = StringField('Dirección del Mapa', render_kw={"class": "rounded-pill"})
    avatar = FileField('Avatar', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])], render_kw={"class": "rounded-pill"})
    empresa = StringField('Empresa', render_kw={"class": "rounded-pill"})
    sitio_web = StringField('Sitio Web', render_kw={"class": "rounded-pill"})
    # Nuevos campos select
    capacidad_persona_choices = [
        ('', 'Seleccionar Capacidad'),
        ('Rápido', 'Rápido'),
        ('Intermedio', 'Intermedio'),
        ('Básico', 'Básico'),
        ('Iniciante', 'Iniciante')
    ]
    capacidad_persona = SelectField('Capacidad de persona', choices=capacidad_persona_choices, render_kw={"class": "rounded-pill form-select"})

    participacion_choices = [
        ('', 'Seleccionar Participación'),
        ('Solo de La Tribu', 'Solo de La Tribu'),
        ('constante', 'constante'),
        ('inconstante', 'inconstante'),
        ('El Camino de Costa Rica', 'El Camino de Costa Rica'),
        ('Parques Nacionales', 'Parques Nacionales'),
        ('Paseo | Recreativo', 'Paseo | Recreativo'),
        ('Revisar/Eliminar', 'Revisar/Eliminar')
    ]
    participacion = SelectField('PARTICIPACION', choices=participacion_choices, render_kw={"class": "rounded-pill form-select"})

    submit = SubmitField('Guardar', render_kw={"class": "btn btn-primary"})

class BusquedaContactoForm(FlaskForm):
    busqueda_actividad = SelectField('Buscar por Actividad', choices=[
        ('', 'Seleccionar Actividad'),
        ('La Tribu', 'La Tribu'),
        ('Senderista', 'Senderista'),
        ('Enfermería', 'Enfermería'),
        ('Cocina', 'Cocina'),
        ('Confección y Diseño', 'Confección y Diseño'),
        ('Restaurante', 'Restaurante'),
        ('Transporte Terrestre', 'Transporte Terrestre'),
        ('Transporte Acuatico', 'Transporte Acuatico'),
        ('Transporte Aereo', 'Transporte Aereo'),
        ('Migración', 'Migración'),
        ('Parque Nacional', 'Parque Nacional'),
        ('Refugio Silvestre', 'Refugio Silvestre'),
        ('Centro de Atracción', 'Centro de Atracción'),
        ('Lugar para Caminata', 'Lugar para Caminata'),
        ('Acarreo', 'Acarreo'),
        ('Oficina de trámite', 'Oficina de trámite'),
        ('Primeros Auxilios', 'Primeros Auxilios'),
        ('Farmacia', 'Farmacia'),
        ('Taller', 'Taller'),
        ('Abobado', 'Abobado'),
        ('Mensajero', 'Mensajero'),
        ('Tienda', 'Tienda'),
        ('Polizas', 'Polizas'),
        ('Aerolínea', 'Aerolínea'),
        ('Guía', 'Guía'),
        ('Banco', 'Banco'),
        ('Otros', 'Otros')
    ], render_kw={"class": "rounded-pill form-select"})
    busqueda_capacidad_persona = SelectField('Buscar por Capacidad', choices=[
        ('', 'Seleccionar Capacidad'),
        ('Rápido', 'Rápido'),
        ('Intermedio', 'Intermedio'),
        ('Básico', 'Básico'),
        ('Iniciante', 'Iniciante')
    ], render_kw={"class": "rounded-pill form-select"})
    busqueda_participacion = SelectField('Buscar por Participación', choices=[
        ('', 'Seleccionar Participación'),
        ('Solo de La Tribu', 'Solo de La Tribu'),
        ('constante', 'constante'),
        ('inconstante', 'inconstante'),
        ('El Camino de Costa Rica', 'El Camino de Costa Rica'),
        ('Parques Nacionales', 'Parques Nacionales'),
        ('Paseo | Recreativo', 'Paseo | Recreativo'),
        ('Revisar/Eliminar', 'Revisar/Eliminar')
    ], render_kw={"class": "rounded-pill form-select"})
    submit_buscar = SubmitField('Buscar', render_kw={"class": "btn btn-secondary"})

class BorrarContactoForm(FlaskForm):
    submit = SubmitField('Confirmar Borrar')


# --- Formulario para Crear Facturas ---
class CrearFacturaForm(FlaskForm):
    # Campos existentes
    cliente_id = SelectField('Caminante', coerce=int, validators=[DataRequired()], render_kw={"class": "form-select form-control"})
    fecha_emision = StringField('Fecha de Emisión (YYYY-MM-DD)', validators=[DataRequired()], render_kw={"class": "form-control"})
    descripcion = TextAreaField('Descripción', render_kw={"class": "form-control"})
    monto_total = StringField('Monto Total', validators=[DataRequired()], render_kw={"class": "form-control"})

    # --- NUEVOS CAMPOS ---
    interes = SelectField('Interés', choices=[('Factura', 'Factura'), ('Cotizacion', 'Cotización')], validators=[DataRequired()], render_kw={"class": "form-select form-control"})
    realizado_por = SelectField('Realizado por', choices=[('Jenny Ceciliano Cordoba', 'Jenny Ceciliano Cordoba'), ('Kenneth Ruiz Matamoros', 'Kenneth Ruiz Matamoros')], validators=[DataRequired()], render_kw={"class": "form-select form-control"})
    sinpe = SelectField('SINPE', choices=[('Jenny Ceciliano Cordoba-86529837', 'Jenny Ceciliano Cordoba - 86529837'), ('Kenneth Ruiz Matamoros-86227500', 'Kenneth Ruiz Matamoros - 86227500'), ('Jenny Ceciliano Cordoba-87984232', 'Jenny Ceciliano Cordoba - 87984232')], validators=[DataRequired()], render_kw={"class": "form-select form-control"})
    tipo_actividad = SelectField('Tipo de actividad', choices=[('El Camino de Costa Rica', 'El Camino de Costa Rica'), ('Parques Nacionales', 'Parques Nacionales'), ('Paseo', 'Paseo'), ('Básico', 'Básico'), ('Intermedio', 'Intermedio'), ('Avanzado', 'Avanzado'), ('Productos', 'Productos'), ('Servicios', 'Servicios')], validators=[DataRequired()], render_kw={"class": "form-select form-control"})
    nombre_actividad_etapa = StringField('Nombre de la actividad o Etapa', validators=[Optional()], render_kw={"class": "form-control"})
    costo_actividad = StringField('Costo de la actividad', validators=[Optional()], render_kw={"class": "form-control"})
    otras_descripcion = TextAreaField('Otras descripción', validators=[Optional()], render_kw={"class": "form-control"})

    submit = SubmitField('Guardar Factura', render_kw={"class": "btn btn-success rounded-pill"})

    def __init__(self, *args, **kwargs):
        super(CrearFacturaForm, self).__init__(*args, **kwargs)
        if current_user and hasattr(current_user, 'id'):
            self.cliente_id.choices = [(
                contacto.id,
                f"{contacto.nombre.title()} {contacto.primer_apellido.title() if contacto.primer_apellido else ''} {contacto.segundo_apellido.title() if contacto.segundo_apellido else ''} - {contacto.movil if contacto.movil else contacto.telefono}"
            ) for contacto in Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre, Contacto.primer_apellido).all()]
        else:
            self.cliente_id.choices = []

# --- Formulario para Editar Facturas ---
class EditarFacturaForm(FlaskForm):
    # Campos existentes
    numero_factura = StringField('Número de Factura', render_kw={"class": "rounded-pill", "readonly": True})
    cliente_id = SelectField('Cliente', coerce=int, render_kw={"class": "rounded-pill form-select"})
    fecha_emision = StringField('Fecha de Emisión (YYYY-MM-DD)', render_kw={"class": "rounded-pill"})
    descripcion = TextAreaField('Descripción', render_kw={"class": "rounded-pill"})
    monto_total = StringField('Monto Total', render_kw={"class": "rounded-pill"})

    # --- NUEVOS CAMPOS ---
    interes = SelectField('Interés', choices=[('Factura', 'Factura'), ('Cotizacion', 'Cotización')], render_kw={"class": "form-select rounded-pill"})
    realizado_por = SelectField('Realizado por', choices=[('Jenny Ceciliano Cordoba', 'Jenny Ceciliano Cordoba'), ('Kenneth Ruiz Matamoros', 'Kenneth Ruiz Matamoros')], render_kw={"class": "form-select rounded-pill"})
    sinpe = SelectField('SINPE', choices=[('Jenny Ceciliano Cordoba-86529837', 'Jenny Ceciliano Cordoba - 86529837'), ('Kenneth Ruiz Matamoros-86227500', 'Kenneth Ruiz Matamoros - 86227500'), ('Jenny Ceciliano Cordoba-87984232', 'Jenny Ceciliano Cordoba - 87984232')], render_kw={"class": "form-select rounded-pill"})
    tipo_actividad = SelectField('Tipo de actividad', choices=[('El Camino de Costa Rica', 'El Camino de Costa Rica'), ('Parques Nacionales', 'Parques Nacionales'), ('Paseo', 'Paseo'), ('Básico', 'Básico'), ('Intermedio', 'Intermedio'), ('Avanzado', 'Avanzado'), ('Productos', 'Productos'), ('Servicios', 'Servicios')], render_kw={"class": "form-select rounded-pill"})
    nombre_actividad_etapa = StringField('Nombre de la actividad o Etapa', render_kw={"class": "rounded-pill"})
    costo_actividad = StringField('Costo de la actividad', render_kw={"class": "rounded-pill"})
    otras_descripcion = TextAreaField('Otras descripción', render_kw={"class": "rounded-pill"})

    submit = SubmitField('Guardar Cambios', render_kw={"class": "btn btn-primary"})

    def __init__(self, factura, *args, **kwargs):
        super(EditarFacturaForm, self).__init__(*args, **kwargs)
        if current_user and hasattr(current_user, 'id'):
            self.cliente_id.choices = [(
                contacto.id,
                f"{contacto.nombre.title()} {contacto.primer_apellido.title() if contacto.primer_apellido else ''} {contacto.segundo_apellido.title() if contacto.segundo_apellido else ''} - {contacto.movil if contacto.movil else contacto.telefono}"
            ) for contacto in Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre, Contacto.primer_apellido).all()]
        else:
            self.cliente_id.choices = []

# Nuevo formulario para Eventos
class EventoForm(FlaskForm):
    flyer = FileField('Flyer del Evento', validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Solo se permiten imágenes (png, jpg, jpeg, gif) o PDFs.')])
    tipo_evento = SelectField('Tipo de Evento', choices=[
        ('Parque Nacional', 'Parque Nacional'),
        ('El Camino de Costa Rica', 'El Camino de Costa Rica')
    ], validators=[DataRequired()])
    nombre_evento = StringField('Nombre del Evento', validators=[DataRequired()])
    precio_evento = StringField('Precio del Evento (₡)', validators=[DataRequired(), Regexp(r'^\d+(\.\d{1,2})?$', message="El precio debe ser un número válido con hasta 2 decimales.")])
    fecha_evento = StringField('Fecha del Evento (YYYY-MM-DD)', validators=[DataRequired()])
    dificultad_evento = SelectField('Dificultad del Evento', choices=[
        ('Iniciante', 'Iniciante'),
        ('Básico', 'Básico'),
        ('Intermedio', 'Intermedio'),
        ('Avanzado', 'Avanzado'),
        ('Técnico', 'Técnico')
    ], validators=[DataRequired()])
    incluye = TextAreaField('Incluye', validators=[Optional()])
    lugar_salida = SelectField('Lugar de Salida', choices=[
        ('Parque de Tres Ríos Escuela', 'Parque de Tres Ríos Escuela'),
        ('Parque de Tres Ríos Cruz Roja', 'Parque de Tres Ríos Cruz Roja'),
        ('Plaza de San Diego', 'Plaza de San Diego'),
        ('Iglesia De San Diego', 'Iglesia De San Diego')
    ], validators=[DataRequired()])
    hora_salida = StringField('Hora de Salida (HH:MM)', validators=[DataRequired(), Regexp(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', message="Formato de hora inválido (HH:MM).")])
    distancia = StringField('Distancia', validators=[Optional()])
    capacidad = SelectField('Capacidad', choices=[
        ('14', '14'),
        ('17', '17'),
        ('28', '28'),
        ('42', '42')
    ], coerce=int, validators=[DataRequired()])
    descripcion = TextAreaField('Descripción', validators=[Optional()])
    instrucciones = TextAreaField('Instrucciones', validators=[Optional()])
    recomendaciones = TextAreaField('Recomendaciones', validators=[Optional()])
    submit = SubmitField('Guardar Evento')

# Formulario para Editar Eventos (similar al de crear, pero para pre-llenar)
class EditarEventoForm(FlaskForm):
    flyer = FileField('Flyer del Evento', validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Solo se permiten imágenes (png, jpg, jpeg, gif) o PDFs.')])
    tipo_evento = SelectField('Tipo de Evento', choices=[
        ('Parque Nacional', 'Parque Nacional'),
        ('El Camino de Costa Rica', 'El Camino de Costa Rica')
    ], validators=[DataRequired()])
    nombre_evento = StringField('Nombre del Evento', validators=[DataRequired()])
    precio_evento = StringField('Precio del Evento (₡)', validators=[DataRequired(), Regexp(r'^\d+(\.\d{1,2})?$', message="El precio debe ser un número válido con hasta 2 decimales.")])
    fecha_evento = StringField('Fecha del Evento (YYYY-MM-DD)', validators=[DataRequired()])
    dificultad_evento = SelectField('Dificultad del Evento', choices=[
        ('Iniciante', 'Iniciante'),
        ('Básico', 'Básico'),
        ('Intermedio', 'Intermedio'),
        ('Avanzado', 'Avanzado'),
        ('Técnico', 'Técnico')
    ], validators=[DataRequired()])
    incluye = TextAreaField('Incluye', validators=[Optional()])
    lugar_salida = SelectField('Lugar de Salida', choices=[
        ('Parque de Tres Ríos Escuela', 'Parque de Tres Ríos Escuela'),
        ('Parque de Tres Ríos Cruz Roja', 'Parque de Tres Ríos Cruz Roja'),
        ('Plaza de San Diego', 'Plaza de San Diego'),
        ('Iglesia De San Diego', 'Iglesia De San Diego')
    ], validators=[DataRequired()])
    hora_salida = StringField('Hora de Salida (HH:MM)', validators=[DataRequired(), Regexp(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', message="Formato de hora inválido (HH:MM).")])
    distancia = StringField('Distancia', validators=[Optional()])
    capacidad = SelectField('Capacidad', choices=[
        ('14', '14'),
        ('17', '17'),
        ('28', '28'),
        ('42', '42')
    ], coerce=int, validators=[DataRequired()])
    descripcion = TextAreaField('Descripción', validators=[Optional()])
    instrucciones = TextAreaField('Instrucciones', validators=[Optional()])
    recomendaciones = TextAreaField('Recomendaciones', validators=[Optional()])
    submit = SubmitField('Guardar Cambios')


# FUNCIONES
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calendario')
def calendario():
    return render_template('calendario.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        cedula = form.cedula.data
        telefono = form.telefono.data
        password = form.password.data
        image = form.image.data

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('registro.html', form=form)
        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
            return render_template('registro.html', form=form)
        if User.query.filter_by(cedula=cedula).first():
            flash('La cédula ya está registrada.', 'danger')
            return render_template('registro.html', form=form)
        if User.query.filter_by(telefono=telefono).first():
            flash('El número de teléfono ya está registrado.', 'danger')
            return render_template('registro.html', form=form)

        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_user = User(username=username, email=email, cedula=cedula, telefono=telefono, image_filename=filename) # Guarda solo el nombre del archivo
        else:
            new_user = User(username=username, email=email, cedula=cedula, telefono=telefono)

        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('¡Inicio de sesión exitoso!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Inicio de sesión fallido. Verifica tu nombre de usuario y contraseña.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('index'))



@app.route('/editar_perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    form = EditUserForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.cedula = form.cedula.data
        current_user.telefono = form.telefono.data
        db.session.commit()
        flash('Tu perfil ha sido actualizado.', 'success')
        return redirect(url_for('perfil'))
    return render_template('editar_perfil.html', form=form)

@app.route('/borrar_perfil', methods=['POST'])
@login_required
def borrar_perfil():
    user_to_delete = User.query.get(current_user.id)
    if user_to_delete:
        logout_user()
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('Tu cuenta ha sido borrada.', 'success')
        return redirect(url_for('index'))
    else:
        flash('Error al intentar borrar la cuenta.', 'danger')
        return redirect(url_for('perfil'))

@app.route('/actualizar_imagen', methods=['POST'])
@login_required
def actualizar_imagen():
    form = UpdateProfileImageForm()
    if form.validate_on_submit():
        image = form.image.data
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            # Eliminar la imagen anterior si existe
            if current_user.image_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], current_user.image_filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_user.image_filename))

            current_user.image_filename = filename
            db.session.commit()
            flash('Tu imagen de perfil ha sido actualizada.', 'success')
        else:
            flash('No se seleccionó ninguna imagen.', 'warning')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error en el campo {getattr(form, field).label.text}: {error}', 'danger')
    return redirect(url_for('perfil'))

@app.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    if current_user.id == user_id:
        flash('No puedes editar tu propio perfil desde aquí.', 'warning')
        return redirect(url_for('perfil'))

    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.cedula = form.cedula.data
        user.telefono = form.telefono.data
        db.session.commit()
        flash(f'El usuario {user.username} ha sido actualizado.', 'success')
        return redirect(url_for('perfil'))

    return render_template('editar_usuario.html', form=form, user=user)

@app.route('/borrar_usuario/<int:user_id>', methods=['POST'])
@login_required
def borrar_usuario(user_id):
    if current_user.id == user_id:
        flash('No puedes borrar tu propia cuenta desde aquí.', 'warning')
        return redirect(url_for('perfil'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'El usuario {user.username} ha sido borrado.', 'success')
    return redirect(url_for('perfil'))

@app.route('/buscar_usuarios', methods=['POST'])
@login_required
def buscar_usuarios():
    form = SearchForm()
    results = []
    if form.validate_on_submit():
        search_term = form.search_term.data.lower()
        words = search_term.split()
        if words:
            conditions = []
            for word in words:
                conditions.append(db.func.lower(User.username).contains(word))
                conditions.append(db.func.lower(User.email).contains(word))
                conditions.append(db.func.lower(User.cedula).contains(word))
                conditions.append(db.func.lower(User.telefono).contains(word))
            results = User.query.filter(db.or_(*conditions)).all()
    return render_template('perfil.html', users=results, form=UpdateProfileImageForm(), search_form=form)

@app.route('/limpiar_busqueda')
@login_required
def limpiar_busqueda():
    return redirect(url_for('perfil'))

@app.route('/perfil')
@login_required
def perfil():
    search_form = SearchForm()
    form = UpdateProfileImageForm()
    return render_template('perfil.html', form=form, search_form=search_form)






# CONTACTOS
@app.route('/listar_contacto')
@login_required
def listar_contacto():
    form_busqueda = BusquedaContactoForm()
    contactos = Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre, Contacto.primer_apellido, Contacto.segundo_apellido).all()
    return render_template('listar_contacto.html', contactos=contactos, form_busqueda=form_busqueda)

@app.route('/crear_contacto', methods=['GET', 'POST'])
@login_required
def crear_contacto():
    form = ContactoForm()
    if form.validate_on_submit():
        nombre = form.nombre.data
        primer_apellido = form.primer_apellido.data
        segundo_apellido = form.segundo_apellido.data
        telefono = form.telefono.data
        movil = form.movil.data
        email = form.email.data
        direccion = form.direccion.data
        tipo_actividad = form.tipo_actividad.data
        nota = form.nota.data
        direccion_mapa = form.direccion_mapa.data
        empresa = form.empresa.data
        sitio_web = form.sitio_web.data
        capacidad_persona = form.capacidad_persona.data
        participacion = form.participacion.data

        # Manejo del avatar
        if form.avatar.data:
            avatar_filename = secure_filename(form.avatar.data.filename)
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
            form.avatar.data.save(avatar_path)
        else:
            avatar_path = None

        nuevo_contacto = Contacto(
            nombre=nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            telefono=telefono,
            movil=movil,
            email=email,
            direccion=direccion,
            tipo_actividad=tipo_actividad,
            nota=nota,
            direccion_mapa=direccion_mapa,
            avatar_path=avatar_path,
            usuario_id=current_user.id,
            empresa=empresa,
            sitio_web=sitio_web,
            capacidad_persona=capacidad_persona,
            participacion=participacion
        )
        db.session.add(nuevo_contacto)
        db.session.commit()
        flash('¡Contacto creado exitosamente!', 'success')
        return redirect(url_for('listar_contacto'))
    return render_template('crear_contacto.html', form=form)

@app.route('/editar_contacto/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_contacto(id):
    contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = ContactoForm(obj=contacto)
    if form.validate_on_submit():
        contacto.nombre = form.nombre.data
        contacto.primer_apellido = form.primer_apellido.data
        contacto.segundo_apellido = form.segundo_apellido.data
        contacto.telefono = form.telefono.data
        contacto.movil = form.movil.data
        contacto.email = form.email.data
        contacto.direccion = form.direccion.data
        contacto.tipo_actividad = form.tipo_actividad.data
        contacto.nota = form.nota.data
        contacto.direccion_mapa = form.direccion_mapa.data
        contacto.empresa = form.empresa.data
        contacto.sitio_web = form.sitio_web.data
        contacto.capacidad_persona = form.capacidad_persona.data
        contacto.participacion = form.participacion.data

        # Manejo del avatar en la edición
        if form.avatar.data:
            # Si se sube un nuevo avatar, guardar y actualizar la ruta
            avatar_filename = secure_filename(form.avatar.data.filename)
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
            form.avatar.data.save(avatar_path)
            contacto.avatar_path = avatar_path

        db.session.commit()
        flash('¡Contacto actualizado exitosamente!', 'success')
        return redirect(url_for('listar_contacto'))
    return render_template('editar_contacto.html', form=form, contacto=contacto, contacto_id=id) # ¡Pasa 'contacto' aquí!

@app.route('/borrar_contacto/<int:id>', methods=['POST', 'DELETE'])
@login_required
def borrar_contacto(id):
    contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if contacto:
        if request.method == 'POST' or request.method == 'DELETE':
            db.session.delete(contacto)
            db.session.commit()
            flash('¡Contacto borrado exitosamente!', 'success')
            return redirect(url_for('listar_contacto'))
    else:
        flash('Error al intentar borrar el contacto.', 'danger')
    return redirect(url_for('listar_contacto'))

@app.route('/buscar_contacto', methods=['POST'])
@login_required
def buscar_contacto():
    form_busqueda = BusquedaContactoForm()
    contactos = Contacto.query.filter_by(usuario_id=current_user.id)

    if form_busqueda.validate_on_submit():
        termino_actividad = form_busqueda.busqueda_actividad.data
        termino_capacidad = form_busqueda.busqueda_capacidad_persona.data
        termino_participacion = form_busqueda.busqueda_participacion.data

        if termino_actividad:
            contactos = contactos.filter(Contacto.tipo_actividad == termino_actividad)

        if termino_capacidad:
            contactos = contactos.filter(Contacto.capacidad_persona == termino_capacidad)

        if termino_participacion:
            contactos = contactos.filter(Contacto.participacion == termino_participacion)

        resultados = contactos.order_by(Contacto.nombre, Contacto.primer_apellido, Contacto.segundo_apellido).all()
        return render_template('listar_contacto.html', contactos=resultados, form_busqueda=form_busqueda)

    # Si la solicitud es GET o el formulario no es válido, mostrar todos los contactos ordenados
    return render_template('listar_contacto.html', contactos=Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre, Contacto.primer_apellido, Contacto.segundo_apellido).all(), form_busqueda=form_busqueda)



# VCARD Individual
@app.route('/exportar_vcard/<int:contacto_id>')
@login_required
def exportar_vcard(contacto_id):
    contacto = Contacto.query.filter_by(id=contacto_id, usuario_id=current_user.id).first_or_404()

    v = vobject.vCard()
    v.add('fn').value = f"{contacto.nombre} {contacto.primer_apellido or ''} {contacto.segundo_apellido or ''}".strip()

    if contacto.telefono:
        tel_param = v.add('TEL')
        tel_param.type_param = 'HOME'
        tel_param.value = contacto.telefono
    if contacto.movil:
        tel_param = v.add('TEL')
        tel_param.type_param = 'CELL'
        tel_param.value = contacto.movil
    if contacto.email:
        email_param = v.add('EMAIL')
        email_param.type_param = 'INTERNET'
        email_param.value = contacto.email
    if contacto.direccion:
        adr_param = v.add('ADR')
        adr_param.type_param = 'HOME'
        adr_param.value = vobject.vcard.Address(street=contacto.direccion)
    if contacto.empresa:
        org_param = v.add('ORG')
        org_param.value = [contacto.empresa]  # ORG es una lista
    if contacto.sitio_web:
        url_param = v.add('URL')
        url_param.value = contacto.sitio_web
    if contacto.capacidad_persona:
        v.add('X-CAPACIDAD-PERSONA').value = contacto.capacidad_persona # Campo personalizado
    if contacto.participacion:
        v.add('X-PARTICIPACION').value = contacto.participacion # Campo personalizado

    vcard_content = v.serialize()
    filename = f"{contacto.nombre.lower()}_{contacto.primer_apellido.lower() if contacto.primer_apellido else ''}.vcf"
    buffer = io.BytesIO(vcard_content.encode('utf-8'))
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/vcard')

# VCARD Todos
@app.route('/exportar_todos_vcard')
@login_required
def exportar_todos_vcard():
    contactos = Contacto.query.filter_by(usuario_id=current_user.id).all()

    if not contactos:
        flash('No hay contactos para exportar.', 'info')
        return redirect(url_for('listar_contacto'))

    vcards = []
    for contacto in contactos:
        v = vobject.vCard()
        v.add('fn').value = f"{contacto.nombre} {contacto.primer_apellido or ''} {contacto.segundo_apellido or ''}".strip()
        if contacto.telefono:
            tel_param = v.add('TEL')
            tel_param.type_param = 'HOME'
            tel_param.value = contacto.telefono
        if contacto.movil:
            tel_param = v.add('TEL')
            tel_param.type_param = 'CELL'
            tel_param.value = contacto.movil
        if contacto.email:
            email_param = v.add('EMAIL')
            email_param.type_param = 'INTERNET'
            email_param.value = contacto.email
        if contacto.direccion:
            adr_param = v.add('ADR')
            adr_param.type_param = 'HOME'
            adr_param.value = vobject.vcard.Address(street=contacto.direccion)
        if contacto.empresa:
            org_param = v.add('ORG')
            org_param.value = [contacto.empresa]
        if contacto.sitio_web:
            url_param = v.add('URL')
            url_param.value = contacto.sitio_web
        if contacto.capacidad_persona:
            v.add('X-CAPACIDAD-PERSONA').value = contacto.capacidad_persona
        if contacto.participacion:
            v.add('X-PARTICIPACION').value = contacto.participacion

        vcards.append(v.serialize())

    all_vcards_content = "\n".join(vcards)
    filename = f"todos_los_contactos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.vcf"
    buffer = io.BytesIO(all_vcards_content.encode('utf-8'))

    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/vcard')

# EXCEL Todos
@app.route('/exportar_todos_excel')
@login_required
def exportar_todos_excel():
    contactos = Contacto.query.filter_by(usuario_id=current_user.id).all()

    if not contactos:
        flash('No hay contactos para exportar a Excel.', 'info')
        return redirect(url_for('listar_contacto'))

    # Crear una lista de diccionarios con los datos de los contactos
    data = []
    for contacto in contactos:
        data.append({
            'Nombre': contacto.nombre,
            'Primer Apellido': contacto.primer_apellido or '',
            'Segundo Apellido': contacto.segundo_apellido or '',
            'Teléfono': contacto.telefono,
            'Móvil': contacto.movil or '',
            'Email': contacto.email or '',
            'Dirección': contacto.direccion or '',
            'Actividad': contacto.tipo_actividad or '',
            'Nota': contacto.nota or '',
            'Dirección Mapa': contacto.direccion_mapa or '',
            'Fecha Ingreso': contacto.fecha_ingreso.strftime('%Y-%m-%d %H:%M:%S') if contacto.fecha_ingreso else '',
            'Empresa': contacto.empresa or '',
            'Sitio Web': contacto.sitio_web or '',
            'Capacidad Persona': contacto.capacidad_persona or '',
            'Participacion': contacto.participacion or '',
        })

    # Crear un DataFrame de pandas
    df = pd.DataFrame(data)

    # Crear un nuevo libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active

    # Escribir los encabezados desde las columnas del DataFrame
    ws.append(list(df.columns))

    # Escribir los datos del DataFrame a la hoja de cálculo
    for row in dataframe_to_rows(df, index=False, header=False):
        ws.append(row)

    # Crear un buffer en memoria para el archivo Excel
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"todos_los_contactos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')



# CALENDARIO
@app.route('/api/events', methods=['POST', 'GET'])
def handle_events():
    if request.method == 'GET':
        events = Event.query.order_by(Event.date).all()
        return jsonify([event.to_dict() for event in events])
    elif request.method == 'POST':
        data = request.get_json()
        date_str = data.get('date')
        time_str = data.get('time')  # Obtener la hora del request
        title = data.get('title')
        description = data.get('description')

        if not date_str or not title:
            return jsonify({'error': 'La fecha y el título son obligatorios'}), 400

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_obj = None # Inicializar time_obj
            if time_str:
                time_obj = datetime.strptime(time_str, '%H:%M').time()  # Convertir la hora a objeto time
            new_event = Event(date=date_obj, time=time_obj, title=title, description=description)
            db.session.add(new_event)
            db.session.commit()
            return jsonify({'message': 'Evento guardado exitosamente', 'id': new_event.id, 'event': new_event.to_dict()}), 201
        except ValueError as ve:
            db.session.rollback()
            print(f"Error de formato de fecha/hora: {ve}")
            return jsonify({'error': f'Formato de fecha/hora inválido (YYYY-MM-DD HH:MM): {ve}'}), 400
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar el evento: {e}")
            return jsonify({'error': f'Error al guardar el evento: {e}'}), 500

@app.route('/api/events/<int:id>', methods=['GET', 'DELETE', 'PUT'])
def handle_single_event(id):
    event = db.session.get(Event, id)
    if not event:
        return jsonify({'error': f'Evento con ID {id} no encontrado'}), 404

    if request.method == 'GET':
        return jsonify({'event': event.to_dict()}), 200  # Devuelve el evento como JSON
    elif request.method == 'DELETE':
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': f'Evento con ID {id} eliminado exitosamente'}), 200
    elif request.method == 'PUT':
        data = request.get_json()
        date_str = data.get('date')
        time_str = data.get('time') # Obtener la hora del request
        title = data.get('title')
        description = data.get('description')

        if date_str:
            try:
                event.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido (YYYY-MM-DD)'}), 400
        if time_str:
            try:
                event.time = datetime.strptime(time_str, '%H:%M').time()  # Convertir la hora a objeto time
            except ValueError:
                return jsonify({'error': 'Formato de hora inválido (HH:MM)'}), 400
        elif 'time' in data and data['time'] is None:
            event.time = None
        if title:
            event.title = title
        if description is not None:  # Permitir borrar la descripción si se envía null
            event.description = description

        db.session.commit()
        return jsonify({'message': f'Evento con ID {id} actualizado exitosamente', 'event': event.to_dict()}), 200

@app.route('/api/events/<int:id>', methods=['PUT'])
def update_event(id):
    event = db.session.get(Event, id)
    if event:
        data = request.get_json()
        date_str = data.get('date')
        time_str = data.get('time')  # Obtener la hora del request
        title = data.get('title')
        description = data.get('description')

        if date_str:
            try:
                event.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido (YYYY-MM-DD)'}), 400
        if time_str:
            try:
                event.time = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                return jsonify({'error': 'Formato de hora inválido (HH:MM)'}), 400
        elif 'time' in data and data['time'] is None:
            event.time = None
        if title:
            event.title = title
        if description is not None:  # Permitir borrar la descripción si se envía null
            event.description = description

        db.session.commit()
        return jsonify({'message': f'Evento con ID {id} actualizado exitosamente', 'event': event.to_dict()}), 200
    else:
        return jsonify({'error': f'Evento con ID {id} no encontrado'}), 404




# --- Rutas para Eventos ---
@app.route('/ver_eventos')
@login_required
def ver_eventos():
    # Asegúrate de usar el modelo 'Evento' que creamos para el CRUD de eventos
    eventos = Evento.query.filter_by(usuario_id=current_user.id).order_by(Evento.fecha_evento.desc()).all()
    return render_template('ver_evento.html', eventos=eventos, generate_csrf=generate_csrf) # Pasa generate_csrf

@app.route('/crear_evento', methods=['GET', 'POST'])
@login_required
def crear_evento():
    form = EventoForm() # Usar EventoForm
    if form.validate_on_submit():
        try:
            # Manejo del flyer
            flyer_filename = None
            if form.flyer.data:
                flyer_filename = secure_filename(form.flyer.data.filename)
                flyer_path = os.path.join(app.config['UPLOAD_FOLDER'], flyer_filename)
                form.flyer.data.save(flyer_path)

            fecha_evento_obj = datetime.strptime(form.fecha_evento.data, '%Y-%m-%d').date()
            hora_salida_obj = datetime.strptime(form.hora_salida.data, '%H:%M').time()

            nuevo_evento = Evento( # Usar Evento
                usuario_id=current_user.id,
                flyer_filename=flyer_filename,
                tipo_evento=form.tipo_evento.data,
                nombre_evento=form.nombre_evento.data,
                precio_evento=form.precio_evento.data,
                fecha_evento=fecha_evento_obj,
                dificultad_evento=form.dificultad_evento.data,
                incluye=form.incluye.data,
                lugar_salida=form.lugar_salida.data,
                hora_salida=hora_salida_obj,
                distancia=form.distancia.data,
                capacidad=form.capacidad.data,
                descripcion=form.descripcion.data,
                instrucciones=form.instrucciones.data,
                recomendaciones=form.recomendaciones.data
            )
            db.session.add(nuevo_evento)
            db.session.commit()
            flash('¡Evento creado exitosamente!', 'success')
            return redirect(url_for('ver_eventos'))
        except ValueError as e:
            flash(f'Error de formato de fecha/hora o precio: {e}. Asegúrese de usar BCE-MM-DD y HH:MM.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al guardar el evento: {e}', 'danger')
    return render_template('crear_evento.html', form=form)

@app.route('/editar_evento/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_evento(id):
    evento = Evento.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = EditarEventoForm(obj=evento) # Usar EditarEventoForm

    if request.method == 'GET':
        form.fecha_evento.data = evento.fecha_evento.strftime('%Y-%m-%d') if evento.fecha_evento else ''
        form.hora_salida.data = evento.hora_salida.strftime('%H:%M') if evento.hora_salida else ''
        form.precio_evento.data = str(evento.precio_evento) # Asegurarse de que sea string para el campo de texto

    if form.validate_on_submit():
        try:
            # Manejo del flyer
            if form.flyer.data:
                # Eliminar el flyer anterior si existe
                if evento.flyer_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], evento.flyer_filename)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], evento.flyer_filename))
                
                flyer_filename = secure_filename(form.flyer.data.filename)
                flyer_path = os.path.join(app.config['UPLOAD_FOLDER'], flyer_filename)
                form.flyer.data.save(flyer_path)
                evento.flyer_filename = flyer_filename
            
            evento.tipo_evento = form.tipo_evento.data
            evento.nombre_evento = form.nombre_evento.data
            evento.precio_evento = form.precio_evento.data
            evento.fecha_evento = datetime.strptime(form.fecha_evento.data, '%Y-%m-%d').date()
            evento.dificultad_evento = form.dificultad_evento.data
            evento.incluye = form.incluye.data
            evento.lugar_salida = form.lugar_salida.data
            evento.hora_salida = datetime.strptime(form.hora_salida.data, '%H:%M').time()
            evento.distancia = form.distancia.data
            evento.capacidad = form.capacidad.data
            evento.descripcion = form.descripcion.data
            evento.instrucciones = form.instrucciones.data
            evento.recomendaciones = form.recomendaciones.data

            db.session.commit()
            flash('¡Evento actualizado exitosamente!', 'success')
            return redirect(url_for('ver_eventos'))
        except ValueError as e:
            flash(f'Error de formato de fecha/hora o precio: {e}. Asegúrese de usar BCE-MM-DD y HH:MM.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al actualizar el evento: {e}', 'danger')
    return render_template('editar_evento.html', form=form, evento=evento)

@app.route('/borrar_evento/<int:id>', methods=['POST'])
@login_required
def borrar_evento(id):
    evento = Evento.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if evento:
        # Eliminar el flyer asociado si existe
        if evento.flyer_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], evento.flyer_filename)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], evento.flyer_filename))
        
        db.session.delete(evento)
        db.session.commit()
        flash('¡Evento borrado exitosamente!', 'success')
    else:
        flash('Error al intentar borrar el evento.', 'danger')
    return redirect(url_for('ver_eventos'))

@app.route('/exportar_evento_pdf/<int:id>')
@login_required
def exportar_evento_pdf(id):
    evento = Evento.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20))
    # Modificar el estilo 'Heading2' existente en lugar de añadir uno nuevo
    styles['Heading2'].fontSize = 14
    styles['Heading2'].leading = 16
    styles['Heading2'].spaceBefore = 12
    styles['Heading2'].spaceAfter = 6
    styles['Heading2'].fontName = 'Helvetica-Bold'

    # Modificar el estilo 'BodyText' existente en lugar de añadir uno nuevo
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 12
    styles['BodyText'].spaceAfter = 6

    # Añadir el estilo 'ListText' si no existe, o modificarlo si existe
    if 'ListText' not in styles:
        styles.add(ParagraphStyle(name='ListText', fontSize=10, leading=12, spaceAfter=3, bulletIndent=18, leftIndent=36))
    else:
        styles['ListText'].fontSize = 10
        styles['ListText'].leading = 12
        styles['ListText'].spaceAfter = 3
        styles['ListText'].bulletIndent = 18
        styles['ListText'].leftIndent = 36

    story = []

    # Título del evento
    story.append(Paragraph(evento.nombre_evento, styles['TitleStyle']))
    story.append(Spacer(1, 0.2 * inch))

    # Flyer del evento (si existe)
    if evento.flyer_filename:
        flyer_path = os.path.join(app.config['UPLOAD_FOLDER'], evento.flyer_filename)
        if os.path.exists(flyer_path):
            try:
                # Determinar el tipo de archivo para mostrarlo correctamente
                mime_type, _ = mimetypes.guess_type(flyer_path)
                if mime_type and mime_type.startswith('image'):
                    img = Image(flyer_path)
                    # Ajustar tamaño de la imagen para que quepa en la página
                    img_width = 4 * inch
                    img_height = img_width * (img.drawHeight / img.drawWidth)
                    img.drawWidth = img_width
                    img.drawHeight = img_height
                    story.append(img)
                    story.append(Spacer(1, 0.2 * inch))
                elif mime_type == 'application/pdf':
                    story.append(Paragraph("<i>(El flyer es un PDF y no se puede incrustar directamente en este PDF. Por favor, ábralo por separado.)</i>", styles['BodyText']))
                    story.append(Spacer(1, 0.2 * inch))
                else:
                    story.append(Paragraph("<i>(Tipo de archivo de flyer no soportado para incrustar en PDF.)</i>", styles['BodyText']))

            except Exception as e:
                flash(f"No se pudo cargar la imagen/PDF del flyer: {e}", "warning")
                story.append(Paragraph("<i>(No se pudo cargar el flyer del evento)</i>", styles['BodyText']))
        else:
            story.append(Paragraph("<i>(Flyer no encontrado en el servidor)</i>", styles['BodyText']))
    
    # Información general
    story.append(Paragraph(f"<b>Tipo de Evento:</b> {evento.tipo_evento}", styles['BodyText']))
    story.append(Paragraph(f"<b>Fecha:</b> {evento.fecha_evento.strftime('%d-%m-%Y')}", styles['BodyText']))
    story.append(Paragraph(f"<b>Hora de Salida:</b> {evento.hora_salida.strftime('%H:%M')}", styles['BodyText']))
    story.append(Paragraph(f"<b>Precio:</b> ₡{evento.precio_evento:,.2f}", styles['BodyText']))
    story.append(Paragraph(f"<b>Dificultad:</b> {evento.dificultad_evento}", styles['BodyText']))
    story.append(Paragraph(f"<b>Lugar de Salida:</b> {evento.lugar_salida}", styles['BodyText']))
    story.append(Paragraph(f"<b>Distancia:</b> {evento.distancia or 'N/A'}", styles['BodyText']))
    story.append(Paragraph(f"<b>Capacidad:</b> {evento.capacidad} personas", styles['BodyText']))
    story.append(Spacer(1, 0.2 * inch))

    # Descripción
    if evento.descripcion:
        story.append(Paragraph("<b>Descripción:</b>", styles['Heading2']))
        story.append(Paragraph(evento.descripcion, styles['BodyText']))
        story.append(Spacer(1, 0.2 * inch))

    # Incluye
    if evento.incluye:
        story.append(Paragraph("<b>Incluye:</b>", styles['Heading2']))
        # Dividir por líneas si es una lista
        for item in evento.incluye.split('\n'):
            if item.strip():
                story.append(Paragraph(f"• {item.strip()}", styles['ListText']))
        story.append(Spacer(1, 0.2 * inch))

    # Instrucciones
    if evento.instrucciones:
        story.append(Paragraph("<b>Instrucciones:</b>", styles['Heading2']))
        for item in evento.instrucciones.split('\n'):
            if item.strip():
                story.append(Paragraph(f"• {item.strip()}", styles['ListText']))
        story.append(Spacer(1, 0.2 * inch))

    # Recomendaciones
    if evento.recomendaciones:
        story.append(Paragraph("<b>Recomendaciones:</b>", styles['Heading2']))
        for item in evento.recomendaciones.split('\n'):
            if item.strip():
                story.append(Paragraph(f"• {item.strip()}", styles['ListText']))
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    buffer.seek(0)
    
    filename = f"evento_{evento.nombre_evento.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# --- Ruta para Ver Facturas --- 
@app.route('/ver_facturas')
@login_required
def ver_facturas():
    facturas = Factura.query.filter_by(usuario_id=current_user.id).all()
    # ESTA ES LA LÍNEA QUE DEBE CAMBIAR:
    # Antes: return render_template('ver_facturas.html', facturas=facturas, csrf_token=generate_csrf())
    # Ahora: Pasa la función 'generate_csrf' a la plantilla.
    # La plantilla la llamará como 'generate_csrf()' en el JavaScript.
    return render_template('ver_facturas.html', facturas=facturas, generate_csrf=generate_csrf)

# --- Nueva Ruta para Ver el Detalle Completo de una Factura ---
@app.route('/ver_detalle_factura/<int:id>')
@login_required
def ver_detalle_factura(id):
    # Busca la factura por su ID y asegúrate de que pertenezca al usuario actual
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    return render_template('ver_detalle_factura.html', factura=factura)

# --- Ruta para Crear Nueva Factura ---
@app.route('/crear_factura', methods=['GET', 'POST'])
@login_required
def crear_factura():
    form = CrearFacturaForm()

    if form.validate_on_submit():
        cliente_id = form.cliente_id.data
        fecha_emision_str = form.fecha_emision.data
        descripcion = form.descripcion.data
        monto_total = form.monto_total.data

        # --- Obtener datos de los NUEVOS CAMPOS ---
        interes = form.interes.data
        realizado_por = form.realizado_por.data
        sinpe = form.sinpe.data
        tipo_actividad = form.tipo_actividad.data
        nombre_actividad_etapa = form.nombre_actividad_etapa.data
        costo_actividad = form.costo_actividad.data
        otras_descripcion = form.otras_descripcion.data
        # --- Fin de obtención de NUEVOS CAMPOS ---

        # --- Lógica para generar automáticamente el numero_factura ---
        existing_factura_numbers = db.session.query(Factura.numero_factura) \
                                         .filter_by(usuario_id=current_user.id) \
                                         .all()
        numeric_factura_numbers = []
        for row in existing_factura_numbers:
            num_str = row.numero_factura
            if num_str and num_str.isdigit():
                numeric_factura_numbers.append(int(num_str))

        MAX_INITIAL_FACTURA_NUMBER = 158 # Asegúrate de que este número tenga sentido para ti
        max_num = 0
        if numeric_factura_numbers:
            max_num = max(numeric_factura_numbers)

        if max_num < MAX_INITIAL_FACTURA_NUMBER:
            next_num = MAX_INITIAL_FACTURA_NUMBER
        else:
            next_num = max_num + 1

        generated_numero_factura = f"{next_num:06d}" # Formato a 6 dígitos con ceros iniciales

        if Factura.query.filter_by(numero_factura=generated_numero_factura, usuario_id=current_user.id).first():
            flash(f'Error al generar número de factura automático: El número {generated_numero_factura} ya existe. Por favor, intente de nuevo.', 'danger')
            return render_template('crear_factura.html', form=form)
        # --- Fin de la lógica de generación ---

        try:
            fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            nueva_factura = Factura(
                numero_factura=generated_numero_factura,
                cliente_id=cliente_id,
                fecha_emision=fecha_emision,
                descripcion=descripcion,
                monto_total=monto_total,
                usuario_id=current_user.id,
                # --- ASIGNAR NUEVOS CAMPOS (con manejo de Optional si es necesario) ---
                interes=interes,
                realizado_por=realizado_por,
                sinpe=sinpe,
                tipo_actividad=tipo_actividad,
                nombre_actividad_etapa=nombre_actividad_etapa if nombre_actividad_etapa else None,
                costo_actividad=costo_actividad if costo_actividad else None, # Puede ser None si es Optional y vacío
                otras_descripcion=otras_descripcion if otras_descripcion else None
                # --- FIN ASIGNACIÓN NUEVOS CAMPOS ---
            )
            db.session.add(nueva_factura)
            db.session.commit()
            flash(f'¡Factura {generated_numero_factura} creada exitosamente!', 'success')
            return redirect(url_for('ver_facturas'))
        except ValueError:
            flash('Formato de fecha de emisión o costo de actividad inválido. Asegúrese de usar BCE-MM-DD y un número válido para el costo.', 'danger')
            return render_template('crear_factura.html', form=form)
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al guardar la factura: {e}', 'danger')
            return render_template('crear_factura.html', form=form)

    return render_template('crear_factura.html', form=form)

# --- Ruta para Editar Factura ---
@app.route('/editar_factura/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_factura(id):
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = EditarFacturaForm(factura)

    if request.method == 'GET':
        # --- Pre-llenar campos existentes ---
        form.numero_factura.data = factura.numero_factura
        form.cliente_id.data = factura.cliente_id
        form.fecha_emision.data = factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else ''
        form.descripcion.data = factura.descripcion
        form.monto_total.data = str(factura.monto_total) if factura.monto_total is not None else ''

        # --- Pre-llenar NUEVOS CAMPOS ---
        form.interes.data = factura.interes if factura.interes else 'Factura' # Asegura un valor por defecto si es None
        form.realizado_por.data = factura.realizado_por if factura.realizado_por else 'Jenny Ceciliano Cordoba'
        form.sinpe.data = factura.sinpe if factura.sinpe else 'Jenny Ceciliano Cordoba-86529837'
        form.tipo_actividad.data = factura.tipo_actividad if factura.tipo_actividad else 'Servicios'
        form.nombre_actividad_etapa.data = factura.nombre_actividad_etapa
        form.costo_actividad.data = str(factura.costo_actividad) if factura.costo_actividad is not None else ''
        form.otras_descripcion.data = factura.otras_descripcion
        # --- Fin de pre-llenado de NUEVOS CAMPOS ---

    if form.validate_on_submit():
        factura.cliente_id = form.cliente_id.data
        fecha_emision_str = form.fecha_emision.data
        factura.descripcion = form.descripcion.data
        factura.monto_total = form.monto_total.data

        # --- Actualizar NUEVOS CAMPOS ---
        factura.interes = form.interes.data
        factura.realizado_por = form.realizado_por.data
        factura.sinpe = form.sinpe.data
        factura.tipo_actividad = form.tipo_actividad.data
        factura.nombre_actividad_etapa = form.nombre_actividad_etapa.data if form.nombre_actividad_etapa.data else None
        factura.costo_actividad = form.costo_actividad.data if form.costo_actividad.data else None
        factura.otras_descripcion = form.otras_descripcion.data if form.otras_descripcion.data else None
        # --- Fin de actualización de NUEVOS CAMPOS ---

        try:
            factura.fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            db.session.commit()
            flash('¡Factura actualizada exitosamente!', 'success')
            return redirect(url_for('ver_facturas'))
        except ValueError:
            flash('Formato de fecha de emisión o costo de actividad inválido. Asegúrese de usar BCE-MM-DD y un número válido para el costo.', 'danger')
            return render_template('editar_factura.html', form=form, factura_id=id)
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al actualizar la factura: {e}', 'danger')
            return render_template('editar_factura.html', form=form, factura_id=id)

    return render_template('editar_factura.html', form=form, factura_id=id)

# --- Ruta para Borrar Factura ---
@app.route('/borrar_factura/<int:id>', methods=['POST'])
@login_required
def borrar_factura(id):
    # Nota: Es crucial usar un formulario POST y el token CSRF para esto
    # para proteger contra ataques CSRF.
    # El token se genera y se pasa en ver_facturas.html
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if factura:
        db.session.delete(factura)
        db.session.commit()
        flash('¡Factura borrada exitosamente!', 'success')
    else:
        flash('Error al intentar borrar la factura.', 'danger')
    return redirect(url_for('ver_facturas'))


# --- Nueva ruta para ver el detalle de un evento ---
@app.route('/detalle_evento/<int:id>')
@login_required
def detalle_evento(id):
    evento = Evento.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    return render_template('detalle_evento.html', evento=evento, generate_csrf=generate_csrf)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=3030)

# Migraciones Cmder
        # set FLASK_APP=main.py     <--Crea un directorio de migraciones
        # flask db init             <--
        # $ flask db stamp head
        # $ flask db migrate
        # $ flask db migrate -m "mensaje x"
        # $ flask db upgrade
        # ERROR [flask_migrate] Error: Target database is not up to date.
        # $ flask db stamp head
        # $ flask db migrate
        # $ flask db upgrade
        # git clone https://github.com/kerm1977/MI_APP_FLASK.git
        # mysql> DROP DATABASE kenth1977$db; PYTHONANYWHATE
# -----------------------

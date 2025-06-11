from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, FileField, TextAreaField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, Optional, NumberRange
from flask_wtf.csrf import generate_csrf, CSRFProtect # Importar CSRFProtect
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
import os
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from PIL import Image as PILImage # Importar Pillow para convertir a JPG
import fitz # Importar PyMuPDF para manejar PDFs (necesario para convertir a JPG)
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user # Importar LoginManager



# Importar db y los modelos desde models.py
from models import db, User, Contacto, Factura, Event, Evento, GestorProyecto, Info, ListaActividad, ContactoActividad, Abono # Asegúrate de que Factura y Evento estén importados y AHORA los nuevos modelos




#Importar Funciones del Invetarios
from inventario import inventario_bp

# Importar el Blueprint de pagos desde el nuevo módulo pagos.py
from pagos import pagos_bp # Importa el Blueprint de pagos

# Importar el Blueprint de rifas y su función de configuración desde rifas.py
from rifas import rifas_bp, configure_rifas_uploads # CAMBIO CLAVE AQUÍ: Importa configure_rifas_uploads

# Importar el blueprint de notas
from notas import notas_bp # Importa el blueprint que creamos

# Importar el blueprint del reproductor multimedia
from player import player_bp # <-- Importar el blueprint del reproductor

# Importar el blueprint del gestor de proyectos y su función de configuración
from gestor import gestor_bp, configure_gestor_uploads # <-- IMPORTAR EL GESTOR DE PROYECTOS

# Importar el blueprint de info
from info import info_bp # Importa el blueprint de info para el nuevo CRUD

# Importar el blueprint de abonos y su función de configuración
from lista_abonos import abonos_bp, configure_abonos_uploads # <-- NUEVA LÍNEA



app = Flask(__name__)

app.config['SECRET_KEY'] = 'tu_clave_secreta' # ¡ASEGÚRATE DE CAMBIAR ESTO EN PRODUCCIÓN!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Nuevas extensiones permitidas para el reproductor multimedia
app.config['ALLOWED_MEDIA_EXTENSIONS'] = {'mp3', 'mp4', 'wma', 'wmv', 'jpg', 'jpeg', 'png', 'pdf'} # <-- Nuevas extensiones para multimedia
# ELIMINADO: csrf = CSRFProtect(app) # <-- ESTA LÍNEA ESTABA DUPLICADA

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

# Inicializar CSRFProtect AQUI (Esta es la única instancia correcta)
csrf = CSRFProtect(app) # <-- ESTA ES LA LÍNEA CRÍTICA A AÑADIR

def is_authenticated(self):
    return True


# --- Registro del Blueprint de Pagos e inventarios ---
app.register_blueprint(pagos_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(rifas_bp, url_prefix='/rifas') # CAMBIO CLAVE AQUÍ: Importa configure_rifas_uploads
app.register_blueprint(notas_bp)
app.register_blueprint(player_bp, url_prefix='/player') # <-- Registrar el blueprint del reproductor
app.register_blueprint(gestor_bp, url_prefix='/proyectos') # <-- REGISTRAR EL BLUEPRINT DEL GESTOR DE PROYECTOS
app.register_blueprint(info_bp, url_prefix='/info') # REGISTRAR EL BLUEPRINT DE INFO
app.register_blueprint(abonos_bp) # <-- NUEVA LÍNEA

# CAMBIO CLAVE AQUÍ: Llama a la función de configuración de la carpeta de subida de rifas
with app.app_context(): # Es buena práctica llamar a esto dentro de un contexto de aplicación
    configure_rifas_uploads(app)
    configure_gestor_uploads(app) # <-- LLAMAR LA FUNCIÓN DE CONFIGURACIÓN DEL GESTOR DE PROYECTOS
    configure_abonos_uploads(app) # <-- NUEVA LÍNEA


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
    impuesto_monto = StringField('Monto de Impuesto (¢)', validators=[Optional(), Regexp(r'^\d+(\.\d{1,2})?$', message="El impuesto debe ser un número válido con hasta 2 decimales.")], render_kw={"class": "form-control"})


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
    impuesto_monto = StringField('Monto de Impuesto (¢)', validators=[Optional(), Regexp(r'^\d+(\.\d{1,2})?$', message="El impuesto debe ser un número válido con hasta 2 decimales.")], render_kw={"class": "form-control"})


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
    precio_evento = StringField('Precio del Evento (¢)', validators=[DataRequired(), Regexp(r'^\d+(\.\d{1,2})?$', message="El precio debe ser un número válido con hasta 2 decimales.")])
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
    precio_evento = StringField('Precio del Evento (¢)', validators=[DataRequired(), Regexp(r'^\d+(\.\d{1,2})?$', message="El precio debe ser un número válido con hasta 2 decimales.")])
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
            new_user = User(username=username, email=email, cedula=cedula, telefono=telefono, image_filename=filename)
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

# NUEVA RUTA PARA VER DETALLE DEL CONTACTO
@app.route('/contacto_detalle/<int:id>')
@login_required
def contacto_detalle(id):
    contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    return render_template('contacto_detail.html', contacto=contacto, generate_csrf=generate_csrf)

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
    return render_template('editar_contacto.html', form=form, contacto=contacto, contacto_id=id)

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
        org_param.value = [contacto.empresa]
    if contacto.sitio_web:
        url_param = v.add('URL')
        url_param.value = contacto.sitio_web
    if contacto.capacidad_persona:
        v.add('X-CAPACIDAD-PERSONA').value = contacto.capacidad_persona
    if contacto.participacion:
        v.add('X-PARTICIPACION').value = contacto.participacion

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
        time_str = data.get('time')
        title = data.get('title')
        description = data.get('description')

        if not date_str or not title:
            return jsonify({'error': 'La fecha y el título son obligatorios'}), 400

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_obj = None
            if time_str:
                time_obj = datetime.strptime(time_str, '%H:%M').time()
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
        return jsonify({'event': event.to_dict()}), 200
    elif request.method == 'DELETE':
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': f'Evento con ID {id} eliminado exitosamente'}), 200
    elif request.method == 'PUT':
        data = request.get_json()
        date_str = data.get('date')
        time_str = data.get('time')
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
        if description is not None:
            event.description = description

        db.session.commit()
        return jsonify({'message': f'Evento con ID {id} actualizado exitosamente', 'event': event.to_dict()}), 200
    else:
        return jsonify({'error': f'Evento con ID {id} no encontrado'}), 404


# --- Rutas para Eventos ---
@app.route('/ver_eventos')
@login_required
def ver_eventos():
    eventos = Evento.query.filter_by(usuario_id=current_user.id).order_by(Evento.fecha_evento.desc()).all()
    return render_template('ver_evento.html', eventos=eventos, generate_csrf=generate_csrf)

@app.route('/crear_evento', methods=['GET', 'POST'])
@login_required
def crear_evento():
    form = EventoForm() # Usa EventoForm aquí
    if form.validate_on_submit():
        try:
            flyer_filename = None
            if form.flyer.data:
                flyer_filename = secure_filename(form.flyer.data.filename)
                flyer_path = os.path.join(app.config['UPLOAD_FOLDER'], flyer_filename)
                form.flyer.data.save(flyer_path)

            fecha_evento_obj = datetime.strptime(form.fecha_evento.data, '%Y-%m-%d').date()
            hora_salida_obj = datetime.strptime(form.hora_salida.data, '%H:%M').time()

            nuevo_evento = Evento(
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
    return render_template('crear_evento.html', form=form) # Renderiza la plantilla de evento

@app.route('/editar_evento/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_evento(id):
    evento = Evento.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = EditarEventoForm(obj=evento)

    if request.method == 'GET':
        form.fecha_evento.data = evento.fecha_evento.strftime('%Y-%m-%d') if evento.fecha_evento else ''
        form.hora_salida.data = evento.hora_salida.strftime('%H:%M') if evento.hora_salida else ''
        form.precio_evento.data = str(evento.precio_evento)

    if form.validate_on_submit():
        try:
            if form.flyer.data:
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
    
    # --- Estilos personalizados para la factura ---
    styles.add(ParagraphStyle(name='CompanyHeader', fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=28, leading=32, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold', textColor=colors.HexColor('#007bff')))
    styles.add(ParagraphStyle(name='DetailText', fontSize=10, leading=12, spaceAfter=3))
    styles.add(ParagraphStyle(name='TableBodyText', fontSize=10, leading=12, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='TableTotalText', fontSize=12, leading=14, alignment=TA_RIGHT, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FooterText', fontSize=9, leading=10, alignment=TA_CENTER, spaceBefore=20))

    story = []

    # --- Encabezado de la Empresa (Placeholder) ---
    story.append(Paragraph("<b>La Tribu Hiking</b>", styles['CompanyHeader']))
    story.append(Paragraph("Dirección: San Diego, La Unión, Cartago, Costa Rica", styles['CompanyHeader']))
    story.append(Paragraph("Teléfono: +506-86227500 | Email: lthikingcr@gmail.com", styles['CompanyHeader']))
    story.append(Spacer(1, 0.4 * inch))

    # --- Título de la Factura ---
    story.append(Paragraph("FACTURA DE EVENTO", styles['InvoiceTitle']))
    story.append(Spacer(1, 0.3 * inch))

    # --- Detalles de la Factura y del Cliente ---
    invoice_details_data = [
        [Paragraph(f"<b>Número de Factura:</b> EVENTO-{evento.id}", styles['DetailText']),
         Paragraph(f"<b>Fecha de Emisión:</b> {evento.fecha_evento.strftime('%d-%m-%Y')}", styles['DetailText'])],
        [Paragraph(f"<b>Cliente:</b> Participante del Evento", styles['DetailText']),
         Paragraph(f"<b>Realizado por:</b> {evento.usuario.username}", styles['DetailText'])],
        [Paragraph(f"<b>Tipo de Evento:</b> {evento.tipo_evento}", styles['DetailText']),
         Paragraph(f"<b>Lugar de Salida:</b> {evento.lugar_salida}", styles['DetailText'])],
        [Paragraph(f"<b>Hora de Salida:</b> {evento.hora_salida.strftime('%H:%M')}", styles['DetailText']),
         Paragraph(f"<b>Dificultad:</b> {evento.dificultad_evento}", styles['DetailText'])]
    ]
    invoice_details_table = Table(invoice_details_data, colWidths=[4 * inch, 3 * inch])
    invoice_details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(invoice_details_table)
    story.append(Spacer(1, 0.3 * inch))

    # --- Tabla de Conceptos ---
    table_data = []
    table_data.append([
        Paragraph("<b>Concepto</b>", styles['SectionHeader']),
        Paragraph("<b>Cantidad</b>", styles['SectionHeader']),
        Paragraph("<b>Precio Unitario</b>", styles['SectionHeader']),
        Paragraph("<b>Total</b>", styles['SectionHeader'])
    ])

    # Fila del evento
    precio_unitario = float(evento.precio_evento)
    total_linea = precio_unitario * 1 # Cantidad es 1 para el evento
    table_data.append([
        Paragraph(evento.nombre_evento, styles['TableBodyText']),
        Paragraph("1", styles['TableBodyText']),
        Paragraph(f"¢{precio_unitario:,.0f}", styles['TableBodyText']),
        Paragraph(f"¢{total_linea:,.0f}", styles['TableBodyText'])
    ])

    # Si hay descripción, se puede añadir como una línea adicional o en el concepto
    if evento.descripcion:
        table_data.append([
            Paragraph(f"<i>Descripción:</i> {evento.descripcion}", styles['TableBodyText']),
            '', '', ''
        ])

    # Crear la tabla
    col_widths = [3.5 * inch, 0.8 * inch, 1.2 * inch, 1.5 * inch]
    invoice_table = Table(table_data, colWidths=col_widths)
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')), # Color de fondo para el encabezado
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')), # Bordes de la tabla
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 0.2 * inch))

    # --- Totales ---
    subtotal = float(evento.precio_evento)
    impuestos = 0.00 # Asumiendo 0% de impuestos por ahora, puedes ajustar esto
    total_final = subtotal + impuestos

    totals_data = [
        [Paragraph("Subtotal:", styles['TableTotalText']), Paragraph(f"¢{subtotal:,.0f}", styles['TableTotalText'])],
        [Paragraph("Impuestos (0%):", styles['TableTotalText']), Paragraph(f"¢{impuestos:,.0f}", styles['TableTotalText'])],
        [Paragraph("TOTAL:", styles['TableTotalText']), Paragraph(f"¢{total_final:,.0f}", styles['TableTotalText'])]
    ]
    totals_table = Table(totals_data, colWidths=[5.5 * inch, 2 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F0F0F0')), # Fondo para la fila total
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.5 * inch))

    # --- Información de Pago (Ejemplo) ---
    story.append(Paragraph("<b>Información de Pago:</b>", styles['SectionHeader']))
    story.append(Paragraph("Método de Pago: Transferencia Bancaria / SINPE Móvil", styles['DetailText']))
    story.append(Paragraph("SINPE Móvil: Jenny Ceciliano Cordoba - 86529837", styles['DetailText']))
    story.append(Paragraph("SINPE Móvil: Kenneth Ruiz Matamoros - 86227500", styles['DetailText']))
    story.append(Spacer(1, 0.5 * inch))

    # --- Pie de Página ---
    story.append(Paragraph("<i>La Tribu de los Libres.</i>", styles['FooterText']))
    story.append(Paragraph(f"Factura generada el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['FooterText']))

    doc.build(story)
    buffer.seek(0)
    
    filename = f"factura_evento_{evento.nombre_evento.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# --- Rutas para Facturas --- 
@app.route('/ver_facturas')
@login_required
def ver_facturas():
    facturas = Factura.query.filter_by(usuario_id=current_user.id).all()
    return render_template('ver_facturas.html', facturas=facturas, generate_csrf=generate_csrf)

# --- Nueva Ruta para Ver el Detalle Completo de una Factura ---
@app.route('/ver_detalle_factura/<int:id>')
@login_required
def ver_detalle_factura(id):
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    return render_template('ver_detalle_factura.html', factura=factura, generate_csrf=generate_csrf)

# --- Ruta para Crear Nueva Factura ---
@app.route('/crear_factura', methods=['GET', 'POST'])
@login_required
def crear_factura():
    form = CrearFacturaForm() # Usa CrearFacturaForm aquí

    if form.validate_on_submit():
        cliente_id = form.cliente_id.data
        fecha_emision_str = form.fecha_emision.data
        descripcion = form.descripcion.data
        monto_total = form.monto_total.data
        impuesto_monto = form.impuesto_monto.data # Obtener el monto del impuesto

        interes = form.interes.data
        realizado_por = form.realizado_por.data
        sinpe = form.sinpe.data
        tipo_actividad = form.tipo_actividad.data
        nombre_actividad_etapa = form.nombre_actividad_etapa.data
        costo_actividad = form.costo_actividad.data
        otras_descripcion = form.otras_descripcion.data

        existing_factura_numbers = db.session.query(Factura.numero_factura) \
                                         .filter_by(usuario_id=current_user.id) \
                                         .all()
        numeric_factura_numbers = []
        for row in existing_factura_numbers:
            num_str = row.numero_factura
            if num_str and num_str.isdigit():
                numeric_factura_numbers.append(int(num_str))

        MAX_INITIAL_FACTURA_NUMBER = 158
        max_num = 0
        if numeric_factura_numbers:
            max_num = max(numeric_factura_numbers)

        if max_num < MAX_INITIAL_FACTURA_NUMBER:
            next_num = MAX_INITIAL_FACTURA_NUMBER
        else:
            next_num = max_num + 1

        generated_numero_factura = f"{next_num:06d}"

        if Factura.query.filter_by(numero_factura=generated_numero_factura, usuario_id=current_user.id).first():
            flash(f'Error al generar número de factura automático: El número {generated_numero_factura} ya existe. Por favor, intente de nuevo.', 'danger')
            return render_template('crear_factura.html', form=form)

        try:
            fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            nueva_factura = Factura(
                numero_factura=generated_numero_factura,
                cliente_id=cliente_id,
                fecha_emision=fecha_emision,
                descripcion=descripcion,
                monto_total=monto_total,
                usuario_id=current_user.id,
                interes=interes,
                realizado_por=realizado_por,
                sinpe=sinpe,
                tipo_actividad=tipo_actividad,
                nombre_actividad_etapa=nombre_actividad_etapa if nombre_actividad_etapa else None,
                costo_actividad=costo_actividad if costo_actividad else None,
                otras_descripcion=otras_descripcion if otras_descripcion else None,
                impuesto_monto=impuesto_monto if impuesto_monto else 0.00 # Guardar el monto del impuesto
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
        form.numero_factura.data = factura.numero_factura
        form.cliente_id.data = factura.cliente_id
        form.fecha_emision.data = factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else ''
        form.descripcion.data = factura.descripcion
        form.monto_total.data = str(factura.monto_total) if factura.monto_total is not None else ''

        form.interes.data = factura.interes if factura.interes else 'Factura'
        form.realizado_por.data = factura.realizado_por if factura.realizado_por else 'Jenny Ceciliano Cordoba'
        form.sinpe.data = factura.sinpe if factura.sinpe else 'Jenny Ceciliano Cordoba-86529837'
        form.tipo_actividad.data = factura.tipo_actividad if factura.tipo_actividad else 'Servicios'
        form.nombre_actividad_etapa.data = factura.nombre_actividad_etapa
        form.costo_actividad.data = str(factura.costo_actividad) if factura.costo_actividad is not None else ''
        form.otras_descripcion.data = factura.otras_descripcion
        form.impuesto_monto.data = str(factura.impuesto_monto) if factura.impuesto_monto is not None else '0.00' # Cargar el monto del impuesto


    if form.validate_on_submit():
        factura.cliente_id = form.cliente_id.data
        fecha_emision_str = form.fecha_emision.data
        factura.descripcion = form.descripcion.data
        factura.monto_total = form.monto_total.data
        factura.impuesto_monto = form.impuesto_monto.data if form.impuesto_monto.data else 0.00 # Actualizar el monto del impuesto


        factura.interes = form.interes.data
        factura.realizado_por = form.realizado_por.data
        factura.sinpe = form.sinpe.data
        factura.tipo_actividad = form.tipo_actividad.data
        factura.nombre_actividad_etapa = form.nombre_actividad_etapa.data if form.nombre_actividad_etapa.data else None
        factura.costo_actividad = form.costo_actividad.data if form.costo_actividad.data else None
        factura.otras_descripcion = form.otras_descripcion.data if form.otras_descripcion.data else None

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

# --- Rutas de Exportación para contacto_detail.html ---

@app.route('/exportar_contacto_pdf/<int:id>')
@login_required
def exportar_contacto_pdf(id):
    contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados: Se modifican los estilos existentes en lugar de añadir nuevos
    styles['Title'].alignment = TA_CENTER
    styles['Title'].fontSize = 24
    styles['Title'].spaceAfter = 20
    styles['Title'].fontName = 'Helvetica-Bold'

    # Modificar 'Heading2' si existe, o crearlo si no existe (aunque ReportLab lo tiene por defecto)
    if 'Heading2' in styles:
        styles['Heading2'].fontSize = 14
        styles['Heading2'].spaceBefore = 12
        styles['Heading2'].spaceAfter = 6
        styles['Heading2'].fontName = 'Helvetica-Bold'
        styles['Heading2'].textColor = colors.HexColor('#007bff')
    else:
        # Esto es un fallback, pero ReportLab suele tener 'Heading2' por defecto
        styles.add(ParagraphStyle(name='Heading2', fontSize=14, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold', textColor=colors.HexColor('#007bff')))

    # Modificar 'BodyText' si existe, o crearlo si no existe
    if 'BodyText' in styles:
        styles['BodyText'].fontSize = 10
        styles['BodyText'].spaceAfter = 5
    else:
        styles.add(ParagraphStyle(name='BodyText', fontSize=10, spaceAfter=5))

    styles.add(ParagraphStyle(name='Label', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#333333')))
    styles.add(ParagraphStyle(name='Value', fontSize=10, fontName='Helvetica'))

    story = []

    story.append(Paragraph(f"Detalle del Contacto: {contacto.nombre} {contacto.primer_apellido or ''}", styles['Title']))
    story.append(Spacer(1, 0.2 * inch))

    # Información general
    story.append(Paragraph("Información General", styles['Heading2']))
    
    # Usar una tabla para organizar la información de forma más estructurada
    # La lista de datos ya tiene encabezados, y las siguientes adiciones deben ser filas completas
    data = [] # Se reinicializa para evitar duplicación con la definición de add_row_if_exists

    # Función auxiliar para añadir filas a la tabla si el dato existe
    def add_row_if_exists(label, value_attr_name):
        attr_value = getattr(contacto, value_attr_name, None)
        display_value = "-"
        if attr_value is not None and attr_value != '':
            if isinstance(attr_value, (date, datetime)):
                # Manejo específico para fechas
                if value_attr_name == "fecha_nacimiento" or value_attr_name == "aniversario":
                    display_value = attr_value.strftime('%Y-%m-%d')
                elif value_attr_name == "proxima_interaccion" or value_attr_name == "fecha_ingreso":
                    display_value = attr_value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    display_value = str(attr_value)
            elif isinstance(attr_value, bool):
                display_value = "Sí" if attr_value else "No"
            else:
                display_value = str(attr_value)
        
        data.append([
            Paragraph(f"<b>{label}:</b>", styles['Label']),
            Paragraph(display_value, styles['Value'])
        ])


    add_row_if_exists("Nombre", 'nombre')
    add_row_if_exists("Primer Apellido", 'primer_apellido')
    add_row_if_exists("Segundo Apellido", 'segundo_apellido')
    add_row_if_exists("Empresa", 'empresa')
    add_row_if_exists("Puesto", 'puesto') # Asumimos que 'puesto' puede existir o no
    add_row_if_exists("Teléfono", 'telefono')
    add_row_if_exists("Móvil", 'movil')
    add_row_if_exists("Email", 'email')
    add_row_if_exists("Dirección", 'direccion')
    add_row_if_exists("Ciudad", 'ciudad') 
    add_row_if_exists("Provincia", 'provincia') 
    add_row_if_exists("Código Postal", 'codigo_postal')
    add_row_if_exists("País", 'pais')
    add_row_if_exists("Fecha de Nacimiento", 'fecha_nacimiento')
    add_row_if_exists("Red Social", 'red_social')
    add_row_if_exists("Sitio Web", 'sitio_web')
    add_row_if_exists("Relación", 'relacion')
    add_row_if_exists("Método de Contacto Preferido", 'metodo_contacto_preferido')
    add_row_if_exists("Fuente del Contacto", 'fuente_contacto')
    add_row_if_exists("Intereses", 'intereses')
    add_row_if_exists("Historial de Interacción", 'historial_interaccion')
    add_row_if_exists("Próxima Interacción", 'proxima_interaccion')
    add_row_if_exists("Etiquetas", 'etiquetas')
    add_row_if_exists("Grupo", 'grupo')
    add_row_if_exists("Preferencias de Comunicación", 'preferencias_comunicacion')
    add_row_if_exists("Consentimiento de Datos", 'consentimiento_datos')
    add_row_if_exists("Notas", 'nota')
    add_row_if_exists("Género", 'genero')
    add_row_if_exists("Organización", 'organizacion')
    add_row_if_exists("Departamento", 'departamento')
    add_row_if_exists("Rol", 'rol')
    add_row_if_exists("Fax", 'fax')
    add_row_if_exists("Páginas Web", 'paginas_web')
    add_row_if_exists("Apodo", 'apodo')
    add_row_if_exists("Hijos", 'hijos')
    add_row_if_exists("Cargos", 'cargos')
    add_row_if_exists("Cónyuge", 'conyuge')
    add_row_if_exists("Aniversario", 'aniversario')
    add_row_if_exists("Tipo de Dirección", 'tipo_direccion')
    add_row_if_exists("Dirección de Mapa", 'direccion_mapa')
    add_row_if_exists("Capacidad de Persona", 'capacidad_persona')
    add_row_if_exists("Participación", 'participacion')
    add_row_if_exists("Fecha de Ingreso", 'fecha_ingreso')
    add_row_if_exists("Tipo de Actividad", 'tipo_actividad')
    

    # Si hay avatar, añadirlo
    if contacto.avatar_path:
        avatar_full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(contacto.avatar_path))

        if os.path.exists(avatar_full_path):
            try:
                img = Image(avatar_full_path)
                img_width = 1.5 * inch
                img_height = img_width * (img.drawHeight / img.drawWidth) # Mantener la proporción
                img.drawWidth = img_width
                img.drawHeight = img_height
                data.append([Paragraph("<b>Avatar:</b>", styles['Label']), img])
            except Exception as e:
                print(f"Error al cargar la imagen para PDF: {e}")
                data.append([Paragraph("<b>Avatar:</b>", styles['Label']), Paragraph("Error al cargar avatar", styles['Value'])])
        else:
            data.append([Paragraph("<b>Avatar:</b>", styles['Label']), Paragraph("No disponible", styles['Value'])])
    else:
        data.append([Paragraph("<b>Avatar:</b>", styles['Label']), Paragraph("No hay avatar", styles['Value'])])


    table = Table(data, colWidths=[2 * inch, 5 * inch]) # Ancho de columnas para las etiquetas y valores
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'contacto_{contacto.id}.pdf', mimetype='application/pdf')

@app.route('/exportar_contacto_vcard/<int:id>')
@login_required
def exportar_contacto_vcard(id):
    contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    vcard = vobject.vCard()
    
    # Nombre y apellidos
    vcard.add('n')
    vcard.n.value = vobject.vcard.Name(
        family=contacto.primer_apellido or '', 
        given=contacto.nombre or '', 
        additional=contacto.segundo_apellido or ''
    )

    vcard.add('fn')
    vcard.fn.value = f"{contacto.nombre} {contacto.primer_apellido or ''} {contacto.segundo_apellido or ''}".strip()

    # Teléfonos - Usando los campos existentes en ContactoForm
    if contacto.telefono:
        tel = vcard.add('tel')
        tel.type = 'HOME,VOICE' # Asignado a HOME,VOICE ya que es el principal general
        tel.value = contacto.telefono
    if contacto.movil:
        tel = vcard.add('tel')
        tel.type = 'CELL'
        tel.value = contacto.movil

    # Emails - Usando el campo existente en ContactoForm
    if contacto.email:
        email = vcard.add('email')
        email.type = 'INTERNET'
        email.value = contacto.email

    # Dirección
    # Usar getattr para campos opcionales del modelo de Contacto que pueden no existir
    if contacto.direccion or getattr(contacto, 'ciudad', None) or getattr(contacto, 'provincia', None) or \
       getattr(contacto, 'codigo_postal', None) or getattr(contacto, 'pais', None):
        vcard.add('adr')
        vcard.adr.value = vobject.vcard.Address(
            street=contacto.direccion or '',
            city=getattr(contacto, 'ciudad', '') or '',
            region=getattr(contacto, 'provincia', '') or '',
            code=getattr(contacto, 'codigo_postal', '') or '',
            country=getattr(contacto, 'pais', '') or ''
        )

    # Organización y Sitio Web
    if contacto.empresa:
        vcard.add('org')
        vcard.org.value = [contacto.empresa]
    if contacto.sitio_web:
        vcard.add('url')
        vcard.url.value = contacto.sitio_web

    # Campos adicionales con X-PROPERTY para campos personalizados
    if contacto.capacidad_persona:
        vcard.add('X-CAPACIDAD-PERSONA').value = contacto.capacidad_persona
    if contacto.participacion:
        vcard.add('X-PARTICIPACION').value = contacto.participacion
    if contacto.tipo_actividad:
        vcard.add('X-TIPO-ACTIVIDAD').value = contacto.tipo_actividad
    if contacto.nota:
        vcard.add('NOTE').value = contacto.nota
    if contacto.direccion_mapa:
        vcard.add('X-DIRECCION-MAPA').value = contacto.direccion_mapa


    # Avatar
    if contacto.avatar_path:
        # Asumo que contacto.avatar_path es el nombre del archivo en UPLOAD_FOLDER
        avatar_full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(contacto.avatar_path))
        if os.path.exists(avatar_full_path):
            try:
                with open(avatar_full_path, 'rb') as f:
                    image_data = f.read()
                
                mime_type, _ = mimetypes.guess_type(avatar_full_path)
                if not mime_type:
                    mime_type = 'application/octet-stream' # Fallback
                
                vcard.add('photo')
                vcard.photo.value = base64.b64encode(image_data).decode('utf-8')
                vcard.photo.type_param = mime_type.split('/')[-1].upper() # Ej: 'JPEG', 'PNG'
                vcard.photo.encoding_param = 'BASE64' # CAMBIO: 'B' a 'BASE64'
            except Exception as e:
                print(f"Error al añadir avatar a vCard: {e}") # Para depuración
    
    # Serializa la vCard
    vcard_content = vcard.serialize()
    filename = f'{contacto.nombre}_{contacto.primer_apellido}.vcf'.replace(' ', '_').replace('__','_').lower()
    buffer = BytesIO(vcard_content.encode('utf-8'))
    
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/vcard')

@app.route('/exportar_contacto_excel/<int:id>')
@login_required
def exportar_contacto_excel(id):
    contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()

    # Preparar los datos en un diccionario para DataFrame
    data = {
        'Campo': [],
        'Valor': []
    }

    # Función auxiliar para añadir datos al diccionario
    def add_data(label, value):
        # Usar getattr para acceder a atributos que pueden no existir
        # y proporcionar un valor predeterminado si no existen
        attr_value = getattr(contacto, value, None)
        data['Campo'].append(label)
        if attr_value is not None and attr_value != '':
            # Formatear fechas si son objetos date o datetime
            if isinstance(attr_value, (date, datetime)):
                # Verifica si el atributo es 'fecha_ingreso' para incluir la hora
                if value == 'fecha_ingreso':
                    data['Valor'].append(attr_value.strftime('%Y-%m-%d %H:%M:%S'))
                else: # Para otras fechas como 'fecha_nacimiento', solo la fecha
                    data['Valor'].append(attr_value.strftime('%Y-%m-%d'))
            elif isinstance(attr_value, bool):
                data['Valor'].append("Sí" if attr_value else "No")
            else:
                data['Valor'].append(str(attr_value))
        else:
            data['Valor'].append('-')

    add_data("Nombre", 'nombre')
    add_data("Primer Apellido", 'primer_apellido')
    add_data("Segundo Apellido", 'segundo_apellido')
    add_data("Empresa", 'empresa')
    add_data("Puesto", 'puesto') # Ahora usando getattr
    add_data("Teléfono", 'telefono') # Usando el campo 'telefono' existente
    add_data("Móvil", 'movil')
    add_data("Email", 'email') # Usando el campo 'email' existente
    add_data("Dirección", 'direccion')
    add_data("Ciudad", 'ciudad') # Ahora usando getattr
    add_data("Provincia", 'provincia') # Ahora usando getattr
    add_data("Código Postal", 'codigo_postal') # Ahora usando getattr
    add_data("País", 'pais') # Ahora usando getattr
    add_data("Fecha de Nacimiento", 'fecha_nacimiento') # Ahora usando getattr
    add_data("Red Social", 'red_social') # Ahora usando getattr
    add_data("Sitio Web", 'sitio_web')
    add_data("Relación", 'relacion') # Ahora usando getattr
    add_data("Método de Contacto Preferido", 'metodo_contacto_preferido') # Ahora usando getattr
    add_data("Fuente del Contacto", 'fuente_contacto') # Ahora usando getattr
    add_data("Intereses", 'intereses') # Ahora usando getattr
    add_data("Historial de Interacción", 'historial_interaccion') # Ahora usando getattr
    add_data("Próxima Interacción", 'proxima_interaccion') # Ahora usando getattr
    add_data("Etiquetas", 'etiquetas') # Ahora usando getattr
    add_data("Grupo", 'grupo') # Ahora usando getattr
    add_data("Preferencias de Comunicación", 'preferencias_comunicacion') # Ahora usando getattr
    add_data("Consentimiento de Datos", 'consentimiento_datos') # Ahora usando getattr
    add_data("Notas", 'nota')
    add_data("Género", 'genero') # Ahora usando getattr
    add_data("Organización", 'organizacion') # Ahora usando getattr
    add_data("Departamento", 'departamento') # Ahora usando getattr
    add_data("Rol", 'rol') # Ahora usando getattr
    add_data("Fax", 'fax') # Ahora usando getattr
    add_data("Páginas Web", 'paginas_web') # Ahora usando getattr
    add_data("Apodo", 'apodo') # Ahora usando getattr
    add_data("Hijos", 'hijos') # Ahora usando getattr
    add_data("Cargos", 'cargos') # Ahora usando getattr
    add_data("Cónyuge", 'conyuge') # Ahora usando getattr
    add_data("Aniversario", 'aniversario') # Ahora usando getattr
    add_data("Tipo de Dirección", 'tipo_direccion') # Ahora usando getattr
    add_data("Dirección de Mapa", 'direccion_mapa')
    add_data("Avatar", 'avatar_path') # Solo la ruta del archivo
    add_data("Capacidad de Persona", 'capacidad_persona')
    add_data("Participación", 'participacion')
    add_data("Fecha de Ingreso", 'fecha_ingreso')
    add_data("Tipo de Actividad", 'tipo_actividad')

    df = pd.DataFrame(data)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Detalle Contacto')
    writer.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=f'contacto_{contacto.id}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/exportar_contacto_jpg/<int:id>')
@login_required
def exportar_contacto_jpg(id):
    # Nota: La conversión de HTML a JPG en el servidor es compleja y requiere herramientas externas.
    # Una forma común es usar wkhtmltoimage o Selenium con un navegador headless.
    # Dado que no se proporcionan esas dependencias aquí, la forma más sencilla es:
    # 1. Generar el PDF y luego convertirlo a JPG usando una librería Python (ej. PyMuPDF, Pillow + Ghostscript)
    #    Pero estas tienen dependencias externas.
    # 2. Recomendar al usuario imprimir a PDF desde el navegador y luego usar un convertidor online.

    # Implementación de ejemplo si tuvieras una forma de generar la imagen del HTML
    # Esto es solo un placeholder, no funcionará sin librerías adicionales.

    # Opción 1: Simplemente redirigir a una página que el usuario pueda imprimir a PDF
    # y luego convertir (menos automatizado)
    flash('Para exportar a JPG, por favor, imprime esta página a PDF desde tu navegador y luego usa una herramienta de conversión de PDF a JPG.', 'info')
    return redirect(url_for('contacto_detalle', id=id)) # Asegúrate de que esta URL sea la correcta

    # Opción 2: (Más compleja) Generar un PDF primero y luego intentar convertirlo a JPG
    # Esto requeriría PyMuPDF o Pillow con Ghostscript u otra herramienta.
    # from PIL import Image
    # import fitz # PyMuPDF

    # pdf_buffer = BytesIO()
    # # Lógica para generar el PDF (similar a exportar_contacto_pdf)
    # contacto = Contacto.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    # doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    # styles = getSampleStyleSheet()
    # # ... (código de generación de PDF aquí, copiar de exportar_contacto_pdf)
    # doc.build(story) # story debería estar definido
    # pdf_buffer.seek(0)

    # # Convertir el PDF a JPG
    # doc_pdf = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
    # page = doc_pdf.load_page(0)  # load page number 0 (first page)
    # pix = page.get_pixmap()
    # img_buffer = BytesIO()
    # img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # img.save(img_buffer, "JPEG")
    # img_buffer.seek(0)
    # doc_pdf.close()

    # return send_file(img_buffer, as_attachment=True, download_name=f'contacto_{contacto.id}.jpg', mimetype='image/jpeg')













# ===========================================================================
# MODIFICACIÓN CLAVE #2: Funciones de exportación corregidas.
# Se eliminan los DUMMYs y se usan los objetos de DB reales.
# ===========================================================================

@app.route('/exportar_factura_pdf/<int:id>')
@login_required 
def exportar_factura_pdf(id):
    # OBTENER LA FACTURA Y EL CLIENTE REALES DE LA BASE DE DATOS
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    # MODIFICACIÓN CLAVE: Usar Contacto.query en lugar de Cliente.query
    cliente = Contacto.query.get_or_404(factura.cliente_id) 

    # NO HAY CÓDIGO DUMMY AQUÍ. TODO USA 'factura' y 'cliente' REALES.

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados para la factura
    styles.add(ParagraphStyle(name='CompanyHeader', fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=28, leading=32, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold', textColor=colors.HexColor('#007bff')))
    styles.add(ParagraphStyle(name='DetailText', fontSize=10, leading=12, spaceAfter=3))
    styles.add(ParagraphStyle(name='TableBodyText', fontSize=10, leading=12, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='TableTotalText', fontSize=12, leading=14, alignment=TA_RIGHT, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FooterText', fontSize=9, leading=10, alignment=TA_CENTER, spaceBefore=20))

    story = []

    # --- Encabezado de la Empresa ---
    story.append(Paragraph("<b>La Tribu Hiking</b>", styles['CompanyHeader']))
    story.append(Paragraph("Dirección: San Diego, La Unión, Cartago, Costa Rica", styles['CompanyHeader']))
    story.append(Paragraph("Teléfono: +506-86227500 | Email: lthikingcr@gmail.com", styles['CompanyHeader']))
    story.append(Spacer(1, 0.4 * inch))

    # --- Título de la Factura/Cotización ---
    title_text = "FACTURA" 
    story.append(Paragraph(title_text, styles['InvoiceTitle']))
    story.append(Spacer(1, 0.3 * inch))

    # --- Detalles de la Factura y del Cliente ---
    # SE USAN LOS OBJETOS 'factura' y 'cliente' REALES AQUÍ
    invoice_details_data = [
        [Paragraph(f"<b>Número de {title_text}:</b> {factura.numero_factura}", styles['DetailText']),
         Paragraph(f"<b>Fecha de Creación:</b> {factura.fecha_registro.strftime('%d-%m-%Y %H:%M')}", styles['DetailText'])],
        [Paragraph(f"<b>Fecha de Emisión:</b> {factura.fecha_emision.strftime('%d-%m-%Y')}", styles['DetailText']),
         Paragraph(f"<b>Realizado por:</b> {factura.realizado_por}", styles['DetailText'])],
        [Paragraph(f"<b>Cliente:</b> {cliente.nombre} {cliente.primer_apellido or ''} {cliente.segundo_apellido or ''}", styles['DetailText']),
         Paragraph(f"<b>Teléfono Cliente:</b> {cliente.movil or cliente.telefono or 'N/A'}", styles['DetailText'])],
        [Paragraph(f"<b>Email Cliente:</b> {cliente.email or 'N/A'}", styles['DetailText']),
         Paragraph(f"<b>SINPE:</b> {factura.sinpe}", styles['DetailText'])],
    ]
    invoice_details_table = Table(invoice_details_data, colWidths=[4 * inch, 3 * inch])
    invoice_details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(invoice_details_table)
    story.append(Spacer(1, 0.3 * inch))

    # --- Detalles de Conceptos ---
    table_data = []
    table_data.append([
        Paragraph("<b>Concepto</b>", styles['SectionHeader']),
        Paragraph("<b>Monto</b>", styles['SectionHeader'])
    ])

    if factura.descripcion:
        table_data.append([
            Paragraph(f"Descripción General: {factura.descripcion}", styles['TableBodyText']),
            Paragraph("N/A", styles['TableBodyText'])
        ])

    if factura.tipo_actividad or factura.nombre_actividad_etapa or factura.costo_actividad:
        concept_detail = f"Tipo de Actividad: {factura.tipo_actividad}"
        if factura.nombre_actividad_etapa:
            concept_detail += f" - {factura.nombre_actividad_etapa}"

        costo = float(factura.costo_actividad) if factura.costo_actividad is not None else 0.00
        table_data.append([
            Paragraph(concept_detail, styles['TableBodyText']),
            Paragraph(f"¢{costo:,.2f}", styles['TableBodyText'])
        ])

    if factura.otras_descripcion:
        table_data.append([
            Paragraph(f"Otras Descripciones: {factura.otras_descripcion}", styles['TableBodyText']),
            Paragraph("N/A", styles['TableBodyText'])
        ])

    monto_total_float = float(factura.monto_total) if factura.monto_total is not None else 0.00
    impuesto_monto_float = float(factura.impuesto_monto) if factura.impuesto_monto is not None else 0.00

    subtotal_calculado = monto_total_float - impuesto_monto_float

    table_data.append([
        Paragraph("Subtotal del servicio/producto:", styles['TableTotalText']),
        Paragraph(f"¢{subtotal_calculado:,.2f}", styles['TableTotalText'])
    ])
    table_data.append([
        Paragraph("Monto de Impuesto:", styles['TableTotalText']),
        Paragraph(f"¢{impuesto_monto_float:,.2f}", styles['TableTotalText'])
    ])

    col_widths_concepts = [5.5 * inch, 2 * inch]
    concepts_table = Table(table_data, colWidths=col_widths_concepts)
    concepts_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('SPAN', (0, -2), (0, -1)),
    ]))
    story.append(concepts_table)
    story.append(Spacer(1, 0.2 * inch))

    total_final_data = [
        [Paragraph("TOTAL (con Impuestos):", styles['TableTotalText']), Paragraph(f"¢{monto_total_float:,.2f}", styles['TableTotalText'])]
    ]
    total_final_table = Table(total_final_data, colWidths=[5.5 * inch, 2 * inch])
    total_final_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
    ]))
    story.append(total_final_table)
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph("<b>Información de Pago:</b>", styles['SectionHeader']))
    story.append(Paragraph(f"SINPE Móvil: {factura.sinpe}", styles['DetailText']))
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph("<i>¡Gracias por tu preferencia!</i>", styles['FooterText']))
    story.append(Paragraph(f"{title_text} generada el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['FooterText']))

    doc.build(story)
    buffer.seek(0)

    filename = f"{title_text.lower()}_{factura.numero_factura}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@app.route('/exportar_factura_jpg/<int:id>')
@login_required
def exportar_factura_jpg(id):
    # OBTENER LA FACTURA Y EL CLIENTE REALES DE LA BASE DE DATOS
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    # MODIFICACIÓN CLAVE: Usar Contacto.query en lugar de Cliente.query
    cliente = Contacto.query.get_or_404(factura.cliente_id) 

    # NO HAY CÓDIGO DUMMY AQUÍ. Todo usa 'factura' y 'cliente' REALES.

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados para la factura (estos son los que me proporcionaste y están bien)
    styles.add(ParagraphStyle(name='CompanyHeader', fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=28, leading=32, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold', textColor=colors.HexColor('#007bff')))
    styles.add(ParagraphStyle(name='DetailText', fontSize=10, leading=12, spaceAfter=3))
    styles.add(ParagraphStyle(name='TableBodyText', fontSize=10, leading=12, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='TableTotalText', fontSize=12, leading=14, alignment=TA_RIGHT, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FooterText', fontSize=9, leading=10, alignment=TA_CENTER, spaceBefore=20))

    story = []

    # --- Encabezado de la Empresa ---
    story.append(Paragraph("<b>La Tribu Hiking</b>", styles['CompanyHeader']))
    story.append(Paragraph("Dirección: San Diego, La Unión, Cartago, Costa Rica", styles['CompanyHeader']))
    story.append(Paragraph("Teléfono: +506-86227500 | Email: lthikingcr@gmail.com", styles['CompanyHeader']))
    story.append(Spacer(1, 0.4 * inch))

    # --- Título de la Factura/Cotización ---
    title_text = "FACTURA" 
    story.append(Paragraph(title_text, styles['InvoiceTitle']))
    story.append(Spacer(1, 0.3 * inch))

    # --- Detalles de la Factura y del Cliente ---
    # SE USAN LOS OBJETOS 'factura' y 'cliente' REALES AQUÍ
    invoice_details_data = [
        [Paragraph(f"<b>Número de {title_text}:</b> {factura.numero_factura}", styles['DetailText']),
         Paragraph(f"<b>Fecha de Creación:</b> {factura.fecha_registro.strftime('%d-%m-%Y %H:%M')}", styles['DetailText'])],
        [Paragraph(f"<b>Fecha de Emisión:</b> {factura.fecha_emision.strftime('%d-%m-%Y')}", styles['DetailText']),
         Paragraph(f"<b>Realizado por:</b> {factura.realizado_por}", styles['DetailText'])],
        [Paragraph(f"<b>Caminante:</b> {cliente.nombre} {cliente.primer_apellido or ''} {cliente.segundo_apellido or ''}", styles['DetailText']),
         Paragraph(f"<b>Teléfono Caminante:</b> {cliente.movil or cliente.telefono or 'N/A'}", styles['DetailText'])],
        [Paragraph(f"<b>Email Caminante:</b> {cliente.email or 'N/A'}", styles['DetailText']),
         Paragraph(f"<b>SINPE:</b> {factura.sinpe}", styles['DetailText'])],
    ]
    invoice_details_table = Table(invoice_details_data, colWidths=[4 * inch, 3 * inch])
    invoice_details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(invoice_details_table)
    story.append(Spacer(1, 0.3 * inch))

    # --- Detalles de Conceptos ---
    table_data = []
    table_data.append([
        Paragraph("<b>Concepto</b>", styles['SectionHeader']),
        Paragraph("<b>Monto</b>", styles['SectionHeader'])
    ])

    if factura.descripcion:
        table_data.append([
            Paragraph(f"Descripción General: {factura.descripcion}", styles['TableBodyText']),
            Paragraph("N/A", styles['TableBodyText'])
        ])

    if factura.tipo_actividad or factura.nombre_actividad_etapa or factura.costo_actividad:
        concept_detail = f"Tipo de Actividad: {factura.tipo_actividad}"
        if factura.nombre_actividad_etapa:
            concept_detail += f" - {factura.nombre_actividad_etapa}"

        costo = float(factura.costo_actividad) if factura.costo_actividad is not None else 0.00
        table_data.append([
            Paragraph(concept_detail, styles['TableBodyText']),
            Paragraph(f"¢{costo:,.2f}", styles['TableBodyText'])
        ])

    if factura.otras_descripcion:
        table_data.append([
            Paragraph(f"Otras Descripciones: {factura.otras_descripcion}", styles['TableBodyText']),
            Paragraph("N/A", styles['TableBodyText'])
        ])

    monto_total_float = float(factura.monto_total) if factura.monto_total is not None else 0.00
    impuesto_monto_float = float(factura.impuesto_monto) if factura.impuesto_monto is not None else 0.00

    subtotal_calculado = monto_total_float - impuesto_monto_float

    table_data.append([
        Paragraph("Subtotal del servicio/producto:", styles['TableTotalText']),
        Paragraph(f"¢{subtotal_calculado:,.2f}", styles['TableTotalText'])
    ])
    table_data.append([
        Paragraph("Monto de Impuesto:", styles['TableTotalText']),
        Paragraph(f"¢{impuesto_monto_float:,.2f}", styles['TableTotalText'])
    ])

    col_widths_concepts = [5.5 * inch, 2 * inch]
    concepts_table = Table(table_data, colWidths=col_widths_concepts)
    concepts_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('SPAN', (0, -2), (0, -1)),
    ]))
    story.append(concepts_table)
    story.append(Spacer(1, 0.2 * inch))

    total_final_data = [
        [Paragraph("TOTAL (con Impuestos):", styles['TableTotalText']), Paragraph(f"¢{monto_total_float:,.2f}", styles['TableTotalText'])]
    ]
    total_final_table = Table(total_final_data, colWidths=[5.5 * inch, 2 * inch])
    total_final_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#D3D3D3')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
    ]))
    story.append(total_final_table)
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph("<b>Información de Pago:</b>", styles['SectionHeader']))
    story.append(Paragraph(f"SINPE Móvil: {factura.sinpe}", styles['DetailText']))
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph("<i>¡Gracias por tu preferencia!</i>", styles['FooterText']))
    story.append(Paragraph(f"{title_text} generada el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['FooterText']))

    doc.build(story)
    pdf_buffer.seek(0)

    try:
        doc_pdf = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        page = doc_pdf.load_page(0) 

        zoom = 2
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img_buffer = BytesIO()
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples) 
        img.save(img_buffer, "JPEG", quality=90) # Ajustar calidad si es necesario
        img_buffer.seek(0)
        doc_pdf.close()

        filename = f"{title_text.lower()}_{factura.numero_factura}.jpg"
        return send_file(img_buffer, as_attachment=True, download_name=filename, mimetype='image/jpeg')
    except Exception as e:
        flash(f"Error al convertir PDF a JPG: {e}. Asegúrese de tener PyMuPDF (fitz) y Pillow instalados.", "danger")
        print(f"Error al convertir PDF a JPG: {e}")
        return redirect(url_for('ver_detalle_factura', id=id))
















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

# del db.db
# rmdir /s /q migrations
# flask db init
# flask db migrate -m "Reinitial migration with all correct models"
# flask db upgrade

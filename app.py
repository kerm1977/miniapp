from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, FileField, TextAreaField,PasswordField, BooleanField # Asegúrate de que SelectField y TextAreaField estén aquí
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from flask_migrate import Migrate
from flask import send_file
import io
from io import BytesIO
import vobject
import base64
import mimetypes
import os
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
import numpy


app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
migrate = Migrate(app, db)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."


def is_authenticated(self):
    return True


# MODELOS
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128))
    image_filename = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return True
    @property
    @property
    def is_anonymous(self):
        return False

class Contacto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100))
    segundo_apellido = db.Column(db.String(100))
    telefono = db.Column(db.String(20), nullable=False)
    movil = db.Column(db.String(20))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    actividad = db.Column(db.String(100))  # Corrección: Usando 'actividad' para el modelo
    tipo_actividad = db.Column(db.String(100)) # Manteniendo tipo_actividad si lo usas en el formulario
    nota = db.Column(db.Text)
    direccion_mapa = db.Column(db.String(255))
    avatar_path = db.Column(db.String(255)) # Para guardar la ruta del avatar
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('contactos', lazy=True))
    empresa = db.Column(db.String(100))
    sitio_web = db.Column(db.String(200))
    # Nuevos campos select
    capacidad_persona = db.Column(db.String(20))
    participacion = db.Column(db.String(30))

    def __repr__(self):
        return f'<Contacto {self.nombre}>'

class Event(db.Model):
    __tablename__ = 'event'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)  # Nuevo campo para la hora
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'time': self.time.strftime('%H:%M') if self.time else None, # Formatea la hora para la respuesta
            'title': self.title,
            'description': self.description
        }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    imagen_post = db.Column(db.String(255))
    tipo_caminata = db.Column(db.Enum('PARQUE NACIONAL', 'RESERVA', 'REFUGIO AMBIENTAL', 'ISLA', 'CERRO', 'RIO', 'PLAYA', 'VOLCAN', 'CATARATA', 'CENTRO RECREACION', 'SENDERO', 'EL CAMINO DE COSTA RICA'), nullable=False)
    etapas = db.Column(db.Enum(
        '1a & 1b PARISMINA-CIMARRONES',
        '1a PARISMINA-BARRA PACUARE',
        '1b MUELLE GOSHEN-CIMARRONES',
        '2 CIMARRONES-LAS BRISAS(TSINIKISHA)',
        '3 TSINIKISHA-TSIOBATA',
        '4 TIOBATA-HACIENDA TRES EQUIS',
        '5 HACIENDA TRES EQUIS-PACAYITAS',
        '6 PACAYITAS-LA SUIZA',
        '7 LA SUIZA-HUMO DE PEJIBAYE',
        '8 HUMO DE PEJIBAYE A TAPANTI',
        '9 TAPANTI-MUÑECO NAVARRO',
        '10 MUÑECO NAVARRO-PALO VERDE',
        '11 PALO VERDE-CERRO ALTO',
        '12 CERRO ALTO-SAN PABLO LEON CORTES',
        '13 SAN PABLO LEON CORTES-NAPOLES',
        '14 NAPOLES-NARANJITO',
        '15 NARANJITO-ESQUIPULAS',
        '16 ESQUIPULAS-QUIPOS'
    ))
    nombre_lugar = db.Column(db.String(255), nullable=False)
    provincia = db.Column(db.Enum('ALAJUELA', 'CARTAGO', 'HEREDIA', 'SAN JOSE', 'PUNTARENAS', 'LIMON', 'GUANACASTE'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    precio = db.Column(db.Numeric(10, 2))
    incluye = db.Column(db.Enum('Transporte', 'Tranporte + Entrada', 'Tranporte + Entrada + Guia'))
    dificultad = db.Column(db.Enum('Iniciante', 'Básico', 'Básico-Intermedio', 'Intermedio', 'Intermedio-Dificil', 'Dificil', 'Muy Dificil'))
    distancia = db.Column(db.String(50))
    capacidad_buseta = db.Column(db.Enum('14', '15', '17'))
    salimos_de = db.Column(db.Enum('PARQUE DE TRES RÍOS DIAGONAL A LA ESCUELA', 'PARQUE DE TRES RÍOS FRENTE A LA CRUZ ROJA', 'SAN DIEGO LA PLAZA', 'SAN DIEGO FRENTE A LA IGLESIA'))
    se_recoge_en = db.Column(db.Enum('CARTAGO-TURRIALBA', 'CARTAGO-PZ', 'SAN JOSE'))
    reserva_con = db.Column(db.Numeric(10, 2))
    altitud_maxima = db.Column(db.String(50))
    altitud_minima = db.Column(db.String(50))
    banos = db.Column(db.Enum('NO APLICA', 'SI', 'NO'))
    duchas = db.Column(db.Enum('NO APLICA', 'SI', 'NO'))
    parqueo = db.Column(db.Enum('NO APLICA', 'SI', 'NO'))
    sinpe = db.Column(db.Enum('Jenny Ceciliano Cordoba - 8652 9837', 'Kenneth Ruiz Matamoros - 86227500', 'Jenny Ceciliano Cordoba - 87984232'))

    # Relación con el modelo de Usuario (asumiendo que se llama 'User')
    user = db.relationship('User', backref=db.backref('posts', lazy=True))

    def __repr__(self):
        return f"<Post {self.nombre_lugar}>"



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
    # Nuevos campos select en el formulario
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



# FACTURAS
class Factura(db.Model):
    __tablename__ = 'facturas'

    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(100), unique=True, nullable=False)
    fecha_emision = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    cliente_id = db.Column(db.Integer, db.ForeignKey('contacto.id'), nullable=False)
    cliente = db.relationship('Contacto', backref=db.backref('facturas', lazy=True))
    descripcion = db.Column(db.Text)
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('facturas', lazy=True))

    def __repr__(self):
        return f'<Factura {self.numero_factura}>'

class CrearFacturaForm(FlaskForm):
    numero_factura = StringField('Número de Factura', validators=[DataRequired()], render_kw={"class": "rounded-pill"})
    cliente_id = SelectField('Cliente', coerce=int, validators=[DataRequired()], render_kw={"class": "form-select rounded-pill"})
    fecha_emision = StringField('Fecha de Emisión (YYYY-MM-DD)', validators=[DataRequired()], render_kw={"class": "rounded-pill"})
    descripcion = TextAreaField('Descripción', render_kw={"class": "rounded-pill"})
    monto_total = StringField('Monto Total', validators=[DataRequired()], render_kw={"class": "rounded-pill"})
    submit = SubmitField('Guardar Factura', render_kw={"class": "btn btn-success rounded-pill"})

    def __init__(self, *args, **kwargs):
        super(CrearFacturaForm, self).__init__(*args, **kwargs)
        self.cliente_id.choices = [(
            contacto.id,
            f"{contacto.nombre.title()} {contacto.primer_apellido.title() if contacto.primer_apellido else ''} {contacto.segundo_apellido.title() if contacto.segundo_apellido else ''} - {contacto.movil if contacto.movil else contacto.telefono}"
        ) for contacto in Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre, Contacto.primer_apellido).all()]

class EditarFacturaForm(FlaskForm):
    numero_factura = StringField('Número de Factura', render_kw={"class": "rounded-pill"})
    cliente_id = SelectField('Cliente', coerce=int, render_kw={"class": "rounded-pill form-select"})
    fecha_emision = StringField('Fecha de Emisión (YYYY-MM-DD)', render_kw={"class": "rounded-pill"})
    descripcion = TextAreaField('Descripción', render_kw={"class": "rounded-pill"})
    monto_total = StringField('Monto Total', render_kw={"class": "rounded-pill"})
    submit = SubmitField('Guardar Cambios', render_kw={"class": "btn btn-primary"})

    def __init__(self, factura, *args, **kwargs):
        super(EditarFacturaForm, self).__init__(*args, **kwargs)
        self.cliente_id.choices = [(
            contacto.id,
            f"{contacto.nombre.title()} {contacto.primer_apellido.title() if contacto.primer_apellido else ''} {contacto.segundo_apellido.title() if contacto.segundo_apellido else ''} - {contacto.movil if contacto.movil else contacto.telefono}"
        ) for contacto in Contacto.query.filter_by(usuario_id=current_user.id).order_by(Contacto.nombre, Contacto.primer_apellido).all()]
        self.cliente_id.data = factura.cliente_id
        self.numero_factura.data = factura.numero_factura
        self.fecha_emision.data = factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else ''
        self.descripcion.data = factura.descripcion
        self.monto_total.data = str(factura.monto_total) if factura.monto_total is not None else ''
        # No necesitamos process() aquí si usamos 'data'







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





# FACTURAS
@app.route('/ver_facturas')
@login_required
def ver_facturas():
    facturas = Factura.query.filter_by(usuario_id=current_user.id).all()
    return render_template('ver_facturas.html', facturas=facturas)

@app.route('/crear_factura', methods=['GET', 'POST'])
@login_required
def crear_factura():
    form = CrearFacturaForm()
    if form.validate_on_submit():
        numero_factura = form.numero_factura.data
        cliente_id = form.cliente_id.data
        fecha_emision_str = form.fecha_emision.data
        descripcion = form.descripcion.data
        monto_total = form.monto_total.data

        if Factura.query.filter_by(numero_factura=numero_factura, usuario_id=current_user.id).first():
            flash('El número de factura ya existe.', 'danger')
            return render_template('crear_factura.html', form=form)

        try:
            fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            nueva_factura = Factura(
                numero_factura=numero_factura,
                cliente_id=cliente_id,
                fecha_emision=fecha_emision,
                descripcion=descripcion,
                monto_total=monto_total,
                usuario_id=current_user.id
            )
            db.session.add(nueva_factura)
            db.session.commit()
            flash('¡Factura creada exitosamente!', 'success')
            return redirect(url_for('ver_facturas'))
        except ValueError:
            flash('Formato de fecha de emisión inválido (YYYY-MM-DD).', 'danger')
            return render_template('crear_factura.html', form=form)

    return render_template('crear_factura.html', form=form)

@app.route('/editar_factura/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_factura(id):
    factura = Factura.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = EditarFacturaForm(factura)

    print(f"Tipo de numero_factura: {type(factura.numero_factura)}, Valor: {factura.numero_factura}")
    print(f"Tipo de fecha_emision: {type(factura.fecha_emision)}, Valor: {factura.fecha_emision}")
    print(f"Tipo de monto_total: {type(factura.monto_total)}, Valor: {factura.monto_total}")

    form.numero_factura.data = factura.numero_factura
    form.cliente_id.data = factura.cliente_id
    form.fecha_emision.data = factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else ''
    form.descripcion.data = factura.descripcion
    form.monto_total.data = str(factura.monto_total) if factura.monto_total is not None else ''

    if form.validate_on_submit():
        factura.numero_factura = form.numero_factura.data
        factura.cliente_id = form.cliente_id.data
        fecha_emision_str = form.fecha_emision.data
        factura.descripcion = form.descripcion.data
        factura.monto_total = form.monto_total.data

        try:
            factura.fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            db.session.commit()
            flash('¡Factura actualizada exitosamente!', 'success')
            return redirect(url_for('ver_facturas'))
        except ValueError:
            flash('Formato de fecha de emisión inválido (YYYY-MM-DD).', 'danger')
            return render_template('editar_factura.html', form=form, factura_id=id)

    return render_template('editar_factura.html', form=form, factura_id=id)

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
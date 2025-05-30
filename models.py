from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, date, time
import enum

db = SQLAlchemy()

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

# Nuevo modelo para Eventos (CRUD de eventos)
class Evento(db.Model):
    __tablename__ = 'eventos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    flyer_filename = db.Column(db.String(255), nullable=True) # Para guardar la ruta del flyer (imagen o PDF)
    tipo_evento = db.Column(db.String(100), nullable=False) # Parque Nacional, El Camino de Costa Rica
    nombre_evento = db.Column(db.String(255), nullable=False)
    precio_evento = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_evento = db.Column(db.Date, nullable=False)
    dificultad_evento = db.Column(db.String(50), nullable=False) # Iniciante, Básico, Intermedio, Avanzado, Técnico
    incluye = db.Column(db.Text, nullable=True)
    lugar_salida = db.Column(db.String(255), nullable=False) # Parque de Tres Ríos Escuela, etc.
    hora_salida = db.Column(db.Time, nullable=False)
    distancia = db.Column(db.String(100), nullable=True) # Se cambia a String para permitir "N/A" o rangos
    capacidad = db.Column(db.Integer, nullable=False) # 14, 17, 28, 42
    descripcion = db.Column(db.Text, nullable=True)
    instrucciones = db.Column(db.Text, nullable=True)
    recomendaciones = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('User', backref=db.backref('eventos', lazy=True))

    def __repr__(self):
        return f'<Evento {self.nombre_evento}>'

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

    interes = db.Column(db.String(50), nullable=True)
    realizado_por = db.Column(db.String(100), nullable=True)
    sinpe = db.Column(db.String(100), nullable=True)
    tipo_actividad = db.Column(db.String(100), nullable=True)
    nombre_actividad_etapa = db.Column(db.String(255), nullable=True)
    costo_actividad = db.Column(db.Numeric(10, 2), nullable=True)
    otras_descripcion = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Factura {self.numero_factura}>'

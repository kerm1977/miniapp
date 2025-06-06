from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import enum

db = SQLAlchemy()

# MODELOS
class User(UserMixin, db.Model):
    __tablename__ = 'users' # Nombre de la tabla es 'users'

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
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

class Contacto(db.Model):
    __tablename__ = 'contacto'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=True)
    segundo_apellido = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(20), nullable=False)
    movil = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    tipo_actividad = db.Column(db.String(100), nullable=True)
    nota = db.Column(db.Text, nullable=True)
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    direccion_mapa = db.Column(db.String(255), nullable=True)
    avatar_path = db.Column(db.String(255), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    empresa = db.Column(db.String(100), nullable=True)
    sitio_web = db.Column(db.String(255), nullable=True)
    capacidad_persona = db.Column(db.String(50), nullable=True)
    participacion = db.Column(db.String(50), nullable=True)

    usuario = db.relationship('User', backref=db.backref('contactos', lazy=True))

    def __repr__(self):
        return f'<Contacto {self.nombre} {self.primer_apellido}>'

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'time': self.time.strftime('%H:%M') if self.time else None,
            'title': self.title,
            'description': self.description
        }

class Evento(db.Model):
    __tablename__ = 'eventos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    flyer_filename = db.Column(db.String(255), nullable=True)
    tipo_evento = db.Column(db.String(100), nullable=False)
    nombre_evento = db.Column(db.String(255), nullable=False)
    precio_evento = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_evento = db.Column(db.Date, nullable=False)
    dificultad_evento = db.Column(db.String(100), nullable=False)
    incluye = db.Column(db.Text, nullable=True)
    lugar_salida = db.Column(db.String(255), nullable=False)
    hora_salida = db.Column(db.Time, nullable=False)
    distancia = db.Column(db.String(50), nullable=True)
    capacidad = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    instrucciones = db.Column(db.Text, nullable=True)
    recomendaciones = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('User', backref=db.backref('eventos', lazy=True))

    def __repr__(self):
        return f'<Evento {self.nombre_evento}>'

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
    
    # Nuevo campo para el monto del impuesto
    impuesto_monto = db.Column(db.Numeric(10, 2), nullable=True, default=0.00) 
    
    def __repr__(self):
        return f'<Factura {self.numero_factura}>'


# --- Nuevo Modelo para Inventario ---
class ArticuloInventario(db.Model):
    __tablename__ = 'articulos_inventario'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    cantidad = db.Column(db.Integer, nullable=False, default=0)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('articulos_inventario', lazy=True))

    def __repr__(self):
        return f'<ArticuloInventario {self.nombre}>'

# Nuevo modelo para Notas
class Nota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) 
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ¡CORRECCIÓN CRÍTICA AQUÍ!
    # Define la relación para que 'Nota' pueda acceder al objeto 'User' a través de 'nota.usuario'
    # El backref 'notas' creará una colección 'usuario.notas' para acceder a las notas de un usuario.
    usuario = db.relationship('User', backref='notas', lazy=True) 

    def __repr__(self):
        return f'<Nota {self.titulo}>'

# --- Nuevo Modelo para Archivos Multimedia ---
class ArchivoMultimedia(db.Model):
    __tablename__ = 'archivos_multimedia'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.String(500), nullable=False)
    tipo_archivo = db.Column(db.String(50), nullable=False) # 'audio', 'video', 'imagen', 'pdf'
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('User', backref=db.backref('archivos_multimedia', lazy=True))

    def __repr__(self):
        return f'<ArchivoMultimedia {self.nombre_archivo}>'

# --- Nuevo Modelo para Gestor de Proyectos ---
class GestorProyecto(db.Model):
    __tablename__ = 'gestor_proyectos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre_proyecto = db.Column(db.String(255), nullable=False)
    imagen_proyecto = db.Column(db.String(255), nullable=True) # Ruta del archivo de imagen
    propuesta_por = db.Column(db.String(100), nullable=False) # Kenneth, Jenny, Invitado
    nombre_invitado = db.Column(db.String(255), nullable=True) # Solo si propuesta_por es 'Invitado'
    provincia = db.Column(db.String(100), nullable=False)
    canton = db.Column(db.String(100), nullable=False)
    fecha_actividad_propuesta = db.Column(db.Date, nullable=False)
    dificultad = db.Column(db.String(100), nullable=False)
    acompanantes = db.Column(db.Text, nullable=True) # Almacenar IDs de contactos como JSON/CSV
    transporte = db.Column(db.String(50), nullable=False)
    transporte_adicional = db.Column(db.String(50), nullable=True) # No aplica, Acuatico, Aereo
    precio_entrada = db.Column(db.Numeric(10, 2), nullable=True)
    nombre_lugar = db.Column(db.String(255), nullable=False)
    contacto_lugar = db.Column(db.String(255), nullable=True)
    telefono_lugar = db.Column(db.String(20), nullable=True)
    tipo_terreno = db.Column(db.String(100), nullable=False)
    mas_tipo_terreno = db.Column(db.Boolean, default=False)
    notas_adicionales = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('User', backref=db.backref('gestor_proyectos', lazy=True))

    def __repr__(self):
        return f'<GestorProyecto {self.nombre_proyecto}>'

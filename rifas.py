# rifas.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, DecimalField, DateField, FileField
from wtforms.validators import DataRequired, NumberRange, Optional
from flask_wtf.file import FileAllowed
from datetime import datetime
import os
from flask_login import login_required, current_user

# Importar db y los modelos existentes desde models.py
from models import db

# --- Blueprint para Rifas ---
# Se define un Blueprint para agrupar todas las rutas y vistas relacionadas con las rifas.
rifas_bp = Blueprint('rifas', __name__, template_folder='templates', static_folder='static')

# --- Modelos de Rifa ---
# Modelo para la tabla 'rifas' en la base de datos.
class Rifa(db.Model):
    __tablename__ = 'rifas'
    id = db.Column(db.Integer, primary_key=True)
    nombre_rifa = db.Column(db.String(255), nullable=False)
    valor_rifa = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_rifa = db.Column(db.Date, nullable=False)
    descripcion_rifa = db.Column(db.Text, nullable=True)
    imagen_rifa = db.Column(db.String(255), nullable=True) # Nombre del archivo de la imagen

    # Relación con NumeroRifa: una rifa puede tener muchos números vendidos.
    # 'cascade="all, delete-orphan"' asegura que los números asociados se borren si la rifa se borra.
    numeros_vendidos = db.relationship('NumeroRifa', backref='rifa', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Rifa {self.nombre_rifa}>'

# Modelo para la tabla 'numeros_rifa' en la base de datos.
class NumeroRifa(db.Model):
    __tablename__ = 'numeros_rifa'
    id = db.Column(db.Integer, primary_key=True)
    rifa_id = db.Column(db.Integer, db.ForeignKey('rifas.id'), nullable=False)
    numero = db.Column(db.String(2), nullable=False) # Almacena el número como string (ej. "00", "05", "99")
    nombre_jugador = db.Column(db.String(255), nullable=False)
    telefono_jugador = db.Column(db.String(20), nullable=False)
    fecha_seleccion = db.Column(db.DateTime, default=datetime.utcnow)

    # Restricción única para asegurar que un número solo se pueda vender una vez por rifa.
    __table_args__ = (db.UniqueConstraint('rifa_id', 'numero', name='_rifa_numero_uc'),)

    def __repr__(self):
        return f'<NumeroRifa Rifa: {self.rifa_id}, Número: {self.numero}, Jugador: {self.nombre_jugador}>'

# --- Formularios de Rifa ---
# Formulario para crear una nueva rifa.
class CrearRifaForm(FlaskForm):
    nombre_rifa = StringField('Nombre de la Rifa', validators=[DataRequired()])
    valor_rifa = DecimalField('Valor de la Rifa', validators=[DataRequired(), NumberRange(min=0.01)])
    fecha_rifa = DateField('Fecha de la Rifa', format='%Y-%m-%d', validators=[DataRequired()])
    descripcion_rifa = TextAreaField('Descripción de la Rifa', validators=[Optional()])
    imagen_rifa = FileField('Imagen de la Rifa', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Solo se permiten imágenes!')])
    submit = SubmitField('Crear Rifa')

# Formulario para que un jugador seleccione números.
class SeleccionarNumerosForm(FlaskForm):
    nombre_jugador = StringField('Nombre del Jugador', validators=[DataRequired()])
    telefono_jugador = StringField('Teléfono del Jugador', validators=[DataRequired()])
    # Este campo se usará para pasar los números seleccionados desde JavaScript al servidor.
    numeros_seleccionados = StringField('Números Seleccionados (internos)', render_kw={'readonly': True})
    submit = SubmitField('Guardar mis números')

# --- Lista de correos autorizados para crear rifas ---
# Solo los usuarios con estos correos podrán ver y usar el botón "Crear una nueva rifa".
AUTHORIZED_RIFA_CREATORS = [
    "kenth1977@gmail.com",
    "jceciliano69@gmail.com",
    "lthikingcr@gmail.com"
]

# --- Funciones Lógicas de Rifa ---
# Función para guardar la imagen de la rifa en el sistema de archivos.
def guardar_imagen_rifa(imagen):
    if imagen:
        # Genera un nombre de archivo único basado en la fecha y hora.
        filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + imagen.filename
        # Define la ruta completa donde se guardará la imagen.
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        imagen.save(filepath) # Guarda la imagen.
        return filename # Retorna el nombre del archivo guardado.
    return None

# Función para obtener todos los números vendidos para una rifa específica.
def obtener_numeros_vendidos(rifa_id):
    return NumeroRifa.query.filter_by(rifa_id=rifa_id).all()

# Función para obtener una rifa por su ID.
def obtener_rifa_por_id(rifa_id):
    return Rifa.query.get(rifa_id)

# Función para guardar los números seleccionados por un jugador.
def guardar_seleccion_numeros(rifa_id, nombre_jugador, telefono_jugador, numeros):
    try:
        for num_str in numeros:
            numero = NumeroRifa(
                rifa_id=rifa_id,
                numero=num_str,
                nombre_jugador=nombre_jugador,
                telefono_jugador=telefono_jugador
            )
            db.session.add(numero) # Añade cada número a la sesión de la base de datos.
        db.session.commit() # Confirma los cambios en la base de datos.
        return True, "Números guardados exitosamente."
    except Exception as e:
        db.session.rollback() # Deshace los cambios si ocurre un error.
        # Manejo específico para errores de restricción única (número ya ocupado).
        if "UNIQUE constraint failed: numeros_rifa.rifa_id, numeros_rifa.numero" in str(e):
            return False, "Alguno de los números seleccionados ya está ocupado."
        return False, f"Error al guardar los números: {str(e)}"

# --- Rutas de Rifa (dentro del Blueprint) ---

@rifas_bp.route('/rifas')
@login_required # Requiere que el usuario esté logueado para acceder.
def lista_rifas(): # Nombre de la función cambiado a lista_rifas
    # Obtiene todas las rifas ordenadas por fecha de forma descendente.
    rifas = Rifa.query.order_by(Rifa.fecha_rifa.desc()).all()
    # Verifica si el usuario actual tiene permiso para crear rifas.
    can_create_rifa = current_user.email in AUTHORIZED_RIFA_CREATORS
    return render_template('lista_rifas.html', rifas=rifas, can_create_rifa=can_create_rifa) # Plantilla cambiada a lista_rifas.html

@rifas_bp.route('/crear_rifa', methods=['GET', 'POST'])
@login_required
def crear_rifa():
    # Redirige si el usuario no tiene permiso para crear rifas.
    if current_user.email not in AUTHORIZED_RIFA_CREATORS:
        flash('No tienes permiso para crear rifas.', 'danger')
        return redirect(url_for('rifas.lista_rifas')) # Usar 'rifas.lista_rifas' para referenciar la ruta del blueprint

    form = CrearRifaForm()
    if form.validate_on_submit():
        # Guarda la imagen y obtiene su nombre de archivo.
        imagen_filename = guardar_imagen_rifa(form.imagen_rifa.data)

        # Crea una nueva instancia de Rifa con los datos del formulario.
        nueva_rifa = Rifa(
            nombre_rifa=form.nombre_rifa.data,
            valor_rifa=form.valor_rifa.data,
            fecha_rifa=form.fecha_rifa.data,
            descripcion_rifa=form.descripcion_rifa.data,
            imagen_rifa=imagen_filename
        )
        db.session.add(nueva_rifa) # Añade la nueva rifa a la sesión.
        db.session.commit() # Confirma los cambios.
        flash('¡Rifa creada exitosamente!', 'success')
        # Redirige a la vista de la rifa recién creada.
        return redirect(url_for('rifas.ver_rifa', rifa_id=nueva_rifa.id))
    return render_template('crear_rifa.html', form=form)

@rifas_bp.route('/ver_rifa/<int:rifa_id>', methods=['GET', 'POST'])
@login_required
def ver_rifa(rifa_id):
    # Obtiene la rifa por su ID.
    rifa = obtener_rifa_por_id(rifa_id)
    if not rifa:
        flash('Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.lista_rifas')) # Redirige a lista_rifas

    # Obtiene los números ya vendidos para esta rifa y los formatea para la vista.
    numeros_vendidos_objetos = obtener_numeros_vendidos(rifa_id)
    numeros_ocupados = {n.numero: {'nombre': n.nombre_jugador, 'telefono': n.telefono_jugador} for n in numeros_vendidos_objetos}

    form = SeleccionarNumerosForm()

    if form.validate_on_submit() and request.method == 'POST':
        # Obtiene los números seleccionados desde el campo oculto del formulario.
        numeros_seleccionados_str = request.form.get('selected_numbers_hidden', '[]')
        try:
            # Parsea la cadena JSON de números a una lista de Python.
            numeros_seleccionados_list = [num.strip() for num in numeros_seleccionados_str.strip('[]').split(',') if num.strip()]
        except Exception:
            flash('Error en la selección de números. Inténtalo de nuevo.', 'danger')
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

        if not numeros_seleccionados_list:
            flash('Debes seleccionar al menos un número.', 'danger')
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

        # Intenta guardar los números seleccionados.
        exito, mensaje = guardar_seleccion_numeros(
            rifa_id,
            form.nombre_jugador.data,
            form.telefono_jugador.data,
            numeros_seleccionados_list
        )
        if exito:
            flash(mensaje, 'success')
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))
        else:
            flash(mensaje, 'danger')
            # Si hay un error, recarga la página para mostrar los números ya ocupados.
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

    # Renderiza la plantilla con los datos de la rifa, números ocupados y el formulario.
    return render_template('ver_rifa.html', rifa=rifa, numeros_ocupados=numeros_ocupados, form=form)

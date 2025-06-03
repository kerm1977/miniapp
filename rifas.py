# rifas.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, DecimalField, DateField, FileField
from wtforms.validators import DataRequired, NumberRange, Optional
from flask_wtf.file import FileAllowed
from datetime import datetime
import os
from flask_login import login_required, current_user
import re # Importar el módulo re para expresiones regulares
from flask_wtf.csrf import generate_csrf # Importar generate_csrf

# CAMBIO CLAVE AQUÍ: Solo importa 'db' desde models.py, ya que Rifa y NumeroRifa están definidos en este archivo.
from models import db 

# --- Blueprint para Rifas ---
rifas_bp = Blueprint('rifas', __name__, template_folder='templates', static_folder='static')

# --- Configuración de la carpeta de subida de imágenes para las rifas ---
RIFAS_UPLOAD_FOLDER_RELATIVE = os.path.join('static', 'uploads')

def configure_rifas_uploads(app):
    """
    Configura la carpeta de subida de imágenes para las rifas.
    Esta función debe ser llamada después de inicializar la aplicación Flask.
    """
    upload_folder_absolute = os.path.join(app.root_path, RIFAS_UPLOAD_FOLDER_RELATIVE)
    app.config['UPLOAD_FOLDER'] = upload_folder_absolute
    os.makedirs(upload_folder_absolute, exist_ok=True)
    print(f"Carpeta de subida de rifas configurada en: {upload_folder_absolute}")


# --- Modelos de Rifa (DEFINIDOS AQUÍ) ---
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
class CrearRifaForm(FlaskForm):
    nombre_rifa = StringField('Nombre de la Rifa', validators=[DataRequired()])
    valor_rifa = DecimalField('Valor de la Rifa', validators=[DataRequired(), NumberRange(min=0.01)])
    fecha_rifa = DateField('Fecha de la Rifa', format='%Y-%m-%d', validators=[DataRequired()])
    descripcion_rifa = TextAreaField('Descripción de la Rifa', validators=[Optional()])
    imagen_rifa = FileField('Imagen de la Rifa', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Solo se permiten imágenes!')])
    submit = SubmitField('Crear Rifa')

class SeleccionarNumerosForm(FlaskForm):
    nombre_jugador = StringField('Nombre del Jugador', validators=[DataRequired()])
    telefono_jugador = StringField('Teléfono del Jugador', validators=[DataRequired()])
    numeros_seleccionados = StringField('Números Seleccionados (internos)', render_kw={'readonly': True})
    submit = SubmitField('Guardar mis números')

AUTHORIZED_RIFA_CREATORS = [
    "kenth1977@gmail.com",
    "jceciliano69@gmail.com",
    "lthikingcr@gmail.com"
]

# --- Funciones Lógicas de Rifa ---
def guardar_imagen_rifa(imagen):
    if imagen:
        filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + imagen.filename
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        imagen.save(filepath)
        return filename
    return None

def obtener_numeros_vendidos(rifa_id):
    return NumeroRifa.query.filter_by(rifa_id=rifa_id).all()

def obtener_rifa_por_id(rifa_id):
    return Rifa.query.get(rifa_id)

def guardar_seleccion_numeros(rifa_id, nombre_jugador, telefono_jugador, numeros):
    try:
        for num_str in numeros:
            numero = NumeroRifa(
                rifa_id=rifa_id,
                numero=num_str,
                nombre_jugador=nombre_jugador,
                telefono_jugador=telefono_jugador
            )
            db.session.add(numero)
        db.session.commit()
        return True, "Números guardados exitosamente."
    except Exception as e:
        db.session.rollback()
        if "UNIQUE constraint failed: numeros_rifa.rifa_id, numeros_rifa.numero" in str(e):
            return False, "Alguno de los números seleccionados ya está ocupado."
        return False, f"Error al guardar los números: {str(e)}"

# --- Rutas de Rifa (dentro del Blueprint) ---

@rifas_bp.route('/rifas')
@login_required
def lista_rifas():
    rifas = Rifa.query.order_by(Rifa.fecha_rifa.desc()).all()
    can_create_rifa = current_user.email in AUTHORIZED_RIFA_CREATORS
    csrf_token_value = generate_csrf() # Genera el token CSRF aquí
    return render_template('lista_rifas.html', rifas=rifas, can_create_rifa=can_create_rifa, csrf_token=csrf_token_value)

@rifas_bp.route('/crear_rifa', methods=['GET', 'POST'])
@login_required
def crear_rifa():
    if current_user.email not in AUTHORIZED_RIFA_CREATORS:
        flash('No tienes permiso para crear rifas.', 'danger')
        return redirect(url_for('rifas.lista_rifas'))

    form = CrearRifaForm()
    if form.validate_on_submit():
        imagen_filename = guardar_imagen_rifa(form.imagen_rifa.data)

        nueva_rifa = Rifa(
            nombre_rifa=form.nombre_rifa.data,
            valor_rifa=form.valor_rifa.data,
            fecha_rifa=form.fecha_rifa.data,
            descripcion_rifa=form.descripcion_rifa.data,
            imagen_rifa=imagen_filename
        )
        db.session.add(nueva_rifa)
        db.session.commit()
        flash('¡Rifa creada exitosamente!', 'success')
        return redirect(url_for('rifas.ver_rifa', rifa_id=nueva_rifa.id))
    return render_template('crear_rifa.html', form=form)

@rifas_bp.route('/ver_rifa/<int:rifa_id>', methods=['GET', 'POST'])
@login_required
def ver_rifa(rifa_id):
    rifa = obtener_rifa_por_id(rifa_id)
    if not rifa:
        flash('Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.lista_rifas'))

    numeros_vendidos_objetos = obtener_numeros_vendidos(rifa_id)
    
    numeros_ocupados_para_botones = {n.numero: {'nombre': n.nombre_jugador, 'telefono': n.telefono_jugador} for n in numeros_vendidos_objetos}

    grouped_numeros_por_jugador = {}
    for num_obj in numeros_vendidos_objetos:
        normalized_nombre = num_obj.nombre_jugador.strip().lower()
        normalized_telefono = re.sub(r'\D', '', num_obj.telefono_jugador).strip()

        player_key = (normalized_nombre, normalized_telefono)
        
        # --- DEBUGGING PRINTS ---
        print(f"DEBUG: Numero: {num_obj.numero}, Nombre Original: '{num_obj.nombre_jugador}', Telefono Original: '{num_obj.telefono_jugador}'")
        print(f"DEBUG: Nombre Normalizado: '{normalized_nombre}', Telefono Normalizado: '{normalized_telefono}'")
        print(f"DEBUG: Clave de Jugador: {player_key}")
        # --- FIN DEBUGGING PRINTS ---

        if player_key not in grouped_numeros_por_jugador:
            grouped_numeros_por_jugador[player_key] = {
                'nombre_original': num_obj.nombre_jugador,
                'telefono': num_obj.telefono_jugador,
                'numeros': []
            }
        grouped_numeros_por_jugador[player_key]['numeros'].append(num_obj.numero)
    
    for player_data in grouped_numeros_por_jugador.values():
        player_data['numeros'].sort()

    form = SeleccionarNumerosForm()

    if form.validate_on_submit() and request.method == 'POST':
        numeros_seleccionados_str = request.form.get('selected_numbers_hidden', '[]')
        try:
            numeros_seleccionados_list = [num.strip() for num in numeros_seleccionados_str.strip('[]').split(',') if num.strip()]
        except Exception:
            flash('Error en la selección de números. Inténtalo de nuevo.', 'danger')
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

        if not numeros_seleccionados_list:
            flash('Debes seleccionar al menos un número.', 'danger')
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

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
            return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

    return render_template('ver_rifa.html',
                           rifa=rifa,
                           numeros_ocupados=numeros_ocupados_para_botones,
                           grouped_numeros_por_jugador=grouped_numeros_por_jugador,
                           form=form)

@rifas_bp.route('/borrar_rifa/<int:rifa_id>', methods=['POST'])
@login_required
def borrar_rifa(rifa_id):
    if current_user.email not in AUTHORIZED_RIFA_CREATORS:
        flash('No tienes permiso para borrar rifas.', 'danger')
        return redirect(url_for('rifas.lista_rifas'))

    rifa = Rifa.query.get_or_404(rifa_id)
    
    try:
        if rifa.imagen_rifa:
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], rifa.imagen_rifa)
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"DEBUG: Imagen eliminada: {image_path}")
            else:
                print(f"DEBUG: La imagen no se encontró en la ruta: {image_path}")

        db.session.delete(rifa)
        db.session.commit()
        flash(f'¡Rifa "{rifa.nombre_rifa}" eliminada exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al intentar borrar la rifa: {str(e)}', 'danger')
        print(f"ERROR: Fallo al borrar rifa {rifa_id}: {e}")
    
    return redirect(url_for('rifas.lista_rifas'))


@rifas_bp.route('/test_rifas')
def test_rifas():
    return "¡La ruta de prueba de rifas funciona!"
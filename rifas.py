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
import json # Importar json para parsear los números seleccionados

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
    # Este campo se usa para enviar los números seleccionados desde JS
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
            # Asegura que el número se guarde como una cadena de 2 dígitos
            nuevo_numero = NumeroRifa( 
                rifa_id=rifa_id,
                numero=str(num_str).zfill(2), 
                nombre_jugador=nombre_jugador,
                telefono_jugador=telefono_jugador
            )
            db.session.add(nuevo_numero)
        db.session.commit()
        print(f"DEBUG: Números guardados exitosamente en la DB para rifa {rifa_id}: {numeros}") 
        return True, "Números guardados exitosamente."
    except Exception as e:
        db.session.rollback()
        # Captura el error específico de restricción única
        if "UNIQUE constraint failed: numeros_rifa.rifa_id, numeros_rifa.numero" in str(e):
            return False, "Alguno de los números seleccionados ya está ocupado."
        print(f"ERROR: Fallo al guardar números para rifa {rifa_id}: {e}") 
        return False, f"Error al guardar los números: {str(e)}"

# --- Rutas de Rifa (dentro del Blueprint) ---

@rifas_bp.route('/rifas')
@login_required
def lista_rifas():
    rifas = Rifa.query.order_by(Rifa.fecha_rifa.desc()).all()
    can_create_rifa = current_user.email in AUTHORIZED_RIFA_CREATORS
    csrf_token_value = generate_csrf() 
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
    
    numeros_ocupados_para_botones = {str(n.numero).zfill(2): {'nombre': n.nombre_jugador, 'telefono': n.telefono_jugador} for n in numeros_vendidos_objetos} 
    
    grouped_numeros_por_jugador = {}
    for num_obj in numeros_vendidos_objetos:
        # Normalizar nombre y teléfono para agrupar
        normalized_nombre = num_obj.nombre_jugador.strip().lower()
        normalized_telefono = re.sub(r'\D', '', num_obj.telefono_jugador).strip() 

        # CAMBIO CLAVE AQUÍ: Crear una clave de cadena para el diccionario
        player_key = f"{normalized_nombre}_{normalized_telefono}" 
        
        if player_key not in grouped_numeros_por_jugador:
            grouped_numeros_por_jugador[player_key] = {
                'nombre_original': num_obj.nombre_jugador, 
                'telefono': num_obj.telefono_jugador,
                'numeros': []
            }
        grouped_numeros_por_jugador[player_key]['numeros'].append(str(num_obj.numero).zfill(2)) 
    
    for player_data in grouped_numeros_por_jugador.values():
        player_data['numeros'].sort()

    form = SeleccionarNumerosForm()

    if request.method == 'POST': 
        selected_numbers_json = request.form.get('selected_numbers_hidden', '[]')
        try:
            form.numeros_seleccionados.data = json.dumps([str(num).zfill(2) for num in json.loads(selected_numbers_json)])
        except json.JSONDecodeError:
            flash('Error en la selección de números. Formato inválido.', 'danger')
            form.numeros_seleccionados.data = '[]' 
        
    if form.validate_on_submit(): 
        nombre_jugador = form.nombre_jugador.data
        telefono_jugador = form.telefono_jugador.data
        
        selected_numbers_list = json.loads(form.numeros_seleccionados.data)

        if not selected_numbers_list:
            flash('Debes seleccionar al menos un número.', 'danger')
            return render_template('ver_rifa.html',
                                   rifa=rifa,
                                   numeros_ocupados=numeros_ocupados_para_botones, 
                                   grouped_numeros_por_jugador=grouped_numeros_por_jugador,
                                   form=form)

        current_numeros_ocupados_en_db = {str(n.numero).zfill(2) for n in obtener_numeros_vendidos(rifa_id)} 
        
        nuevos_numeros_a_guardar = []
        numeros_conflictivos = []

        for num_elegido in selected_numbers_list:
            if num_elegido in current_numeros_ocupados_en_db:
                numeros_conflictivos.append(num_elegido)
            else:
                nuevos_numeros_a_guardar.append(num_elegido)

        if numeros_conflictivos:
            flash(f'Los números {", ".join(numeros_conflictivos)} ya han sido ocupados. Por favor, selecciona otros.', 'danger')
            form.nombre_jugador.data = nombre_jugador
            form.telefono_jugador.data = telefono_jugador
            
            return render_template('ver_rifa.html',
                                   rifa=rifa,
                                   numeros_ocupados=numeros_ocupados_para_botones, 
                                   grouped_numeros_por_jugador=grouped_numeros_por_jugador,
                                   form=form) 

        try:
            exito, mensaje = guardar_seleccion_numeros(
                rifa_id,
                form.nombre_jugador.data,
                form.telefono_jugador.data,
                nuevos_numeros_a_guardar
            )
            if exito:
                flash(mensaje, 'success')
                return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))
            else:
                flash(mensaje, 'danger')
                return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error inesperado al guardar los números: {e}', 'danger')
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

@rifas_bp.route('/<int:rifa_id>/eliminar_jugador', methods=['POST'])
@login_required
def eliminar_jugador_rifa(rifa_id):
    # Solo los creadores autorizados pueden eliminar jugadores
    if current_user.email not in AUTHORIZED_RIFA_CREATORS:
        flash('No tienes permiso para eliminar jugadores de rifas.', 'danger')
        return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

    nombre_jugador_a_eliminar = request.form.get('nombre_jugador')
    telefono_jugador_a_eliminar = request.form.get('telefono_jugador')
    
    if not nombre_jugador_a_eliminar or not telefono_jugador_a_eliminar:
        flash('Datos del jugador incompletos para la eliminación.', 'danger')
        return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))

    try:
        # Encuentra y elimina todos los números asociados a este jugador en esta rifa
        numeros_a_eliminar = NumeroRifa.query.filter_by(
            rifa_id=rifa_id,
            nombre_jugador=nombre_jugador_a_eliminar,
            telefono_jugador=telefono_jugador_a_eliminar
        ).all()

        if numeros_a_eliminar:
            for num_obj in numeros_a_eliminar:
                db.session.delete(num_obj)
            db.session.commit()
            flash(f'Los números del jugador "{nombre_jugador_a_eliminar}" han sido restablecidos.', 'success')
        else:
            flash(f'No se encontraron números para el jugador "{nombre_jugador_a_eliminar}" en esta rifa.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al intentar eliminar los números del jugador: {str(e)}', 'danger')
        print(f"ERROR: Fallo al eliminar números de jugador {nombre_jugador_a_eliminar} en rifa {rifa_id}: {e}")
    
    return redirect(url_for('rifas.ver_rifa', rifa_id=rifa_id))


@rifas_bp.route('/test_rifas')
def test_rifas():
    return "¡La ruta de prueba de rifas funciona!"

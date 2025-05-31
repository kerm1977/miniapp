# pagos.py
# Este módulo contiene el modelo, formulario y rutas para la gestión de pagos.

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, DecimalField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import generate_csrf # Importar generate_csrf
import enum

# Importar db y User desde models.py para la relación
from models import db, User

# --- Modelo de Datos: Pago ---
class Pago(db.Model):
    __tablename__ = 'pagos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('pagos', lazy=True))

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_cambio = db.Column(db.Numeric(10, 4), nullable=False)
    actividad = db.Column(db.String(100), nullable=False)
    nombre_actividad = db.Column(db.String(255), nullable=False)
    costo_paquete = db.Column(db.Numeric(10, 2), nullable=False)
    cantidad_personas = db.Column(db.Integer, nullable=False)

    # Costos Transporte
    costo_busetas = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_lanchas_transporte = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_otro_transporte = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_aerolinea = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    # Costos Grupales
    costo_guia = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_entrada = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_parqueo = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_lancha_grupal = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_alquiler_local = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_estadia = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    # Costos Individuales
    costo_bano_duchas = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_impuestos = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_desayuno = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_almuerzo = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_cafe = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_cena = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_refrigerio = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_certificados = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    costo_reconocimientos = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    nota = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Pago {self.nombre_actividad} - {self.fecha_registro.strftime("%Y-%m-%d")}>'

    # Propiedades calculadas
    @property
    def total_costos_transporte(self):
        total = (self.costo_busetas or 0) + \
                (self.costo_lanchas_transporte or 0) + \
                (self.costo_otro_transporte or 0) + \
                (self.costo_aerolinea or 0)
        return total / self.cantidad_personas if self.cantidad_personas else 0

    @property
    def total_costos_grupales(self):
        total = (self.costo_guia or 0) + \
                (self.costo_entrada or 0) + \
                (self.costo_parqueo or 0) + \
                (self.costo_lancha_grupal or 0) + \
                (self.costo_alquiler_local or 0) + \
                (self.costo_estadia or 0)
        # Solo calcular si el total es mayor que cero para evitar división por cero si todos son cero
        return total / self.cantidad_personas if self.cantidad_personas and total > 0 else 0

    @property
    def total_costos_individuales(self):
        return (self.costo_bano_duchas or 0) + \
               (self.costo_impuestos or 0) + \
               (self.costo_desayuno or 0) + \
               (self.costo_almuerzo or 0) + \
               (self.costo_cafe or 0) + \
               (self.costo_cena or 0) + \
               (self.costo_refrigerio or 0) + \
               (self.costo_certificados or 0) + \
               (self.costo_reconocimientos or 0)

    @property
    def total_bruto_individual(self):
        return self.total_costos_transporte + \
               self.total_costos_grupales + \
               self.total_costos_individuales

    @property
    def total_bruto_general_colones(self):
        return self.total_bruto_individual * self.cantidad_personas

    @property
    def total_bruto_general_dolar(self):
        # Asegurarse de que tipo_cambio no sea cero para evitar ZeroDivisionError
        return self.costo_paquete / self.tipo_cambio if self.tipo_cambio else 0

    @property
    def total_ganancia_pp(self):
        return self.costo_paquete - self.total_bruto_individual

    @property
    def total_ganancia_general(self):
        return self.total_ganancia_pp * self.cantidad_personas if self.cantidad_personas else 0


# --- Formulario de Pagos: PagoForm ---
class PagoForm(FlaskForm):
    tipo_cambio = DecimalField('Tipo de Cambio', validators=[DataRequired(), NumberRange(min=0.01)], render_kw={"step": "0.01"})
    actividad = SelectField('Actividad', choices=[
        ('El Camino de Costa Rica', 'El Camino de Costa Rica'),
        ('Parque Nacional', 'Parque Nacional'),
        ('Iniciante', 'Iniciante'),
        ('Básico', 'Básico'),
        ('Intermedio', 'Intermedio'),
        ('Avanzado', 'Avanzado'),
        ('Internacional', 'Internacional'),
        ('Convivio', 'Convivio')
    ], validators=[DataRequired()])
    nombre_actividad = StringField('Nombre de Actividad', validators=[DataRequired(), Length(max=255)])
    costo_paquete = DecimalField('Costo Paquete', validators=[DataRequired(), NumberRange(min=0)], render_kw={"step": "0.01"})
    cantidad_personas = IntegerField('Cantidad de Personas', validators=[DataRequired(), NumberRange(min=1)])

    # Costos Transporte
    costo_busetas = DecimalField('Costo Busetas', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_lanchas_transporte = DecimalField('Costo Lanchas', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_otro_transporte = DecimalField('Costo Otro Transporte (acarreo, 4x4)', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_aerolinea = DecimalField('Costo Aerolínea', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})

    # Costos Grupales
    costo_guia = DecimalField('Costo Guía', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_entrada = DecimalField('Costo Entrada', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_parqueo = DecimalField('Costo Parqueo', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_lancha_grupal = DecimalField('Costo Lancha', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_alquiler_local = DecimalField('Costo Alquiler local', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_estadia = DecimalField('Costo Estadía', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})

    # Costos Individuales
    costo_bano_duchas = DecimalField('Costo Baño/Duchas', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_impuestos = DecimalField('Costo Impuestos', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_desayuno = DecimalField('Costo Desayuno', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_almuerzo = DecimalField('Costo Almuerzo', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_cafe = DecimalField('Costo Café', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_cena = DecimalField('Costo Cena', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_refrigerio = DecimalField('Costo Refrigerio', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_certificados = DecimalField('Costo Certificados', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})
    costo_reconocimientos = DecimalField('Costo Reconocimientos', validators=[Optional(), NumberRange(min=0)], default=0, render_kw={"step": "0.01"})

    nota = TextAreaField('Nota', validators=[Optional()])

    submit = SubmitField('Guardar Pago')


# --- Blueprint para Pagos ---
pagos_bp = Blueprint('pagos', __name__, template_folder='templates')

@pagos_bp.route('/ver_pagos')
@login_required
def ver_pagos():
    """
    Muestra una lista de todos los pagos registrados por el usuario actual.
    """
    pagos = Pago.query.filter_by(usuario_id=current_user.id).order_by(Pago.fecha_registro.desc()).all()
    # Se pasa generate_csrf para que el formulario de borrado en la tabla pueda usarlo.
    return render_template('ver_pagos.html', pagos=pagos, generate_csrf=generate_csrf)

@pagos_bp.route('/crear_pagos', methods=['GET', 'POST'])
@login_required
def crear_pagos():
    """
    Permite al usuario crear un nuevo registro de pago.
    Muestra el formulario GET y procesa los datos POST.
    """
    form = PagoForm()
    if form.validate_on_submit():
        try:
            nuevo_pago = Pago(
                usuario_id=current_user.id,
                tipo_cambio=form.tipo_cambio.data,
                actividad=form.actividad.data,
                nombre_actividad=form.nombre_actividad.data,
                costo_paquete=form.costo_paquete.data,
                cantidad_personas=form.cantidad_personas.data,
                costo_busetas=form.costo_busetas.data,
                costo_lanchas_transporte=form.costo_lanchas_transporte.data,
                costo_otro_transporte=form.costo_otro_transporte.data,
                costo_aerolinea=form.costo_aerolinea.data,
                costo_guia=form.costo_guia.data,
                costo_entrada=form.costo_entrada.data,
                costo_parqueo=form.costo_parqueo.data,
                costo_lancha_grupal=form.costo_lancha_grupal.data,
                costo_alquiler_local=form.costo_alquiler_local.data,
                costo_estadia=form.costo_estadia.data,
                costo_bano_duchas=form.costo_bano_duchas.data,
                costo_impuestos=form.costo_impuestos.data,
                costo_desayuno=form.costo_desayuno.data,
                costo_almuerzo=form.costo_almuerzo.data,
                costo_cafe=form.costo_cafe.data,
                costo_cena=form.costo_cena.data,
                costo_refrigerio=form.costo_refrigerio.data,
                costo_certificados=form.costo_certificados.data,
                costo_reconocimientos=form.costo_reconocimientos.data,
                nota=form.nota.data
            )
            db.session.add(nuevo_pago)
            db.session.commit()
            flash('¡Pago creado exitosamente!', 'success')
            return redirect(url_for('pagos.ver_pagos')) # Usar pagos.ver_pagos para referenciar la ruta del blueprint
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el pago: {e}', 'danger')
            print(f"Error al crear pago: {e}") # Para depuración
    return render_template('crear_pagos.html', form=form, title='Crear Nuevo Pago', generate_csrf=generate_csrf)

@pagos_bp.route('/editar_pagos/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_pagos(id):
    """
    Permite al usuario editar un registro de pago existente.
    Muestra el formulario precargado GET y procesa los datos POST.
    """
    pago = Pago.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = PagoForm(obj=pago) # Carga los datos existentes del pago en el formulario

    if form.validate_on_submit():
        try:
            form.populate_obj(pago) # Actualiza el objeto pago con los datos del formulario
            db.session.commit()
            flash('¡Pago actualizado exitosamente!', 'success')
            return redirect(url_for('pagos.ver_pagos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el pago: {e}', 'danger')
            print(f"Error al actualizar pago: {e}") # Para depuración
    return render_template('crear_pagos.html', form=form, title='Editar Pago', generate_csrf=generate_csrf) # Reutilizamos la misma plantilla

@pagos_bp.route('/borrar_pagos/<int:id>', methods=['POST'])
@login_required
def borrar_pagos(id):
    """
    Permite al usuario borrar un registro de pago existente.
    """
    pago = Pago.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if pago:
        try:
            db.session.delete(pago)
            db.session.commit()
            flash('¡Pago borrado exitosamente!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al intentar borrar el pago: {e}', 'danger')
            print(f"Error al borrar pago: {e}") # Para depuración
    else:
        flash('Pago no encontrado o no autorizado.', 'danger')
    return redirect(url_for('pagos.ver_pagos'))

# pagos.py
# Este módulo contiene el modelo, formulario y rutas para la gestión de pagos.

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import generate_csrf
import enum
import io # Importar para manejar el PDF en memoria

# Importar componentes de ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors

# Importar db y User desde models.py para la relación
from models import db, User

# --- Modelo de Datos: Pago ---
class Pago(db.Model):
    __tablename__ = 'pagos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('pagos', lazy=True))

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_cambio = db.Column(db.Integer, nullable=False)
    actividad = db.Column(db.String(100), nullable=False)
    nombre_actividad = db.Column(db.String(255), nullable=False)
    costo_paquete = db.Column(db.Integer, nullable=False)
    cantidad_personas = db.Column(db.Integer, nullable=False)

    # Costos Transporte
    costo_busetas = db.Column(db.Integer, nullable=True, default=0)
    costo_lanchas_transporte = db.Column(db.Integer, nullable=True, default=0)
    costo_otro_transporte = db.Column(db.Integer, nullable=True, default=0)
    costo_aerolinea = db.Column(db.Integer, nullable=True, default=0)

    # Costos Grupales
    costo_guia = db.Column(db.Integer, nullable=True, default=0)
    costo_entrada = db.Column(db.Integer, nullable=True, default=0)
    costo_parqueo = db.Column(db.Integer, nullable=True, default=0)
    costo_lancha_grupal = db.Column(db.Integer, nullable=True, default=0)
    costo_alquiler_local = db.Column(db.Integer, nullable=True, default=0)
    costo_estadia = db.Column(db.Integer, nullable=True, default=0)

    # Costos Individuales
    costo_bano_duchas = db.Column(db.Integer, nullable=True, default=0)
    costo_impuestos = db.Column(db.Integer, nullable=True, default=0)
    costo_desayuno = db.Column(db.Integer, nullable=True, default=0)
    costo_almuerzo = db.Column(db.Integer, nullable=True, default=0)
    costo_cafe = db.Column(db.Integer, nullable=True, default=0)
    costo_cena = db.Column(db.Integer, nullable=True, default=0)
    costo_refrigerio = db.Column(db.Integer, nullable=True, default=0)
    costo_certificados = db.Column(db.Integer, nullable=True, default=0)
    costo_reconocimientos = db.Column(db.Integer, nullable=True, default=0)

    nota = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Pago {self.nombre_actividad} - {self.fecha_registro.strftime("%Y-%m-%d")}>'

    # Propiedades calculadas (ajustadas para manejar enteros en el backend)
    @property
    def total_costos_transporte(self):
        total = (self.costo_busetas or 0) + \
                (self.costo_lanchas_transporte or 0) + \
                (self.costo_otro_transporte or 0) + \
                (self.costo_aerolinea or 0)
        # Usar round() para asegurar enteros en la división
        return round(total / self.cantidad_personas) if self.cantidad_personas else 0

    @property
    def total_costos_grupales(self):
        total = (self.costo_guia or 0) + \
                (self.costo_entrada or 0) + \
                (self.costo_parqueo or 0) + \
                (self.costo_lancha_grupal or 0) + \
                (self.costo_alquiler_local or 0) + \
                (self.costo_estadia or 0)
        # Solo calcular si el total es mayor que cero para evitar división por cero si todos son cero
        return round(total / self.cantidad_personas) if self.cantidad_personas and total > 0 else 0

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
        # Usar round() para asegurar enteros en la división
        return round(self.total_bruto_general_colones / self.tipo_cambio) if self.tipo_cambio else 0

    @property
    def total_ganancia_pp(self):
        return self.costo_paquete - self.total_bruto_individual

    @property
    def total_ganancia_general(self):
        return self.total_ganancia_pp * self.cantidad_personas if self.cantidad_personas else 0


# --- Formulario de Pagos: PagoForm ---
class PagoForm(FlaskForm):
    tipo_cambio = IntegerField('Tipo de Cambio', validators=[DataRequired(), NumberRange(min=1)])
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
    costo_paquete = IntegerField('Costo Paquete', validators=[DataRequired(), NumberRange(min=0)])
    cantidad_personas = IntegerField('Cantidad de Personas', validators=[DataRequired(), NumberRange(min=1)])

    # Costos Transporte
    costo_busetas = IntegerField('Costo Busetas', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_lanchas_transporte = IntegerField('Costo Lanchas', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_otro_transporte = IntegerField('Costo Otro Transporte (acarreo, 4x4)', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_aerolinea = IntegerField('Costo Aerolínea', validators=[Optional(), NumberRange(min=0)], default=0)

    # Costos Grupales
    costo_guia = IntegerField('Costo Guía', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_entrada = IntegerField('Costo Entrada', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_parqueo = IntegerField('Costo Parqueo', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_lancha_grupal = IntegerField('Costo Lancha', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_alquiler_local = IntegerField('Costo Alquiler local', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_estadia = IntegerField('Costo Estadía', validators=[Optional(), NumberRange(min=0)], default=0)

    # Costos Individuales
    costo_bano_duchas = IntegerField('Costo Baño/Duchas', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_impuestos = IntegerField('Costo Impuestos', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_desayuno = IntegerField('Costo Desayuno', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_almuerzo = IntegerField('Costo Almuerzo', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_cafe = IntegerField('Costo Café', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_cena = IntegerField('Costo Cena', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_refrigerio = IntegerField('Costo Refrigerio', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_certificados = IntegerField('Costo Certificados', validators=[Optional(), NumberRange(min=0)], default=0)
    costo_reconocimientos = IntegerField('Costo Reconocimientos', validators=[Optional(), NumberRange(min=0)], default=0)

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
            return redirect(url_for('pagos.ver_pagos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el pago: {e}', 'danger')
            print(f"Error al crear pago: {e}")
    return render_template('crear_pagos.html', form=form, title='Crear Nuevo Pago', generate_csrf=generate_csrf)

@pagos_bp.route('/editar_pagos/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_pagos(id):
    """
    Permite al usuario editar un registro de pago existente.
    Muestra el formulario precargado GET y procesa los datos POST.
    """
    pago = Pago.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = PagoForm(obj=pago)

    if form.validate_on_submit():
        try:
            form.populate_obj(pago)
            db.session.commit()
            flash('¡Pago actualizado exitosamente!', 'success')
            return redirect(url_for('pagos.ver_pagos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el pago: {e}', 'danger')
            print(f"Error al actualizar pago: {e}")
    return render_template('crear_pagos.html', form=form, title='Editar Pago', generate_csrf=generate_csrf)

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
            print(f"Error al borrar pago: {e}")
    else:
        flash('Pago no encontrado o no autorizado.', 'danger')
    return redirect(url_for('pagos.ver_pagos'))

@pagos_bp.route('/exportar_pagos_pdf')
@login_required
def exportar_pagos_pdf():
    """
    Genera un PDF con la lista de pagos del usuario actual.
    """
    pagos = Pago.query.filter_by(usuario_id=current_user.id).order_by(Pago.fecha_registro.desc()).all()
    
    return _generar_pdf_pagos(pagos, "reporte_pagos.pdf", "Reporte de Pagos")

@pagos_bp.route('/exportar_pago_individual_pdf/<int:pago_id>')
@login_required
def exportar_pago_individual_pdf(pago_id):
    """
    Genera un PDF para un pago individual específico.
    """
    pago = Pago.query.filter_by(id=pago_id, usuario_id=current_user.id).first_or_404()
    return _generar_pdf_pagos([pago], f"pago_{pago.id}.pdf", f"Detalle de Pago #{pago.id}")


def _generar_pdf_pagos(pagos, filename, title):
    """
    Función auxiliar para generar el PDF de uno o varios pagos.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Estilos personalizados para el PDF
    style_h1 = styles['h1']
    style_h1.alignment = TA_CENTER
    style_h1.spaceAfter = 0.2 * inch

    style_h2 = styles['h2']
    style_h2.alignment = TA_CENTER
    style_h2.spaceAfter = 0.1 * inch

    style_body = styles['Normal']
    style_body.fontSize = 10
    style_body.leading = 12 # Espaciado entre líneas

    style_bold = ParagraphStyle(
        'BoldParagraph',
        parent=style_body,
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12
    )

    style_total = ParagraphStyle(
        'TotalParagraph',
        parent=style_body,
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=TA_RIGHT
    )

    elements = []

    elements.append(Paragraph(title, style_h1))
    elements.append(Paragraph(f"Usuario: {current_user.username}", style_h2))
    elements.append(Spacer(1, 0.2 * inch))

    if not pagos:
        elements.append(Paragraph("No hay pagos registrados para exportar.", style_body))
    else:
        for pago in pagos:
            elements.append(Paragraph(f"<b>Pago # {pago.id}</b> - {pago.fecha_registro.strftime('%Y-%m-%d %H:%M')}", style_bold))
            elements.append(Paragraph(f"<b>Actividad:</b> {pago.actividad}", style_body))
            elements.append(Paragraph(f"<b>Nombre de Actividad:</b> {pago.nombre_actividad}", style_body))
            elements.append(Paragraph(f"<b>Costo Paquete:</b> ¢{pago.costo_paquete}", style_body))
            elements.append(Paragraph(f"<b>Cantidad de Personas:</b> {pago.cantidad_personas}", style_body))
            elements.append(Paragraph(f"<b>Tipo de Cambio:</b> {pago.tipo_cambio}", style_body))
            
            elements.append(Spacer(1, 0.1 * inch)) # Pequeño espacio

            # Sección de Costos
            elements.append(Paragraph("<b>Costos Detallados:</b>", style_bold))
            costos_data = [
                ["Transporte:", f"¢{pago.costo_busetas}", f"Lanchas: ¢{pago.costo_lanchas_transporte}"],
                ["", f"Otro: ¢{pago.costo_otro_transporte}", f"Aerolínea: ¢{pago.costo_aerolinea}"],
                ["Grupales:", f"Guía: ¢{pago.costo_guia}", f"Entrada: ¢{pago.costo_entrada}"],
                ["", f"Parqueo: ¢{pago.costo_parqueo}", f"Lancha Grupal: ¢{pago.costo_lancha_grupal}"],
                ["", f"Alquiler Local: ¢{pago.costo_alquiler_local}", f"Estadía: ¢{pago.costo_estadia}"],
                ["Individuales:", f"Baño/Duchas: ¢{pago.costo_bano_duchas}", f"Impuestos: ¢{pago.costo_impuestos}"],
                ["", f"Desayuno: ¢{pago.costo_desayuno}", f"Almuerzo: ¢{pago.costo_almuerzo}"],
                ["", f"Café: ¢{pago.costo_cafe}", f"Cena: ¢{pago.costo_cena}"],
                ["", f"Refrigerio: ¢{pago.costo_refrigerio}", f"Certificados: ¢{pago.costo_certificados}"],
                ["", f"Reconocimientos: ¢{pago.costo_reconocimientos}", ""]
            ]
            
            # Filtrar filas vacías para que no aparezcan si los valores son 0 o N/A
            filtered_costos_data = []
            for row in costos_data:
                # Si la primera columna no es vacía, o si alguna de las siguientes columnas tiene un valor distinto de "¢0" o "0"
                # Se ajusta la condición para que '0' como string también se filtre
                if row[0] != "" or any(str(val).strip() not in ["¢0", "0", "N/A", ""] for val in row[1:]):
                    filtered_costos_data.append(row)

            if filtered_costos_data:
                costos_table = Table(filtered_costos_data, colWidths=[2*inch, 2.5*inch, 2.5*inch])
                costos_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('GRID', (0,0), (-1,-1), 0.25, colors.white),
                    ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                ]))
                elements.append(costos_table)
            else:
                elements.append(Paragraph("No hay costos detallados registrados.", style_body))

            elements.append(Spacer(1, 0.1 * inch)) # Pequeño espacio

            elements.append(Paragraph(f"<b>TOTAL BRUTO INDIVIDUAL:</b> ¢{pago.total_bruto_individual}", style_total))
            elements.append(Paragraph(f"<b>TOTAL BRUTO GENERAL COLONES:</b> ¢{pago.total_bruto_general_colones}", style_total))
            elements.append(Paragraph(f"<b>TOTAL BRUTO GENERAL DÓLAR:</b> ${pago.total_bruto_general_dolar}", style_total))
            elements.append(Paragraph(f"<b>TOTAL GANANCIA P.P:</b> ¢{pago.total_ganancia_pp}", style_total))
            elements.append(Paragraph(f"<b>TOTAL GANANCIA GENERAL:</b> ¢{pago.total_ganancia_general}", style_total))

            if pago.nota:
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph(f"<b>Nota:</b> {pago.nota}", style_body))

            elements.append(Spacer(1, 0.5 * inch)) # Espacio entre facturas

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

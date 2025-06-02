# inventario.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DecimalField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional
from datetime import datetime
import io
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

# Importar db y ArticuloInventario desde models.py
# NOTA: ArticuloInventario ahora solo se define en models.py
from models import db, User, ArticuloInventario 

# --- Blueprint para Inventario ---
inventario_bp = Blueprint('inventario_bp', __name__, template_folder='templates')

# --- Formularios WTForms para Inventario ---
class ArticuloInventarioForm(FlaskForm):
    nombre = StringField('Nombre del Artículo', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción', validators=[Optional()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=0)])
    precio_unitario = DecimalField('Precio Unitario', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    submit = SubmitField('Guardar Artículo')

# --- Rutas para Inventario ---

@inventario_bp.route('/ver_inventario')
@login_required
def ver_inventario():
    articulos = ArticuloInventario.query.filter_by(usuario_id=current_user.id).all()
    return render_template('ver_inventario.html', articulos=articulos)

@inventario_bp.route('/agregar_inventario', methods=['GET', 'POST'])
@login_required
def agregar_inventario():
    form = ArticuloInventarioForm()
    if form.validate_on_submit():
        nuevo_articulo = ArticuloInventario(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            cantidad=form.cantidad.data,
            precio_unitario=form.precio_unitario.data,
            usuario_id=current_user.id
        )
        db.session.add(nuevo_articulo)
        db.session.commit()
        flash('Artículo agregado exitosamente!', 'success')
        return redirect(url_for('inventario_bp.ver_inventario'))
    return render_template('agregar_inventario.html', form=form)

@inventario_bp.route('/editar_inventario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_inventario(id):
    articulo = ArticuloInventario.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    form = ArticuloInventarioForm(obj=articulo)
    if form.validate_on_submit():
        form.populate_obj(articulo)
        db.session.commit()
        flash('Artículo actualizado exitosamente!', 'success')
        return redirect(url_for('inventario_bp.ver_inventario'))
    return render_template('editar_inventarios.html', form=form, articulo=articulo)

@inventario_bp.route('/borrar_inventario/<int:id>', methods=['POST'])
@login_required
def borrar_inventario(id):
    articulo = ArticuloInventario.query.filter_by(id=id, usuario_id=current_user.id).first_or_404()
    if articulo:
        db.session.delete(articulo)
        db.session.commit()
        flash('Artículo borrado exitosamente!', 'success')
    else:
        flash('Error al intentar borrar el artículo.', 'danger')
    return redirect(url_for('inventario_bp.ver_inventario'))

@inventario_bp.route('/exportar_inventario_pdf')
@login_required
def exportar_inventario_pdf():
    articulos = ArticuloInventario.query.filter_by(usuario_id=current_user.id).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    data_style = ParagraphStyle(
        'DataStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        alignment=TA_LEFT
    )

    elements = []
    elements.append(Paragraph("Reporte de Inventario", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    data = [
        [
            Paragraph("Nombre", header_style),
            Paragraph("Descripción", header_style),
            Paragraph("Cantidad", header_style),
            Paragraph("Precio Unitario", header_style)
        ]
    ]
    for articulo in articulos:
        data.append([
            Paragraph(articulo.nombre, data_style),
            Paragraph(articulo.descripcion if articulo.descripcion else '', data_style),
            Paragraph(str(articulo.cantidad), data_style),
            Paragraph(f"${articulo.precio_unitario:.2f}", data_style)
        ])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])

    table = Table(data, colWidths=[2 * inch, 3 * inch, 1 * inch, 1 * inch])
    table.setStyle(table_style)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='reporte_inventario.pdf'
    )

@inventario_bp.route('/exportar_inventario_excel')
@login_required
def exportar_inventario_excel():
    articulos = ArticuloInventario.query.filter_by(usuario_id=current_user.id).all()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Inventario"

    headers = ["ID", "Nombre", "Descripción", "Cantidad", "Precio Unitario", "Fecha Registro"]
    sheet.append(headers)

    for articulo in articulos:
        sheet.append([
            articulo.id,
            articulo.nombre,
            articulo.descripcion,
            articulo.cantidad,
            float(articulo.precio_unitario),
            articulo.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
        ])

    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        sheet.column_dimensions[column].width = adjusted_width

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='reporte_inventario.xlsx'
    )

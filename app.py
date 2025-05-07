from flask import Flask, render_template, redirect, url_for, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."


def is_authenticated(self):
    return True

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

@app.route('/')
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=3030)
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración de Flask
app = Flask(__name__)

app.secret_key = os.urandom(24)  # Para manejo de sesiones

# Conexión a la base de datos MySQL
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',  # Son valores de default pero si tienen algo diferente cambienlo
        password='root',  # Son valores de default pero si tienen algo diferente cambienlo
        database='DB_conFIA'
    )

#Ruta de la página principal
@app.route('/')
def index():
    return render_template('index.html')


# Página de Registro de Personal
@app.route('/registrarPersonal', methods=['GET', 'POST'])
def registroP():
    if request.method == 'POST':
        nombre_Personal = request.form['nombre_Personal']
        correo_Personal = request.form['correo_Personal']
        contrasena1_Personal = request.form['contrasena1_Personal']
        contrasena2_Personal = request.form['contrasena2_Personal']

        # Verificar si las contraseñas coinciden
        if contrasena1_Personal != contrasena2_Personal:
            flash('Las contraseñas no coinciden. Intenta de nuevo.', 'danger')
            return render_template('registrarPersonal.html')  # Volver a cargar el formulario con el mensaje de error

        # Hashear la contraseña
        contrasena_hash = generate_password_hash(contrasena1_Personal)

        # Guardar el usuario en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Usuario (email, nombre, contrasena, tipo) VALUES (%s, %s, %s, %s)",
                       (correo_Personal, nombre_Personal, contrasena_hash, 'Personal'))
        
        cursor.execute("INSERT INTO Personal (email) VALUES (%s)", (correo_Personal,))  

        conn.commit()
        cursor.close()
        conn.close()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('inicio_sesion'))

    return render_template('registrarPersonal.html')


# Página de Registro de Empresarial
@app.route('/registrarEmpresarial', methods=['GET', 'POST'])
def registroE():
    if request.method == 'POST':
        nombre_Empresa = request.form['nombre_Empresa']
        direc_Empresa = request.form['direc_Empresa']
        correo_Empresa = request.form['correo_Empresa']
        descrip_Empresa = request.form['descrip_Empresa']
        contrasena1_Empresa = request.form['contrasena1_Empresa']
        contrasena2_Empresa = request.form['contrasena2_Empresa']

        # Verificar si las contraseñas coinciden
        if contrasena1_Empresa != contrasena2_Empresa:
            flash('Las contraseñas no coinciden. Intenta de nuevo.', 'danger')
            return render_template('registrarEmpresarial.html')  # Volver a cargar el formulario con el mensaje de error

        # Hashear la contraseña
        contrasena_hash = generate_password_hash(contrasena1_Empresa)

        # Guardar el usuario en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Usuario (email, nombre, contrasena, tipo) VALUES (%s, %s, %s, %s)",
                       (correo_Empresa, nombre_Empresa, contrasena_hash, 'Empresarial'))
        
        cursor.execute("INSERT INTO Empresarial (email, direccion, descripcion) VALUES (%s, %s, %s)", 
                       (correo_Empresa, direc_Empresa, descrip_Empresa,))  

        conn.commit()
        cursor.close()
        conn.close()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('inicio_sesion'))

    return render_template('registrarEmpresarial.html')


# Página de Inicio de Sesión
@app.route('/inicio_sesion', methods=['GET', 'POST'])
def inicio_sesion():
    if request.method == 'POST':
        email_Usuario = request.form['email_Usuario']
        contrasena_Usuario = request.form['contrasena_Usuario']

        # Verificar usuario y contraseña
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuario WHERE email = %s", (email_Usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            print("Contraseña en base de datos:", user[2])  # Imprime la contraseña cifrada de la base de datos
            print("Contraseña proporcionada:", contrasena_Usuario)  # Imprime la contraseña que el usuario ingresa

            # Verifica si la contraseña cifrada y la proporcionada coinciden
            if check_password_hash(user[2], contrasena_Usuario):
                session['email_Usuario'] = user[0]  # Guardamos el correo del usuario en la sesión
                session['nombre'] = user[1]  # Guardamos el nombre de usuario en la sesión
                session['tipo'] = user[3]  # Guardamos el tipo de usuario en la sesión
                print("Sesión iniciada con éxito. Redirigiendo a indexCorrespondiente.")
                if session['tipo'] == 'Personal':
                    return redirect(url_for('perfilP'))  # Redirige a la página de perfil
                else:
                    return redirect(url_for('perfilE'))  # Redirige a la página de empresa
            else:
                print("Contraseña incorrecta.")
                flash('Usuario o contraseña incorrectos', 'danger')
        else:
            print("Usuario no encontrado en la base de datos.")

    return render_template('IniciarSesion.html')

# Página de Registro de Usuarios
@app.route('/registroUsuarios')
def registroUsuarios():
    return render_template('RegistrarUsuario.html')

# Página de index Personal
@app.route('/indexPersonal')
def perfilP():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    # Obtener los datos del usuario desde la base de datos utilizando el id en la sesión
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, nombre, contrasena, tipo FROM Usuario WHERE email = %s", (session['email_Usuario'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user[3] != 'Personal':
        flash('No tienes permiso para acceder a esta página.', 'danger')
        return redirect(url_for('error'))

    # Pasamos los datos del usuario al template 'indexCUPersonal.html'
    return render_template('indexCUPersonal.html', email_Usuario=user)

# Página de index Empresarial
@app.route('/indexEmpresarial')
def perfilE():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    # Obtener los datos del usuario desde la base de datos utilizando el id en la sesión
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, nombre, contrasena, tipo FROM Usuario WHERE email = %s", (session['email_Usuario'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user[3] != 'Empresarial':
        flash('No tienes permiso para acceder a esta página.', 'danger')
        return redirect(url_for('error'))

    # Pasamos los datos del usuario al template 'indexEmpresarial.html'
    return render_template('indexEmpresarial.html', email_Usuario=user)

# Página de recuperación de contraseña
@app.route('/recuperarContrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        email_Usuario = request.form['email_Usuario']

        # Verificar si el usuario existe
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuario WHERE email = %s", (email_Usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # Enviar un correo con un link para restablecer la contraseña
            flash('Se ha enviado un correo con instrucciones para restablecer tu contraseña.', 'success')
            return redirect(url_for('inicio_sesion'))
        else:
            flash('Usuario no encontrado', 'danger')

    return render_template('RecuperarContrasenia.html')


# Página de Error 
@app.route('/error')
def error():
    return render_template('errorTemplate.html')


if __name__ == '__main__':
    app.run(debug=True)
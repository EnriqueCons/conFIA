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

# Página de Registro de Personal
@app.route('/registrarPersonal', methods=['GET', 'POST'])
def registro():
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
        return redirect(url_for('registro'))

    return render_template('registrarPersonal.html')


if __name__ == '__main__':
    app.run(debug=True)
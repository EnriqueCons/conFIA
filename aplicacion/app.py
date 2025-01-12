import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import numpy as np
from numpy.linalg import norm
import qrcode
import json
from io import BytesIO
from PIL import Image
import re
from deepface import DeepFace
import base64
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# Configuración de Flask
app = Flask(__name__)

app.secret_key = os.urandom(24)  # Para manejo de sesiones

# Configuración de carpetas para guardar imágenes
UPLOAD_FOLDER = 'static/eventos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Conexión a la base de datos MySQL
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',  # Son valores de default pero si tienen algo diferente cambienlo
        password='root',  # Son valores de default pero si tienen algo diferente cambienlo
        database='DB_conFIA',
        ssl_disabled=True
    )

#Comprobar si el usuario está autenticado
def verificar_tipo_usuario(tipo_requerido):
    def decorador(f):
        @wraps(f)
        def verificacion(*args, **kwargs):
            if 'tipo' not in session or session['tipo'] != tipo_requerido:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('error'))
            return f(*args, **kwargs)
        return verificacion
    return decorador

#Ruta de la página principal
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == "POST":
            # Manejo de búsqueda
            search = request.form['buscar']
            cursor.execute("""
                SELECT 
                    E.id,
                    E.nombre AS eventoNombre, 
                    E.descripcion, 
                    E.fechaHora, 
                    E.imagen AS eventoImagen, 
                    E.creadorEmail AS creadorEmail,
                    U.nombre AS creadorNombre
                FROM Evento E
                JOIN Usuario U ON E.creadorEmail = U.email
                WHERE E.nombre LIKE %s
                ORDER BY E.fechaHora DESC
            """, (f"%{search}%",))
            eventos = cursor.fetchall()
        else:
            # Obtener todos los eventos si no hay búsqueda
            cursor.execute("""
                SELECT 
                    E.id,
                    E.nombre AS eventoNombre, 
                    E.descripcion, 
                    E.fechaHora, 
                    E.imagen AS eventoImagen, 
                    E.creadorEmail AS creadorEmail,
                    U.nombre AS creadorNombre
                FROM Evento E
                JOIN Usuario U ON E.creadorEmail = U.email
                ORDER BY E.fechaHora DESC
            """)
            eventos = cursor.fetchall()

        # Construir rutas de imágenes basadas en la estructura de carpetas
        for evento in eventos:
            evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
            evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"
    finally:
        cursor.close()
        conn.close()

    # Renderizar plantilla según si es búsqueda o no
    if request.method == "POST":
        return render_template('resultadoBusqueda.html', eventos=eventos, busqueda=search)
    return render_template('index.html', eventos=eventos)




#-----------------------------------------------------------Registro de Usuarios-----------------------------------------------------------

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

#-----------------------------------------------------------Inicio de Sesión-----------------------------------------------------------

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
                    return redirect(url_for('indexP'))  # Redirige a la página de perfil
                else:
                    return redirect(url_for('indexE'))  # Redirige a la página de empresa
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

#-----------------------------------------------------------Páginas Index-----------------------------------------------------------

# Página de index Personal
@app.route('/indexPersonal', methods=['GET', 'POST'])
@verificar_tipo_usuario('Personal')
def indexP():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == "POST":
            # Manejo de búsqueda
            search = request.form.get('buscar', '').strip()  # Obtener el término de búsqueda
            cursor.execute("""
                SELECT 
                    E.id AS id,
                    E.nombre AS eventoNombre,
                    E.descripcion,
                    E.fechaHora,
                    E.imagen AS eventoImagen,
                    E.creadorEmail AS creadorEmail,
                    U.nombre AS creadorNombre,
                    EXISTS(
                        SELECT 1 
                        FROM Inscripcion I 
                        WHERE I.evento_id = E.id AND I.usuario_email = %s
                    ) AS inscrito
                FROM Evento E
                JOIN Usuario U ON E.creadorEmail = U.email
                WHERE E.nombre LIKE %s
                ORDER BY E.fechaHora DESC
            """, (session['email_Usuario'], f"%{search}%"))
            eventos = cursor.fetchall()
        else:
            # Obtener todos los eventos si no hay búsqueda
            cursor.execute("""
                SELECT 
                    E.id AS id,
                    E.nombre AS eventoNombre,
                    E.descripcion,
                    E.fechaHora,
                    E.imagen AS eventoImagen,
                    E.creadorEmail AS creadorEmail,
                    U.nombre AS creadorNombre,
                    EXISTS(
                        SELECT 1 
                        FROM Inscripcion I 
                        WHERE I.evento_id = E.id AND I.usuario_email = %s
                    ) AS inscrito
                FROM Evento E
                JOIN Usuario U ON E.creadorEmail = U.email
                ORDER BY E.fechaHora DESC
            """, (session['email_Usuario'],))
            eventos = cursor.fetchall()

        # Construir rutas de imágenes
        for evento in eventos:
            evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
            evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"
    finally:
        cursor.close()
        conn.close()

    # Renderizar plantilla según si es búsqueda o no
    if request.method == "POST":
        return render_template('resultadoBusquedaP.html', eventos=eventos, busqueda=search)
    return render_template('indexCUPersonal.html', eventos=eventos)

@app.route('/indexEmpresarial', methods=['GET', 'POST'])
@verificar_tipo_usuario('Empresarial')
def indexE():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener los datos del usuario empresarial
        cursor.execute("""
            SELECT email, nombre, tipo 
            FROM Usuario 
            WHERE email = %s
        """, (session['email_Usuario'],))
        user = cursor.fetchone()

        # Manejo de búsqueda
        if request.method == "POST":
            search = request.form.get('buscar', '').strip()
            cursor.execute("""
                SELECT 
                    E.id AS id,
                    E.nombre AS eventoNombre, 
                    E.descripcion, 
                    E.fechaHora, 
                    E.imagen AS eventoImagen, 
                    E.creadorEmail AS creadorEmail,
                    U.nombre AS creadorNombre
                FROM Evento E
                JOIN Usuario U ON E.creadorEmail = U.email
                WHERE E.nombre LIKE %s
                ORDER BY E.fechaHora DESC
            """, (f"%{search}%",))
            eventos = cursor.fetchall()
        else:
            # Obtener todos los eventos (sin filtrar por creador)
            cursor.execute("""
                SELECT 
                    E.id AS id,
                    E.nombre AS eventoNombre, 
                    E.descripcion, 
                    E.fechaHora, 
                    E.imagen AS eventoImagen, 
                    E.creadorEmail AS creadorEmail,
                    U.nombre AS creadorNombre
                FROM Evento E
                JOIN Usuario U ON E.creadorEmail = U.email
                ORDER BY E.fechaHora DESC
            """)
            eventos = cursor.fetchall()

        # Construir rutas de imágenes
        for evento in eventos:
            evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
            evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"
    finally:
        cursor.close()
        conn.close()

    # Renderizar la plantilla correspondiente
    if request.method == "POST":
        return render_template('resultadoBusquedaE.html', eventos=eventos, busqueda=search)
    return render_template('indexCUEmpresarial.html', email_Usuario=user, eventos=eventos)



#-----------------------------------------------------------Ver más...-----------------------------------------------------------
#ver Más sin Perfil
@app.route('/verMas/<int:evento_id>')
def verMasSP(evento_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            E.id, 
            E.nombre AS eventoNombre, 
            E.descripcion, 
            E.fechaHora, 
            E.aforoMax, 
            E.tipoAcceso, 
            E.imagen, 
            E.creadorEmail,
            E.ubicacion,
            U.nombre AS creadorNombre
        FROM Evento E
        JOIN Usuario U ON E.creadorEmail = U.email
        WHERE E.id = %s
    """,(evento_id,))
    evento = cursor.fetchone()
    cursor.close()
    conn.close()


    # Si no hay eventos, retorna un mensaje
    if not evento:
        return "No hay eventos disponibles."

    # Construir rutas de imágenes basadas en la estructura de carpetas
    
    evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
    evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"

    if evento['tipoAcceso'] == 'QR':
        return render_template('InformacionEventoQR.html', evento=evento)
    elif evento['tipoAcceso'] == 'Reconocimiento Facial':
        return render_template('InformacionEventoRF.html', evento=evento)
    else:
        return "El tipo de acceso no está definido para este evento.", 400

#Ver más Personal
@app.route('/verMasP/<int:evento_id>')
def verMasPersonal(evento_id):
    # Verificar si el usuario ha iniciado sesión
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Consulta para obtener la información del evento con inscripción
    cursor.execute("""
        SELECT 
            E.id AS id,
            E.nombre AS eventoNombre,
            E.descripcion,
            E.fechaHora,
            E.tipoAcceso,
            E.ubicacion,
            E.aforoMax,
            E.imagen AS eventoImagen,
            E.creadorEmail AS creadorEmail,
            U.nombre AS creadorNombre,
            EXISTS(
                SELECT 1 
                FROM Inscripcion I 
                WHERE I.evento_id = E.id AND I.usuario_email = %s
            ) AS inscrito
        FROM Evento E
        JOIN Usuario U ON E.creadorEmail = U.email
        WHERE E.id = %s
        ORDER BY E.fechaHora DESC
    """, (session['email_Usuario'], evento_id))
    evento = cursor.fetchone()
    cursor.close()
    conn.close()

    # Validar si se encontró el evento
    if not evento:
        return "Evento no encontrado.", 404

    # Construir rutas de imágenes
    evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
    evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"

    # Renderizar la plantilla correspondiente
    if evento['tipoAcceso'] == 'QR':
        return render_template('InformacionEventoPersonalQR.html', evento=evento)
    elif evento['tipoAcceso'] == 'Reconocimiento Facial':
        return render_template('InformacionEventoPersonalRF.html', evento=evento)
    else:
        return "El tipo de acceso no está definido para este evento.", 400

#ver Más Empresarial
@app.route('/verMasE/<int:evento_id>')
def verMasEmpresa(evento_id):
    # Verificar si el usuario ha iniciado sesión
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Consulta para obtener la información del evento con inscripción
    cursor.execute("""
        SELECT 
            E.id AS id,
            E.nombre AS eventoNombre,
            E.descripcion,
            E.fechaHora,
            E.tipoAcceso,
            E.ubicacion,
            E.aforoMax,
            E.imagen AS eventoImagen,
            E.creadorEmail AS creadorEmail,
            U.nombre AS creadorNombre,
            EXISTS(
                SELECT 1 
                FROM Inscripcion I 
                WHERE I.evento_id = E.id AND I.usuario_email = %s
            ) AS inscrito
        FROM Evento E
        JOIN Usuario U ON E.creadorEmail = U.email
        WHERE E.id = %s
        ORDER BY E.fechaHora DESC
    """, (session['email_Usuario'], evento_id))
    evento = cursor.fetchone()
    cursor.close()
    conn.close()

    # Validar si se encontró el evento
    if not evento:
        return "Evento no encontrado.", 404

    # Construir rutas de imágenes
    evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
    evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"

    # Renderizar la plantilla correspondiente
    if evento['tipoAcceso'] == 'QR':
        return render_template('InformacionEventoEmpresaQR.html', evento=evento)
    elif evento['tipoAcceso'] == 'Reconocimiento Facial':
        return render_template('InformacionEventoEmpresaRF.html', evento=evento)
    else:
        return "El tipo de acceso no está definido para este evento.", 400


#-----------------------------------------------------------Perfil de Usuario-----------------------------------------------------------

# Página para ver el perfil de usuario
@app.route('/perfilUsuario')
def perfilUsuario():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, nombre, imagen FROM Usuario WHERE email = %s", (session['email_Usuario'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('error'))

    # Pasa la ruta completa de la imagen al template
    return render_template('perfilPersonal.html', usuario={
        'email': user[0],
        'nombre': user[1],
        'imagen': user[2] or 'static/uploads/default-profile.png'  # Ruta predeterminada si no hay imagen
    })
@verificar_tipo_usuario('Personal')

#Actualizar datos de usuario
@app.route('/actualizar_datosUsu', methods=['POST'])
def actualizar_datosUsu():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    correo_actual = session['email_Usuario']
    nuevo_nombre = request.form.get('nombre')
    nueva_contrasena = request.form.get('password')
    archivo_imagen = request.files.get('imagen')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Actualizar el nombre en la base de datos
        if nuevo_nombre and nuevo_nombre != session['nombre']:
            cursor.execute("UPDATE Usuario SET nombre = %s WHERE email = %s", (nuevo_nombre, correo_actual))
            session['nombre'] = nuevo_nombre  # Actualizar la sesión con el nuevo nombre
            print(f"Nombre actualizado en sesión: {session['nombre']}")

        # Actualizar la contraseña si se proporciona una nueva
        if nueva_contrasena:
            nueva_contrasena_hash = generate_password_hash(nueva_contrasena)
            cursor.execute("UPDATE Usuario SET contrasena = %s WHERE email = %s",
                           (nueva_contrasena_hash, correo_actual))

        # Guardar la imagen si se proporciona
        if archivo_imagen:
            ruta_imagen = f'static/uploads/{correo_actual}.png'
            archivo_imagen.save(ruta_imagen)
            cursor.execute("UPDATE Usuario SET imagen = %s WHERE email = %s", (ruta_imagen, correo_actual))

        conn.commit()
        flash('Datos actualizados correctamente.', 'success')
    except Exception as e:
        conn.rollback()
        print(f"Error al actualizar los datos: {str(e)}")
        flash(f'Error al actualizar los datos: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('perfilUsuario'))
@verificar_tipo_usuario('Personal')

#-----------------------------------------------------------Perfil de Empresa-----------------------------------------------------------

#Pagina para ver el perfil de la empresa desde el prefil de la empresa
@app.route('/perfilEmpresa')
def perfilEmpresa():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.email, u.nombre, u.imagen, e.direccion, e.descripcion
        FROM Usuario u
        LEFT JOIN Empresarial e ON u.email = e.email
        WHERE u.email = %s
    """, (session['email_Usuario'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('error'))

    # Pasa todos los datos al template
    return render_template('PerfilEmpresa.html', usuario={
        'email': user[0],
        'nombre': user[1],
        'imagen': user[2] or 'static/uploads/default-profile.png',
        'direccion': user[3] or '',
        'descripcion': user[4] or ''
    })
@verificar_tipo_usuario('Empresarial')

#Actualizar datos de empresa
@app.route('/actualizar_datosEmp', methods=['POST'])
def actualizar_datosEmp():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    correo_actual = session['email_Usuario']
    nuevo_nombre = request.form.get('nombre')
    nueva_direccion = request.form.get('direccion')
    nueva_descripcion = request.form.get('descripcion')
    nueva_contrasena = request.form.get('password')
    archivo_imagen = request.files.get('imagen')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Actualizar el nombre en la base de datos
        if nuevo_nombre and nuevo_nombre != session.get('nombre', ''):
            cursor.execute("UPDATE Usuario SET nombre = %s WHERE email = %s", (nuevo_nombre, correo_actual))
            session['nombre'] = nuevo_nombre  # Actualizar la sesión con el nuevo nombre

        # Actualizar la dirección
        if nueva_direccion:
            cursor.execute("UPDATE Empresarial SET direccion = %s WHERE email = %s", (nueva_direccion, correo_actual))
        
        # Actualizar la descripción
        if nueva_descripcion:
            cursor.execute("UPDATE Empresarial SET descripcion = %s WHERE email = %s", (nueva_descripcion, correo_actual))

        # Actualizar la contraseña si se proporciona una nueva
        if nueva_contrasena:
            nueva_contrasena_hash = generate_password_hash(nueva_contrasena)
            cursor.execute("UPDATE Usuario SET contrasena = %s WHERE email = %s",
                           (nueva_contrasena_hash, correo_actual))

        # Guardar la imagen si se proporciona
        if archivo_imagen:
            ruta_imagen = f'static/uploads/{correo_actual}.png'
            archivo_imagen.save(ruta_imagen)
            cursor.execute("UPDATE Usuario SET imagen = %s WHERE email = %s", (ruta_imagen, correo_actual))

        conn.commit()
        flash('Datos actualizados correctamente.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al actualizar los datos: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('perfilEmpresa'))
@verificar_tipo_usuario('Empresarial')

#Ver perfil de empresa desde el perfil de personal
@app.route('/verPerfilEmpresa/<string:email>')
@verificar_tipo_usuario('Personal')  # Ajustado para que funcione para usuarios personales que ven perfiles empresariales
def verPerfilEmpresa(email):
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener información de la empresa
        cursor.execute("""
            SELECT u.email, u.nombre, u.imagen, e.direccion, e.descripcion
            FROM Usuario u
            LEFT JOIN Empresarial e ON u.email = e.email
            WHERE u.email = %s
        """, (email,))
        empresa = cursor.fetchone()

        if not empresa:
            flash('La empresa no fue encontrada.', 'danger')
            return redirect(url_for('error'))

        # Ajustar la ruta de la imagen de la empresa
        empresa['imagen'] = f"uploads/{empresa['email']}.png" if empresa['imagen'] else "uploads/default-profile.png"

        # Obtener eventos publicados por la empresa, con información de inscripción
        cursor.execute("""
            SELECT 
                E.id AS id,
                E.nombre AS eventoNombre,
                E.descripcion,
                E.fechaHora,
                E.aforoMax,
                E.tipoAcceso,
                E.ubicacion,
                E.imagen AS eventoImagen,
                EXISTS(
                    SELECT 1 
                    FROM Inscripcion I 
                    WHERE I.evento_id = E.id AND I.usuario_email = %s
                ) AS inscrito
            FROM Evento E
            WHERE E.creadorEmail = %s
            ORDER BY E.fechaHora DESC
        """, (session['email_Usuario'], email))
        eventos = cursor.fetchall()

        # Ajustar las rutas de las imágenes de los eventos
        for evento in eventos:
            if evento['eventoImagen']:
                # Si la ruta ya incluye "static/", quítala para evitar duplicados
                evento['eventoImagen'] = evento['eventoImagen'].replace("static/", "")
            else:
                # Imagen predeterminada para eventos sin imagen
                evento['eventoImagen'] = "eventos/default-event.png"

    except Exception as e:
        flash(f"Error al cargar la información: {e}", 'danger')
        return redirect(url_for('error'))
    finally:
        cursor.close()
        conn.close()

    # Pasar la información al template
    return render_template('verPerfilEmpresa.html', empresa=empresa, eventos=eventos)


#-----------------------------------------------------------Eventos Empresa-----------------------------------------------------------
#Ver eventos de la empresa
@app.route('/eventosEmpresa')
def eventosEmpresa():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Retorna los resultados como diccionarios
    cursor.execute("""
        SELECT id, nombre, descripcion, fechaHora, aforoMax, tipoAcceso, imagen 
        FROM Evento 
        WHERE creadorEmail = %s
    """, (session['email_Usuario'],))
    eventos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('verEventosEmpresa.html', eventos=eventos)
@verificar_tipo_usuario('Empresarial')

#Crear un evento
@app.route('/crearEvento', methods=['GET', 'POST'])
def crearEvento():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre_evento = request.form['nombre']
        descripcion = request.form['descripcion']
        fecha_hora = request.form['fecha_hora']
        aforo_max = request.form['aforo_max']
        tipo_acceso = request.form['tipo_acceso']
        ubicacion = request.form['ubicacion']
        organizador = session['nombre']

        # Manejo de la imagen
        imagen = request.files['imagen']
        if imagen:
            correo_usuario = session['email_Usuario']
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], correo_usuario)
            os.makedirs(user_folder, exist_ok=True)
            filename = secure_filename(f"{nombre_evento}.png")
            image_path = os.path.join(user_folder, filename)
            imagen.save(image_path)

        # Guardar en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Crear el evento en la base de datos
            cursor.execute("""
                INSERT INTO Evento (nombre, descripcion, fechaHora, aforoMax, tipoAcceso, creadorEmail, ubicacion, imagen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre_evento, descripcion, fecha_hora, aforo_max, tipo_acceso, session['email_Usuario'], ubicacion, image_path))
            conn.commit()

            # Crear una notificación para el creador
            crear_notificacion(
                session['email_Usuario'],
                f"Has creado el evento '{nombre_evento}'",
                cursor.lastrowid
            )

            flash('Evento creado exitosamente.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al crear el evento: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('eventosEmpresa'))

    return render_template('CrearEvento.html')
@verificar_tipo_usuario('Empresarial')


#Eliminar un evento
@app.route('/eliminarEvento/<int:evento_id>', methods=['POST'])
@verificar_tipo_usuario('Empresarial')
def eliminar_evento(evento_id):
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Verifica que el evento pertenece al usuario y obtiene el nombre del evento
        cursor.execute("""
            SELECT id, nombre 
            FROM Evento 
            WHERE id = %s AND creadorEmail = %s
        """, (evento_id, session['email_Usuario']))
        evento = cursor.fetchone()

        if not evento:
            flash('No tienes permiso para eliminar este evento o no existe.', 'danger')
            return redirect(url_for('eventosEmpresa'))

        evento_nombre = evento['nombre']

        # Notificar a los usuarios inscritos antes de eliminar el evento
        cursor.execute("""
            SELECT usuario_email 
            FROM Inscripcion 
            WHERE evento_id = %s
        """, (evento_id,))
        inscritos = cursor.fetchall()

        for inscrito in inscritos:
            crear_notificacion(
                inscrito['usuario_email'],
                f"El evento '{evento_nombre}' ha sido cancelado por el organizador.",
                evento_id
            )

        # Crear una notificación para el creador del evento
        crear_notificacion(
            session['email_Usuario'],
            f"Has eliminado el evento '{evento_nombre}'.",
            evento_id
        )

        # Eliminar las inscripciones relacionadas con el evento (si hay claves foráneas)
        cursor.execute("DELETE FROM Inscripcion WHERE evento_id = %s", (evento_id,))

        # Eliminar el evento
        cursor.execute("DELETE FROM Evento WHERE id = %s", (evento_id,))
        conn.commit()

        flash('Evento eliminado correctamente.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al eliminar el evento: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('eventosEmpresa'))


#Editar un evento
@app.route('/editarEvento/<int:evento_id>', methods=['GET', 'POST'])
def editar_evento(evento_id):
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            # Datos del formulario
            nombre_evento = request.form['nombre']
            descripcion = request.form['descripcion']
            fecha_hora = request.form['fecha_hora']
            aforo_max = int(request.form['aforo_max'])
            tipo_acceso = request.form['tipo_acceso']
            ubicacion = request.form['ubicacion']
            imagen = request.files.get('imagen')

            # Consulta para obtener datos actuales del evento
            cursor.execute("SELECT * FROM Evento WHERE id = %s AND creadorEmail = %s", 
                           (evento_id, session['email_Usuario']))
            evento_actual = cursor.fetchone()

            if not evento_actual:
                flash('Evento no encontrado o no tienes permiso para editarlo.', 'danger')
                return redirect(url_for('eventosEmpresa'))

            # Manejo de imagen
            correo_usuario = session['email_Usuario']
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], correo_usuario)
            os.makedirs(user_folder, exist_ok=True)

            # Si se sube una nueva imagen, guarda con el nuevo nombre del evento
            if imagen and imagen.filename != '':
                filename = secure_filename(f"{nombre_evento.replace(' ', '_')}.png")
                image_path = os.path.join(user_folder, filename)
                imagen.save(image_path)
                image_path = image_path.replace("\\", "/")
            else:
                # Si no se sube nueva imagen, renombra el archivo existente
                current_image_path = evento_actual['imagen']
                if current_image_path:
                    old_filename = os.path.basename(current_image_path)
                    new_filename = secure_filename(f"{nombre_evento.replace(' ', '_')}.png")
                    new_image_path = os.path.join(user_folder, new_filename)

                    # Renombrar el archivo solo si el nombre del evento ha cambiado
                    if old_filename != new_filename:
                        os.rename(current_image_path, new_image_path)
                        current_image_path = new_image_path.replace("\\", "/")

                image_path = current_image_path

            # Validación de tipo_acceso
            if tipo_acceso not in ['QR', 'Reconocimiento Facial']:
                raise ValueError("Tipo de acceso no válido.")

            # Actualizar en la base de datos
            cursor.execute("""
                UPDATE Evento
                SET nombre = %s, descripcion = %s, fechaHora = %s, aforoMax = %s, tipoAcceso = %s, ubicacion = %s, imagen = %s
                WHERE id = %s AND creadorEmail = %s
            """, (nombre_evento, descripcion, fecha_hora, aforo_max, tipo_acceso, ubicacion, image_path, evento_id, session['email_Usuario']))

            conn.commit()
            flash('Evento actualizado correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error en la base de datos: {err}', 'danger')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('eventosEmpresa'))

    # Obtener los datos del evento para el formulario
    cursor.execute("SELECT * FROM Evento WHERE id = %s AND creadorEmail = %s", (evento_id, session['email_Usuario']))
    evento = cursor.fetchone()
    cursor.close()
    conn.close()

    if not evento:
        flash('Evento no encontrado o no tienes permiso para editarlo.', 'danger')
        return redirect(url_for('eventosEmpresa'))

    return render_template('EditarEvento.html', evento=evento)

@verificar_tipo_usuario('Empresarial')


#-----------------------------------------------------------Inscribirse a Eventos-----------------------------------------------------------
# Ruta para inscribirse a eventos
@app.route('/inscribirse/<int:evento_id>', methods=['GET'])
def inscribirse(evento_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Incluye `aforoMax` en la consulta para verificar si el evento está lleno
    cursor.execute("SELECT tipoAcceso, aforoMax FROM Evento WHERE id = %s", (evento_id,))
    evento = cursor.fetchone()

    if not evento:
        flash('Evento no encontrado.', 'danger')
        return redirect(url_for('indexP'))

    # Verificar si el evento está lleno
    cursor.execute("""
        SELECT COUNT(*) AS inscritos FROM Inscripcion WHERE evento_id = %s
    """, (evento_id,))
    inscritos = cursor.fetchone()['inscritos']

    if inscritos >= evento['aforoMax']:
        flash('El evento ya ha alcanzado el aforo máximo.', 'danger')
        return redirect(url_for('indexP'))

    tipo_acceso = evento['tipoAcceso']
    if tipo_acceso == "QR":
        return redirect(url_for('inscribirse_qr', evento_id=evento_id))
    elif tipo_acceso == "Reconocimiento Facial":
        return redirect(url_for('inscribirse_rec_facial', evento_id=evento_id))
    else:
        flash('Tipo de acceso desconocido.', 'danger')
        return redirect(url_for('indexP'))



# Ruta para inscribirse a eventos con QR
@app.route('/inscribirse_qr/<int:evento_id>', methods=['GET', 'POST'])
@verificar_tipo_usuario('Personal')
def inscribirse_qr(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Verificar si el evento existe
        cursor.execute("""
            SELECT id, nombre, descripcion, fechaHora, aforoMax, tipoAcceso, ubicacion, creadorEmail 
            FROM Evento 
            WHERE id = %s
        """, (evento_id,))
        evento = cursor.fetchone()

        if not evento:
            flash('El evento no existe.', 'danger')
            return redirect(url_for('indexP'))

        # Obtener el nombre del organizador
        cursor.execute("""
            SELECT Usuario.nombre AS organizador_nombre
            FROM Evento
            LEFT JOIN Empresarial ON Evento.creadorEmail = Empresarial.email
            LEFT JOIN Usuario ON Empresarial.email = Usuario.email
            WHERE Evento.id = %s
        """, (evento_id,))
        organizador = cursor.fetchone()

        organizador_nombre = organizador['organizador_nombre'] if organizador else "Sin organizador"

        # Extraer valores del evento
        nombre = evento['nombre']
        descripcion = evento['descripcion']
        fechaHora = evento['fechaHora']
        aforoMax = evento['aforoMax']
        tipoAcceso = evento['tipoAcceso']
        ubicacion = evento['ubicacion']
        creadorEmail = evento['creadorEmail']

        evento_nombre = nombre.replace(' ', '_') if nombre else "Desconocido"

        # Construir rutas de imágenes
        evento_imagen = f"eventos/{creadorEmail}/{evento_nombre}.png" if creadorEmail else "eventos/default.png"

        # Generar ruta del QR
        qr_data = f"Usuario: {session['nombre']} | Evento: {evento_nombre} | Evento ID: {evento_id}"
        qr_img = qrcode.make(qr_data)

        # Crear la carpeta del usuario si no existe
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['email_Usuario'])
        os.makedirs(user_folder, exist_ok=True)

        qr_filename = f"{evento_nombre}_qr_{evento_id}.png"
        qr_path = os.path.join(user_folder, qr_filename)
        qr_img.save(qr_path)

        # Verificar si ya está inscrito al evento
        cursor.execute("""
            SELECT * FROM Inscripcion 
            WHERE usuario_email = %s AND evento_id = %s
        """, (session['email_Usuario'], evento_id))
        inscripcion = cursor.fetchone()

        if inscripcion:
            flash('Ya estás inscrito a este evento.', 'warning')
            return redirect(url_for('indexP'))

        # Guardar inscripción en la base de datos
        cursor.execute("""
            INSERT INTO Inscripcion (usuario_email, evento_id, qr) 
            VALUES (%s, %s, %s)
        """, (session['email_Usuario'], evento_id, qr_path.replace('static/', '')))
        conn.commit()

        # Crear una notificación
        crear_notificacion(
            session['email_Usuario'],
            f"Te has inscrito al evento '{evento['nombre']}'",
            evento_id
        )


        # Redirigir a la página de confirmación de QR
        return render_template(
            'InformacionEventoPersonalQRInscrito.html',
            evento_nombre=nombre,
            nombre=session['nombre'],
            correo=session['email_Usuario'],
            ubicacion=ubicacion,
            fecha=fechaHora,
            asistentes=aforoMax,  # Número de asistentes (dato de ejemplo)
            acceso=tipoAcceso,
            descripcion=descripcion,
            evento_imagen=evento_imagen,
            qr_path=qr_path.replace('static/', ''),
            organizador_nombre=organizador_nombre
        )

    except Exception as e:
        conn.rollback()
        flash(f"Error al inscribirse al evento: {e}", 'danger')
        return redirect(url_for('indexP'))
    finally:
        cursor.close()
        conn.close()
@verificar_tipo_usuario('Personal')


#Insribirse a eventos con reconocimiento facial
@app.route('/inscribirse_rec_facial/<int:evento_id>', methods=['GET', 'POST'])
@verificar_tipo_usuario('Personal')
def inscribirse_rec_facial(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Verificar si el evento existe
        cursor.execute("""
            SELECT id, nombre, descripcion, fechaHora, aforoMax, tipoAcceso, ubicacion, creadorEmail 
            FROM Evento 
            WHERE id = %s
        """, (evento_id,))
        evento = cursor.fetchone()

        if not evento:
            flash('El evento no existe.', 'danger')
            return redirect(url_for('indexP'))

        # Obtener el nombre del organizador
        cursor.execute("""
            SELECT Usuario.nombre AS organizador_nombre
            FROM Evento
            LEFT JOIN Empresarial ON Evento.creadorEmail = Empresarial.email
            LEFT JOIN Usuario ON Empresarial.email = Usuario.email
            WHERE Evento.id = %s
        """, (evento_id,))
        organizador = cursor.fetchone()

        organizador_nombre = organizador['organizador_nombre'] if organizador else "Sin organizador"

        # Extraer valores del evento
        nombre = evento['nombre']
        descripcion = evento['descripcion']
        fechaHora = evento['fechaHora']
        aforoMax = evento['aforoMax']
        tipoAcceso = evento['tipoAcceso']
        ubicacion = evento['ubicacion']
        creadorEmail = evento['creadorEmail']

        evento_nombre = nombre.replace(' ', '_') if nombre else "Desconocido"

        # Construir rutas de imágenes
        evento_imagen = f"eventos/{creadorEmail}/{evento_nombre}.png" if creadorEmail else "eventos/default.png"

        if request.method == 'POST':
            foto = request.files.get('foto')
            if not foto:
                flash('Debes subir una foto para completar la inscripción.', 'danger')
                return redirect(request.url)

            # Crear la carpeta del usuario si no existe
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['email_Usuario'])
            os.makedirs(user_folder, exist_ok=True)

            # Generar un nombre de archivo único basado en el evento
            foto_filename = f"{evento_nombre}_rostro_{evento_id}.jpg"
            foto_path = os.path.join(user_folder, foto_filename)
            foto.save(foto_path)

            # Generar el encoding facial
            encoding = DeepFace.represent(img_path=foto_path, model_name="Facenet")

            # Verificar si ya está inscrito al evento
            cursor.execute("""
                SELECT * FROM Inscripcion 
                WHERE usuario_email = %s AND evento_id = %s
            """, (session['email_Usuario'], evento_id))
            inscripcion = cursor.fetchone()

            if inscripcion:
                flash('Ya estás inscrito a este evento.', 'warning')
                return redirect(url_for('indexP'))

            # Guardar inscripción en la base de datos
            cursor.execute("""
                INSERT INTO Inscripcion (usuario_email, evento_id, foto, data) 
                VALUES (%s, %s, %s, %s)
            """, (session['email_Usuario'], evento_id, foto_path.replace('static/', ''), str(encoding)))
            conn.commit()

             # Crear una notificación
            crear_notificacion(
                session['email_Usuario'],
                f"Te has inscrito al evento '{evento['nombre']}'",
                evento_id
            )


            # Redirigir a la página de confirmación de reconocimiento facial
            return render_template(
                'InformacionEventoPersonalRFInscrito.html',
                evento_nombre=nombre,
                nombre=session['nombre'],
                correo=session['email_Usuario'],
                ubicacion=ubicacion,
                fecha=fechaHora,
                asistentes=aforoMax,  # Número de asistentes (dato de ejemplo)
                acceso=tipoAcceso,
                descripcion=descripcion,
                evento_imagen=evento_imagen,
                organizador_nombre=organizador_nombre
            )

    except Exception as e:
        conn.rollback()
        flash(f"Error al inscribirse al evento: {e}", 'danger')
        return redirect(url_for('indexP'))

    finally:
        cursor.close()
        conn.close()

    return render_template(
        'InscribirseRecFac.html',
        evento_id=evento_id,
        organizador_nombre=organizador_nombre
    )
@verificar_tipo_usuario('Personal')

#-----------------------------------------------------------Inscrito a Eventos-----------------------------------------------------------

@app.route('/inscrito/<int:evento_id>', methods=['GET', 'POST'])
def inscrito(evento_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT tipoAcceso FROM Evento WHERE id = %s", (evento_id,))
        evento = cursor.fetchone()

        if not evento:
            flash('Evento no encontrado.', 'danger')
            return redirect(url_for('indexP'))

        tipo_acceso = evento['tipoAcceso']
        if tipo_acceso == "QR":
            return redirect(url_for('inscrito_qr', evento_id=evento_id))
        elif tipo_acceso == "Reconocimiento Facial":
            return redirect(url_for('inscrito_rec_facial', evento_id=evento_id))
        else:
            flash('Tipo de acceso desconocido.', 'danger')
            return redirect(url_for('indexP'))

    except Exception as e:
        flash(f"Error al procesar el evento: {e}", 'danger')
        return redirect(url_for('indexP'))
    finally:
        cursor.close()
        conn.close()

@app.route('/inscritoQR/<int:evento_id>', methods=['GET', 'POST'])
def inscrito_qr(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Verificar si ya está inscrito al evento
        cursor.execute("""
            SELECT qr FROM Inscripcion 
            WHERE usuario_email = %s AND evento_id = %s
        """, (session['email_Usuario'], evento_id))
        inscripcion = cursor.fetchone()

        if not inscripcion:
            flash('No estás inscrito a este evento.', 'warning')
            return redirect(url_for('indexP'))

        qr_path = inscripcion['qr']  # Usa la ruta directamente

        # Verificar si el evento existe
        cursor.execute("""
            SELECT id, nombre, descripcion, fechaHora, aforoMax, tipoAcceso, ubicacion, creadorEmail 
            FROM Evento 
            WHERE id = %s
        """, (evento_id,))
        evento = cursor.fetchone()

        if not evento:
            flash('El evento no existe.', 'danger')
            return redirect(url_for('indexP'))

        # Obtener el nombre del organizador
        cursor.execute("""
            SELECT Usuario.nombre AS organizador_nombre
            FROM Evento
            LEFT JOIN Empresarial ON Evento.creadorEmail = Empresarial.email
            LEFT JOIN Usuario ON Empresarial.email = Usuario.email
            WHERE Evento.id = %s
        """, (evento_id,))
        organizador = cursor.fetchone()

        organizador_nombre = organizador['organizador_nombre'] if organizador else "Sin organizador"

        # Extraer valores del evento
        nombre = evento['nombre']
        descripcion = evento['descripcion']
        fechaHora = evento['fechaHora']
        aforoMax = evento['aforoMax']
        tipoAcceso = evento['tipoAcceso']
        ubicacion = evento['ubicacion']
        creadorEmail = evento['creadorEmail']

        evento_nombre = nombre.replace(' ', '_') if nombre else "Desconocido"

        # Construir rutas de imágenes
        evento_imagen = f"static/eventos/{creadorEmail}/{evento_nombre}.png" if creadorEmail else "static/eventos/default.png"

        # Renderizar la página de confirmación
        return render_template(
            'InformacionEventoPersonalQRInscrito.html',
            evento_nombre=nombre,
            nombre=session['nombre'],
            correo=session['email_Usuario'],
            ubicacion=ubicacion,
            fecha=fechaHora,
            asistentes=aforoMax,  # Número de asistentes (dato de ejemplo)
            acceso=tipoAcceso,
            descripcion=descripcion,
            evento_imagen=evento_imagen,
            qr_path=qr_path.replace('static/', ''),
            organizador_nombre=organizador_nombre
        )

    except Exception as e:
        flash(f"Error al acceder al evento: {e}", 'danger')
        return redirect(url_for('indexP'))
    finally:
        cursor.close()
        conn.close()
@verificar_tipo_usuario('Personal')

#inscrito RecFac
@app.route('/inscritoRF/<int:evento_id>', methods=['GET', 'POST'])
def inscrito_rec_facial(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Verificar si ya está inscrito al evento
        cursor.execute("""
            SELECT * FROM Inscripcion 
            WHERE usuario_email = %s AND evento_id = %s
        """, (session['email_Usuario'], evento_id))
        inscripcion = cursor.fetchone()

        if not inscripcion:
            flash('No estás inscrito a este evento.', 'warning')
            return redirect(url_for('indexP'))

        # Verificar si el evento existe
        cursor.execute("""
            SELECT id, nombre, descripcion, fechaHora, aforoMax, tipoAcceso, ubicacion, creadorEmail 
            FROM Evento 
            WHERE id = %s
        """, (evento_id,))
        evento = cursor.fetchone()

        if not evento:
            flash('El evento no existe.', 'danger')
            return redirect(url_for('indexP'))
        
         # Obtener el nombre del organizador
        cursor.execute("""
            SELECT Usuario.nombre AS organizador_nombre
            FROM Evento
            LEFT JOIN Empresarial ON Evento.creadorEmail = Empresarial.email
            LEFT JOIN Usuario ON Empresarial.email = Usuario.email
            WHERE Evento.id = %s
        """, (evento_id,))
        organizador = cursor.fetchone()

        organizador_nombre = organizador['organizador_nombre'] if organizador else "Sin organizador"

        # Extraer valores del evento
        nombre = evento['nombre']
        descripcion = evento['descripcion']
        fechaHora = evento['fechaHora']
        aforoMax = evento['aforoMax']
        tipoAcceso = evento['tipoAcceso']
        ubicacion = evento['ubicacion']
        creadorEmail = evento['creadorEmail']

        evento_nombre = nombre.replace(' ', '_') if nombre else "Desconocido"

        # Construir rutas de imágenes
        evento_imagen = f"static/eventos/{creadorEmail}/{evento_nombre}.png" if creadorEmail else "static/eventos/default.png"

        # Renderizar la página de confirmación
        return render_template(
            'InformacionEventoPersonalRFInscrito.html',
            evento_nombre=nombre,
            nombre=session['nombre'],
            correo=session['email_Usuario'],
            ubicacion=ubicacion,
            fecha=fechaHora,
            asistentes=aforoMax,  # Número de asistentes (dato de ejemplo)
            acceso=tipoAcceso,
            descripcion=descripcion,
            evento_imagen=evento_imagen,
                        organizador_nombre=organizador_nombre

        )

    except Exception as e:
        flash(f"Error al acceder al evento: {e}", 'danger')
        return redirect(url_for('indexP'))
    finally:
        cursor.close()
        conn.close()
@verificar_tipo_usuario('Personal')

#-----------------------------------------------------------Cancelar asistencia-----------------------------------------------------------
@app.route('/cancelar_asistencia/<int:evento_id>', methods=['POST'])
@verificar_tipo_usuario('Personal')
def cancelar_asistencia(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener el nombre del evento y validar existencia
        cursor.execute("SELECT nombre FROM Evento WHERE id = %s", (evento_id,))
        evento = cursor.fetchone()
        if not evento:
            flash('El evento no existe.', 'danger')
            return redirect(url_for('mis_eventosP'))
        evento_nombre = evento['nombre']

        # Verificar si el usuario está inscrito
        cursor.execute(
            """
            SELECT qr, foto 
            FROM Inscripcion 
            WHERE usuario_email = %s AND evento_id = %s
            """,
            (session['email_Usuario'], evento_id)
        )
        inscripcion = cursor.fetchone()
        if not inscripcion:
            flash('No se encontró la inscripción para este evento.', 'danger')
            return redirect(url_for('mis_eventosP'))

        #Eliminar la inscripción
        cursor.execute(
            "DELETE FROM Inscripcion WHERE usuario_email = %s AND evento_id = %s",
            (session['email_Usuario'], evento_id)
        )

        # Crear notificación
        crear_notificacion(
            session['email_Usuario'],
            f"Has cancelado tu asistencia al evento '{evento_nombre}'",
            evento_id
        )

        # Eliminar archivos relacionados con la inscripción
        for file_key in ['qr', 'foto']:
            file_path = inscripcion[file_key]
            if file_path and os.path.exists(os.path.join('static', file_path)):
                os.remove(os.path.join('static', file_path))

        conn.commit()
        flash('Tu asistencia al evento ha sido cancelada exitosamente.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Ocurrió un error al cancelar tu asistencia: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('mis_eventosP'))


#-----------------------------------------------------------Ver Eventos-----------------------------------------------------------
@app.route('/mis_eventos', methods=['GET'])
def mis_eventosP():
    if 'email_Usuario' not in session:
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener eventos donde el usuario está inscrito
        cursor.execute("""
            SELECT 
                E.id AS id,
                E.nombre AS eventoNombre,
                E.descripcion,
                E.fechaHora,
                E.imagen AS eventoImagen,
                E.creadorEmail AS creadorEmail,
                U.nombre AS creadorNombre,
                E.tipoAcceso AS tipoAcceso
            FROM Inscripcion I
            JOIN Evento E ON I.evento_id = E.id
            JOIN Usuario U ON E.creadorEmail = U.email
            WHERE I.usuario_email = %s
            ORDER BY E.fechaHora DESC
        """, (session['email_Usuario'],))
        eventos = cursor.fetchall()

        # Construir rutas de imágenes
        for evento in eventos:
            evento['creadorImagen'] = f"uploads/{evento['creadorEmail']}.png"
            evento['eventoImagen'] = f"eventos/{evento['creadorEmail']}/{evento['eventoNombre'].replace(' ', '_')}.png"

    finally:
        cursor.close()
        conn.close()

    return render_template('verEventosPersonal.html', eventos=eventos)
@verificar_tipo_usuario('Personal')


#-----------------------------------------------------------Acceder a eventos-----------------------------------------------------------
@app.route('/acceder_evento/<int:evento_id>', methods=['GET'])
def acceder_evento(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener el tipo de acceso del evento
        cursor.execute("""
            SELECT tipoAcceso FROM Evento WHERE id = %s
        """, (evento_id,))
        evento = cursor.fetchone()

        if not evento:
            flash('Evento no encontrado.', 'danger')
            return redirect(url_for('eventosEmpresa'))

        # Redirigir según el tipo de acceso
        tipo_acceso = evento['tipoAcceso']
        if tipo_acceso == 'QR':
            return redirect(url_for('escanear_qr', evento_id=evento_id))
        elif tipo_acceso == 'Reconocimiento Facial':
            return redirect(url_for('escanear_rec_facial', evento_id=evento_id))
        else:
            flash('Tipo de acceso no definido.', 'warning')
            return redirect(url_for('eventosEmpresa'))
    except Exception as e:
        flash(f"Error al acceder al evento: {e}", 'danger')
        return redirect(url_for('eventosEmpresa'))
    finally:
        cursor.close()
        conn.close()


#Acceder a eventos con QR
@app.route('/escanearQR/<int:evento_id>', methods=['GET'])
def escanear_qr(evento_id):
    return render_template('escanearQR.html', evento_id=evento_id)


@app.route('/validarQR/<int:evento_id>', methods=['POST'])
def validar_qr(evento_id):
    try:
        # Obtener los datos enviados desde el frontend
        data = request.get_json()
        qr_data = data.get('qr_data')

        if not qr_data:
            return jsonify({'status': 'error', 'message': 'No se recibió ningún código QR.'})

        # Extraer información del QR usando una expresión regular
        pattern = r"Usuario: (.+?) \| Evento: (.+?) \| Evento ID: (\d+)"
        match = re.match(pattern, qr_data)

        if not match:
            return jsonify({'status': 'error', 'message': 'El formato del QR no es válido.'})

        user_name = match.group(1)
        event_name = match.group(2)
        qr_event_id = int(match.group(3))

        # Validar que el evento ID del QR coincida con el de la ruta
        if qr_event_id != evento_id:
            return jsonify({'status': 'error', 'message': 'El QR no corresponde a este evento.'})

        # Conectar a la base de datos y realizar la consulta
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Buscar el usuario en la base de datos
            cursor.execute("""
                SELECT U.nombre, U.email, E.nombre AS evento_nombre 
                FROM Usuario U
                JOIN Inscripcion I ON U.email = I.usuario_email
                JOIN Evento E ON I.evento_id = E.id
                WHERE U.nombre = %s AND E.id = %s
            """, (user_name, qr_event_id))
            user = cursor.fetchone()

            if user:
                return jsonify({
                    'status': 'success',
                    'message': f'Acceso concedido a {user["nombre"]} para el evento "{user["evento_nombre"]}".',
                    'email': user["email"]
                })
            else:
                return jsonify({'status': 'error', 'message': 'Usuario o evento no encontrado.'})
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Ocurrió un error inesperado: {str(e)}'})

@verificar_tipo_usuario('Empresarial')


#Acceder a eventos con reconocimiento facial
@app.route('/escanearRecFac/<int:evento_id>', methods=['GET', 'POST'])
def escanear_rec_facial(evento_id):
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'danger')
        return redirect(url_for('inicio_sesion'))

    from numpy.linalg import norm  # Asegura que norm esté disponible

    if request.method == 'POST':
        try:
            # Obtener y validar la imagen
            photo = request.form.get('photo')
            if not photo:
                return jsonify({'status': 'error', 'message': 'No se recibió ninguna imagen.'}), 400

            # Decodificar la imagen base64
            import base64
            from io import BytesIO
            from PIL import Image

            header, encoded = photo.split(',', 1)
            image_data = base64.b64decode(encoded)
            image = Image.open(BytesIO(image_data))

            if image.mode != 'RGB':
                image = image.convert('RGB')

            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_image.jpg')
            image.save(temp_path, format='JPEG')

            # Generar encoding de la imagen
            encoding_result = DeepFace.represent(img_path=temp_path, model_name="Facenet")
            if not encoding_result or not isinstance(encoding_result, list):
                return jsonify({'status': 'error', 'message': 'No se detectó ningún rostro en la imagen.'}), 400

            # Obtener el encoding
            encoding = np.array(encoding_result[0]['embedding'], dtype=np.float32)

            # Conectar a la base de datos
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT data, usuario_email 
                FROM Inscripcion 
                WHERE evento_id = %s AND data IS NOT NULL
            """, (evento_id,))
            inscripciones = cursor.fetchall()

            min_distance = float('inf')
            closest_user = None

            for inscripcion in inscripciones:
                try:
                    stored_encoding = eval(inscripcion['data'])[0]['embedding']
                    db_encoding = np.array(stored_encoding, dtype=np.float32)

                    # Normalización explícita
                    encoding_norm = encoding / norm(encoding)
                    db_encoding_norm = db_encoding / norm(db_encoding)

                    # Cálculo de la distancia
                    distance = np.linalg.norm(encoding_norm - db_encoding_norm)
                    print(f"Comparing with {inscripcion['usuario_email']}: Distance = {distance}")

                    if distance < min_distance:
                        min_distance = distance
                        closest_user = inscripcion['usuario_email']

                except Exception as e:
                    print(f"Error al comparar con {inscripcion['usuario_email']}: {e}")

            # Ajustar umbral realista
            similarity_threshold = 0.8
            if min_distance < similarity_threshold and closest_user:
                response = {
                    'status': 'success',
                    'message': f'Acceso permitido. Bienvenido, {closest_user}.',
                }
            else:
                response = {
                    'status': 'error',
                    'message': 'Acceso denegado. No se encontró coincidencia.',
                }

        except Exception as e:
            response = {'status': 'error', 'message': f'Ocurrió un error inesperado: {e}'}

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if 'conn' in locals():
                cursor.close()
                conn.close()

        return jsonify(response)

    return render_template('escanearRecFac.html', evento_id=evento_id)
@verificar_tipo_usuario('Empresarial')


#-----------------------------------------------------------Notificaciones-----------------------------------------------------------------

def crear_notificacion(usuario_email, mensaje, evento_id=None):
    """
    Crea una notificación para un usuario.

    Args:
        usuario_email (str): Correo del usuario que recibirá la notificación.
        mensaje (str): Mensaje de la notificación.
        evento_id (int, optional): ID del evento relacionado (opcional).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Notificacion (mensaje, fechaEnvio, usuarioEmail, evento_id)
            VALUES (%s, NOW(), %s, %s)
        """, (mensaje, usuario_email, evento_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error al crear notificación: {e}")
    finally:
        cursor.close()
        conn.close()


@app.route('/notificaciones', methods=['GET'])
def notificaciones():
    if 'email_Usuario' not in session:
        flash('Debes iniciar sesión para ver tus notificaciones.', 'danger')
        return redirect(url_for('inicio_sesion'))

    usuario_email = session['email_Usuario']
    usuario_tipo = session.get('tipo', 'Personal')  # Predeterminado a Personal si no está definido
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT N.mensaje, N.fechaEnvio, E.nombre AS eventoNombre
            FROM Notificacion N
            LEFT JOIN Evento E ON N.evento_id = E.id
            WHERE N.usuarioEmail = %s
            ORDER BY N.fechaEnvio DESC
        """, (usuario_email,))
        notificaciones = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Renderizar plantilla según el tipo de usuario
    if usuario_tipo == 'Personal':
        return render_template('verNotificacionesPersonal.html', notificaciones=notificaciones)
    elif usuario_tipo == 'Empresarial':
        return render_template('verNotificacionesEmpresa.html', notificaciones=notificaciones)
    else:
        flash('Tipo de usuario desconocido.', 'danger')
        return redirect(url_for('inicio_sesion'))



#-----------------------------------------------------------Recuperación de Contraseña-----------------------------------------------------------

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

#-----------------------------------------------------------Cerrar Sesión-----------------------------------------------------------

# Ruta para cerrar sesión
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear() # Elimina los datos de la sesión
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('inicio_sesion'))

#-----------------------------------------------------------Página de Error-----------------------------------------------------------

# Página de Error 
@app.route('/error')
def error():
    return render_template('errorTemplate.html')


if __name__ == '__main__':
    app.run(debug=True)
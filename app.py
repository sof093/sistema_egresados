from flask import Flask, Response, jsonify, render_template, request, redirect, session, url_for
import psycopg2
import psycopg2.extras
import logging
from werkzeug.security import generate_password_hash
import os, uuid
from werkzeug.utils import secure_filename
from telegram import Bot

TELEGRAM_TOKEN = "8228079798:AAGQdTst1MuV3V1sV_4ApPphgEg7dzEHYac"

telegram_bot = Bot(token=TELEGRAM_TOKEN)

def enviar_telegram(chat_id, mensaje):
    if chat_id:
        telegram_bot.send_message(chat_id=chat_id, text=mensaje)

app = Flask(__name__)
app.secret_key = 'UMB-UES'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def conectar_db():
    try:
        conexion = psycopg2.connect(
            host='dpg-d5kl39re5dus73acnoe0-a.oregon-postgres.render.com',
            user='db_egresados_umb_user',
            password='KvPkUmbrPMy8im2r9WB7aiedaddMAkEW',
            database='db_egresados_umb',
            port=5432,
            sslmode='require',
            cursor_factory=psycopg2.extras.DictCursor
        )
        print("Conexión exitosa a la base de datos")
        return conexion
    except psycopg2.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

@app.route('/')
def index():
    conexion = conectar_db()
    if conexion:
        conexion.close()
    return render_template('index.html')

from datetime import datetime
@app.route('/inicio')
def inicio():
    conexion = conectar_db()
    if not conexion:
        return redirect(url_for('index'))

    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.id_carrera,
                    c.nombre_carrera,
                    COUNT(e.id_egresado) AS total_graduados
                FROM carreras c
                LEFT JOIN egresados e 
                    ON e.id_carrera = c.id_carrera
                GROUP BY c.id_carrera, c.nombre_carrera
                ORDER BY c.nombre_carrera ASC
            """)
            carreras = cursor.fetchall()

    finally:
        conexion.close()

    return render_template(
        'inicio.html',
        carreras=carreras
    )


@app.route('/admin')
def dashboard_admin():
    if 'useradmin' not in session:
        return redirect(url_for('index'))

    conexion = conectar_db()
    if not conexion:
        return redirect(url_for('index'))

    try:
        with conexion.cursor() as cursor:

            # TOTAL EGRESADOS
            cursor.execute("SELECT COUNT(*) AS total FROM egresados")
            total_egresados = cursor.fetchone()["total"]

            # ÚLTIMA FECHA (PostgreSQL)
            cursor.execute("""
                SELECT TO_CHAR(CURRENT_DATE, 'DD Month, YYYY') AS fecha
            """)
            ultima_fecha = cursor.fetchone()["fecha"]

            # GRADUADOS POR CARRERA
            cursor.execute("""
                SELECT 
                    c.id_carrera,
                    c.nombre_carrera,
                    c.imagen,
                    COUNT(e.id_egresado) AS total_graduados
                FROM carreras c
                LEFT JOIN egresados e 
                    ON e.id_carrera = c.id_carrera
                GROUP BY c.id_carrera, c.nombre_carrera, c.imagen
                ORDER BY c.nombre_carrera
            """)
            carreras = cursor.fetchall()

    finally:
        conexion.close()

    return render_template(
        'dashboard_admin.html',
        total_egresados=total_egresados,
        ultima_fecha=ultima_fecha,
        carreras=carreras
    )


@app.route('/login_admin', methods=['POST'])
def login_admin():
    username = request.form['useradmin']
    password = request.form['password_coordi'] 
    conexion = conectar_db()
    if not conexion:
        return redirect(url_for('index', error='db'))

    try:
        with conexion.cursor() as cursor:
            sql = "SELECT * FROM coordinador WHERE numero_empleado = %s AND password = %s"
            cursor.execute(sql, (username, password))
            user = cursor.fetchone()
            if user:
                session['useradmin'] = user['numero_empleado']
                session['nombre'] = user['nombre_coordinador']
                session['fotografia'] = user['fotografia']
                return redirect(url_for('dashboard_admin'))
            else:
                return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_admin: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conexion.close()


@app.route('/login_control', methods=['POST'])
def login_control():
    username = request.form['useradmin']
    password = request.form['password_control']
    conexion = conectar_db()
    if not conexion:
        return redirect(url_for('index', error='db'))

    try:
        with conexion.cursor() as cursor:
            sql = "SELECT * FROM control_escolar WHERE numero_empleado = %s AND password = %s"
            cursor.execute(sql, (username, password))
            user = cursor.fetchone()
            if user:
                session['usercontrol'] = user['numero_empleado']
                session['nombre'] = f"{user['nombre_control']} {user['apellido_paterno']} {user['apellido_materno']}"
                return redirect(url_for('dashboard_control_escolar'))
            else:
                return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_control: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conexion.close()


@app.route('/dashboard_estudiante')
def dashboard_estudiante():
    if 'user_egresado' in session:
        return render_template('dashboard_estudiante.html', nombre=session['nombre'])
    else:
        return redirect(url_for('index'))
    

@app.route('/login_egresado', methods=['POST'])
def login_egresado():
    matricula = request.form['matricula']
    password = request.form['password']
    conexion = conectar_db()
    if not conexion:
        return redirect(url_for('index', error='db'))

    try:
        with conexion.cursor() as cursor:
            sql = "SELECT * FROM egresados WHERE matricula = %s AND password = %s"
            cursor.execute(sql, (matricula, password))
            egresado = cursor.fetchone()
            if egresado:
                session['user_egresado'] = egresado['matricula']
                session['nombre'] = f"{egresado['nombre_egresado']} {egresado['apellido_paterno']} {egresado['apellido_materno']}"
                return redirect(url_for('dashboard_estudiante'))
            else:
                return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_egresado: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conexion.close() 


@app.route('/consulta_egresados')
def consulta_egresados():
    conexion = conectar_db()
    if conexion:
        with conexion.cursor() as cursor:
            sql = "SELECT * FROM egresados"
            cursor.execute(sql)
            egresados = cursor.fetchall()
            return render_template('consulta_egresados.html', egresados=egresados)
    else:
        return "Error al conectar la base de datos"


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/consulta_carrera")
def consulta_carrera():
    conexion = conectar_db()
    if not conexion:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
            return jsonify(carreras)
    finally:
        conexion.close()


@app.route("/consulta_ues")
def consulta_ues():
    conexion = conectar_db()
    if not conexion:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_ues, nombre_ues FROM ues")
            ues = cursor.fetchall()
            return jsonify(ues)
    finally:
        conexion.close()


@app.route("/consulta_municipio")
def consulta_municipio():
    conexion = conectar_db()
    if not conexion:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_municipio, nombre_municipio FROM municipio")
            municipio = cursor.fetchall()
            return jsonify(municipio)
    finally:
        conexion.close()


@app.route('/consulta_localidades/<int:id_municipio>')
def consulta_localidades(id_municipio):
    conexion = conectar_db()
    if conexion:
        try:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT id_localidad, nombre_localidad 
                    FROM localidades 
                    WHERE id_municipio = %s
                    ORDER BY nombre_localidad ASC
                """, (id_municipio,))
                localidades = cursor.fetchall()
            return jsonify(localidades)
        finally:
            conexion.close()
    else:
        return jsonify({'error': 'Error al conectar a la base de datos'}), 500
    

@app.route('/registrar_egresado', methods=['POST'])
def registrar_egresado():
    try:
        data = request.form
        files = request.files

        campos = [
            'nombre_egresado', 'apellido_paterno', 'apellido_materno', 'genero','telefono', 'coorreo_electronico',
            'ni', 'ne', 'estatus_laboral', 'estatus_titulacion', 'matricula',
            'generacion', 'password', 'id_carrera', 'perfil',
            'id_ues', 'id_municipio', 'id_localidad'
        ]

        for campo in campos:
            if not data.get(campo):
                return jsonify({"success": False, "message": f"Falta el campo {campo}"}), 400

        password_hash = generate_password_hash(data['password'])
        foto = files.get('fotografiaegr')
        if not foto or foto.filename == '':
            return jsonify({"success": False, "message": "Debe subir una fotografía"}), 400

        matricula_segura = secure_filename(data['matricula']).strip()
        dir_fotos = os.path.join('static', 'uploads', 'egresados')
        dir_foto = os.path.join('uploads', 'egresados')
        os.makedirs(dir_fotos, exist_ok=True)
        _, ext_foto = os.path.splitext(foto.filename)
        ext_foto = ext_foto.lower() or '.jpg'
        nombre_foto = f"{matricula_segura}{ext_foto}"
        ruta_foto = os.path.join(dir_fotos, nombre_foto)
        ruta_foto_s = os.path.join(dir_foto, nombre_foto)
        if os.path.exists(ruta_foto):
            base, ext = os.path.splitext(nombre_foto)
            i = 1
            while os.path.exists(os.path.join(dir_fotos, f"{base}_{i}{ext}")):
                i += 1
            ruta_foto = os.path.join(dir_fotos, f"{base}_{i}{ext}")
        foto.save(ruta_foto)
        ruta_foto = ruta_foto.replace('\\', '/')
        ruta_foto_s = ruta_foto_s.replace('\\', '/')

        modalidad = data.get('modalidad')
        archivo_modalidad = None
        if modalidad in ('I', 'II', 'III', 'VI', 'VIII', 'XI'):
            doc = files.get('archivo_modalidad')
            if doc and doc.filename:
                dir_docs = os.path.join('static', 'uploads', 'modalidades')
                dir_doc = os.path.join('uploads', 'modalidades')
                os.makedirs(dir_docs, exist_ok=True)
                _, ext_doc = os.path.splitext(doc.filename)
                ext_doc = ext_doc.lower() or '.pdf'
                nombre_doc = f"{matricula_segura}{ext_doc}"
                ruta_doc = os.path.join(dir_docs, nombre_doc)
                ruta_doc_s = os.path.join(dir_doc, nombre_doc)
                if os.path.exists(ruta_doc):
                    base, ext = os.path.splitext(nombre_doc)
                    i = 1
                    while os.path.exists(os.path.join(dir_docs, f"{base}_{i}{ext}")):
                        i += 1
                    ruta_doc = os.path.join(dir_docs, f"{base}_{i}{ext}")
                doc.save(ruta_doc)
                archivo_modalidad = ruta_doc_s
                ruta_doc = ruta_doc.replace('\\', '/')
                ruta_doc_s = ruta_doc_s.replace('\\', '/')

        conexion = conectar_db()
        if not conexion:
            return jsonify({"success": False, "message": "No se pudo conectar a la base de datos"}), 500

        with conexion.cursor() as cursor:

            # INSERTAR EGRESADO
            sql = """
            INSERT INTO egresados (
                    nombre_egresado, apellido_paterno, apellido_materno, genero, telefono, coorreo_electronico,
                    ni, ne, estatus_laboral, estatus_titulacion,
                    modalidad, matricula, generacion, password,
                    id_carrera, perfil, id_ues, id_municipio, id_localidad,
                    fotografia, documentos
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cursor.execute(sql, (
                data['nombre_egresado'], data['apellido_paterno'], data['apellido_materno'],data['genero'],
                data['telefono'], data['coorreo_electronico'], data['ni'], data['ne'],
                data['estatus_laboral'], data['estatus_titulacion'], modalidad,
                data['matricula'], data['generacion'], password_hash,
                data['id_carrera'], data['perfil'], data['id_ues'],
                data['id_municipio'], data['id_localidad'],
                ruta_foto_s, archivo_modalidad
            ))

            conexion.commit()

            # BUSCAR CHAT_ID POR TELÉFONO
            cursor.execute(
                "SELECT chat_id, nombre_egresado FROM egresados WHERE telefono=%s",
                (data['telefono'],)
            )
            egresado = cursor.fetchone()

            # ENVIAR TELEGRAM (SI EXISTE)
            if egresado and egresado["chat_id"]:
                enviar_telegram(
                    egresado["chat_id"],
                    f"🟢 Hola {egresado['nombre_egresado']}\n"
                    "El sistema ha detectado tu registro.\n"
                    "Tu cuenta ya está activa y en línea."
                )
    
        return jsonify({"success": True, "message": "Registro exitoso"})

    except Exception as e:
        logging.exception("Error en registrar_egresado")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/obtener_egresado/<int:id>', methods=['GET'])
def obtener_egresado(id):
    conexion = conectar_db()
    if not conexion:
        return jsonify({"error": "No hay conexión a BD"}), 500

    try:
        with conexion.cursor() as cursor:
            sql = """
                SELECT 
                    e.*, 
                    m.nombre_municipio, 
                    l.nombre_localidad, 
                    c.nombre_carrera, 
                    u.nombre_ues
                FROM egresados e
                LEFT JOIN municipio m ON e.id_municipio = m.id_municipio
                LEFT JOIN localidades l ON e.id_localidad = l.id_localidad
                LEFT JOIN carreras c ON e.id_carrera = c.id_carrera
                LEFT JOIN ues u ON e.id_ues = u.id_ues
                WHERE e.id_egresado = %s
            """
            cursor.execute(sql, (id,))
            egresado = cursor.fetchone()

            if not egresado:
                return jsonify({"error": "Egresado no encontrado"}), 404

            return jsonify(egresado)

    except Exception as e:
        print("Error interno:", e)
        return jsonify({"error": "Error interno"}), 500

    finally:
        conexion.close()


@app.route('/actualizar_egresado', methods=['POST'])
def actualizar_egresado():
    try:
        # DATOS DEL FORMULARIO
        id_egresado = request.form['id_egresado']

        nombre = request.form['nombre_egresado_ac']
        paterno = request.form['apellido_paterno_ac']
        materno = request.form['apellido_materno_ac']
        genero = request.form['genero_ac']
        telefono = request.form['telefono_ac']
        correo = request.form['coorreo_electronico_ac']
        ni = request.form['ni_ac']
        ne = request.form['ne_ac']
        generacion = request.form['generacion_ac']
        modalidad = request.form['modalidad_ac']
        estatus_titulacion = request.form['estatus_titulacion_ac']
        estatus_laboral = request.form['estatus_laboral_ac']
        perfil = request.form['perfil_ac']
        matricula = request.form['matricula_ac']

        id_carrera = request.form['id_carrera_ac']
        id_ues = request.form['id_ues_ac']
        id_municipio = request.form['id_municipio_ac']
        id_localidad = request.form['id_localidad_ac']

        # FOTO (SI SE SUBE)
        foto = request.files.get('fotografiaegr_ac')
        ruta_foto_s = None

        if foto and foto.filename:
            matricula_segura = secure_filename(matricula)

            dir_fotos = os.path.join('static', 'uploads', 'egresados')
            dir_foto = os.path.join('uploads', 'egresados')
            os.makedirs(dir_fotos, exist_ok=True)

            _, ext = os.path.splitext(foto.filename)
            ext = ext.lower() or '.jpg'

            nombre_foto = f"{matricula_segura}_{uuid.uuid4().hex}{ext}"
            ruta_foto = os.path.join(dir_fotos, nombre_foto)
            ruta_foto_s = os.path.join(dir_foto, nombre_foto)

            foto.save(ruta_foto)
            ruta_foto_s = ruta_foto_s.replace('\\', '/')

        # BASE DE DATOS
        conn = conectar_db()
        if not conn:
            return jsonify({"success": False, "message": "No hay conexión a BD"}), 500

        cursor = conn.cursor()

        # UPDATE (con o sin foto)
        if ruta_foto_s:
            sql = """
                UPDATE egresados SET
                    nombre_egresado=%s,
                    apellido_paterno=%s,
                    apellido_materno=%s,
                    genero=%s,
                    telefono=%s,
                    coorreo_electronico=%s,
                    ni=%s,
                    ne=%s,
                    generacion=%s,
                    modalidad=%s,
                    estatus_titulacion=%s,
                    estatus_laboral=%s,
                    perfil=%s,
                    matricula=%s,
                    id_carrera=%s,
                    id_ues=%s,
                    id_municipio=%s,
                    id_localidad=%s,
                    fotografia=%s
                WHERE id_egresado=%s
            """

            valores = (
                nombre, paterno, materno, genero, telefono, correo,
                ni, ne, generacion, modalidad, estatus_titulacion, estatus_laboral,
                perfil, matricula,
                id_carrera, id_ues, id_municipio, id_localidad,
                ruta_foto_s,
                id_egresado
            )
        else:
            sql = """
                UPDATE egresados SET
                    nombre_egresado=%s,
                    apellido_paterno=%s,
                    apellido_materno=%s,
                    genero=%s,
                    telefono=%s,
                    coorreo_electronico=%s,
                    ni=%s,
                    ne=%s,
                    generacion=%s,
                    modalidad=%s,
                    estatus_titulacion=%s,
                    estatus_laboral=%s,
                    perfil=%s,
                    matricula=%s,
                    id_carrera=%s,
                    id_ues=%s,
                    id_municipio=%s,
                    id_localidad=%s
                WHERE id_egresado=%s
            """

            valores = (
                nombre, paterno, materno, genero, telefono, correo,
                ni, ne, generacion, modalidad, estatus_titulacion, estatus_laboral,
                perfil, matricula,
                id_carrera, id_ues, id_municipio, id_localidad,
                id_egresado
            )

        cursor.execute(sql, valores)
        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        print("❌ Error al actualizar egresado:", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/eliminar_egresado', methods=['POST'])
def eliminar_egresado():
    try:
        id_egresado = request.form.get("id_egresado")

        conexion = conectar_db()
        with conexion.cursor() as cursor:
            sql = "DELETE FROM egresados WHERE id_egresado = %s"
            cursor.execute(sql, (id_egresado,))
            conexion.commit()
        conexion.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/datos_estadisticas")
def datos_estadisticas():
    estatus = request.args.get("estatus")
    carrera = request.args.get("carrera")

    conexion = conectar_db()
    if not conexion:
        return jsonify([])

    try:
        with conexion.cursor() as cursor:

            query = """
                SELECT estatus_titulacion, COUNT(*) AS total
                FROM egresados
                WHERE 1=1
            """

            params = []

            if estatus:
                query += " AND LOWER(estatus_titulacion) = %s"
                params.append(estatus.lower())

            if carrera:
                query += " AND id_carrera = %s"
                params.append(carrera)

            query += " GROUP BY estatus_titulacion"

            cursor.execute(query, params)
            data = cursor.fetchall()

            return jsonify(data)

    finally:
        conexion.close()


@app.route("/lista_carreras")
def lista_carreras():
    conexion = conectar_db()
    if not conexion:
        return jsonify([])

    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            return jsonify(cursor.fetchall())
    finally:
        conexion.close()


@app.route("/vista_estadisticas")
def vista_estadisticas():
    return render_template("estadisticas_egresados.html")


if __name__ == '__main__':
    conexion = conectar_db()
    if conexion:
        conexion.close()
    app.run(debug=True, host='0.0.0.0', port=5000)
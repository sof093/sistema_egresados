from flask import Flask, Response, jsonify, render_template, request, redirect, session, url_for
import psycopg2  # Cambiamos pymysql por psycopg2 para PostgreSQL
import logging
from werkzeug.security import generate_password_hash, check_password_hash
import os, uuid
from werkzeug.utils import secure_filename
from telegram import Bot
from datetime import datetime
import ssl

# Configuración de Telegram (si sigues usando)
TELEGRAM_TOKEN = "8228079798:AAGQdTst1MuV3V1sV_4ApPphgEg7dzEHYac"
telegram_bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

def enviar_telegram(chat_id, mensaje):
    if chat_id and telegram_bot:
        try:
            telegram_bot.send_message(chat_id=chat_id, text=mensaje)
        except Exception as e:
            logging.error(f"Error enviando telegram: {e}")

app = Flask(__name__)
app.secret_key = 'UMB-UES'

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de la base de datos PostgreSQL en Render
DB_CONFIG = {
    'host': 'dpg-d5kl39re5dus73acnoe0-a.oregon-postgres.render.com',
    'database': 'db_egresados_umb',
    'user': 'db_egresados_umb_user',
    'password': 'KvPkUmbrPMy8im2r9WB7aiedaddMAkEW',
    'port': 5432,
    'sslmode': 'require'  # Render requiere SSL
}

def conectar_db():
    """Conectar a PostgreSQL en Render"""
    try:
        # Cadena de conexión para PostgreSQL con SSL
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
            sslmode=DB_CONFIG['sslmode']
        )
        print("✅ Conexión exitosa a PostgreSQL en Render")
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        logging.error(f"Error de conexión a PostgreSQL: {e}")
        return None

@app.route('/')
def index():
    conexion = conectar_db()
    if conexion:
        conexion.close()
    return render_template('index.html')

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
            return render_template('inicio.html', carreras=carreras)
    except Exception as e:
        print(f"Error en /inicio: {e}")
        return redirect(url_for('index'))
    finally:
        conexion.close()

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
            total_egresados = cursor.fetchone()[0]

            # ÚLTIMA FECHA
            cursor.execute("SELECT TO_CHAR(CURRENT_DATE, 'DD Month, YYYY') AS fecha")
            ultima_fecha = cursor.fetchone()[0]

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

        return render_template(
            'dashboard_admin.html',
            total_egresados=total_egresados,
            ultima_fecha=ultima_fecha,
            carreras=carreras
        )
    except Exception as e:
        print(f"Error en dashboard_admin: {e}")
        return redirect(url_for('index'))
    finally:
        conexion.close()

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
                session['useradmin'] = user[4]  # numero_empleado (índice 4)
                session['nombre'] = user[1]    # nombre_coordinador (índice 1)
                session['fotografia'] = user[7]  # fotografia (índice 7)
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
                session['usercontrol'] = user[4]  # numero_empleado
                session['nombre'] = f"{user[1]} {user[2]} {user[3]}"  # nombre + apellidos
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
            sql = "SELECT * FROM egresados WHERE matricula = %s"
            cursor.execute(sql, (matricula,))
            egresado = cursor.fetchone()
            
            if egresado:
                # Verificar contraseña (ya está encriptada con scrypt en la BD)
                stored_password = egresado[17]  # password (índice 17)
                # Si la contraseña está en texto plano (temporal)
                if password == stored_password or check_password_hash(stored_password, password):
                    session['user_egresado'] = egresado[15]  # matricula
                    session['nombre'] = f"{egresado[1]} {egresado[2]} {egresado[3]}"  # nombre + apellidos
                    return redirect(url_for('dashboard_estudiante'))
            
            return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_egresado: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conexion.close()

@app.route('/consulta_egresados')
def consulta_egresados():
    conexion = conectar_db()
    if not conexion:
        return "Error al conectar la base de datos"

    try:
        with conexion.cursor() as cursor:
            sql = "SELECT * FROM egresados ORDER BY id_egresado"
            cursor.execute(sql)
            egresados = cursor.fetchall()
            
            # Convertir a lista de diccionarios para mejor manejo en templates
            columns = [desc[0] for desc in cursor.description]
            egresados_dict = [dict(zip(columns, row)) for row in egresados]
            
            return render_template('consulta_egresados.html', egresados=egresados_dict)
    finally:
        conexion.close()

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
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras ORDER BY nombre_carrera")
            carreras = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            carreras_dict = [dict(zip(columns, row)) for row in carreras]
            return jsonify(carreras_dict)
    finally:
        conexion.close()

@app.route("/consulta_ues")
def consulta_ues():
    conexion = conectar_db()
    if not conexion:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_ues, nombre_ues FROM ues ORDER BY nombre_ues")
            ues = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            ues_dict = [dict(zip(columns, row)) for row in ues]
            return jsonify(ues_dict)
    finally:
        conexion.close()

@app.route("/consulta_municipio")
def consulta_municipio():
    conexion = conectar_db()
    if not conexion:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_municipio, nombre_municipio FROM municipio ORDER BY nombre_municipio")
            municipios = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            municipios_dict = [dict(zip(columns, row)) for row in municipios]
            return jsonify(municipios_dict)
    finally:
        conexion.close()

@app.route('/consulta_localidades/<int:id_municipio>')
def consulta_localidades(id_municipio):
    conexion = conectar_db()
    if not conexion:
        return jsonify({'error': 'Error al conectar a la base de datos'}), 500
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id_localidad, nombre_localidad 
                FROM localidades 
                WHERE id_municipio = %s
                ORDER BY nombre_localidad ASC
            """, (id_municipio,))
            localidades = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            localidades_dict = [dict(zip(columns, row)) for row in localidades]
            return jsonify(localidades_dict)
    finally:
        conexion.close()

@app.route('/registrar_egresado', methods=['POST'])
def registrar_egresado():
    try:
        data = request.form
        files = request.files

        campos = [
            'nombre_egresado', 'apellido_paterno', 'apellido_materno', 'genero','telefono', 'correo_electronico',
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
            ruta_foto_s = os.path.join(dir_foto, f"{base}_{i}{ext}")
        
        foto.save(ruta_foto)
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
                    ruta_doc_s = os.path.join(dir_doc, f"{base}_{i}{ext}")
                
                doc.save(ruta_doc)
                archivo_modalidad = ruta_doc_s.replace('\\', '/')

        conexion = conectar_db()
        if not conexion:
            return jsonify({"success": False, "message": "No se pudo conectar a la base de datos"}), 500

        with conexion.cursor() as cursor:
            sql = """
            INSERT INTO egresados (
                nombre_egresado, apellido_paterno, apellido_materno, genero, telefono, correo_electronico,
                ni, ne, estatus_laboral, estatus_titulacion, modalidad, matricula, generacion, password,
                id_carrera, perfil, id_ues, id_municipio, id_localidad, fotografia, documentos, chat_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_egresado
            """
            
            cursor.execute(sql, (
                data['nombre_egresado'], data['apellido_paterno'], data['apellido_materno'], data['genero'],
                data['telefono'], data['correo_electronico'], data['ni'], data['ne'],
                data['estatus_laboral'], data['estatus_titulacion'], modalidad,
                data['matricula'], data['generacion'], password_hash,
                data['id_carrera'], data['perfil'], data['id_ues'],
                data['id_municipio'], data['id_localidad'],
                ruta_foto_s, archivo_modalidad, data.get('chat_id', '')
            ))
            
            nuevo_id = cursor.fetchone()[0]
            conexion.commit()

            # Enviar telegram si hay chat_id
            chat_id = data.get('chat_id')
            if chat_id:
                enviar_telegram(
                    chat_id,
                    f"🟢 Hola {data['nombre_egresado']}\n"
                    "El sistema ha detectado tu registro.\n"
                    "Tu cuenta ya está activa y en línea."
                )
        
        return jsonify({"success": True, "message": "Registro exitoso", "id": nuevo_id})

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
            
            # Convertir a diccionario
            columns = [desc[0] for desc in cursor.description]
            egresado_dict = dict(zip(columns, egresado))
            
            return jsonify(egresado_dict)
    except Exception as e:
        print("Error interno:", e)
        return jsonify({"error": "Error interno"}), 500
    finally:
        conexion.close()

@app.route('/actualizar_egresado', methods=['POST'])
def actualizar_egresado():
    try:
        id_egresado = request.form['id_egresado']
        
        # Obtener datos del formulario
        datos = {
            'nombre': request.form['nombre_egresado_ac'],
            'paterno': request.form['apellido_paterno_ac'],
            'materno': request.form['apellido_materno_ac'],
            'genero': request.form['genero_ac'],
            'telefono': request.form['telefono_ac'],
            'correo': request.form['correo_electronico_ac'],
            'ni': request.form['ni_ac'],
            'ne': request.form['ne_ac'],
            'generacion': request.form['generacion_ac'],
            'modalidad': request.form['modalidad_ac'],
            'estatus_titulacion': request.form['estatus_titulacion_ac'],
            'estatus_laboral': request.form['estatus_laboral_ac'],
            'perfil': request.form['perfil_ac'],
            'matricula': request.form['matricula_ac'],
            'id_carrera': request.form['id_carrera_ac'],
            'id_ues': request.form['id_ues_ac'],
            'id_municipio': request.form['id_municipio_ac'],
            'id_localidad': request.form['id_localidad_ac']
        }

        # Manejar foto
        foto = request.files.get('fotografiaegr_ac')
        ruta_foto_s = None

        if foto and foto.filename:
            matricula_segura = secure_filename(datos['matricula'])
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

        conexion = conectar_db()
        if not conexion:
            return jsonify({"success": False, "message": "No hay conexión a BD"}), 500

        with conexion.cursor() as cursor:
            if ruta_foto_s:
                sql = """
                    UPDATE egresados SET
                        nombre_egresado=%s, apellido_paterno=%s, apellido_materno=%s, genero=%s,
                        telefono=%s, correo_electronico=%s, ni=%s, ne=%s, generacion=%s,
                        modalidad=%s, estatus_titulacion=%s, estatus_laboral=%s, perfil=%s,
                        matricula=%s, id_carrera=%s, id_ues=%s, id_municipio=%s, id_localidad=%s,
                        fotografia=%s
                    WHERE id_egresado=%s
                """
                valores = list(datos.values()) + [ruta_foto_s, id_egresado]
            else:
                sql = """
                    UPDATE egresados SET
                        nombre_egresado=%s, apellido_paterno=%s, apellido_materno=%s, genero=%s,
                        telefono=%s, correo_electronico=%s, ni=%s, ne=%s, generacion=%s,
                        modalidad=%s, estatus_titulacion=%s, estatus_laboral=%s, perfil=%s,
                        matricula=%s, id_carrera=%s, id_ues=%s, id_municipio=%s, id_localidad=%s
                    WHERE id_egresado=%s
                """
                valores = list(datos.values()) + [id_egresado]
            
            cursor.execute(sql, valores)
            conexion.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        print("❌ Error al actualizar egresado:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/eliminar_egresado', methods=['POST'])
def eliminar_egresado():
    try:
        id_egresado = request.form.get("id_egresado")
        
        conexion = conectar_db()
        if not conexion:
            return jsonify({"success": False, "message": "No hay conexión a BD"}), 500
        
        with conexion.cursor() as cursor:
            sql = "DELETE FROM egresados WHERE id_egresado = %s"
            cursor.execute(sql, (id_egresado,))
            conexion.commit()
        
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
            
            # Convertir a diccionario
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
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
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras ORDER BY nombre_carrera")
            columns = [desc[0] for desc in cursor.description]
            carreras = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jsonify(carreras)
    finally:
        conexion.close()

@app.route("/vista_estadisticas")
def vista_estadisticas():
    return render_template("estadisticas_egresados.html")

# Ruta faltante para dashboard_control_escolar
@app.route('/dashboard_control_escolar')
def dashboard_control_escolar():
    if 'usercontrol' not in session:
        return redirect(url_for('index'))
    
    conexion = conectar_db()
    if not conexion:
        return redirect(url_for('index'))
    
    try:
        with conexion.cursor() as cursor:
            # Estadísticas básicas
            cursor.execute("SELECT COUNT(*) AS total FROM egresados")
            total_egresados = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) AS total FROM carreras")
            total_carreras = cursor.fetchone()[0]
            
            cursor.execute("SELECT TO_CHAR(CURRENT_DATE, 'DD Month, YYYY') AS fecha")
            ultima_fecha = cursor.fetchone()[0]
        
        return render_template(
            'dashboard_control_escolar.html',
            total_egresados=total_egresados,
            total_carreras=total_carreras,
            ultima_fecha=ultima_fecha
        )
    except Exception as e:
        print(f"Error en dashboard_control_escolar: {e}")
        return redirect(url_for('index'))
    finally:
        conexion.close()

if __name__ == '__main__':
    # Crear directorios necesarios
    os.makedirs('static/uploads/egresados', exist_ok=True)
    os.makedirs('static/uploads/modalidades', exist_ok=True)
    
    # Probar conexión a la base de datos
    conn = conectar_db()
    if conn:
        print("✅ Base de datos PostgreSQL conectada exitosamente")
        conn.close()
    else:
        print("⚠️  Advertencia: No se pudo conectar a la base de datos")
    
    # Ejecutar la aplicación
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
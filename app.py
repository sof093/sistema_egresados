from flask import Flask, Response, jsonify, render_template, request, redirect, session, url_for
import psycopg2
import psycopg2.extras
import logging
from werkzeug.security import generate_password_hash, check_password_hash
import os, uuid
from werkzeug.utils import secure_filename
import sys
from datetime import datetime
import urllib.parse

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'UMB-UES-dev-key-2025-segura')

# ========== CONFIGURACIÓN DE BASE DE DATOS ==========

def get_db_config():
    """
    Obtiene configuración de base de datos desde DATABASE_URL de Render
    o usa configuración manual
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Render usa formato postgres://, psycopg2 necesita postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Parsear URL para obtener componentes
        parsed = urllib.parse.urlparse(database_url)
        
        return {
            'host': parsed.hostname,
            'database': parsed.path[1:],  # Eliminar el '/' inicial
            'user': parsed.username,
            'password': parsed.password,
            'port': parsed.port or 5432,
            'sslmode': 'require'
        }
    else:
        # Configuración manual - USA TUS CREDENCIALES CORRECTAS
        return {
            'host': 'dpg-d5kjdcnfte5s73cmmdu0-a',
            'database': 'egresados_umb_db',
            'user': 'egresados_umb_db_user',
            'password': 'hHE0nFUU1jsz8stqhUGb3s4m2EQI4A82',
            'port': 5432,
            'sslmode': 'require'
        }

def conectar_db():
    """Conectar a PostgreSQL en Render"""
    try:
        config = get_db_config()
        
        # Intentar conexión
        conn = psycopg2.connect(
            host=config['host'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            port=config['port'],
            sslmode=config['sslmode']
        )
        
        print(f"✅ Conexión exitosa a PostgreSQL: {config['host']}")
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        logging.error(f"Error de conexión a PostgreSQL: {e}")
        
        # Para debugging en Render
        config = get_db_config()
        print(f"Configuración usada: host={config['host']}, db={config['database']}, user={config['user']}")
        
        return None

# ========== RUTAS PRINCIPALES ==========

@app.route('/')
def index():
    conn = conectar_db()
    if conn:
        conn.close()
    return render_template('index.html')

@app.route('/inicio')
def inicio():
    conn = conectar_db()
    if not conn:
        return redirect(url_for('index'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
        conn.close()

@app.route('/admin')
def dashboard_admin():
    if 'useradmin' not in session:
        return redirect(url_for('index'))

    conn = conectar_db()
    if not conn:
        return redirect(url_for('index'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # TOTAL EGRESADOS
            cursor.execute("SELECT COUNT(*) AS total FROM egresados")
            total_egresados = cursor.fetchone()['total']

            # ÚLTIMA FECHA
            cursor.execute("SELECT TO_CHAR(CURRENT_DATE, 'DD Month, YYYY') AS fecha")
            ultima_fecha = cursor.fetchone()['fecha']

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
        conn.close()

@app.route('/login_admin', methods=['POST'])
def login_admin():
    username = request.form.get('useradmin', '')
    password = request.form.get('password_coordi', '')
    
    conn = conectar_db()
    if not conn:
        return redirect(url_for('index', error='db'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            sql = "SELECT * FROM coordinador WHERE numero_empleado = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            
            if user and user['password'] == password:
                session['useradmin'] = user['numero_empleado']
                session['nombre'] = user['nombre_coordinador']
                session['fotografia'] = user.get('fotografia', '')
                return redirect(url_for('dashboard_admin'))
            else:
                return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_admin: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conn.close()

@app.route('/login_control', methods=['POST'])
def login_control():
    username = request.form.get('useradmin', '')
    password = request.form.get('password_control', '')
    
    conn = conectar_db()
    if not conn:
        return redirect(url_for('index', error='db'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            sql = "SELECT * FROM control_escolar WHERE numero_empleado = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            
            if user and user['password'] == password:
                session['usercontrol'] = user['numero_empleado']
                session['nombre'] = f"{user['nombre_control']} {user['apellido_paterno']} {user['apellido_materno']}"
                return redirect(url_for('dashboard_control_escolar'))
            else:
                return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_control: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conn.close()

@app.route('/dashboard_control_escolar')
def dashboard_control_escolar():
    if 'usercontrol' not in session:
        return redirect(url_for('index'))
    
    conn = conectar_db()
    if not conn:
        return redirect(url_for('index'))
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM egresados")
            total_egresados = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) AS total FROM carreras")
            total_carreras = cursor.fetchone()['total']
            
            cursor.execute("SELECT TO_CHAR(CURRENT_DATE, 'DD Month, YYYY') AS fecha")
            ultima_fecha = cursor.fetchone()['fecha']
        
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
        conn.close()

@app.route('/dashboard_estudiante')
def dashboard_estudiante():
    if 'user_egresado' in session:
        return render_template('dashboard_estudiante.html', nombre=session.get('nombre', ''))
    else:
        return redirect(url_for('index'))

@app.route('/login_egresado', methods=['POST'])
def login_egresado():
    matricula = request.form.get('matricula', '')
    password = request.form.get('password', '')
    
    conn = conectar_db()
    if not conn:
        return redirect(url_for('index', error='db'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            sql = "SELECT * FROM egresados WHERE matricula = %s"
            cursor.execute(sql, (matricula,))
            egresado = cursor.fetchone()
            
            if egresado and egresado['password'] == password:
                session['user_egresado'] = egresado['matricula']
                session['nombre'] = f"{egresado['nombre_egresado']} {egresado['apellido_paterno']} {egresado['apellido_materno']}"
                return redirect(url_for('dashboard_estudiante'))
            
            return redirect(url_for('index', error='usuario'))
    except Exception as e:
        print(f"Error en login_egresado: {e}")
        return redirect(url_for('index', error='db'))
    finally:
        conn.close()

@app.route('/consulta_egresados')
def consulta_egresados():
    conn = conectar_db()
    if not conn:
        return "Error al conectar la base de datos"

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            sql = "SELECT * FROM egresados ORDER BY id_egresado"
            cursor.execute(sql)
            egresados = cursor.fetchall()
            return render_template('consulta_egresados.html', egresados=egresados)
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ========== RUTAS API (AJAX) ==========

@app.route("/consulta_carrera")
def consulta_carrera():
    conn = conectar_db()
    if not conn:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras ORDER BY nombre_carrera")
            carreras = cursor.fetchall()
            return jsonify([dict(carrera) for carrera in carreras])
    finally:
        conn.close()

@app.route("/consulta_ues")
def consulta_ues():
    conn = conectar_db()
    if not conn:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT id_ues, nombre_ues FROM ues ORDER BY nombre_ues")
            ues = cursor.fetchall()
            return jsonify([dict(u) for u in ues])
    finally:
        conn.close()

@app.route("/consulta_municipio")
def consulta_municipio():
    conn = conectar_db()
    if not conn:
        return jsonify({"error": "Error al conectar a la base de datos"}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT id_municipio, nombre_municipio FROM municipio ORDER BY nombre_municipio")
            municipios = cursor.fetchall()
            return jsonify([dict(m) for m in municipios])
    finally:
        conn.close()

@app.route('/consulta_localidades/<int:id_municipio>')
def consulta_localidades(id_municipio):
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Error al conectar a la base de datos'}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
                SELECT id_localidad, nombre_localidad 
                FROM localidades 
                WHERE id_municipio = %s
                ORDER BY nombre_localidad ASC
            """, (id_municipio,))
            localidades = cursor.fetchall()
            return jsonify([dict(l) for l in localidades])
    finally:
        conn.close()

# ========== CRUD EGRESADOS ==========

@app.route('/registrar_egresado', methods=['POST'])
def registrar_egresado():
    try:
        data = request.form
        files = request.files

        # Validar campos requeridos
        campos_requeridos = [
            'nombre_egresado', 'apellido_paterno', 'apellido_materno', 'genero',
            'telefono', 'correo_electronico', 'ni', 'ne', 'estatus_laboral',
            'estatus_titulacion', 'matricula', 'generacion', 'password',
            'id_carrera', 'perfil', 'id_ues', 'id_municipio', 'id_localidad'
        ]

        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({"success": False, "message": f"Falta el campo {campo}"}), 400

        # Manejar fotografía
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
        
        # Evitar duplicados
        if os.path.exists(ruta_foto):
            base, ext = os.path.splitext(nombre_foto)
            i = 1
            while os.path.exists(os.path.join(dir_fotos, f"{base}_{i}{ext}")):
                i += 1
            ruta_foto = os.path.join(dir_fotos, f"{base}_{i}{ext}")
            ruta_foto_s = os.path.join(dir_foto, f"{base}_{i}{ext}")
        
        foto.save(ruta_foto)

        # Manejar documento de modalidad
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

        # Conectar a BD y registrar
        conn = conectar_db()
        if not conn:
            return jsonify({"success": False, "message": "No se pudo conectar a la base de datos"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            sql = """
            INSERT INTO egresados (
                nombre_egresado, apellido_paterno, apellido_materno, genero, telefono, 
                correo_electronico, ni, ne, estatus_laboral, estatus_titulacion, 
                modalidad, matricula, generacion, password, id_carrera, perfil, 
                id_ues, id_municipio, id_localidad, fotografia, documentos
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_egresado
            """
            
            valores = (
                data['nombre_egresado'], data['apellido_paterno'], data['apellido_materno'], data['genero'],
                data['telefono'], data['correo_electronico'], data['ni'], data['ne'],
                data['estatus_laboral'], data['estatus_titulacion'], modalidad,
                data['matricula'], data['generacion'], data['password'],  # Contraseña sin hash temporal
                data['id_carrera'], data['perfil'], data['id_ues'],
                data['id_municipio'], data['id_localidad'],
                ruta_foto_s.replace('\\', '/'), archivo_modalidad
            )
            
            cursor.execute(sql, valores)
            nuevo_id = cursor.fetchone()['id_egresado']
            conn.commit()
        
        return jsonify({"success": True, "message": "Registro exitoso", "id": nuevo_id})

    except Exception as e:
        logging.exception("Error en registrar_egresado")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/obtener_egresado/<int:id>', methods=['GET'])
def obtener_egresado(id):
    conn = conectar_db()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
            
            return jsonify(dict(egresado))
    except Exception as e:
        print("Error interno:", e)
        return jsonify({"error": "Error interno"}), 500
    finally:
        conn.close()

@app.route('/actualizar_egresado', methods=['POST'])
def actualizar_egresado():
    try:
        id_egresado = request.form['id_egresado']
        
        # Obtener datos
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
            nombre_foto = f"{matricula_segura}_{uuid.uuid4().hex[:8]}{ext}"
            ruta_foto = os.path.join(dir_fotos, nombre_foto)
            ruta_foto_s = os.path.join(dir_foto, nombre_foto)
            
            foto.save(ruta_foto)

        conn = conectar_db()
        if not conn:
            return jsonify({"success": False, "message": "No hay conexión a BD"}), 500

        with conn.cursor() as cursor:
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
            conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        print("❌ Error al actualizar egresado:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/eliminar_egresado', methods=['POST'])
def eliminar_egresado():
    try:
        id_egresado = request.form.get("id_egresado")
        
        conn = conectar_db()
        if not conn:
            return jsonify({"success": False, "message": "No hay conexión a BD"}), 500
        
        with conn.cursor() as cursor:
            sql = "DELETE FROM egresados WHERE id_egresado = %s"
            cursor.execute(sql, (id_egresado,))
            conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ========== ESTADÍSTICAS ==========

@app.route("/datos_estadisticas")
def datos_estadisticas():
    estatus = request.args.get("estatus")
    carrera = request.args.get("carrera")
    
    conn = conectar_db()
    if not conn:
        return jsonify([])
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
            return jsonify([dict(d) for d in data])
    finally:
        conn.close()

@app.route("/lista_carreras")
def lista_carreras():
    conn = conectar_db()
    if not conn:
        return jsonify([])
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras ORDER BY nombre_carrera")
            carreras = cursor.fetchall()
            return jsonify([dict(c) for c in carreras])
    finally:
        conn.close()

@app.route("/vista_estadisticas")
def vista_estadisticas():
    return render_template("estadisticas_egresados.html")

# ========== PÁGINA DE PRUEBA DE CONEXIÓN ==========

@app.route('/test_db')
def test_db():
    """Página para probar la conexión a la base de datos"""
    try:
        conn = conectar_db()
        if not conn:
            return "❌ No se pudo conectar a la base de datos"
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Tablas existentes
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tablas = cursor.fetchall()
            
            # Conteo de registros
            cursor.execute("SELECT COUNT(*) as total FROM egresados")
            total_egresados = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM carreras")
            total_carreras = cursor.fetchone()['total']
            
        conn.close()
        
        html = f"""
        <h1>✅ Conexión a PostgreSQL Exitosa</h1>
        <p><strong>Host:</strong> dpg-d5kjdcnfte5s73cmmdu0-a</p>
        <p><strong>Base de datos:</strong> egresados_umb_db</p>
        <hr>
        <h2>Estadísticas:</h2>
        <p>Total egresados: {total_egresados}</p>
        <p>Total carreras: {total_carreras}</p>
        <hr>
        <h2>Tablas en la base de datos:</h2>
        <ul>
        """
        
        for tabla in tablas:
            html += f"<li>{tabla['table_name']}</li>"
        
        html += "</ul>"
        html += '<p><a href="/">Volver al inicio</a></p>'
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ========== INICIALIZACIÓN ==========

if __name__ == '__main__':
    # Crear directorios necesarios
    os.makedirs('static/uploads/egresados', exist_ok=True)
    os.makedirs('static/uploads/modalidades', exist_ok=True)
    
    # Probar conexión a la base de datos
    print("🔄 Probando conexión a PostgreSQL...")
    try:
        conn = conectar_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM egresados")
                count = cursor.fetchone()[0]
                print(f"✅ Base de datos conectada. Egresados: {count}")
            conn.close()
        else:
            print("⚠️  No se pudo conectar a la base de datos")
    except Exception as e:
        print(f"⚠️  Error en conexión inicial: {e}")
    
    # Configurar puerto para Render
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Iniciando aplicación en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
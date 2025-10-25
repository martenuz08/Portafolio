from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import mysql.connector
import secrets
import calendar

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ------------------------------------------------
# 🔹 Conexión a MySQL
# ------------------------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="123ABCDEFabcdef",  # ⚠️ Cambia por tu contraseña real
        database="mi_basedatos"
    )

# ------------------------------------------------
# 🟢 LOGIN
# ------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Por favor completa todos los campos.", "error")
            return redirect(url_for("login"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            # Guardamos 0/1 como entero para facilidad
            session["is_admin"] = int(user.get("is_admin", 0) or 0)
            flash("Inicio de sesión exitoso.", "success")
            return redirect(url_for("home"))
        else:
            flash("Correo o contraseña incorrectos.", "error")

    return render_template("login.html")

# ------------------------------------------------
# 🟢 REGISTRO
# ------------------------------------------------
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Por favor completa todos los campos.", "error")
            return redirect(url_for("registro"))

        hash_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (email, password) VALUES (%s, %s)",
                (email, hash_password)
            )
            conn.commit()
        except mysql.connector.Error as e:
            print("DB ERROR registro:", e)
            flash("Ocurrió un error al registrar el usuario. Verifica si el email ya existe.", "error")
            return redirect(url_for("registro"))
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

        flash("Registro exitoso. ¡Ahora puedes iniciar sesión!", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")

# ------------------------------------------------
# Helper: cargar contenido por página
# ------------------------------------------------
def cargar_contenido_por_pagina(nombre_pagina):
    """
    Devuelve un dict {campo: texto} con el contenido de la tabla 'contenido'
    para la página solicitada. Si no hay registros, devuelve {}.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT campo, texto FROM contenido WHERE pagina = %s", (nombre_pagina,))
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB ERROR cargar_contenido_por_pagina({nombre_pagina}):", e)
        filas = []

    contenido = {fila["campo"]: fila["texto"] for fila in filas} if filas else {}
    return contenido

# ------------------------------------------------
# 🟢 INICIO / PÁGINA PRINCIPAL (usa contenido dinámico)
# ------------------------------------------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    contenido = cargar_contenido_por_pagina("inicio")
    return render_template("index.html", contenido=contenido)

@app.route("/inicio")
def inicio():
    return redirect(url_for("home"))
# ------------------------------------------------
# 🟢 LOGOUT
# ------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for("login"))

# ------------------------------------------------
# 🗓️ CALENDARIO
# ------------------------------------------------
@app.route("/calendario/<int:mes>/<int:anio>")
def calendario_view(mes, anio):
    if "user_id" not in session:
        return redirect(url_for("login"))

    cal = calendar.monthcalendar(anio, mes)
    nombre_mes = calendar.month_name[mes]

    # Traer eventos del usuario
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM eventos WHERE user_id = %s", (session["user_id"],))
    eventos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("calendario.html",
                           cal=cal,
                           mes=mes,
                           anio=anio,
                           nombre_mes=nombre_mes,
                           eventos=eventos)

@app.route("/calendario")
def calendario_alias():
    hoy = date.today()
    return redirect(url_for('calendario_view', mes=hoy.month, anio=hoy.year))

@app.route("/agregar_evento", methods=["POST"])
def agregar_evento():
    if "user_id" not in session:
        return redirect(url_for("login"))

    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    fecha = request.form.get("fecha")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO eventos (user_id, fecha, titulo, descripcion) VALUES (%s, %s, %s, %s)",
        (session["user_id"], fecha, titulo, descripcion)
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("Evento agregado exitosamente.", "success")
    return redirect(url_for("calendario_view", mes=int(fecha[5:7]), anio=int(fecha[:4])))

# ------------------------------------------------
# ⚖️ IMC
# ------------------------------------------------
@app.route("/imc", methods=["GET", "POST"])
def imc():
    resultado = None
    if request.method == "POST":
        try:
            peso = float(request.form.get("peso"))
            altura = float(request.form.get("altura")) / 100  # cm a metros
            imc_valor = round(peso / (altura ** 2), 2)

            if imc_valor < 18.5:
                resultado = f"Tu IMC es {imc_valor}. Estás por debajo del peso ideal."
            elif 18.5 <= imc_valor < 25:
                resultado = f"Tu IMC es {imc_valor}. ¡Estás en un peso saludable!"
            elif 25 <= imc_valor < 30:
                resultado = f"Tu IMC es {imc_valor}. Tienes sobrepeso."
            else:
                resultado = f"Tu IMC es {imc_valor}. Obesidad, cuida tu salud."
        except:
            resultado = "Por favor ingresa valores válidos."
    return render_template("imc.html", resultado=resultado)

# ------------------------------------------------
# ⏱️ CRONÓMETRO
# ------------------------------------------------
@app.route("/cronometro")
def cronometro():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("cronometro.html")

# ------------------------------------------------
# 📄 PÁGINAS ESTÁTICAS (ahora dinámicas)
# ------------------------------------------------
@app.route("/acercademi")
def acercademi():
    if "user_id" not in session:
        return redirect(url_for("login"))

    contenido = cargar_contenido_por_pagina("acercademi")
    return render_template("acercademi.html", contenido=contenido)

@app.route("/proyecto")
def proyecto():
    if "user_id" not in session:
        return redirect(url_for("login"))

    contenido = cargar_contenido_por_pagina("proyectos")
    return render_template("proyecto.html", contenido=contenido)

@app.route("/contacto")
def contacto():
    if "user_id" not in session:
        return redirect(url_for("login"))

    contenido = cargar_contenido_por_pagina("contacto")
    return render_template("contacto.html", contenido=contenido)

# ------------------------------------------------
# 📨 CONTACTÁNDOME (vista ADMIN)
# ------------------------------------------------
@app.route("/contactandome")
def contactandome():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin"):
        return redirect(url_for("contacto"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM contactos ORDER BY id DESC")
    mensajes = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("contactandome.html", mensajes=mensajes, email=session.get("email"))

# ------------------------------------------------
# 📩 GUARDAR CONTACTO (Usuarios NO Admin)
# ------------------------------------------------
@app.route("/guardar_contacto", methods=["POST"])
def guardar_contacto():
    data = request.get_json() or {}
    nombre = data.get("nombre", "").strip()
    telefono = data.get("telefono", "").strip()
    email = data.get("email", "").strip()
    mensaje = data.get("mensaje", "").strip()

    if not nombre or not email or not mensaje:
        return jsonify({"mensaje": "Faltan datos obligatorios"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contactos (nombre, telefono, email, mensaje) VALUES (%s, %s, %s, %s)",
            (nombre, telefono, email, mensaje)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"mensaje": "Mensaje enviado correctamente"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"mensaje": "Error al guardar el mensaje"}), 500

# ------------------------------------------------
# 📩 ADMIN: LISTAR Y EDITAR CONTENIDO (TABLA 'contenido')
# ------------------------------------------------
@app.route("/admin/contenido")
def admin_contenido():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("home"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM contenido ORDER BY pagina, campo")
        datos = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print("DB ERROR admin_contenido:", e)
        datos = []

    return render_template("admin_contenido.html", contenido=datos)

@app.route("/admin/editar/<int:id_contenido>", methods=["GET", "POST"])
def editar_contenido(id_contenido):
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("home"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            nuevo_texto = request.form.get("texto", "")
            cursor.execute(
                "UPDATE contenido SET texto = %s WHERE id = %s",
                (nuevo_texto, id_contenido)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("Contenido actualizado correctamente", "success")
            return redirect(url_for("admin_contenido"))

        cursor.execute("SELECT * FROM contenido WHERE id = %s", (id_contenido,))
        dato = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        print("DB ERROR editar_contenido:", e)
        flash("Ocurrió un error al acceder al contenido", "error")
        return redirect(url_for("admin_contenido"))

    return render_template("editar_texto.html", contenido=dato)

@app.route("/admin/guardar_pagina", methods=["POST"])
def guardar_pagina():
    if "user_id" not in session or not session.get("is_admin"):
        return jsonify({"mensaje": "Acceso denegado"}), 403

    data = request.get_json()
    nombre_pagina = data.get("pagina")
    contenido = data.get("contenido", {})

    if not nombre_pagina or not contenido:
        return jsonify({"mensaje": "Datos incompletos"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for campo, texto in contenido.items():
            # Verificar si el campo ya existe
            cursor.execute(
                "SELECT id FROM contenido WHERE pagina = %s AND campo = %s",
                (nombre_pagina, campo)
            )
            resultado = cursor.fetchone()

            if resultado:
                # Actualizar si existe
                cursor.execute(
                    "UPDATE contenido SET texto = %s WHERE pagina = %s AND campo = %s",
                    (texto, nombre_pagina, campo)
                )
            else:
                # Insertar si no existe
                cursor.execute(
                    "INSERT INTO contenido (pagina, campo, texto) VALUES (%s, %s, %s)",
                    (nombre_pagina, campo, texto)
                )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"mensaje": "Cambios guardados correctamente"}), 200

    except Exception as e:
        print("DB ERROR guardar_pagina:", e)
        return jsonify({"mensaje": "Error al guardar cambios"}), 500
# ------------------------------------------------
# 🏁 EJECUCIÓN
# ------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
from datetime import datetime
import hashlib
import os
import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)
DB_NAME = "database.db"

# Сюда вставляется ключ API Геокодера Яндекс Карт
YANDEX_API_KEY = "a6cba383-c68b-4835-96ce-ab169b2831fc"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'employee'))
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS work_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER,
                address TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        conn.commit()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_address_from_yandex(lat, lon):
    if not YANDEX_API_KEY or YANDEX_API_KEY == "ТВОЙ_API_КЛЮЧ_ЯНДЕКСА":
        return "Адрес недоступен (API ключ не настроен)"
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": f"{lon},{lat}",
        "format": "json",
        "results": 1,
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            members = data["response"]["GeoObjectCollection"]["featureMember"]
            if members:
                return members[0]["GeoObject"]["metaDataProperty"][
                    "GeocoderMetaData"
                ]["text"]
    except Exception:
        pass
    return f"Координаты: {lat}, {lon}"


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    role = session["role"]

    with get_db_connection() as conn:
        if role == "admin":
            query = """
                SELECT ws.*, u.username 
                FROM work_sessions ws 
                JOIN users u ON ws.user_id = u.id 
                ORDER BY ws.id DESC
            """
            sessions_log = conn.execute(query).fetchall()
            return render_template(
                "admin.html",
                username=session["username"],
                sessions=sessions_log,
            )
        else:
            current_session = conn.execute(
                "SELECT * FROM work_sessions WHERE user_id = ? AND end_time IS NULL",
                (user_id,),
            ).fetchone()
            history = conn.execute(
                "SELECT * FROM work_sessions WHERE user_id = ? AND end_time IS NOT NULL ORDER BY id DESC",
                (user_id,),
            ).fetchall()
            return render_template(
                "employee.html",
                username=session["username"],
                current_session=current_session,
                history=history,
            )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form["role"]

        if not username or not password:
            flash("Заполните все поля")
            return redirect(url_for("register"))

        h_pass = hash_password(password)

        with get_db_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, h_pass, role),
                )
                conn.commit()
                flash("Регистрация успешна. Войдите в аккаунт.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Пользователь с таким логином уже существует")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        with get_db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

            if user and user["password_hash"] == hash_password(password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                return redirect(url_for("index"))
            else:
                flash("Неверный логин или пароль")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- API ЭНДПОИНТ ДЛЯ ЖЕТОНА/КНОПКИ ---


@app.route("/api/session/toggle", methods=["POST"])
def api_toggle():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.get_json() or {}
    lat = data.get("lat")
    lon = data.get("lon")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        active = cursor.execute(
            "SELECT * FROM work_sessions WHERE user_id = ? AND end_time IS NULL",
            (user_id,),
        ).fetchone()

        if not active:
            address = (
                get_address_from_yandex(lat, lon)
                if lat and lon
                else "Локация не передана"
            )
            cursor.execute(
                "INSERT INTO work_sessions (user_id, start_time, address) VALUES (?, ?, ?)",
                (user_id, now, address),
            )
            conn.commit()
            return jsonify({"status": "started", "time": now, "address": address})
        else:
            start_dt = datetime.strptime(
                active["start_time"], "%Y-%m-%d %H:%M:%S"
            )
            duration = int((datetime.now() - start_dt).total_seconds())

            cursor.execute(
                "UPDATE work_sessions SET end_time = ?, duration = ? WHERE id = ?",
                (now, duration, active["id"]),
            )
            conn.commit()
            return jsonify({"status": "stopped", "time": now, "duration": duration})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
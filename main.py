import sys
import os
import sqlite3
import csv
import secrets
import string
import urllib.request
import urllib.parse
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QStackedWidget, QListWidget, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, 
                             QFileDialog, QAbstractItemView, QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

# Строгий корпоративный стиль
STYLE_SHEET = """
    QWidget {
        background-color: #1E1E1E;
        color: #E0E0E0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    QMainWindow {
        background-color: #121212;
    }
    QLineEdit {
        background-color: #2D2D30;
        border: 1px solid #3E3E42;
        border-radius: 3px;
        padding: 8px;
        color: #FFFFFF;
    }
    QLineEdit:focus {
        border: 1px solid #007ACC;
    }
    QPushButton {
        background-color: #007ACC;
        border: none;
        border-radius: 3px;
        padding: 8px 16px;
        color: white;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #0098FF;
    }
    QPushButton:pressed {
        background-color: #005A9E;
    }
    QPushButton#dangerBtn {
        background-color: #C53030;
    }
    QPushButton#dangerBtn:hover {
        background-color: #E53E3E;
    }
    QListWidget {
        background-color: #252526;
        border: none;
        border-right: 1px solid #333337;
        padding: 5px;
    }
    QListWidget::item {
        padding: 10px;
        border-radius: 3px;
        margin-bottom: 2px;
    }
    QListWidget::item:selected {
        background-color: #37373D;
        color: white;
        border-left: 3px solid #007ACC;
    }
    QTableWidget {
        background-color: #1E1E1E;
        border: 1px solid #3E3E42;
        gridline-color: #3E3E42;
    }
    QHeaderView::section {
        background-color: #2D2D30;
        color: #CCCCCC;
        padding: 6px;
        border: 1px solid #3E3E42;
        font-weight: bold;
    }
"""

class DatabaseManager:
    def __init__(self, db_path="entrypro_data.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fio TEXT,
                    role TEXT,
                    company_id INTEGER,
                    login TEXT UNIQUE,
                    password TEXT,
                    tg_chat_id TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    duration TEXT
                )
            """)
            
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO companies (name) VALUES ('ООО «СинхроТех»')")
                comp_id = cursor.lastrowid
                
                cursor.execute("INSERT INTO users (fio, role, company_id, login, password) VALUES (?, ?, ?, ?, ?)",
                               ('Громов Сергей Николаевич', 'director', comp_id, 'admin', 'admin'))
                cursor.execute("INSERT INTO users (fio, role, company_id, login, password) VALUES (?, ?, ?, ?, ?)",
                               ('Котов Максим Андреевич', 'employee', comp_id, 'user1', '12345'))
                conn.commit()

class LoginWindow(QWidget):
    def __init__(self, db, on_login_success):
        super().__init__()
        self.db = db
        self.on_login_success = on_login_success
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("EntryPro — Авторизация")
        self.setFixedSize(350, 400)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists("logo.png"):
            pixmap = QPixmap("logo.png")
            scaled_pixmap = pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("ENTRYPRO")
            self.logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007ACC; letter-spacing: 2px;")
        
        layout.addWidget(self.logo_label)
        layout.addSpacing(20)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        layout.addWidget(self.login_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Пароль")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_input)

        layout.addSpacing(10)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setFixedHeight(35)
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)

        self.setLayout(layout)

    def handle_login(self):
        login = self.login_input.text().strip()
        password = self.pass_input.text().strip()

        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля.")
            return

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.fio, u.role, u.company_id, u.tg_chat_id, c.name 
                FROM users u 
                JOIN companies c ON u.company_id = c.id
                WHERE u.login = ? AND u.password = ? AND u.is_active = 1
            """, (login, password))
            user_data = cursor.fetchone()

            if user_data:
                self.on_login_success(user_data)
            else:
                QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль.")

class EmployeeWindow(QMainWindow):
    def __init__(self, db, user_info, on_logout):
        super().__init__()
        self.db = db
        self.user_id, self.user_fio, self.user_role, self.comp_id, self.tg_id, self.comp_name = user_info
        self.on_logout = on_logout
        self.current_session_id = None
        self.session_start_dt = None
        
        self.init_ui()
        self.check_active_session()

    def init_ui(self):
        self.setWindowTitle(f"EntryPro — Кабинет сотрудника: {self.user_fio}")
        self.setMinimumSize(700, 450)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(180)
        self.menu_list.addItems(["Рабочий стол", "Профиль", "Настройки"])
        self.menu_list.currentRowChanged.connect(self.switch_tab)
        main_layout.addWidget(self.menu_list)

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(self.stack)

        self.create_desktop_tab()
        self.create_profile_tab()
        self.create_settings_tab()
        
        self.menu_list.setCurrentRow(0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer_display)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.load_last_sessions()

    def create_desktop_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setStyleSheet("font-size: 42px; font-weight: bold; color: #FFFFFF;")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_timer)

        self.lbl_status = QLabel("Статус: Смена закрыта")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #AAAAAA; margin-bottom: 10px;")
        layout.addWidget(self.lbl_status)

        self.btn_action = QPushButton("Начать рабочую смену")
        self.btn_action.setFixedHeight(40)
        self.btn_action.clicked.connect(self.toggle_session)
        layout.addWidget(self.btn_action)

        layout.addSpacing(20)
        layout.addWidget(QLabel("Последние сессии:"))
        
        self.table_history = QTableWidget(5, 3)
        self.table_history.setHorizontalHeaderLabels(["Начало", "Конец", "Длительность"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_history.verticalHeader().setVisible(False)
        layout.addWidget(self.table_history)

        self.stack.addWidget(page)

    def create_profile_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(QLabel("ИНФОРМАЦИЯ О СОТРУДНИКЕ"))
        layout.addWidget(QLabel(f"ФИО: {self.user_fio}"))
        layout.addWidget(QLabel("Должность: Сотрудник"))
        layout.addWidget(QLabel(f"Внутренний ID: {self.user_id}"))
        
        layout.addSpacing(20)
        layout.addWidget(QLabel("ОРГАНИЗАЦИЯ"))
        layout.addWidget(QLabel(f"Название: {self.comp_name}"))
        
        layout.addStretch()
        self.stack.addWidget(page)

    def create_settings_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Уведомления Telegram"))
        
        tg_bar = QHBoxLayout()
        self.tg_input = QLineEdit()
        self.tg_input.setPlaceholderText("Telegram Chat ID")
        if self.tg_id:
            self.tg_input.setText(str(self.tg_id))
        tg_bar.addWidget(self.tg_input)

        # Кнопка вызова инструкции с автоматической шириной и красивыми отступами
        btn_help = QPushButton("Как подключить?")
        btn_help.setStyleSheet("""
            QPushButton {
                background-color: #37373D; 
                font-weight: normal;
                padding-left: 12px;
                padding-right: 12px;
            }
            QPushButton:hover {
                background-color: #4F4F56;
            }
        """)
        btn_help.clicked.connect(self.show_tg_tutorial)
        tg_bar.addWidget(btn_help)
        
        layout.addLayout(tg_bar)

        btn_save_tg = QPushButton("Сохранить")
        btn_save_tg.clicked.connect(self.save_tg)
        layout.addWidget(btn_save_tg)

        layout.addSpacing(20)
        layout.addWidget(QLabel("Безопасность"))
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Новый пароль")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_input)

        btn_save_pass = QPushButton("Изменить пароль")
        btn_save_pass.clicked.connect(self.change_password)
        layout.addWidget(btn_save_pass)

        layout.addStretch()
        
        btn_logout = QPushButton("Выйти из аккаунта")
        btn_logout.setObjectName("dangerBtn")
        btn_logout.clicked.connect(self.on_logout)
        layout.addWidget(btn_logout)
        
        self.stack.addWidget(page)

    def show_tg_tutorial(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Инструкция: Подключение Telegram")
        dialog.setFixedSize(400, 250)
        dl = QVBoxLayout(dialog)
        dl.setSpacing(10)

        tutorial_text = (
            "<b>Как настроить уведомления за 3 шага:</b><br><br>"
            "1. Найдите в Telegram бота <b>@userinfobot</b> и отправьте ему "
            "любое сообщение. В ответ он пришлет ваш <b>Id</b> (набор цифр).<br><br>"
            "2. Найдите нашего рабочего бота и нажмите "
            "кнопку <b>Старт (/start)</b>, чтобы разрешить ему отправку.<br><br>"
            "3. Скопируйте цифровой ID из первого шага, вставьте его в поле ввода "
            "в приложении и нажмите кнопку <b>«Сохранить»</b>."
        )
        
        lbl = QLabel(tutorial_text)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        dl.addWidget(lbl)
        
        btn_close = QPushButton("Понятно")
        btn_close.clicked.connect(dialog.accept)
        dl.addWidget(btn_close)
        
        dialog.exec()

    def send_tg_notification(self, text):
        if not self.tg_id:
            return
            
        TOKEN = "8886255680:AAE5FxJ5qxAdf9LDpEsmgcmAIUet-e08pS4" 
        
        encoded_text = urllib.parse.quote(text)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={self.tg_id}&text={encoded_text}"
        
        try:
            urllib.request.urlopen(url, timeout=3)
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")

    def check_active_session(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, start_time FROM sessions WHERE user_id = ? AND end_time IS NULL", (self.user_id,))
            row = cursor.fetchone()
            if row:
                self.current_session_id = row[0]
                self.session_start_dt = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
                self.lbl_status.setText(f"В работе с: {row[1]}")
                self.btn_action.setText("Завершить рабочую смену")
                self.btn_action.setObjectName("dangerBtn")
                self.btn_action.setStyleSheet(STYLE_SHEET)
                self.timer.start(1000)
            else:
                self.load_last_sessions()

    def load_last_sessions(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_time, end_time, duration FROM sessions WHERE user_id = ? AND end_time IS NOT NULL ORDER BY id DESC LIMIT 5", (self.user_id,))
            rows = cursor.fetchall()
            self.table_history.setRowCount(len(rows))
            for r_idx, row in enumerate(rows):
                for c_idx, val in enumerate(row):
                    self.table_history.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def toggle_session(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if self.current_session_id is None:
                cursor.execute("INSERT INTO sessions (user_id, start_time) VALUES (?, ?)", (self.user_id, now_str))
                self.current_session_id = cursor.lastrowid
                self.session_start_dt = datetime.now()
                self.lbl_status.setText(f"В работе с: {now_str}")
                self.btn_action.setText("Завершить рабочую смену")
                self.btn_action.setObjectName("dangerBtn")
                self.timer.start(1000)
                
                self.send_tg_notification(f"🟢 {self.user_fio} НАЧАЛ рабочую смену.\nВремя: {now_str}")
            else:
                self.timer.stop()
                duration = str(datetime.now() - self.session_start_dt).split('.')[0]
                cursor.execute("UPDATE sessions SET end_time = ?, duration = ? WHERE id = ?", (now_str, duration, self.current_session_id))
                self.current_session_id = None
                self.session_start_dt = None
                self.lbl_status.setText("Статус: Смена закрыта")
                self.btn_action.setText("Начать рабочую смену")
                self.btn_action.setObjectName("")
                self.lbl_timer.setText("00:00:00")
                self.load_last_sessions()
                
                self.send_tg_notification(f"🔴 {self.user_fio} ЗАВЕРШИЛ смену.\nОтработано времени: {duration}")
            conn.commit()
            self.btn_action.setStyleSheet(STYLE_SHEET)

    def update_timer_display(self):
        if self.session_start_dt:
            diff = datetime.now() - self.session_start_dt
            self.lbl_timer.setText(str(diff).split('.')[0])

    def save_tg(self):
        tg = self.tg_input.text().strip()
        with self.db.get_connection() as conn:
            conn.cursor().execute("UPDATE users SET tg_chat_id = ? WHERE id = ?", (tg, self.user_id))
            conn.commit()
        self.tg_id = tg
        QMessageBox.information(self, "Успешно", "Настройки сохранены.")

    def change_password(self):
        pwd = self.pass_input.text().strip()
        if not pwd: return
        with self.db.get_connection() as conn:
            conn.cursor().execute("UPDATE users SET password = ? WHERE id = ?", (pwd, self.user_id))
            conn.commit()
        QMessageBox.information(self, "Успешно", "Пароль изменен.")
        self.pass_input.clear()


class DirectorWindow(QMainWindow):
    def __init__(self, db, user_info, on_logout):
        super().__init__()
        self.db = db
        self.user_id, self.user_fio, self.user_role, self.comp_id, _, self.comp_name = user_info
        self.on_logout = on_logout
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Панель управления — {self.comp_name}")
        self.setMinimumSize(950, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(200)
        self.menu_list.addItems(["Мониторинг", "Сотрудники", "История сессий", "Настройки"])
        self.menu_list.currentRowChanged.connect(self.switch_tab)
        main_layout.addWidget(self.menu_list)

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(self.stack)

        self.create_monitoring_tab()
        self.create_employees_tab()
        self.create_history_tab()
        self.create_settings_tab()

        self.menu_list.setCurrentRow(0)
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_monitoring_data)
        self.refresh_timer.start(5000) 

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0: self.load_monitoring_data()
        elif index == 1: self.load_employees_data()
        elif index == 2: self.load_history_data()

    def create_monitoring_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        self.lbl_comp_info = QLabel(f"Организация: {self.comp_name}")
        self.lbl_comp_info.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(self.lbl_comp_info)

        self.table_monitor = QTableWidget(0, 4)
        self.table_monitor.setHorizontalHeaderLabels(["ID", "Сотрудник", "Статус", "В работе"])
        self.table_monitor.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_monitor.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_monitor.verticalHeader().setVisible(False)
        layout.addWidget(self.table_monitor)
        self.stack.addWidget(page)

    def load_monitoring_data(self):
        if self.stack.currentIndex() != 0: return
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.fio, s.start_time 
                FROM users u 
                LEFT JOIN sessions s ON u.id = s.user_id AND s.end_time IS NULL
                WHERE u.company_id = ? AND u.role = 'employee' AND u.is_active = 1
            """, (self.comp_id,))
            rows = cursor.fetchall()
            self.table_monitor.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                status = "В сети" if r[2] else "Оффлайн"
                duration = str(datetime.now() - datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S")).split('.')[0] if r[2] else "—"
                
                self.table_monitor.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                self.table_monitor.setItem(idx, 1, QTableWidgetItem(r[1]))
                self.table_monitor.setItem(idx, 2, QTableWidgetItem(status))
                self.table_monitor.setItem(idx, 3, QTableWidgetItem(duration))

    def create_employees_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        top_bar = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self.add_employee_dialog)
        top_bar.addWidget(btn_add)
        
        btn_export = QPushButton("Экспорт доступов (CSV)")
        btn_export.clicked.connect(self.export_access_data)
        top_bar.addWidget(btn_export)
        top_bar.addStretch()
        
        layout.addLayout(top_bar)

        self.table_emp = QTableWidget(0, 4)
        self.table_emp.setHorizontalHeaderLabels(["ID", "ФИО", "Логин", "Пароль"])
        self.table_emp.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_emp.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_emp.verticalHeader().setVisible(False)
        self.table_emp.itemSelectionChanged.connect(self.on_employee_selected)
        layout.addWidget(self.table_emp)

        self.actions_panel = QWidget()
        self.panel_layout = QHBoxLayout(self.actions_panel)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_fire = QPushButton("Уволить (Деактивировать)")
        self.btn_fire.setObjectName("dangerBtn")
        self.btn_fire.clicked.connect(self.fire_employees)
        self.panel_layout.addWidget(self.btn_fire)
        self.panel_layout.addStretch()
        
        self.actions_panel.setVisible(False)
        layout.addWidget(self.actions_panel)

        self.stack.addWidget(page)

    def load_employees_data(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, fio, login, password FROM users WHERE company_id = ? AND role = 'employee' AND is_active = 1", (self.comp_id,))
            rows = cursor.fetchall()
            self.table_emp.setRowCount(len(rows))
            for r_idx, row in enumerate(rows):
                for c_idx, val in enumerate(row):
                    self.table_emp.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
        self.actions_panel.setVisible(False)

    def on_employee_selected(self):
        selected = self.table_emp.selectionModel().selectedRows()
        self.actions_panel.setVisible(len(selected) > 0)

    def fire_employees(self):
        selected = self.table_emp.selectionModel().selectedRows()
        if not selected: return
        
        reply = QMessageBox.question(self, 'Подтверждение', f"Деактивировать выбранные аккаунты?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                for index in selected:
                    emp_id = self.table_emp.item(index.row(), 0).text()
                    cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (emp_id,))
                conn.commit()
            self.load_employees_data()

    def add_employee_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Регистрация сотрудника")
        dialog.setFixedSize(300, 180)
        dl = QVBoxLayout(dialog)
        
        fio_in = QLineEdit()
        fio_in.setPlaceholderText("ФИО сотрудника")
        log_in = QLineEdit()
        log_in.setPlaceholderText("Логин")
        
        dl.addWidget(fio_in)
        dl.addWidget(log_in)
        
        btn = QPushButton("Сгенерировать доступ")
        dl.addWidget(btn)
        
        def save():
            fio = fio_in.text().strip()
            login = log_in.text().strip()
            
            if fio and login:
                alphabet = string.ascii_letters + string.digits
                generated_password = ''.join(secrets.choice(alphabet) for _ in range(8))
                
                try:
                    with self.db.get_connection() as conn:
                        conn.cursor().execute(
                            "INSERT INTO users (fio, role, company_id, login, password) VALUES (?, 'employee', ?, ?, ?)",
                            (fio, self.comp_id, login, generated_password)
                        )
                        conn.commit()
                    
                    dialog.accept()
                    self.load_employees_data()
                    
                    QMessageBox.information(
                        self, 
                        "Пользователь создан", 
                        f"Сотрудник: {fio}\nЛогин: {login}\nПароль: {generated_password}\n\n(Скопируйте и передайте сотруднику)"
                    )
                except sqlite3.IntegrityError:
                    QMessageBox.critical(dialog, "Ошибка", "Этот логин уже занят.")
            else:
                QMessageBox.warning(dialog, "Ошибка", "Заполните ФИО и Логин.")
                
        btn.clicked.connect(save)
        dialog.exec()

    def export_access_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить доступы", "employees.csv", "CSV Files (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "ФИО", "Логин", "Пароль"])
                for r in range(self.table_emp.rowCount()):
                    writer.writerow([self.table_emp.item(r, c).text() for c in range(4)])
            QMessageBox.information(self, "Готово", "Данные выгружены.")

    def create_history_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        filter_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по ФИО сотрудника...")
        self.search_input.textChanged.connect(self.load_history_data)
        filter_bar.addWidget(self.search_input)

        btn_export_hist = QPushButton("Выгрузить в CSV")
        btn_export_hist.clicked.connect(self.export_history_data)
        filter_bar.addWidget(btn_export_hist)
        layout.addLayout(filter_bar)

        self.table_history = QTableWidget(0, 5)
        self.table_history.setHorizontalHeaderLabels(["ID", "Сотрудник", "Начало", "Конец", "Длительность"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.verticalHeader().setVisible(False)
        self.table_history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_history)

        self.stack.addWidget(page)

    def load_history_data(self):
        search_txt = self.search_input.text().strip()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT s.id, u.fio, s.start_time, s.end_time, s.duration 
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE u.company_id = ? AND u.fio LIKE ? AND s.end_time IS NOT NULL
                ORDER BY s.id DESC
            """
            cursor.execute(query, (self.comp_id, f"%{search_txt}%"))
            rows = cursor.fetchall()
            self.table_history.setRowCount(len(rows))
            for r_idx, row in enumerate(rows):
                for c_idx, val in enumerate(row):
                    self.table_history.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def export_history_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить историю", "history.csv", "CSV Files (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID Сессии", "Сотрудник", "Начало", "Конец", "Длительность"])
                for r in range(self.table_history.rowCount()):
                    writer.writerow([self.table_history.item(r, c).text() for c in range(5)])
            QMessageBox.information(self, "Готово", "История сохранена.")

    def create_settings_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Системные настройки"))
        self.comp_name_input = QLineEdit()
        self.comp_name_input.setText(self.comp_name)
        layout.addWidget(QLabel("Название организации:"))
        layout.addWidget(self.comp_name_input)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_global_settings)
        layout.addWidget(btn_save)

        layout.addStretch()
        btn_logout = QPushButton("Завершить сеанс")
        btn_logout.setObjectName("dangerBtn")
        btn_logout.clicked.connect(self.on_logout)
        layout.addWidget(btn_logout)

        self.stack.addWidget(page)

    def save_global_settings(self):
        new_name = self.comp_name_input.text().strip()
        if not new_name: return
        with self.db.get_connection() as conn:
            conn.cursor().execute("UPDATE companies SET name = ? WHERE id = ?", (new_name, self.comp_id))
            conn.commit()
        QMessageBox.information(self, "Успешно", "Данные обновлены. Требуется перезапуск для применения.")

class ApplicationController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyleSheet(STYLE_SHEET)
        self.db = DatabaseManager()
        self.current_window = None

    def show_login(self):
        if self.current_window:
            self.current_window.close()
        self.current_window = LoginWindow(self.db, self.handle_login_success)
        self.current_window.show()

    def handle_login_success(self, user_data):
        role = user_data[2]
        self.current_window.close()
        
        if role == 'director':
            self.current_window = DirectorWindow(self.db, user_data, self.show_login)
        else:
            self.current_window = EmployeeWindow(self.db, user_data, self.show_login)
        self.current_window.show()

    def run(self):
        self.show_login()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    controller = ApplicationController()
    controller.run()
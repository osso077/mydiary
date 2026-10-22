import sqlite3
import datetime
import bcrypt
import os
import streamlit as st
from streamlit_calendar import calendar
from github import Github, GithubException

# =========================================================
# 0. GitHub 연동을 통한 DB 영구 보존 / 백업 로직
# =========================================================
DB_FILE = "diary_app.db"

def sync_db_from_github():
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            file_content = repo.get_contents(DB_FILE)
            with open(DB_FILE, "wb") as f:
                f.write(file_content.decoded_content)
        except Exception:
            pass

def push_db_to_github(commit_message="Update database"):
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "rb") as f:
                    content = f.read()
                
                try:
                    file_info = repo.get_contents(DB_FILE)
                    repo.update_file(DB_FILE, commit_message, content, file_info.sha)
                except GithubException:
                    repo.create_file(DB_FILE, commit_message, content)
        except Exception as e:
            st.error(f"🚨 깃허브 백업 실패 원인: {e}")

sync_db_from_github()


# =========================================================
# 1. DB 연동 및 테이블 생성 / 마이그레이션
# =========================================================
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            nickname TEXT NOT NULL,
            birthdate TEXT DEFAULT '',
            theme TEXT DEFAULT '포근함',
            main_color TEXT DEFAULT '#DDA15E'
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS diaries (
            username TEXT,
            date TEXT,
            emotion TEXT,
            content TEXT,
            is_public INTEGER DEFAULT 0,
            PRIMARY KEY (username, date),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diary_username TEXT,
            diary_date TEXT,
            comment_username TEXT,
            comment_nickname TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY (diary_username, diary_date) REFERENCES diaries(username, date)
        )
    ''')
    
    # 마이그레이션 컬럼 추가
    try:
        c.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass
        
    try:
        c.execute("ALTER TABLE users ADD COLUMN birthdate TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT '포근함'")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN main_color TEXT DEFAULT '#DDA15E'")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE diaries ADD COLUMN is_public INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()

init_db()

# --- DB 헬퍼 함수들 ---
def register_user(username, password, nickname, birthdate=""):
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute('''
            INSERT INTO users (username, password, nickname, birthdate, theme, main_color) 
            VALUES (?, ?, ?, ?, '포근함', '#DDA15E')
        ''', (username, hashed_pw, nickname, birthdate))
        conn.commit()
        push_db_to_github("New user registered")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password, nickname, birthdate, theme, main_color FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        stored_pw, nickname, birthdate, theme, main_color = row[0], row[1], row[2], row[3], row[4]
        if bcrypt.checkpw(password.encode('utf-8'), stored_pw.encode('utf-8')):
            return True, nickname, birthdate, (theme or '포근함'), (main_color or '#DDA15E')
    return False, None, None, '포근함', '#DDA15E'

def update_user_profile(username, new_nickname, new_birthdate, new_theme, new_main_color):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET nickname = ?, birthdate = ?, theme = ?, main_color = ? 
        WHERE username = ?
    ''', (new_nickname, new_birthdate, new_theme, new_main_color, username))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update profile for user {username}")

def get_user_diaries(username, is_public_flag):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, emotion, content FROM diaries WHERE username = ? AND is_public = ?", 
              (username, 1 if is_public_flag else 0))
    rows = c.fetchall()
    conn.close()
    
    diaries = {}
    for r in rows:
        diaries[r[0]] = {"emotion": r[1], "content": r[2]}
    return diaries

def get_all_public_diaries():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT d.date, d.emotion, d.content, u.nickname, d.username
        FROM diaries d
        JOIN users u ON d.username = u.username
        WHERE d.is_public = 1
        ORDER BY d.date DESC
    ''')
    rows = c.fetchall()
    conn.close()
    
    public_list = []
    for r in rows:
        public_list.append({
            "date": r[0], "emotion": r[1], "content": r[2], 
            "nickname": r[3], "username": r[4]
        })
    return public_list

def save_diary(username, date_str, emotion, content, is_public):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO diaries (username, date, emotion, content, is_public)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            emotion=excluded.emotion, content=excluded.content, is_public=excluded.is_public
    ''', (username, date_str, emotion, content, 1 if is_public else 0))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update diary entry for {date_str}")

def delete_diary(username, date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM diaries WHERE username = ? AND date = ?", (username, date_str))
    c.execute("DELETE FROM comments WHERE diary_username = ? AND diary_date = ?", (username, date_str))
    conn.commit()
    conn.close()
    push_db_to_github(f"Delete diary entry for {date_str}")

# 댓글 DB 함수들
def add_comment(diary_username, diary_date, comment_username, comment_nickname, content):
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('''
        INSERT INTO comments (diary_username, diary_date, comment_username, comment_nickname, content, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (diary_username, diary_date, comment_username, comment_nickname, content, now_str))
    conn.commit()
    conn.close()
    push_db_to_github("New comment added")

def get_comments(diary_username, diary_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, comment_username, comment_nickname, content, created_at
        FROM comments
        WHERE diary_username = ? AND diary_date = ?
        ORDER BY id ASC
    ''', (diary_username, diary_date))
    rows = c.fetchall()
    conn.close()
    
    comments = []
    for r in rows:
        comments.append({
            "id": r[0], "username": r[1], "nickname": r[2],
            "content": r[3], "created_at": r[4]
        })
    return comments

def delete_comment(comment_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Comment deleted")


# =========================================================
# 2. UI 및 동적 테마 설정 (10가지 테마 라인업)
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

THEME_STYLES = {
    "포근함": {
        "bg": "#FAF6F0", "text": "#4A3E3D", "header": "#6C5B52", 
        "card_bg": "#FFFFFF", "card_border": "#E3D5CA", "default_main": "#DDA15E"
    },
    "공주": {
        "bg": "#FFF0F5", "text": "#5C3D46", "header": "#8B4B62", 
        "card_bg": "#FFFFFF", "card_border": "#FFB6C1", "default_main": "#FF69B4"
    },
    "귀여움": {
        "bg": "#FFFBEA", "text": "#4A4438", "header": "#8A7335", 
        "card_bg": "#FFFFFF", "card_border": "#FFE599", "default_main": "#FFB000"
    },
    "심플": {
        "bg": "#F8F9FA", "text": "#212529", "header": "#343A40", 
        "card_bg": "#FFFFFF", "card_border": "#DEE2E6", "default_main": "#495057"
    },
    "클래식": {
        "bg": "#F4F1EA", "text": "#2C2C2C", "header": "#3D312A", 
        "card_bg": "#FCFBF7", "card_border": "#D2C7B8", "default_main": "#8C6D53"
    },
    "🌙 다크(밤)": {
        "bg": "#1E1E24", "text": "#E0E0E0", "header": "#BB86FC", 
        "card_bg": "#2A2A32", "card_border": "#3A3A46", "default_main": "#BB86FC"
    },
    "👾 레트로": {
        "bg": "#E0F7FA", "text": "#004D40", "header": "#00838F", 
        "card_bg": "#FFFFFF", "card_border": "#80DEEA", "default_main": "#00ACC1"
    },

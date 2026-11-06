import sqlite3
import datetime
import bcrypt
import os
import streamlit as st
import streamlit.components.v1 as components
from streamlit_calendar import calendar
from github import Github, GithubException

# =========================================================
# 0. 상수 및 설정 정의
# =========================================================
DB_FILE = "diary_app.db"

SCHEDULE_CATEGORIES = {
    "📖 공부/업무": "#3B82F6",
    "🤝 약속/모임": "#10B981",
    "🎉 기념일/행사": "#EC4899",
    "🏃 운동/건강": "#F97316",
    "📌 기타/개인": "#8B5CF6"
}

DAILY_QUESTIONS = [
    "오늘 가장 나를 미소 짓게 만든 작은 순간은 무엇인가요?",
    "최근에 새로 알게 되었거나 빠져든 취향이 있나요?",
    "오늘 하루 중 가장 솔직했던 순간은 언제인가요?",
    "나에게 해주고 싶은 따뜻한 위로의 한마디는?",
    "오늘 먹은 음식 중 가장 기억에 남는 것은 무엇인가요?",
    "다시 돌아가고 싶은 과거의 순간이 있다면 언제인가요?",
    "내 방에서 가장 아끼는 물건과 그 이유는?",
    "요즘 가장 자주 듣는 음악이나 좋아하는 플레이리스트는?",
    "오늘 하루를 한 줄 요약한다면 어떤 제목을 붙이고 싶나요?",
    "최근에 누군가에게 고마움을 느꼈던 적이 있나요?",
    "내일 나에게 기대되는 일이나 소소한 바람은 무엇인가요?",
    "어릴 적 꿈꾸던 나의 모습과 지금의 나는 얼마나 닮아 있나요?",
    "오늘 하늘을 보았나요? 오늘의 날씨와 나의 기분은 어땠나요?",
    "스트레스가 쌓일 때 나만의 해소법은 무엇인가요?",
    "올해 꼭 이루고 싶은 소소한 목표 한 가지를 적어보세요."
]

PROFILE_ICONS = ["🧸", "✨", "🐰", "🌸", "🍓", "🐥", "🌙", "⭐", "🍀", "🎀", "🐱", "🐶"]
STANDARD_EMOTIONS = ["😊 기쁨", "😢 슬픔", "😡 화남", "😰 불안/두려움", "😌 평온", "🥲 외로움", "🥰 뿌듯함", "😴 피곤", "✨ 설렘", "🥹 그리움"]

THEME_STYLES = {
    "👁️‍🗨️ 드림코어": {
        "title": "👁️‍🗨️ Have you been here before? ☁️",
        "bg": "#120E1A", "text": "#D4C7E7", "header": "#A882DD", 
        "card_bg": "#1D162B", "card_border": "#6B4899", "default_main": "#8B5CF6", "default_sub": "#06B6D4",
        "font_import": "https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Gamja+Flower&display=swap",
        "font_family": "'Gamja Flower', 'Cinzel Decorative', cursive",
        "radius": "28px", "shadow": "0 0 20px rgba(139, 92, 246, 0.4)",
        "paper_bg": "#181222", "paper_text": "#E2D9F3", "paper_line": "#3B2E56"
    },
    "포근함": {
        "title": "🧸 소소하고 포근한 일기장",
        "bg": "#FAF6F0", "text": "#4A3E3D", "header": "#6C5B52", 
        "card_bg": "#FFFFFF", "card_border": "#E3D5CA", "default_main": "#DDA15E", "default_sub": "#BC6C25",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
        "font_family": "'Gowun Dodum', sans-serif",
        "radius": "16px", "shadow": "0 4px 12px rgba(0,0,0,0.05)",
        "paper_bg": "#FFFDF9", "paper_text": "#2C2C2C", "paper_line": "#E5DFD3"
    },
    "공주": {
        "title": "👑 공주님의 비밀 다이어리 🎀",
        "bg": "#FFF0F5", "text": "#5C3D46", "header": "#D81B60", 
        "card_bg": "#FFFFFF", "card_border": "#FFB6C1", "default_main": "#FF69B4", "default_sub": "#FF1493",
        "font_import": "https://fonts.googleapis.com/css2?family=Single+Day&display=swap",
        "font_family": "'Single Day', cursive",
        "radius": "24px", "shadow": "0 8px 20px rgba(255,105,180,0.15)",
        "paper_bg": "#FFFAFC", "paper_text": "#5C3D46", "paper_line": "#FFD1DC"
    },
    "귀여움": {
        "title": "🐣 병아리의 자그마한 일기장 🐥",
        "bg": "#FFFBEA", "text": "#4A4438", "header": "#D97706", 
        "card_bg": "#FFFFFF", "card_border": "#FFE599", "default_main": "#FFB000", "default_sub": "#F59E0B",
        "font_import": "https://fonts.googleapis.com/css2?family=Gamja+Flower&display=swap",
        "font_family": "'Gamja Flower', cursive",
        "radius": "20px", "shadow": "0 6px 14px rgba(255,176,0,0.15)",
        "paper_bg": "#FFFFFD", "paper_text": "#4A4438", "paper_line": "#FFEEB2"
    },
    "심플": {
        "title": "MINIMAL DIARY",
        "bg": "#F8F9FA", "text": "#212529", "header": "#1A1D20", 
        "card_bg": "#FFFFFF", "card_border": "#DEE2E6", "default_main": "#343A40", "default_sub": "#495057",
        "font_import": "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;500&display=swap",
        "font_family": "'Noto Sans KR', sans-serif",
        "radius": "4px", "shadow": "none",
        "paper_bg": "#FFFFFF", "paper_text": "#212529", "paper_line": "#E9ECEF"
    },
    "클래식": {
        "title": "📖 서재 속 양장본 일기장",
        "bg": "#F4F1EA", "text": "#2C2C2C", "header": "#3D312A", 
        "card_bg": "#FCFBF7", "card_border": "#D2C7B8", "default_main": "#8C6D53", "default_sub": "#654321",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Batang&display=swap",
        "font_family": "'Gowun Batang', serif",
        "radius": "8px", "shadow": "0 2px 8px rgba(61,49,42,0.08)",
        "paper_bg": "#FBF9F1", "paper_text": "#2C2C2C", "paper_line": "#E2D9C8"
    },
    "🌙 다크(밤)": {
        "title": "🌙 한밤중의 비밀 기록",
        "bg": "#121216", "text": "#E2E8F0", "header": "#BB86FC", 
        "card_bg": "#1E1E24", "card_border": "#2D2D38", "default_main": "#BB86FC", "default_sub": "#03DAC6",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
        "font_family": "'Gowun Dodum', sans-serif",
        "radius": "12px", "shadow": "0 4px 16px rgba(0,0,0,0.4)",
        "paper_bg": "#1A1A22", "paper_text": "#E2E8F0", "paper_line": "#2E2E3C"
    },
    "👾 레트로": {
        "title": "📟 Y2K 감성 다이어리 👾",
        "bg": "#E0F7FA", "text": "#004D40", "header": "#00838F", 
        "card_bg": "#FFFFFF", "card_border": "#80DEEA", "default_main": "#00ACC1", "default_sub": "#FF5722",
        "font_import": "https://fonts.googleapis.com/css2?family=DungGeunMo&display=swap",
        "font_family": "'DungGeunMo', monospace",
        "radius": "0px", "shadow": "4px 4px 0px #004D40",
        "paper_bg": "#F5FFFF", "paper_text": "#004D40", "paper_line": "#B2EBF2"
    },
    "🌊 바다": {
        "title": "🌊 푸른 바다 속 이야기 🐬",
        "bg": "#EBF4F6", "text": "#1E3E62", "header": "#0B2F9F", 
        "card_bg": "#FFFFFF", "card_border": "#B0C4DE", "default_main": "#0284C7", "default_sub": "#0369A1",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
        "font_family": "'Gowun Dodum', sans-serif",
        "radius": "18px", "shadow": "0 8px 16px rgba(2,132,199,0.12)",
        "paper_bg": "#F4F9FB", "paper_text": "#1E3E62", "paper_line": "#CFE2EC"
    },
    "🌲 숲": {
        "title": "🍃 울창한 숲속 비밀노트 🌲",
        "bg": "#F1F8F5", "text": "#1C352D", "header": "#2D5A27", 
        "card_bg": "#FFFFFF", "card_border": "#C2E0D2", "default_main": "#15803D", "default_sub": "#166534",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Batang&display=swap",
        "font_family": "'Gowun Batang', serif",
        "radius": "14px", "shadow": "0 4px 12px rgba(21,128,61,0.08)",
        "paper_bg": "#F6FBF8", "paper_text": "#1C352D", "paper_line": "#D4ECE1"
    },
    "🔮 몽환": {
        "title": "🔮 달빛 아래 몽환 다이어리 🌙",
        "bg": "#F5EFFF", "text": "#3C2A4D", "header": "#6B21A8", 
        "card_bg": "#FFFFFF", "card_border": "#E9D5FF", "default_main": "#9333EA", "default_sub": "#C084FC",
        "font_import": "https://fonts.googleapis.com/css2?family=Gamja+Flower&display=swap",
        "font_family": "'Gamja Flower', cursive",
        "radius": "22px", "shadow": "0 8px 24px rgba(147,51,234,0.15)",
        "paper_bg": "#FAF5FF", "paper_text": "#3C2A4D", "paper_line": "#EAD6FC"
    }
}


# =========================================================
# 1. 데이터베이스(DB) 및 백업 관련 함수
# =========================================================
def get_database_connection():
    """SQLite 데이터베이스 연결 객체를 생성하여 반환합니다."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def sync_database_from_github():
    """GitHub 저장소로부터 최신 SQLite DB 파일을 다운로드하여 동기화합니다."""
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            github_client = Github(st.secrets["GITHUB_TOKEN"])
            repository = github_client.get_repo(st.secrets["GITHUB_REPO"])
            file_content = repository.get_contents(DB_FILE)
            with open(DB_FILE, "wb") as file:
                file.write(file_content.decoded_content)
        except Exception:
            pass

def push_database_to_github(commit_message="Update database"):
    """현재 로컬 DB 파일을 GitHub 저장소에 커밋 및 푸시하여 영구 백업합니다."""
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            github_client = Github(st.secrets["GITHUB_TOKEN"])
            repository = github_client.get_repo(st.secrets["GITHUB_REPO"])
            
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "rb") as file:
                    file_bytes = file.read()
                
                try:
                    file_info = repository.get_contents(DB_FILE)
                    repository.update_file(
                        path=DB_FILE,
                        message=commit_message,
                        content=file_bytes,
                        sha=file_info.sha
                    )
                except GithubException as ge:
                    if ge.status == 404:
                        repository.create_file(
                            path=DB_FILE,
                            message=commit_message,
                            content=file_bytes
                        )
                    else:
                        raise ge
        except Exception as error:
            st.error(f"🚨 깃허브 백업 실패 원인: {error}")

sync_database_from_github()

def initialize_database_tables():
    """애플리케이션에 필요한 모든 SQLite 테이블과 필수 컬럼을 생성/마이그레이션합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            nickname TEXT NOT NULL,
            birthdate TEXT DEFAULT '',
            profile_icon TEXT DEFAULT '🧸',
            status_message TEXT DEFAULT '',
            theme TEXT DEFAULT '포근함',
            main_color TEXT DEFAULT '#DDA15E',
            sub_color TEXT DEFAULT '#BC6C25'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diaries (
            username TEXT,
            date TEXT,
            emotion TEXT,
            content TEXT,
            drawing TEXT DEFAULT '',
            is_public INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            PRIMARY KEY (username, date),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_answers (
            username TEXT,
            date TEXT,
            question TEXT,
            answer TEXT,
            PRIMARY KEY (username, date)
        )
    ''')

    cursor.execute('''
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            title TEXT,
            category TEXT,
            color TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_ddays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            title TEXT,
            target_date TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    conn.commit()
    conn.close()

initialize_database_tables()


# =========================================================
# 2. 사용자 관리 및 인증 관련 함수
# =========================================================
def register_new_user(username, password, nickname, birthdate=""):
    """새로운 사용자를 등록하고 암호화된 비밀번호를 저장합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        cursor.execute('''
            INSERT INTO users (username, password, nickname, birthdate, profile_icon, status_message, theme, main_color, sub_color) 
            VALUES (?, ?, ?, ?, '🧸', '', '포근함', '#DDA15E', '#BC6C25')
        ''', (username, hashed_password, nickname, birthdate))
        conn.commit()
        push_database_to_github("New user registered")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    """아이디와 비밀번호를 검증하여 로그인 성공 여부 및 사용자 프로필 정보를 반환합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password, nickname, birthdate, profile_icon, status_message, theme, main_color, sub_color FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        stored_hashed_pw = row[0]
        if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_pw.encode('utf-8')):
            return True, row[1], row[2], (row[3] or '🧸'), (row[4] or ''), (row[5] or '포근함'), (row[6] or '#DDA15E'), (row[7] or '#BC6C25')
    return False, None, None, '🧸', '', '포근함', '#DDA15E', '#BC6C25'

def update_user_profile(username, new_nickname, new_birthdate, new_profile_icon, new_status_message):
    """사용자의 프로필 정보(닉네임, 생년월일, 아이콘, 상태메시지)를 수정합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET nickname = ?, birthdate = ?, profile_icon = ?, status_message = ? 
        WHERE username = ?
    ''', (new_nickname, new_birthdate, new_profile_icon, new_status_message, username))
    conn.commit()
    conn.close()
    push_database_to_github(f"Update info for user {username}")

def update_user_theme_settings(username, new_theme, new_main_color, new_sub_color):
    """사용자의 테마 및 컬러 팔레트 설정을 변경합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET theme = ?, main_color = ?, sub_color = ? 
        WHERE username = ?
    ''', (new_theme, new_main_color, new_sub_color, username))
    conn.commit()
    conn.close()
    push_database_to_github(f"Update theme for user {username}")

def delete_user_account_data(username):
    """회원탈퇴 시 사용자의 모든 데이터(일기, 일정, 디데이, 댓글 등)를 영구 삭제합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM diaries WHERE username = ?", (username,))
        cursor.execute("DELETE FROM daily_answers WHERE username = ?", (username,))
        cursor.execute("DELETE FROM comments WHERE comment_username = ? OR diary_username = ?", (username, username))
        cursor.execute("DELETE FROM schedules WHERE username = ?", (username,))
        cursor.execute("DELETE FROM user_ddays WHERE username = ?", (username,))
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        push_database_to_github(f"User account deleted: {username}")
        return True
    except Exception as error:
        print(f"Delete error: {error}")
        return False
    finally:
        conn.close()


# =========================================================
# 3. 다이어리, 일정, 디데이 데이터 처리 함수
# =========================================================
def get_daily_question_for_date(date_str):
    """날짜 문자열에 해당하는 오늘의 질문을 고유하게 산출합니다."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        day_ordinal = dt.toordinal()
        return DAILY_QUESTIONS[day_ordinal % len(DAILY_QUESTIONS)]
    except Exception:
        return DAILY_QUESTIONS[0]

def get_user_diaries_by_visibility(username, is_public_flag):
    """사용자의 비밀일기 또는 공개일기 목록을 조회합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, emotion, content, drawing, is_public FROM diaries WHERE username = ?", (username,))
    rows = cursor.fetchall()
    conn.close()
    
    diaries = {}
    for row in rows:
        date_val, emotion_val, content_val, drawing_val, is_pub_val = row
        if is_public_flag and is_pub_val == 1:
            diaries[date_val] = {"emotion": emotion_val, "content": content_val, "drawing": drawing_val, "is_public": is_pub_val}
        elif not is_public_flag and is_pub_val == 0:
            diaries[date_val] = {"emotion": emotion_val, "content": content_val, "drawing": drawing_val, "is_public": is_pub_val}
    return diaries

def get_all_public_diaries_feed(current_user):
    """모든 사용자의 전체 공개된 일기 피드를 최신순으로 조회합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT d.date, d.emotion, d.content, d.drawing, u.nickname, d.username, d.views, u.profile_icon, d.is_public
        FROM diaries d
        JOIN users u ON d.username = u.username
        WHERE d.is_public = 1
        ORDER BY date DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    public_feed = []
    for row in rows:
        if row[8] == 1:
            public_feed.append({
                "date": row[0], "emotion": row[1], "content": row[2], "drawing": row[3],
                "nickname": row[4], "username": row[5], "views": row[6], "profile_icon": row[7] if row[7] else '🧸'
            })
    return public_feed

def increment_diary_view_count(username, date_str, current_user):
    """공개일기 조회 시 조회수를 1 증가시킵니다. (본인 제외)"""
    if username == current_user:
        return
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE diaries SET views = views + 1 WHERE username = ? AND date = ?", (username, date_str))
    conn.commit()
    conn.close()

def save_diary_entry(username, date_str, emotion, content, drawing, is_public):
    """일기 데이터를 생성하거나 기존 데이터를 수정(Upsert)합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO diaries (username, date, emotion, content, drawing, is_public)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            emotion=excluded.emotion, content=excluded.content, drawing=excluded.drawing, is_public=excluded.is_public
    ''', (username, date_str, emotion, content, drawing, 1 if is_public else 0))
    conn.commit()
    conn.close()
    push_database_to_github(f"Update diary entry for {date_str}")

def delete_diary_entry(username, date_str):
    """특정 날짜의 일기와 연관된 답변, 댓글 데이터를 함께 삭제합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM diaries WHERE username = ? AND date = ?", (username, date_str))
    cursor.execute("DELETE FROM comments WHERE diary_username = ? AND diary_date = ?", (username, date_str))
    cursor.execute("DELETE FROM daily_answers WHERE username = ? AND date = ?", (username, date_str))
    conn.commit()
    conn.close()
    push_database_to_github(f"Delete diary entry for {date_str}")

def get_daily_answer_record(username, date_str):
    """오늘의 질문 답변을 조회합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM daily_answers WHERE username = ? AND date = ?", (username, date_str))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def save_daily_answer_record(username, date_str, question, answer):
    """오늘의 질문 답변을 저장합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO daily_answers (username, date, question, answer)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            question=excluded.question, answer=excluded.answer
    ''', (username, date_str, question, answer))
    conn.commit()
    conn.close()
    push_database_to_github(f"Update daily answer for {date_str}")

def get_user_schedule_list(username):
    """사용자의 일정 목록을 조회합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, title, category, color FROM schedules WHERE username = ? ORDER BY date ASC", (username,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "title": r[2], "category": r[3], "color": r[4]} for r in rows]

def add_user_schedule(username, date_str, title, category):
    """새로운 일정을 추가합니다."""
    color = SCHEDULE_CATEGORIES.get(category, "#8B5CF6")
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO schedules (username, date, title, category, color)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, date_str, title, category, color))
    conn.commit()
    conn.close()
    push_database_to_github("New schedule added")

def delete_user_schedule(schedule_id):
    """일정을 삭제합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    push_database_to_github("Schedule deleted")

def get_user_dday_list(username):
    """사용자의 디데이 목록을 조회합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, target_date FROM user_ddays WHERE username = ? ORDER BY target_date ASC", (username,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "target_date": r[2]} for r in rows]

def add_user_dday_item(username, title, target_date):
    """새로운 디데이를 추가합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_ddays (username, title, target_date) VALUES (?, ?, ?)", (username, title, target_date))
    conn.commit()
    conn.close()
    push_database_to_github("New custom dday added")

def delete_user_dday_item(dday_id):
    """디데이를 삭제합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_ddays WHERE id = ?", (dday_id,))
    conn.commit()
    conn.close()
    push_database_to_github("Custom dday deleted")

def get_diary_comments(diary_username, diary_date):
    """특정 공개일기의 댓글 목록을 조회합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, comment_username, comment_nickname, content, created_at
        FROM comments
        WHERE diary_username = ? AND diary_date = ?
        ORDER BY id ASC
    ''', (diary_username, diary_date))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "nickname": r[2], "content": r[3], "created_at": r[4]} for r in rows]

def add_diary_comment(diary_username, diary_date, comment_username, comment_nickname, content):
    """공개일기에 댓글을 작성합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('''
        INSERT INTO comments (diary_username, diary_date, comment_username, comment_nickname, content, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (diary_username, diary_date, comment_username, comment_nickname, content, timestamp_str))
    conn.commit()
    conn.close()
    push_database_to_github("New comment added")

def delete_diary_comment(comment_id):
    """작성한 댓글을 삭제합니다."""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
    push_database_to_github("Comment deleted")

def parse_calendar_date(raw_date_str):
    """캘린더에서 전달된 날짜 문자열의 타임존 오차를 보정하여 표준 날짜 형식으로 변환합니다."""
    if not raw_date_str:
        return None
    raw_str = str(raw_date_str).strip()
    if 'T' in raw_str:
        try:
            utc_datetime = datetime.datetime.fromisoformat(raw_str.replace('Z', '+00:00'))
            kst_datetime = utc_datetime + datetime.timedelta(hours=9)
            return kst_datetime.strftime("%Y-%m-%d")
        except Exception:
            return raw_str.split('T')[0]
    return raw_str[:10]


# =========================================================
# 4. Streamlit UI 및 스타일 렌더링 설정
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

# 세션 상태 초기화
if "user" not in st.session_state:
    st.session_state.user = None
if "nickname" not in st.session_state:
    st.session_state.nickname = None
if "birthdate" not in st.session_state:
    st.session_state.birthdate = None
if "profile_icon" not in st.session_state:
    st.session_state.profile_icon = "🧸"
if "status_message" not in st.session_state:
    st.session_state.status_message = ""
if "theme" not in st.session_state:
    st.session_state.theme = "포근함"
if "main_color" not in st.session_state:
    st.session_state.main_color = "#DDA15E"
if "sub_color" not in st.session_state:
    st.session_state.sub_color = "#BC6C25"
if "page" not in st.session_state:
    st.session_state.page = "secret_calendar"
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.date.today().strftime("%Y-%m-%d")

active_theme_key = st.session_state.get("theme", "포근함")
if active_theme_key not in THEME_STYLES:
    active_theme_key = "포근함"

current_theme = THEME_STYLES[active_theme_key]
main_color = st.session_state.get("main_color") or current_theme["default_main"]
sub_color = st.session_state.get("sub_color") or current_theme["default_sub"]
application_title = current_theme["title"]

if "page_custom_bg" not in st.session_state:
    st.session_state.page_custom_bg = current_theme["paper_bg"]

is_currently_editor = st.session_state.get("page", "") in ["secret_editor", "public_editor"]
active_background_color = st.session_state.page_custom_bg if is_currently_editor else current_theme['bg']

# CSS 스타일 주입
st.markdown(f"""
    <style>
    @import url('{current_theme['font_import']}');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .stApp, .main, [data-testid="stVerticalBlock"] {{
        background-color: {active_background_color} !important;
        color: {current_theme['text']} !important;
        font-family: {current_theme['font_family']} !important;
    }}
    
    h1, h2, h3, h4 {{
        color: {current_theme['header']} !important;
        font-family: {current_theme['font_family']} !important;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    
    .stTextInput input, div[data-testid="stForm"] {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px dashed {current_theme['card_border']} !important;
        border-radius: 0px !important;
        color: {current_theme['text']} !important;
        font-family: {current_theme['font_family']} !important;
    }}
    
    div.stButton > button {{
        background: linear-gradient(135deg, {main_color} 0%, {sub_color} 100%) !important;
        color: white !important;
        border-radius: {current_theme['radius']} !important;
        border: none !important;
        padding: 8px 18px !important;
        font-weight: bold !important;
        box-shadow: {current_theme['shadow']} !important;
        font-family: {current_theme['font_family']} !important;
        transition: all 0.25s ease-in-out;
    }}
    
    div.stButton > button:hover {{
        opacity: 0.9;
        transform: translateY(-2px) scale(1.02);
    }}

    .circle-icon-btn > button {{
        border-radius: 50% !important;
        width: 50px !important;
        height: 50px !important;
        padding: 0px !important;
        font-size: 1.2rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: {current_theme['card_bg']} !important;
        border-right: 1px solid {current_theme['card_border']} !important;
    }}

    iframe[title="streamlit_calendar.calendar"] {{
        min-height: 580px !important;
        border-radius: {current_theme['radius']} !important;
        border: 1px solid {current_theme['card_border']} !important;
        box-shadow: {current_theme['shadow']} !important;
    }}
    </style>
""", unsafe_allow_html=True)

today_date_obj = datetime.date.today()
today_date_str = today_date_obj.strftime("%Y-%m-%d")


# =========================================================
# 5. 메인 화면 흐름 제어 (인증 및 페이지 렌더링)
# =========================================================
if st.session_state.user is None:
    # [로그인 및 회원가입 화면]
    st.title("🧸 소소하고 포근한 일기장")
    
    auth_mode = st.radio("서비스 이용을 위해 로그인해 주세요.", ["로그인", "회원가입"], horizontal=True)
    
    input_username = st.text_input("아이디", key="auth_user")
    input_password = st.text_input("비밀번호", type="password", key="auth_pw")

    if auth_mode == "로그인":
        if st.button("로그인하기", use_container_width=True):
            if input_username and input_password:
                is_success, nickname, birthdate, profile_icon, status_msg, theme, m_color, s_color = authenticate_user(input_username, input_password)
                if is_success:
                    st.session_state.user = input_username
                    st.session_state.nickname = nickname if nickname else input_username
                    st.session_state.birthdate = birthdate
                    st.session_state.profile_icon = profile_icon if profile_icon else "🧸"
                    st.session_state.status_message = status_msg if status_msg else ""
                    st.session_state.theme = theme
                    st.session_state.main_color = m_color
                    st.session_state.sub_color = s_color

                    st.session_state.page = "secret_calendar"
                    st.success(f"{st.session_state.nickname}님 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해 주세요.")
                
    else:  # 회원가입
        input_nickname = st.text_input("닉네임 (프로필 이름)", key="auth_nick")
        use_birthday_checkbox = st.checkbox("생년월일 입력하기 (선택)")
        birthday_string = ""
        
        if use_birthday_checkbox:
            selected_bday = st.date_input(
                "생년월일 선택",
                value=datetime.date(2000, 1, 1),
                min_value=datetime.date(1920, 1, 1),
                max_value=today_date_obj
            )
            birthday_string = selected_bday.strftime("%Y-%m-%d")

        if st.button("회원가입하기", use_container_width=True):
            if input_username and input_password and input_nickname:
                if register_new_user(input_username, input_password, input_nickname.strip(), birthday_string):
                    st.success("회원가입이 완료되었습니다! 로그인 탭에서 로그인해 주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")
            else:
                st.warning("아이디, 비밀번호, 닉네임은 필수 입력사항입니다.")

else:
    # [로그인 후 메인 서비스 화면]
    current_user = st.session_state.user
    current_nickname = st.session_state.nickname
    user_birthdate = st.session_state.birthdate
    current_profile_icon = st.session_state.profile_icon if st.session_state.profile_icon else "🧸"
    current_status_message = st.session_state.status_message if st.session_state.status_message else ""
    
    # 생일 축하 알림 효과
    if user_birthdate and len(user_birthdate) == 10:
        if user_birthdate[5:] == today_date_str[5:]:
            st.balloons()
            st.toast(f"🎂 {current_nickname}님, 생일을 진심으로 축하합니다! 🎉", icon="🎁")

    # =========================================================
    # 사이드바 구성 (프로필, 테마, 디데이, 메뉴)
    # =========================================================
    st.sidebar.title(application_title.split()[0] + " 일기장")
    st.sidebar.markdown(f"### {current_profile_icon} **{current_nickname}** 님")
    if current_status_message:
        st.sidebar.caption(f"💬 *{current_status_message}*")

    st.sidebar.markdown("---")
    
    # 1. 내 메뉴 (프로필 및 테마 설정)
    st.sidebar.markdown("### 👤 내 메뉴")
    with st.sidebar.expander("⚙️ 정보설정 (프로필 개성꾸미기)"):
        edit_nickname = st.text_input("닉네임", value=current_nickname, key="edit_nick_input")
        edit_status_msg = st.text_input("한 줄 소개 (상태메시지)", value=current_status_message, placeholder="나를 표현하는 한마디 🌟", key="edit_status_input")
        
        st.write("프로필 이모티콘 선택:")
        emoji_columns = st.columns(4)
        for idx, emo in enumerate(PROFILE_ICONS):
            col_idx = idx % 4
            with emoji_columns[col_idx]:
                btn_label = f"✨ {emo}" if emo == current_profile_icon else emo
                if st.button(btn_label, key=f"emo_btn_{emo}", use_container_width=True):
                    st.session_state.profile_icon = emo
                    st.rerun()

        st.caption(f"현재 선택된 이모티콘: **{current_profile_icon}**")
        
        has_birthday = bool(user_birthdate)
        update_birthday_flag = st.checkbox("생년월일 설정/수정", value=has_birthday)
        
        default_bday_date = datetime.date(2000, 1, 1)
        if has_birthday:
            try:
                default_bday_date = datetime.datetime.strptime(user_birthdate, "%Y-%m-%d").date()
            except ValueError: pass

        new_bday_string = user_birthdate
        if update_birthday_flag:
            selected_bday_input = st.date_input(
                "생년월일", value=default_bday_date,
                min_value=datetime.date(1920, 1, 1), max_value=today_date_obj,
                key="edit_bday_input"
            )
            new_bday_string = selected_bday_input.strftime("%Y-%m-%d")
        else:
            new_bday_string = ""

        if st.button("프로필 변경 저장", use_container_width=True):
            cleaned_nickname = edit_nickname.strip()
            if cleaned_nickname:
                update_user_profile(current_user, cleaned_nickname, new_bday_string, current_profile_icon, edit_status_msg.strip())
                st.session_state.nickname = cleaned_nickname
                st.session_state.birthdate = new_bday_string
                st.session_state.status_message = edit_status_msg.strip()
                st.success("프로필이 수정되었습니다!")
                st.rerun()

    with st.sidebar.expander("🎨 테마관리 (분위기 & 색상)"):
        theme_names_list = list(THEME_STYLES.keys())
        current_theme_index = theme_names_list.index(st.session_state.theme) if st.session_state.theme in theme_names_list else 0
        
        selected_theme_name = st.selectbox("테마 분위기 (11종)", theme_names_list, index=current_theme_index)
        
        suggested_main_color = THEME_STYLES[selected_theme_name]["default_main"] if selected_theme_name != st.session_state.theme else main_color
        suggested_sub_color = THEME_STYLES[selected_theme_name]["default_sub"] if selected_theme_name != st.session_state.theme else sub_color
        
        col_main_picker, col_sub_picker = st.columns(2)
        with col_main_picker:
            picked_main_color = st.color_picker("포인트 메인", value=suggested_main_color)
        with col_sub_picker:
            picked_sub_color = st.color_picker("서브 보조", value=suggested_sub_color)

        if st.button("테마 적용하기", use_container_width=True):
            update_user_theme_settings(current_user, selected_theme_name, picked_main_color, picked_sub_color)
            st.session_state.theme = selected_theme_name
            st.session_state.main_color = picked_main_color
            st.session_state.sub_color = picked_sub_color
            st.session_state.page_custom_bg = THEME_STYLES[selected_theme_name]["paper_bg"]
            st.success("테마가 적용되었습니다!")
            st.rerun()

    with st.sidebar.expander("⚠️ 계정 관리 (회원탈퇴)"):
        st.warning("계정을 삭제하면 작성한 모든 일기와 데이터가 영구적으로 삭제되며 복구할 수 없습니다.")
        confirm_deletion = st.checkbox("계정 삭제에 동의합니다.")
        if st.button("🗑️ 회원탈퇴 (계정 삭제)", use_container_width=True):
            if confirm_deletion:
                if delete_user_account_data(current_user):
                    st.session_state.user = None
                    st.session_state.nickname = None
                    st.session_state.page = "secret_calendar"
                    st.success("계정이 성공적으로 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error("계정 삭제 중 오류가 발생했습니다.")
            else:
                st.warning("계정 삭제 동의 체크박스를 체크해 주세요.")

    # 2. 일정 및 디데이 관리
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 일정관리")

    current_year = today_date_obj.year
    fixed_events_to_check = [
        ("🎄 크리스마스", datetime.date(current_year, 12, 25)),
        ("🎉 새해(신정)", datetime.date(current_year + 1, 1, 1))
    ]
    for event_name, event_date in fixed_events_to_check:
        if event_date < today_date_obj:
            event_date = datetime.date(current_year + 1, event_date.month, event_date.day)
        days_remaining = (event_date - today_date_obj).days
        if 0 <= days_remaining <= 14:
            d_label = "D-Day" if days_remaining == 0 else f"D-{days_remaining}"
            st.sidebar.info(f"{event_name}까지 **{d_label}** 남았습니다! 🎉")

    user_ddays_list = get_user_dday_list(current_user)
    if user_ddays_list:
        for dday in user_ddays_list:
            try:
                target_date_obj = datetime.datetime.strptime(dday['target_date'], "%Y-%m-%d").date()
                diff_days = (target_date_obj - today_date_obj).days
                dday_text = "D-Day 🎉" if diff_days == 0 else (f"D-{diff_days}" if diff_days > 0 else f"D+{abs(diff_days)}")
                
                col_dday_title, col_dday_del = st.sidebar.columns([4, 1])
                with col_dday_title:
                    st.write(f"📌 {dday['title']}: {dday_text}")
                with col_dday_del:
                    if st.button("❌", key=f"del_dday_{dday['id']}"):
                        delete_user_dday_item(dday['id'])
                        st.rerun()
            except Exception:
                pass

    with st.sidebar.expander("⏳ 디데이 추가"):
        new_dday_title_input = st.text_input("디데이 제목", placeholder="예: 시험일, 여행")
        new_dday_date_input = st.date_input("목표 날짜", value=today_date_obj)
        if st.button("디데이 등록", use_container_width=True):
            if new_dday_title_input.strip():
                add_user_dday_item(current_user, new_dday_title_input.strip(), new_dday_date_input.strftime("%Y-%m-%d"))
                st.success("디데이가 추가되었습니다!")
                st.rerun()
            else:
                st.warning("디데이 제목을 입력해 주세요.")

    # 3. 메인 일기 메뉴
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📖 일기")
    main_menu_options = ["🔒 비밀일기", "📅 일정 관리 달력", "🌐 공개일기"]
    selected_menu = st.sidebar.radio("일기 메뉴", main_menu_options, label_visibility="collapsed")

    if selected_menu == "🔒 비밀일기" and st.session_state.page not in ["secret_calendar", "secret_editor"]:
        st.session_state.page = "secret_calendar"
        st.rerun()
    elif selected_menu == "📅 일정 관리 달력" and st.session_state.page not in ["schedule_calendar", "schedule_editor"]:
        st.session_state.page = "schedule_calendar"
        st.rerun()
    elif selected_menu == "🌐 공개일기" and st.session_state.page not in ["public_calendar", "public_editor"]:
        st.session_state.page = "public_calendar"
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 로그아웃", use_container_width=True):
        st.session_state.user = None
        st.session_state.nickname = None
        st.session_state.page = "secret_calendar"
        st.rerun()

    # 생일 캘린더 이벤트 생성
    birthday_calendar_events = []
    if user_birthdate and len(user_birthdate) == 10:
        try:
            bday_month_day = user_birthdate[5:]
            bday_current_year = today_date_obj.year
            bday_target_str = f"{bday_current_year}-{bday_month_day}"
            birthday_calendar_events.append({
                "title": "🎂 내 생일! 🎉",
                "start": bday_target_str,
                "end": bday_target_str,
                "allDay": True,
                "color": sub_color
            })
        except Exception:
            pass

    # 디데이 2주 전부터 카운트다운(D-14 ~ D-Day) 캘린더 이벤트 생성 함수
    def generate_dday_calendar_events():
        events_list = []
        user_ddays = get_user_dday_list(current_user)
        for dday in user_ddays:
            try:
                target_dt = datetime.datetime.strptime(dday['target_date'], "%Y-%m-%d").date()
                for i in range(15): # 14일 전부터 당일까지
                    target_day = target_dt - datetime.timedelta(days=i)
                    remaining = (target_dt - target_day).days
                    d_txt = "D-Day 🎉" if remaining == 0 else f"D-{remaining}"
                    
                    events_list.append({
                        "title": f"⏳ [{d_txt}] {dday['title']}",
                        "start": target_day.strftime("%Y-%m-%d"),
                        "end": target_day.strftime("%Y-%m-%d"),
                        "allDay": True,
                        "color": "#F97316"
                    })
            except Exception:
                pass
        return events_list


    # =========================================================
    # 6. 각 페이지별 렌더링 로직
    # =========================================================
    
    # [PAGE 1] 비밀일기 달력 페이지
    if st.session_state.page == "secret_calendar":
        st.title(application_title)
        st.header("🔒 나만의 비밀일기")
        secret_diaries_dict = get_user_diaries_by_visibility(current_user, is_public_flag=False)

        calendar_events = list(birthday_calendar_events) + generate_dday_calendar_events()
        for date_str, diary_data in secret_diaries_dict.items():
            if diary_data.get("content") or diary_data.get("drawing"):
                calendar_events.append({
                    "title": f"🔒 {diary_data['emotion']}",
                    "start": date_str, "end": date_str, "allDay": True,
                    "color": main_color
                })

        calendar_result = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"secret_cal_{active_theme_key}_{main_color}_{sub_color}")

        clicked_calendar_date = None
        if calendar_result and "dateClick" in calendar_result:
            clicked_calendar_date = parse_calendar_date(calendar_result["dateClick"].get("date"))
        elif calendar_result and "select" in calendar_result:
            clicked_calendar_date = parse_calendar_date(calendar_result["select"].get("start"))

        if clicked_calendar_date:
            st.session_state.selected_date = clicked_calendar_date
            st.session_state.page = "secret_editor"
            st.rerun()

    # [PAGE 2] 일정 관리 달력 페이지
    elif st.session_state.page == "schedule_calendar":
        st.title(application_title)
        st.header("📅 나의 카테고리별 일정 관리")
        user_schedules = get_user_schedule_list(current_user)

        legend_columns = st.columns(len(SCHEDULE_CATEGORIES))
        for idx, (cat_name, cat_color) in enumerate(SCHEDULE_CATEGORIES.items()):
            with legend_columns[idx]:
                st.markdown(f"<span style='color:{cat_color}; font-weight:bold;'>■</span> <small>{cat_name.split()[1]}</small>", unsafe_allow_html=True)

        calendar_events = list(birthday_calendar_events) + generate_dday_calendar_events()
        for schedule in user_schedules:
            calendar_events.append({
                "title": f"📌 [{schedule['category'].split()[1]}] {schedule['title']}",
                "start": schedule['date'], "end": schedule['date'], "allDay": True,
                "color": schedule['color']
            })

        calendar_result_sched = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"schedule_cal_{active_theme_key}_{main_color}_{sub_color}")

        clicked_sched_date = None
        if calendar_result_sched and "dateClick" in calendar_result_sched:
            clicked_sched_date = parse_calendar_date(calendar_result_sched["dateClick"].get("date"))
        elif calendar_result_sched and "select" in calendar_result_sched:
            clicked_sched_date = parse_calendar_date(calendar_result_sched["select"].get("start"))

        if clicked_sched_date:
            st.session_state.selected_date = clicked_sched_date
            st.session_state.page = "schedule_editor"
            st.rerun()

    # [PAGE 2-1] 일정 등록 및 수정 에디터
    elif st.session_state.page == "schedule_editor":
        st.title(application_title)
        selected_date_str = st.session_state.selected_date
        st.header(f"📅 일정 관리 ({selected_date_str})")

        all_schedules = get_user_schedule_list(current_user)
        current_day_schedules = [s for s in all_schedules if s['date'] == selected_date_str]

        if current_day_schedules:
            st.subheader("📋 이날의 기존 일정")
            for schedule_item in current_day_schedules:
                col_info, col_delete = st.columns([5, 1])
                with col_info:
                    st.markdown(f"<span style='color:{schedule_item['color']}; font-weight:bold;'>■</span> **{schedule_item['category']}** : {schedule_item['title']}", unsafe_allow_html=True)
                with col_delete:
                    if st.button("삭제", key=f"del_sched_{schedule_item['id']}"):
                        delete_user_schedule(schedule_item['id'])
                        st.success("일정이 삭제되었습니다.")
                        st.rerun()
            st.markdown("---")

        st.subheader("➕ 새 일정 추가하기")
        new_schedule_title = st.text_input("일정 제목", placeholder="예: 친구 생일파티, 스터디 카페 가기")
        new_schedule_category = st.selectbox("일정 카테고리", list(SCHEDULE_CATEGORIES.keys()))

        col_save_btn, col_back_btn = st.columns([1, 1])
        with col_save_btn:
            if st.button("💾 일정 등록", use_container_width=True):
                if new_schedule_title.strip():
                    add_user_schedule(current_user, selected_date_str, new_schedule_title.strip(), new_schedule_category)
                    st.success("일정이 등록되었습니다!")
                    st.session_state.page = "schedule_calendar"
                    st.rerun()
                else:
                    st.warning("일정 제목을 입력해 주세요.")
        with col_back_btn:
            if st.button("🗓️ 일정 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "schedule_calendar"
                st.rerun()

    # [PAGE 3] 공개일기 달력 및 피드 모아보기 페이지
    elif st.session_state.page == "public_calendar":
        st.title(application_title)
        st.header("🌐 공유하는 공개일기")
        tab_calendar, tab_feed = st.tabs(["🗓️ 내 공개일기 달력", "📖 모두의 이야기 모아보기"])

        with tab_calendar:
            my_public_diaries_dict = get_user_diaries_by_visibility(current_user, is_public_flag=True)
            calendar_events = list(birthday_calendar_events) + generate_dday_calendar_events()
            for date_str, diary_data in my_public_diaries_dict.items():
                if diary_data.get("content") or diary_data.get("drawing"):
                    calendar_events.append({
                        "title": f"🌐 {diary_data['emotion']}", "start": date_str, "end": date_str, "allDay": True, "color": main_color
                    })

            calendar_result_public = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"public_cal_{active_theme_key}_{main_color}_{sub_color}")

            clicked_public_date = None
            if calendar_result_public and "dateClick" in calendar_result_public:
                clicked_public_date = parse_calendar_date(calendar_result_public["dateClick"].get("date"))
            elif calendar_result_public and "select" in calendar_result_public:
                clicked_public_date = parse_calendar_date(calendar_result_public["select"].get("start"))

            if clicked_public_date:
                st.session_state.selected_date = clicked_public_date
                st.session_state.page = "public_editor"
                st.rerun()

        with tab_feed:
            public_diaries_feed = get_all_public_diaries_feed(current_user)
            if public_diaries_feed:
                for feed_item in public_diaries_feed:
                    increment_diary_view_count(feed_item['username'], feed_item['date'], current_user)
                    
                    with st.container():
                        profile_icon_str = feed_item['profile_icon'] if feed_item['profile_icon'] else '🧸'
                        feed_header = f"{profile_icon_str} {feed_item['emotion']} **{feed_item['nickname']}** 님의 이야기 ({feed_item['date']})"

                        st.markdown(f"#### {feed_header}  \n<small>👁️ 조회수 {feed_item['views'] + (1 if feed_item['username'] == current_user else 0)}</small>", unsafe_allow_html=True)
                        
                        if feed_item['content']:
                            st.markdown(f"""
                                <div style="background-color: {current_theme['paper_bg']}; color: {current_theme['paper_text']}; border: 1px solid {current_theme['card_border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px; white-space: pre-wrap; font-family: {current_theme['font_family']};">{feed_item['content']}</div>
                            """, unsafe_allow_html=True)
                        
                        if feed_item['drawing']:
                            st.image(feed_item['drawing'], caption=f"{feed_item['nickname']}님의 그림일기 🎨", use_column_width=True)
                        
                        comments_list = get_diary_comments(feed_item['username'], feed_item['date'])
                        with st.expander(f"💬 댓글 ({len(comments_list)})"):
                            for comment in comments_list:
                                col_comment_text, col_comment_del = st.columns([5, 1])
                                with col_comment_text:
                                    st.markdown(f"**{comment['nickname']}**: {comment['content']} *(<small>{comment['created_at']}</small>)*", unsafe_allow_html=True)
                                with col_comment_del:
                                    if comment['username'] == current_user:
                                        if st.button("삭제", key=f"del_comment_{comment['id']}"):
                                            delete_diary_comment(comment['id'])
                                            st.rerun()

                            new_comment_input = st.text_input("댓글 작성", key=f"comment_input_{feed_item['username']}_{feed_item['date']}")
                            if st.button("댓글 작성 완료", key=f"btn_submit_comment_{feed_item['username']}_{feed_item['date']}"):
                                if new_comment_input.strip():
                                    add_diary_comment(feed_item['username'], feed_item['date'], current_user, current_nickname, new_comment_input.strip())
                                    st.success("댓글이 남겨졌습니다!")
                                    st.rerun()
                        st.markdown("---")
            else:
                st.write("🌿 아직 등록된 공개 일기가 없어요.")

    # [PAGE 4] 일기 작성 및 수정 에디터 페이지
    elif st.session_state.page in ["secret_editor", "public_editor"]:
        selected_date_str = st.session_state.selected_date
        is_public_page = (st.session_state.page == "public_editor")

        existing_diaries = get_user_diaries_by_visibility(current_user, is_public_flag=is_public_page)
        has_existing_diary = selected_date_str in existing_diaries and (bool(existing_diaries[selected_date_str].get("content", "").strip()) or bool(existing_diaries[selected_date_str].get("drawing", "")))
        existing_diary_data = existing_diaries.get(selected_date_str, {})

        col_editor_title, col_palette_btn = st.columns([7, 1])
        with col_editor_title:
            st.markdown(f"# {application_title.split()[0]} DIARY")
        with col_palette_btn:
            st.markdown('<div class="circle-icon-btn">', unsafe_allow_html=True)
            if st.button("🎨", key="btn_toggle_color_picker"):
                if "show_color_picker" not in st.session_state:
                    st.session_state.show_color_picker = True
                else:
                    st.session_state.show_color_picker = not st.session_state.show_color_picker
                st.rerun()
            st.caption("색상")
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("show_color_picker", False):
            picked_new_bg = st.color_picker("전체 배경 색상 선택", value=st.session_state.page_custom_bg, key="picker_bg_color")
            if picked_new_bg != st.session_state.page_custom_bg:
                st.session_state.page_custom_bg = picked_new_bg
                st.rerun()

        col_date_display, col_emotion_select = st.columns([1, 1])
        with col_date_display:
            st.markdown(f"### ✏️ 날짜: **{selected_date_str}**")
        with col_emotion_select:
            emotion_index = STANDARD_EMOTIONS.index(existing_diary_data.get("emotion")) if existing_diary_data.get("emotion") in STANDARD_EMOTIONS else 0
            selected_emotion_full = st.selectbox("오늘의 감정:", STANDARD_EMOTIONS, index=emotion_index, label_visibility="collapsed")
            selected_emotion_emoji = selected_emotion_full.split()[0]

        diary_title_input = st.text_input("제목:", placeholder="제목을 입력하세요...", key=f"title_{selected_date_str}")

        saved_content_text = existing_diary_data.get("content", "")
        
        # 커스텀 텍스트에디터 HTML 컴포넌트 렌더링
        note_editor_html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    background-color: transparent;
                    margin: 0;
                    padding: 0;
                    font-family: {current_theme['font_family']};
                }}
                textarea {{
                    width: 100%;
                    height: 320px;
                    background-color: transparent !important;
                    background-image: linear-gradient({current_theme['paper_line']} 1px, transparent 1px) !important;
                    background-size: 100% 32px !important;
                    border: none !important;
                    outline: none !important;
                    color: {current_theme['text']} !important;
                    font-family: {current_theme['font_family']} !important;
                    font-size: 1.2rem !important;
                    line-height: 32px !important;
                    padding-top: 4px !important;
                    resize: vertical;
                }}
            </style>
        </head>
        <body>
            <textarea id="noteTextarea" placeholder="내용을 기록하세요...">{saved_content_text}</textarea>
            <script>
                const textarea = document.getElementById('noteTextarea');
                const parentInput = window.parent.document.querySelector('input[aria-label="content_hidden_{selected_date_str}"]');
                if (parentInput) {{
                    textarea.value = parentInput.value;
                }}
                textarea.addEventListener('input', function() {{
                    if (parentInput) {{
                        parentInput.value = textarea.value;
                        parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }});
            </script>
        </body>
        </html>
        """
        hidden_content_input_val = st.text_input(f"content_hidden_{selected_date_str}", value=saved_content_text, label_visibility="collapsed", key=f"content_hidden_key_{selected_date_str}")
        components.html(note_editor_html_template, height=340)
        final_diary_content = hidden_content_input_val

        st.markdown("---")
        daily_question_str = get_daily_question_for_date(selected_date_str)
        saved_answer_text = get_daily_answer_record(current_user, selected_date_str)
        st.markdown(f"### 💡 오늘의 질문")
        st.write(f"**{daily_question_str}**")
        daily_answer_input = st.text_area("답변 작성:", value=saved_answer_text, height=80, placeholder="답변을 입력하세요...", label_visibility="collapsed")

        st.markdown("---")
        st.markdown("### 🔒 공개범위 설정")
        visibility_selection = st.radio(
            "공개 대상을 선택하세요:",
            ["🔒 나만 보기", "🌐 전체 공개"],
            index=1 if is_public_page else 0,
            label_visibility="collapsed"
        )

        st.markdown("---")
        col_save_action, col_return_action, col_delete_action = st.columns([2, 2, 1])
        with col_save_action:
            if st.button("💾 일기 저장", use_container_width=True):
                if final_diary_content is not None:
                    is_target_public = 1 if visibility_selection == "🌐 전체 공개" else 0
                    
                    save_diary_entry(current_user, selected_date_str, selected_emotion_emoji, final_diary_content, "", is_target_public)
                    
                    if daily_answer_input and daily_answer_input.strip():
                        save_daily_answer_record(current_user, selected_date_str, daily_question_str, daily_answer_input.strip())
                    
                    st.success("일기가 성공적으로 저장되었습니다!")
                    st.session_state.page = "public_calendar" if is_target_public else "secret_calendar"
                    st.rerun()
                else:
                    st.warning("내용을 입력해 주세요.")
        with col_return_action:
            if st.button("🗓️ 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "public_calendar" if is_public_page else "secret_calendar"
                st.rerun()
        with col_delete_action:
            if has_existing_diary and st.button("🗑️ 삭제", use_container_width=True):
                delete_diary_entry(current_user, selected_date_str)
                st.success("일기가 삭제되었습니다.")
                st.session_state.page = "public_calendar" if is_public_page else "secret_calendar"
                st.rerun()

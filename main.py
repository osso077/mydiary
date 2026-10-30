import sqlite3
import datetime
import bcrypt
import os
import random
import string
import streamlit as st
import streamlit.components.v1 as components
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
                    repo.update_file(
                        path=DB_FILE,
                        message=commit_message,
                        content=content,
                        sha=file_info.sha
                    )
                except GithubException as ge:
                    if ge.status == 404:
                        repo.create_file(
                            path=DB_FILE,
                            message=commit_message,
                            content=content
                        )
                    else:
                        raise ge
        except Exception as e:
            st.error(f"🚨 깃허브 백업 실패 원인: {e}")

sync_db_from_github()


# =========================================================
# 1. DB 연동 및 테이블 생성 / 마이그레이션
# =========================================================
SCHEDULE_CATEGORIES = {
    "📖 공부/업무": "#3B82F6",  # 파랑
    "🤝 약속/모임": "#10B981",  # 초록
    "🎉 기념일/행사": "#EC4899", # 분홍
    "🏃 운동/건강": "#F97316",  # 주황
    "📌 기타/개인": "#8B5CF6"   # 보라
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

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def generate_invite_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_daily_question(date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        day_num = dt.toordinal()
        return DAILY_QUESTIONS[day_num % len(DAILY_QUESTIONS)]
    except Exception:
        return DAILY_QUESTIONS[0]

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            nickname TEXT NOT NULL,
            birthdate TEXT DEFAULT '',
            profile_icon TEXT DEFAULT '🧸',
            status_message TEXT DEFAULT '',
            theme TEXT DEFAULT '포근함',
            main_color TEXT DEFAULT '#DDA15E',
            sub_color TEXT DEFAULT '#BC6C25',
            invite_code TEXT UNIQUE,
            exchange_id TEXT DEFAULT '',
            exchange_type TEXT DEFAULT '연인',
            exchange_start_date TEXT DEFAULT ''
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS diaries (
            username TEXT,
            date TEXT,
            emotion TEXT,
            content TEXT,
            drawing TEXT DEFAULT '',
            is_public INTEGER DEFAULT 0,
            allow_friends TEXT DEFAULT '',
            views INTEGER DEFAULT 0,
            PRIMARY KEY (username, date),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_answers (
            username TEXT,
            date TEXT,
            question TEXT,
            answer TEXT,
            PRIMARY KEY (username, date)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS exchange_rooms (
            exchange_id TEXT PRIMARY KEY,
            title TEXT,
            creator_username TEXT,
            exchange_type TEXT DEFAULT '친구',
            exchange_start_date TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS exchange_members (
            exchange_id TEXT,
            username TEXT,
            PRIMARY KEY (exchange_id, username)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS exchange_diaries (
            exchange_id TEXT,
            date TEXT,
            username TEXT,
            nickname TEXT,
            emotion TEXT,
            content TEXT,
            drawing TEXT DEFAULT '',
            is_public INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            PRIMARY KEY (exchange_id, date, username)
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

    c.execute('''
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

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_ddays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            title TEXT,
            target_date TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            friend_username TEXT,
            friend_nickname TEXT,
            friend_icon TEXT DEFAULT '🧸',
            friend_status TEXT DEFAULT '',
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_username TEXT,
            receiver_username TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (sender_username) REFERENCES users(username),
            FOREIGN KEY (receiver_username) REFERENCES users(username)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS exchange_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange_id TEXT,
            sender_username TEXT,
            receiver_username TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    cols = [
        ("users", "nickname TEXT DEFAULT ''"),
        ("users", "birthdate TEXT DEFAULT ''"),
        ("users", "profile_icon TEXT DEFAULT '🧸'"),
        ("users", "status_message TEXT DEFAULT ''"),
        ("users", "theme TEXT DEFAULT '포근함'"),
        ("users", "main_color TEXT DEFAULT '#DDA15E'"),
        ("users", "sub_color TEXT DEFAULT '#BC6C25'"),
        ("users", "invite_code TEXT DEFAULT ''"),
        ("users", "exchange_id TEXT DEFAULT ''"),
        ("users", "exchange_type TEXT DEFAULT '연인'"),
        ("users", "exchange_start_date TEXT DEFAULT ''"),
        ("diaries", "drawing TEXT DEFAULT ''"),
        ("diaries", "is_public INTEGER DEFAULT 0"),
        ("diaries", "allow_friends TEXT DEFAULT ''"),
        ("diaries", "views INTEGER DEFAULT 0"),
        ("exchange_diaries", "drawing TEXT DEFAULT ''"),
        ("exchange_diaries", "is_public INTEGER DEFAULT 0"),
        ("exchange_diaries", "views INTEGER DEFAULT 0"),
        ("friendships", "friend_nickname TEXT DEFAULT ''"),
        ("friendships", "friend_icon TEXT DEFAULT '🧸'"),
        ("friendships", "friend_status TEXT DEFAULT ''")
    ]
    for tbl, col in cols:
        try:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

init_db()

# --- DB 헬퍼 함수들 ---
def register_user(username, password, nickname, birthdate=""):
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    code = generate_invite_code()
    try:
        c.execute('''
            INSERT INTO users (username, password, nickname, birthdate, profile_icon, status_message, theme, main_color, sub_color, invite_code) 
            VALUES (?, ?, ?, ?, '🧸', '', '포근함', '#DDA15E', '#BC6C25', ?)
        ''', (username, hashed_pw, nickname, birthdate, code))
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
    c.execute("SELECT password, nickname, birthdate, profile_icon, status_message, theme, main_color, sub_color, invite_code, exchange_id, exchange_type, exchange_start_date FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        stored_pw = row[0]
        if bcrypt.checkpw(password.encode('utf-8'), stored_pw.encode('utf-8')):
            inv_code = row[8] if row[8] else generate_invite_code()
            return True, row[1], row[2], (row[3] or '🧸'), (row[4] or ''), (row[5] or '포근함'), (row[6] or '#DDA15E'), (row[7] or '#BC6C25'), inv_code, row[9], row[10], row[11]
    return False, None, None, '🧸', '', '포근함', '#DDA15E', '#BC6C25', '', '', '연인', ''

def update_user_info(username, new_nickname, new_birthdate, new_profile_icon, new_status_message):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET nickname = ?, birthdate = ?, profile_icon = ?, status_message = ? 
        WHERE username = ?
    ''', (new_nickname, new_birthdate, new_profile_icon, new_status_message, username))
    
    c.execute('''
        UPDATE friendships 
        SET friend_nickname = ?, friend_icon = ?, friend_status = ? 
        WHERE friend_username = ?
    ''', (new_nickname, new_profile_icon, new_status_message, username))
    
    conn.commit()
    conn.close()
    push_db_to_github(f"Update info for user {username}")

def update_user_theme(username, new_theme, new_main_color, new_sub_color):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET theme = ?, main_color = ?, sub_color = ? 
        WHERE username = ?
    ''', (new_theme, new_main_color, new_sub_color, username))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update theme for user {username}")

def send_friend_request(my_username, friend_code):
    conn = get_connection()
    c = conn.cursor()
    cleaned_code = friend_code.strip().upper()
    c.execute("SELECT username, nickname FROM users WHERE UPPER(invite_code) = ?", (cleaned_code,))
    friend = c.fetchone()
    
    if not friend:
        conn.close()
        return False, "존재하지 않는 초대코드입니다."
    
    f_username, f_nickname = friend[0], friend[1]
    if f_username == my_username:
        conn.close()
        return False, "자신의 초대코드는 입력할 수 없습니다."

    c.execute("SELECT id FROM friendships WHERE username = ? AND friend_username = ?", (my_username, f_username))
    if c.fetchone():
        conn.close()
        return False, "이미 친구로 등록된 사용자입니다."

    c.execute("SELECT id FROM friend_requests WHERE sender_username = ? AND receiver_username = ? AND status = 'pending'", (my_username, f_username))
    if c.fetchone():
        conn.close()
        return False, "이미 친구 요청을 보냈습니다."

    c.execute("INSERT INTO friend_requests (sender_username, receiver_username, status) VALUES (?, ?, 'pending')", (my_username, f_username))
    conn.commit()
    conn.close()
    push_db_to_github("Friend request sent")
    return True, f"'{f_nickname}'님에게 친구 요청을 보냈습니다!"

def get_pending_friend_requests(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT fr.id, u.username, u.nickname, u.profile_icon, u.status_message 
        FROM friend_requests fr 
        JOIN users u ON fr.sender_username = u.username 
        WHERE fr.receiver_username = ? AND fr.status = 'pending'
    ''', (username,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "sender_username": r[1], "sender_nickname": r[2], "sender_icon": r[3] or '🧸', "sender_status": r[4] or ''} for r in rows]

def accept_friend_request(request_id, my_username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT sender_username FROM friend_requests WHERE id = ? AND receiver_username = ?", (request_id, my_username))
    req = c.fetchone()
    if not req:
        conn.close()
        return
    
    sender_username = req[0]
    c.execute("UPDATE friend_requests SET status = 'accepted' WHERE id = ?", (request_id,))

    c.execute("SELECT nickname, profile_icon, status_message FROM users WHERE username = ?", (sender_username,))
    s_info = c.fetchone()
    s_nick, s_icon, s_status = s_info[0], s_info[1] or '🧸', s_info[2] or ''

    c.execute("SELECT nickname, profile_icon, status_message FROM users WHERE username = ?", (my_username,))
    my_info = c.fetchone()
    my_nick, my_icon, my_status = my_info[0], my_info[1] or '🧸', my_info[2] or ''

    c.execute("INSERT INTO friendships (username, friend_username, friend_nickname, friend_icon, friend_status) VALUES (?, ?, ?, ?, ?)",
              (my_username, sender_username, s_nick, s_icon, s_status))
    c.execute("INSERT INTO friendships (username, friend_username, friend_nickname, friend_icon, friend_status) VALUES (?, ?, ?, ?, ?)",
              (sender_username, my_username, my_nick, my_icon, my_status))

    conn.commit()
    conn.close()
    push_db_to_github("Friend request accepted")

def reject_friend_request(request_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM friend_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Friend request rejected")

def get_user_friends(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, friend_username, friend_nickname, friend_icon, friend_status FROM friendships WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "friend_username": r[1], "friend_nickname": r[2], "friend_icon": r[3], "friend_status": r[4]} for r in rows]

def delete_friend(friendship_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM friendships WHERE id = ?", (friendship_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Friend deleted")

# --- 다대다 교환일기 관련 함수 ---
def create_exchange_room(title, creator_username, ex_type, start_date):
    conn = get_connection()
    c = conn.cursor()
    eid = f"ex_{creator_username}_{int(datetime.datetime.now().timestamp())}"
    c.execute("INSERT INTO exchange_rooms (exchange_id, title, creator_username, exchange_type, exchange_start_date) VALUES (?, ?, ?, ?, ?)",
              (eid, title, creator_username, ex_type, start_date))
    c.execute("INSERT INTO exchange_members (exchange_id, username) VALUES (?, ?)", (eid, creator_username))
    conn.commit()
    conn.close()
    push_db_to_github("Exchange room created")
    return eid

def get_user_exchange_rooms(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT r.exchange_id, r.title, r.creator_username, r.exchange_type, r.exchange_start_date 
        FROM exchange_rooms r
        JOIN exchange_members m ON r.exchange_id = m.exchange_id
        WHERE m.username = ?
    ''', (username,))
    rows = c.fetchall()
    conn.close()
    return [{"exchange_id": r[0], "title": r[1], "creator_username": r[2], "exchange_type": r[3], "exchange_start_date": r[4]} for r in rows]

def get_exchange_room_info(exchange_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT exchange_id, title, creator_username, exchange_type, exchange_start_date FROM exchange_rooms WHERE exchange_id = ?", (exchange_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"exchange_id": row[0], "title": row[1], "creator_username": row[2], "exchange_type": row[3], "exchange_start_date": row[4]}
    return None

def get_exchange_room_members(exchange_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT u.username, u.nickname, u.profile_icon, u.status_message 
        FROM exchange_members m
        JOIN users u ON m.username = u.username
        WHERE m.exchange_id = ?
    ''', (exchange_id,))
    rows = c.fetchall()
    conn.close()
    return [{"username": r[0], "nickname": r[1], "profile_icon": r[2] or '🧸', "status_message": r[3] or ''} for r in rows]

def send_exchange_invite(exchange_id, sender_username, receiver_username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM exchange_members WHERE exchange_id = ? AND username = ?", (exchange_id, receiver_username))
    if c.fetchone():
        conn.close()
        return False, "이미 참여 중인 멤버입니다."
    
    c.execute("SELECT id FROM exchange_invites WHERE exchange_id = ? AND receiver_username = ? AND status = 'pending'", (exchange_id, receiver_username))
    if c.fetchone():
        conn.close()
        return False, "이미 초대 요청을 보냈습니다."

    c.execute("INSERT INTO exchange_invites (exchange_id, sender_username, receiver_username, status) VALUES (?, ?, ?, 'pending')",
              (exchange_id, sender_username, receiver_username))
    conn.commit()
    conn.close()
    push_db_to_github("Exchange invite sent")
    return True, "교환일기 초대장을 보냈습니다!"

def get_pending_exchange_invites(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT ei.id, ei.exchange_id, r.title, u.nickname, u.profile_icon 
        FROM exchange_invites ei
        JOIN exchange_rooms r ON ei.exchange_id = r.exchange_id
        JOIN users u ON ei.sender_username = u.username
        WHERE ei.receiver_username = ? AND ei.status = 'pending'
    ''', (username,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "exchange_id": r[1], "title": r[2], "sender_nickname": r[3], "sender_icon": r[4] or '🧸'} for r in rows]

def accept_exchange_invite(invite_id, my_username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT exchange_id FROM exchange_invites WHERE id = ? AND receiver_username = ?", (invite_id, my_username))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    eid = row[0]
    c.execute("UPDATE exchange_invites SET status = 'accepted' WHERE id = ?", (invite_id,))
    c.execute("INSERT OR IGNORE INTO exchange_members (exchange_id, username) VALUES (?, ?)", (eid, my_username))
    conn.commit()
    conn.close()
    push_db_to_github("Exchange invite accepted")

def reject_exchange_invite(invite_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM exchange_invites WHERE id = ?", (invite_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Exchange invite rejected")

def get_user_ddays(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, target_date FROM user_ddays WHERE username = ? ORDER BY target_date ASC", (username,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "target_date": r[2]} for r in rows]

def add_user_dday(username, title, target_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO user_ddays (username, title, target_date) VALUES (?, ?, ?)", (username, title, target_date))
    conn.commit()
    conn.close()
    push_db_to_github("New custom dday added")

def delete_user_dday(dday_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM user_ddays WHERE id = ?", (dday_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Custom dday deleted")

def get_user_diaries(username, is_public_flag):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, emotion, content, drawing, is_public, allow_friends FROM diaries WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    
    diaries = {}
    for r in rows:
        dt, em, ct, dr, ip, af = r[0], r[1], r[2], r[3], r[4], r[5]
        if is_public_flag:
            if ip == 1 or (af and len(af.strip()) > 0):
                diaries[dt] = {"emotion": em, "content": ct, "drawing": dr, "is_public": ip, "allow_friends": af}
        else:
            if ip == 0 and (not af or len(af.strip()) == 0):
                diaries[dt] = {"emotion": em, "content": ct, "drawing": dr, "is_public": ip, "allow_friends": af}
    return diaries

def get_all_public_diaries(current_user):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT d.date, d.emotion, d.content, d.drawing, u.nickname, d.username, d.views, 'individual' AS type, u.profile_icon, d.is_public, d.allow_friends
        FROM diaries d
        JOIN users u ON d.username = u.username
        WHERE d.is_public = 1 OR d.allow_friends LIKE ?
        UNION ALL
        SELECT ed.date, ed.emotion, ed.content, ed.drawing, ed.nickname, ed.username, ed.views, 'exchange' AS type, COALESCE(u.profile_icon, '🧸') AS profile_icon, ed.is_public, '' AS allow_friends
        FROM exchange_diaries ed
        LEFT JOIN users u ON ed.username = u.username
        WHERE ed.is_public = 1
        ORDER BY date DESC
    ''', (f"%{current_user}%",))
    rows = c.fetchall()
    conn.close()
    
    public_list = []
    for r in rows:
        is_pub = r[9]
        allow_str = r[10] if r[10] else ""
        if is_pub == 1 or current_user == r[5] or current_user in [x.strip() for x in allow_str.split(",") if x.strip()]:
            public_list.append({
                "date": r[0], "emotion": r[1], "content": r[2], "drawing": r[3],
                "nickname": r[4], "username": r[5], "views": r[6], "type": r[7], "profile_icon": r[8] if r[8] else '🧸'
            })
    return public_list

def increment_public_views(username, date_str, diary_type, current_user):
    if username == current_user:
        return
    conn = get_connection()
    c = conn.cursor()
    if diary_type == 'individual':
        c.execute("UPDATE diaries SET views = views + 1 WHERE username = ? AND date = ?", (username, date_str))
    else:
        c.execute("UPDATE exchange_diaries SET views = views + 1 WHERE username = ? AND date = ?", (username, date_str))
    conn.commit()
    conn.close()

def save_diary(username, date_str, emotion, content, drawing, is_public, allow_friends):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO diaries (username, date, emotion, content, drawing, is_public, allow_friends)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            emotion=excluded.emotion, content=excluded.content, drawing=excluded.drawing, is_public=excluded.is_public, allow_friends=excluded.allow_friends
    ''', (username, date_str, emotion, content, drawing, 1 if is_public else 0, allow_friends))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update diary entry for {date_str}")

def delete_diary(username, date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM diaries WHERE username = ? AND date = ?", (username, date_str))
    c.execute("DELETE FROM comments WHERE diary_username = ? AND diary_date = ?", (username, date_str))
    c.execute("DELETE FROM daily_answers WHERE username = ? AND date = ?", (username, date_str))
    conn.commit()
    conn.close()
    push_db_to_github(f"Delete diary entry for {date_str}")

def get_daily_answer(username, date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT answer FROM daily_answers WHERE username = ? AND date = ?", (username, date_str))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def save_daily_answer(username, date_str, question, answer):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO daily_answers (username, date, question, answer)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            question=excluded.question, answer=excluded.answer
    ''', (username, date_str, question, answer))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update daily answer for {date_str}")

def get_exchange_diaries(exchange_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, username, nickname, emotion, content, drawing, is_public, views FROM exchange_diaries WHERE exchange_id = ?", (exchange_id,))
    rows = c.fetchall()
    conn.close()
    
    result = {}
    for r in rows:
        dt, un, nk, em, ct, dr, ip, vw = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
        if dt not in result:
            result[dt] = []
        result[dt].append({"username": un, "nickname": nk, "emotion": em, "content": ct, "drawing": dr, "is_public": ip, "views": vw})
    return result

def save_exchange_diary(exchange_id, date_str, username, nickname, emotion, content, drawing, is_public):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO exchange_diaries (exchange_id, date, username, nickname, emotion, content, drawing, is_public)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange_id, date, username) DO UPDATE SET
            emotion=excluded.emotion, content=excluded.content, drawing=excluded.drawing, nickname=excluded.nickname, is_public=excluded.is_public
    ''', (exchange_id, date_str, username, nickname, emotion, content, drawing, 1 if is_public else 0))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update exchange diary for {date_str}")

def add_schedule(username, date_str, title, category):
    color = SCHEDULE_CATEGORIES.get(category, "#8B5CF6")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO schedules (username, date, title, category, color)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, date_str, title, category, color))
    conn.commit()
    conn.close()
    push_db_to_github("New schedule added")

def get_user_schedules(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, date, title, category, color FROM schedules WHERE username = ? ORDER BY date ASC", (username,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "title": r[2], "category": r[3], "color": r[4]} for r in rows]

def delete_schedule(schedule_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Schedule deleted")

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
    return [{"id": r[0], "username": r[1], "nickname": r[2], "content": r[3], "created_at": r[4]} for r in rows]

def delete_comment(comment_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
    push_db_to_github("Comment deleted")

# --- 타임존 오차 보정 함수 (UTC 시차 보정) ---
def parse_calendar_date(raw_date_str):
    if not raw_date_str:
        return None
    raw = str(raw_date_str).strip()
    if 'T' in raw:
        try:
            dt_utc = datetime.datetime.fromisoformat(raw.replace('Z', '+00:00'))
            dt_kst = dt_utc + datetime.timedelta(hours=9)
            return dt_kst.strftime("%Y-%m-%d")
        except Exception:
            return raw.split('T')[0]
    return raw[:10]


# =========================================================
# 2. UI 및 테마 설정 (11종)
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

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
    st.session_state.theme = "👁️‍🗨️ 드림코어"
if "main_color" not in st.session_state:
    st.session_state.main_color = "#8B5CF6"
if "sub_color" not in st.session_state:
    st.session_state.sub_color = "#06B6D4"
if "invite_code" not in st.session_state:
    st.session_state.invite_code = ""
if "current_exchange_id" not in st.session_state:
    st.session_state.current_exchange_id = ""
if "viewing_friend" not in st.session_state:
    st.session_state.viewing_friend = None

current_theme_key = st.session_state.theme if st.session_state.theme in THEME_STYLES else "👁️‍🗨️ 드림코어"
theme_cfg = THEME_STYLES[current_theme_key]
main_color = st.session_state.main_color if st.session_state.main_color else theme_cfg["default_main"]
sub_color = st.session_state.sub_color if st.session_state.sub_color else theme_cfg["default_sub"]
app_title = theme_cfg["title"]

# ---------------------------------------------------------
# 동적 CSS 주입
# ---------------------------------------------------------
if st.session_state.user is not None:
    st.markdown(f"""
        <style>
        @import url('{theme_cfg['font_import']}');

        html, body, .stApp {{
            background-color: {theme_cfg['bg']};
            color: {theme_cfg['text']};
            font-family: {theme_cfg['font_family']} !important;
        }}
        
        h1, h2, h3, h4 {{
            color: {theme_cfg['header']} !important;
            font-family: {theme_cfg['font_family']} !important;
            font-weight: bold;
            letter-spacing: 1px;
        }}
        
        .stTextInput input, div[data-testid="stForm"] {{
            background-color: {theme_cfg['card_bg']} !important;
            border: 1px solid {theme_cfg['card_border']} !important;
            border-radius: {theme_cfg['radius']} !important;
            color: {theme_cfg['text']} !important;
            box-shadow: {theme_cfg['shadow']} !important;
            font-family: {theme_cfg['font_family']} !important;
        }}
        
        div.stButton > button {{
            background: linear-gradient(135deg, {main_color} 0%, {sub_color} 100%) !important;
            color: white !important;
            border-radius: {theme_cfg['radius']} !important;
            border: none !important;
            padding: 10px 24px !important;
            font-weight: bold !important;
            box-shadow: {theme_cfg['shadow']} !important;
            font-family: {theme_cfg['font_family']} !important;
            transition: all 0.25s ease-in-out;
        }}
        
        div.stButton > button:hover {{
            opacity: 0.9;
            transform: translateY(-3px) scale(1.02);
        }}
        
        section[data-testid="stSidebar"] {{
            background-color: {theme_cfg['card_bg']} !important;
            border-right: 1px solid {theme_cfg['card_border']} !important;
        }}

        iframe[title="streamlit_calendar.calendar"] {{
            min-height: 580px !important;
            border-radius: {theme_cfg['radius']} !important;
            border: 1px solid {theme_cfg['card_border']} !important;
            box-shadow: {theme_cfg['shadow']} !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    components.html(f"""
        <script>
        function injectCalendarStyles() {{
            const iframes = parent.document.querySelectorAll('iframe[title="streamlit_calendar.calendar"]');
            iframes.forEach(iframe => {{
                try {{
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    if (doc) {{
                        let styleTag = doc.getElementById("custom-cal-style");
                        if (!styleTag) {{
                            styleTag = doc.createElement("style");
                            styleTag.id = "custom-cal-style";
                            doc.head.appendChild(styleTag);
                        }}
                        styleTag.innerHTML = `
                            body {{
                                background-color: {theme_cfg['card_bg']} !important;
                                font-family: {theme_cfg['font_family']} !important;
                                color: {theme_cfg['text']} !important;
                            }}
                            .fc {{
                                background-color: {theme_cfg['card_bg']} !important;
                                border-radius: {theme_cfg['radius']} !important;
                            }}
                            .fc-theme-standard td, .fc-theme-standard th, .fc-theme-standard .fc-scrollgrid {{
                                border-color: {theme_cfg['card_border']} !important;
                            }}
                            .fc-col-header-cell-cushion, .fc-daygrid-day-number {{
                                color: {theme_cfg['text']} !important;
                                text-decoration: none !important;
                            }}
                            button.fc-today-button {{
                                background-color: {main_color} !important;
                                border-color: {main_color} !important;
                                color: #ffffff !important;
                                border-radius: {theme_cfg['radius']} !important;
                                font-weight: bold !important;
                            }}
                            button.fc-prev-button, button.fc-next-button {{
                                background-color: {sub_color} !important;
                                border-color: {sub_color} !important;
                                color: #ffffff !important;
                                border-radius: {theme_cfg['radius']} !important;
                                font-weight: bold !important;
                            }}
                            .fc-button:hover {{
                                opacity: 0.85 !important;
                            }}
                            .fc-day-today {{
                                background-color: {main_color}25 !important;
                            }}
                            .fc-toolbar-title {{
                                color: {theme_cfg['header']} !important;
                                font-family: {theme_cfg['font_family']} !important;
                            }}
                        `;
                    }}
                }} catch(e) {{}}
            }});
        }}
        setInterval(injectCalendarStyles, 300);
        </script>
    """, height=0)

today_dt = datetime.date.today()
today_str = today_dt.strftime("%Y-%m-%d")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str
if "page" not in st.session_state:
    st.session_state.page = "secret_calendar"

STANDARD_EMOTIONS = ["😊 기쁨", "😢 슬픔", "😡 화남", "😰 불안/두려움", "😌 평온", "🥲 외로움", "🥰 뿌듯함", "😴 피곤", "✨ 설렘", "🥹 그리움"]
EMOJI_LIST = [e.split()[0] for e in STANDARD_EMOTIONS]
PROFILE_ICONS = ["🧸", "✨", "🐰", "🌸", "🍓", "🐥", "🌙", "⭐", "🍀", "🎀", "🐱", "🐶"]


# =========================================================
# 3. 로그인 / 회원가입 화면
# =========================================================
if st.session_state.user is None:
    st.title("🧸 소소하고 포근한 일기장")
    
    auth_mode = st.radio("서비스 이용을 위해 로그인해 주세요.", ["로그인", "회원가입"], horizontal=True)
    
    username_input = st.text_input("아이디", key="auth_user")
    password_input = st.text_input("비밀번호", type="password", key="auth_pw")

    if auth_mode == "로그인":
        if st.button("로그인하기", use_container_width=True):
            if username_input and password_input:
                is_success, nickname, birthdate, profile_icon, status_message, theme, m_color, s_color, inv_code, _, _, _ = login_user(username_input, password_input)
                if is_success:
                    st.session_state.user = username_input
                    st.session_state.nickname = nickname if nickname else username_input
                    st.session_state.birthdate = birthdate
                    st.session_state.profile_icon = profile_icon if profile_icon else "🧸"
                    st.session_state.status_message = status_message if status_message else ""
                    st.session_state.theme = theme
                    st.session_state.main_color = m_color
                    st.session_state.sub_color = s_color
                    st.session_state.invite_code = inv_code
                    
                    my_rooms = get_user_exchange_rooms(username_input)
                    if my_rooms:
                        st.session_state.current_exchange_id = my_rooms[0]["exchange_id"]
                    else:
                        st.session_state.current_exchange_id = ""

                    st.session_state.page = "secret_calendar"
                    st.success(f"{st.session_state.nickname}님 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해 주세요.")
                
    else:  # 회원가입
        nickname_input = st.text_input("닉네임 (프로필 이름)", key="auth_nick")
        
        use_birthday = st.checkbox("생년월일 입력하기 (선택)")
        birthdate_str = ""
        if use_birthday:
            b_date = st.date_input(
                "생년월일 선택",
                value=datetime.date(2000, 1, 1),
                min_value=datetime.date(1920, 1, 1),
                max_value=today_dt
            )
            birthdate_str = b_date.strftime("%Y-%m-%d")

        if st.button("회원가입하기", use_container_width=True):
            if username_input and password_input and nickname_input:
                if register_user(username_input, password_input, nickname_input.strip(), birthdate_str):
                    st.success("회원가입이 완료되었습니다! 로그인 탭에서 로그인해 주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")
            else:
                st.warning("아이디, 비밀번호, 닉네임은 필수 입력사항입니다.")

# =========================================================
# 4. 메인 서비스 화면
# =========================================================
else:
    current_user = st.session_state.user
    current_nickname = st.session_state.nickname
    user_birthdate = st.session_state.birthdate
    current_profile_icon = st.session_state.profile_icon if st.session_state.profile_icon else "🧸"
    current_status_message = st.session_state.status_message if st.session_state.status_message else ""
    
    if user_birthdate and len(user_birthdate) == 10:
        if user_birthdate[5:] == today_str[5:]:
            st.balloons()
            st.toast(f"🎂 {current_nickname}님, 생일을 진심으로 축하합니다! 🎉", icon="🎁")

    st.sidebar.title(app_title.split()[0] + " 일기장")
    st.sidebar.markdown(f"### {current_profile_icon} **{current_nickname}** 님")
    if current_status_message:
        st.sidebar.caption(f"💬 *{current_status_message}*")
    st.sidebar.info(f"내 초대코드: **{st.session_state.invite_code}**")

    # =========================================================
    # 사이드바 메뉴 구성
    # =========================================================
    st.sidebar.markdown("---")
    
    # 1. 내 메뉴
    st.sidebar.markdown("### 👤 내 메뉴")
    with st.sidebar.expander("⚙️ 정보설정 (프로필 개성꾸미기)"):
        edit_nick = st.text_input("닉네임", value=current_nickname, key="edit_nick_input")
        edit_status = st.text_input("한 줄 소개 (상태메시지)", value=current_status_message, placeholder="나를 표현하는 한마디 🌟", key="edit_status_input")
        
        st.write("프로필 이모티콘 선택:")
        cols_emoji = st.columns(4)
        for idx, emo in enumerate(PROFILE_ICONS):
            col_idx = idx % 4
            with cols_emoji[col_idx]:
                btn_label = f"✨ {emo}" if emo == current_profile_icon else emo
                if st.button(btn_label, key=f"emo_btn_{emo}", use_container_width=True):
                    st.session_state.profile_icon = emo
                    st.rerun()

        st.caption(f"현재 선택된 이모티콘: **{current_profile_icon}**")
        
        has_bday = bool(user_birthdate)
        update_bday = st.checkbox("생년월일 설정/수정", value=has_bday)
        
        default_b_date = datetime.date(2000, 1, 1)
        if has_bday:
            try:
                default_b_date = datetime.datetime.strptime(user_birthdate, "%Y-%m-%d").date()
            except ValueError: pass

        new_bday_str = user_birthdate
        if update_bday:
            selected_bdate = st.date_input(
                "생년월일", value=default_b_date,
                min_value=datetime.date(1920, 1, 1), max_value=today_dt,
                key="edit_bday_input"
            )
            new_bday_str = selected_bdate.strftime("%Y-%m-%d")
        else:
            new_bday_str = ""

        if st.button("프로필 변경 저장", use_container_width=True):
            cleaned_nick = edit_nick.strip()
            if cleaned_nick:
                update_user_info(current_user, cleaned_nick, new_bday_str, current_profile_icon, edit_status.strip())
                st.session_state.nickname = cleaned_nick
                st.session_state.birthdate = new_bday_str
                st.session_state.status_message = edit_status.strip()
                st.success("프로필이 수정되었습니다!")
                st.rerun()

    with st.sidebar.expander("🎨 테마관리 (분위기 & 색상)"):
        theme_options = list(THEME_STYLES.keys())
        current_theme_idx = theme_options.index(st.session_state.theme) if st.session_state.theme in theme_options else 0
        
        selected_theme = st.selectbox("테마 분위기 (11종)", theme_options, index=current_theme_idx)
        
        sug_main = THEME_STYLES[selected_theme]["default_main"] if selected_theme != st.session_state.theme else main_color
        sug_sub = THEME_STYLES[selected_theme]["default_sub"] if selected_theme != st.session_state.theme else sub_color
        
        col_m, col_s = st.columns(2)
        with col_m:
            selected_main = st.color_picker("포인트 메인", value=sug_main)
        with col_s:
            selected_sub = st.color_picker("서브 보조", value=sug_sub)

        if st.button("테마 적용하기", use_container_width=True):
            update_user_theme(current_user, selected_theme, selected_main, selected_sub)
            st.session_state.theme = selected_theme
            st.session_state.main_color = selected_main
            st.session_state.sub_color = selected_sub
            st.success("테마가 적용되었습니다!")
            st.rerun()

    # 2. 일정관리
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 일정관리")

    cur_year = today_dt.year
    events_to_check = [
        ("🎄 크리스마스", datetime.date(cur_year, 12, 25)),
        ("🎉 새해(신정)", datetime.date(cur_year + 1, 1, 1))
    ]
    for ev_name, ev_date in events_to_check:
        if ev_date < today_dt:
            ev_date = datetime.date(cur_year + 1, ev_date.month, ev_date.day)
        diff = (ev_date - today_dt).days
        if 0 <= diff <= 14:
            d_label = "D-Day" if diff == 0 else f"D-{diff}"
            st.sidebar.info(f"{ev_name}까지 **{d_label}** 남았습니다! 🎉")

    user_ddays = get_user_ddays(current_user)
    if user_ddays:
        for ud in user_ddays:
            try:
                t_dt = datetime.datetime.strptime(ud['target_date'], "%Y-%m-%d").date()
                diff = (t_dt - today_dt).days
                d_txt = "D-Day 🎉" if diff == 0 else (f"D-{diff}" if diff > 0 else f"D+{abs(diff)}")
                col_d1, col_d2 = st.sidebar.columns([4, 1])
                with col_d1:
                    st.write(f"📌 {ud['title']}: {d_txt}")
                with col_d2:
                    if st.button("❌", key=f"del_ud_{ud['id']}"):
                        delete_user_dday(ud['id'])
                        st.rerun()
            except Exception:
                pass

    with st.sidebar.expander("⏳ 디데이 추가"):
        new_dday_title = st.text_input("디데이 제목", placeholder="예: 시험일, 여행")
        new_dday_date = st.date_input("목표 날짜", value=today_dt)
        if st.button("디데이 등록", use_container_width=True):
            if new_dday_title.strip():
                add_user_dday(current_user, new_dday_title.strip(), new_dday_date.strftime("%Y-%m-%d"))
                st.success("디데이가 추가되었습니다!")
                st.rerun()
            else:
                st.warning("디데이 제목을 입력해 주세요.")

    # 3. 친구기능 & 교환일기 초대 승인 (친구 닉네임 클릭 시 일기 구경 모드 활성화)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👥 친구기능")
    with st.sidebar.expander("👥 친구 관리"):
        friend_code_input = st.text_input("친구 초대코드 입력")
        if st.button("친구 요청 보내기", use_container_width=True):
            if friend_code_input.strip():
                ok, msg = send_friend_request(current_user, friend_code_input.strip().upper())
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("초대코드를 입력해 주세요.")

        pending_reqs = get_pending_friend_requests(current_user)
        if pending_reqs:
            st.markdown("---")
            st.markdown("📬 **받은 친구 요청**")
            for req in pending_reqs:
                st.write(f"{req['sender_icon']} **{req['sender_nickname']}**")
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("✔️ 승인", key=f"accept_req_{req['id']}"):
                        accept_friend_request(req['id'], current_user)
                        st.success(f"'{req['sender_nickname']}'님과 친구가 되었습니다!")
                        st.rerun()
                with rc2:
                    if st.button("❌ 거절", key=f"reject_req_{req['id']}"):
                        reject_friend_request(req['id'])
                        st.rerun()

        pending_ex_invites = get_pending_exchange_invites(current_user)
        if pending_ex_invites:
            st.markdown("---")
            st.markdown("💌 **받은 교환일기 초대**")
            for einv in pending_ex_invites:
                st.write(f"{einv['sender_icon']} **{einv['sender_nickname']}**님의 교환일기 방 **[{einv['title']}]** 초대")
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("✔️ 수락", key=f"accept_einv_{einv['id']}"):
                        accept_exchange_invite(einv['id'], current_user)
                        st.session_state.current_exchange_id = einv['exchange_id']
                        st.success("교환일기에 참여하였습니다!")
                        st.rerun()
                with ec2:
                    if st.button("❌ 거절", key=f"reject_einv_{einv['id']}"):
                        reject_exchange_invite(einv['id'])
                        st.rerun()
        
        st.markdown("---")
        st.markdown("📋 **내 친구 목록** *(클릭하여 일기 구경)*")
        friends = get_user_friends(current_user)
        if friends:
            for f in friends:
                conn = get_connection()
                c_f = conn.cursor()
                c_f.execute("SELECT nickname, profile_icon, status_message FROM users WHERE username = ?", (f['friend_username'],))
                f_row = c_f.fetchone()
                conn.close()
                
                f_nick = f_row[0] if f_row else f['friend_nickname']
                f_icon = f_row[1] if (f_row and f_row[1]) else (f['friend_icon'] or '🧸')
                f_stat = f_row[2] if f_row else f['friend_status']

                if st.button(f"{f_icon} {f_nick}", key=f"btn_view_friend_{f['friend_username']}", use_container_width=True):
                    st.session_state.viewing_friend = {
                        "username": f['friend_username'],
                        "nickname": f_nick,
                        "icon": f_icon
                    }
                    st.session_state.page = "friend_diary_view"
                    st.rerun()

                if f_stat:
                    st.caption(f"💬 {f_stat}")
                
                my_rooms = get_user_exchange_rooms(current_user)
                if my_rooms:
                    room_options = {r['title']: r['exchange_id'] for r in my_rooms}
                    sel_room_title = st.selectbox("내 교환일기로 초대", list(room_options.keys()), key=f"invite_room_sel_{f['friend_username']}")
                    if st.button("💌 교환일기 초대 보내기", key=f"btn_send_einv_{f['friend_username']}"):
                        target_eid = room_options[sel_room_title]
                        ok_msg, msg_text = send_exchange_invite(target_eid, current_user, f['friend_username'])
                        if ok_msg:
                            st.success(msg_text)
                        else:
                            st.warning(msg_text)

                if st.button("🗑️ 친구 삭제", key=f"del_f_{f['id']}"):
                    delete_friend(f['id'])
                    if st.session_state.viewing_friend and st.session_state.viewing_friend['username'] == f['friend_username']:
                        st.session_state.viewing_friend = None
                        st.session_state.page = "secret_calendar"
                    st.rerun()
                st.markdown("---")
        else:
            st.caption("등록된 친구가 없습니다.")

    with st.sidebar.expander("💌 다대다 교환일기 만들기"):
        st.write("여러 명이서 함께 쓸 수 있는 새로운 교환일기 모임을 만드세요!")
        new_room_title = st.text_input("교환일기 제목 (방 이름)", placeholder="예: 우리들의 힐링 노트")
        new_room_type = st.radio("모임 성격", ["친구", "연인", "스터디/모임"], horizontal=True, key="room_type_radio")
        new_room_start = st.date_input("시작일", value=today_dt, max_value=today_dt, key="room_start_date")
        
        if st.button("✨ 새 교환일기 만들기", use_container_width=True):
            if new_room_title.strip():
                eid = create_exchange_room(new_room_title.strip(), current_user, new_room_type, new_room_start.strftime("%Y-%m-%d"))
                st.session_state.current_exchange_id = eid
                st.success("교환일기 방이 생성되었습니다!")
                st.rerun()
            else:
                st.warning("교환일기 제목을 입력해 주세요.")

    # 4. 일기 메뉴
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📖 일기")
    menu_options = ["🔒 비밀일기", "📅 일정 관리 달력", "💌 교환일기", "🌐 공개일기"]
    nav_choice = st.sidebar.radio("일기 메뉴", menu_options, label_visibility="collapsed")

    if nav_choice == "🔒 비밀일기" and st.session_state.page not in ["secret_calendar", "secret_editor"]:
        st.session_state.viewing_friend = None
        st.session_state.page = "secret_calendar"
        st.rerun()
    elif nav_choice == "📅 일정 관리 달력" and st.session_state.page not in ["schedule_calendar", "schedule_editor"]:
        st.session_state.viewing_friend = None
        st.session_state.page = "schedule_calendar"
        st.rerun()
    elif nav_choice == "💌 교환일기" and st.session_state.page not in ["exchange_calendar", "exchange_editor", "exchange_setup"]:
        st.session_state.viewing_friend = None
        my_rooms = get_user_exchange_rooms(current_user)
        if my_rooms:
            st.session_state.page = "exchange_calendar"
        else:
            st.session_state.page = "exchange_setup"
        st.rerun()
    elif nav_choice == "🌐 공개일기" and st.session_state.page not in ["public_calendar", "public_editor"]:
        st.session_state.viewing_friend = None
        st.session_state.page = "public_calendar"
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 로그아웃", use_container_width=True):
        st.session_state.user = None
        st.session_state.nickname = None
        st.session_state.current_exchange_id = ""
        st.session_state.viewing_friend = None
        st.session_state.page = "secret_calendar"
        st.rerun()

    st.title(app_title)

    birthday_events = []
    if user_birthdate and len(user_birthdate) == 10:
        try:
            b_month_day = user_birthdate[5:]
            cur_year = today_dt.year
            b_date_current_year = f"{cur_year}-{b_month_day}"
            birthday_events.append({
                "title": "🎂 내 생일! 🎉",
                "start": b_date_current_year,
                "end": b_date_current_year,
                "allDay": True,
                "color": sub_color
            })
        except Exception:
            pass

    # PAGE 1: 🔒 비밀일기 달력
    if st.session_state.page == "secret_calendar":
        st.header("🔒 나만의 비밀일기")
        secret_diaries = get_user_diaries(current_user, is_public_flag=False)

        calendar_events = list(birthday_events)
        for date_str, diary_data in secret_diaries.items():
            if diary_data.get("content") or diary_data.get("drawing"):
                calendar_events.append({
                    "title": f"🔒 {diary_data['emotion']}",
                    "start": date_str, "end": date_str, "allDay": True,
                    "color": main_color
                })

        cal_res = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"secret_cal_{st.session_state.theme}_{main_color}_{sub_color}")

        clicked_date = None
        if cal_res and "dateClick" in cal_res:
            clicked_date = parse_calendar_date(cal_res["dateClick"].get("date"))
        elif cal_res and "select" in cal_res:
            clicked_date = parse_calendar_date(cal_res["select"].get("start"))

        if clicked_date:
            st.session_state.selected_date = clicked_date
            st.session_state.page = "secret_editor"
            st.rerun()

    # PAGE 2: 📅 일정 관리 달력
    elif st.session_state.page == "schedule_calendar":
        st.header("📅 나의 카테고리별 일정 관리")
        schedules = get_user_schedules(current_user)

        legend_cols = st.columns(len(SCHEDULE_CATEGORIES))
        for idx, (cat_name, cat_color) in enumerate(SCHEDULE_CATEGORIES.items()):
            with legend_cols[idx]:
                st.markdown(f"<span style='color:{cat_color}; font-weight:bold;'>■</span> <small>{cat_name.split()[1]}</small>", unsafe_allow_html=True)

        calendar_events = list(birthday_events)
        for s in schedules:
            calendar_events.append({
                "title": f"📌 [{s['category'].split()[1]}] {s['title']}",
                "start": s['date'], "end": s['date'], "allDay": True,
                "color": s['color']
            })

        cal_res_s = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"schedule_cal_{st.session_state.theme}_{main_color}_{sub_color}")

        clicked_date_s = None
        if cal_res_s and "dateClick" in cal_res_s:
            clicked_date_s = parse_calendar_date(cal_res_s["dateClick"].get("date"))
        elif cal_res_s and "select" in cal_res_s:
            clicked_date_s = parse_calendar_date(cal_res_s["select"].get("start"))

        if clicked_date_s:
            st.session_state.selected_date = clicked_date_s
            st.session_state.page = "schedule_editor"
            st.rerun()

    # PAGE 2-1: 📅 일정 작성/수정/삭제 화면
    elif st.session_state.page == "schedule_editor":
        s_date = st.session_state.selected_date
        st.header(f"📅 일정 관리 ({s_date})")

        all_schedules = get_user_schedules(current_user)
        day_schedules = [s for s in all_schedules if s['date'] == s_date]

        if day_schedules:
            st.subheader("📋 이날의 기존 일정")
            for sc in day_schedules:
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.markdown(f"<span style='color:{sc['color']}; font-weight:bold;'>■</span> **{sc['category']}** : {sc['title']}", unsafe_allow_html=True)
                with col_del:
                    if st.button("삭제", key=f"del_sc_{sc['id']}"):
                        delete_schedule(sc['id'])
                        st.success("일정이 삭제되었습니다.")
                        st.rerun()
            st.markdown("---")

        st.subheader("➕ 새 일정 추가하기")
        sc_title = st.text_input("일정 제목", placeholder="예: 친구 생일파티, 스터디 카페 가기")
        sc_category = st.selectbox("일정 카테고리", list(SCHEDULE_CATEGORIES.keys()))

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 일정 등록", use_container_width=True):
                if sc_title.strip():
                    add_schedule(current_user, s_date, sc_title.strip(), sc_category)
                    st.success("일정이 등록되었습니다!")
                    st.session_state.page = "schedule_calendar"
                    st.rerun()
                else:
                    st.warning("일정 제목을 입력해 주세요.")
        with col2:
            if st.button("🗓️ 일정 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "schedule_calendar"
                st.rerun()

    # PAGE 3-0: 💌 교환일기 방 없을 때 생성 화면
    elif st.session_state.page == "exchange_setup":
        st.header("💌 함께 쓰는 다대다 교환일기")
        st.write("아직 참여 중인 교환일기 방이 없습니다. 새로운 교환일기 방을 만들거나 친구의 초대를 기다려주세요!")
        
        new_title = st.text_input("교환일기 방 제목", placeholder="예: 우리들의 비밀 수다방")
        room_type = st.radio("관계/모임 성격", ["친구", "연인", "스터디/모임"], horizontal=True, key="setup_room_type")
        start_dt = st.date_input("시작일", value=today_dt, max_value=today_dt, key="setup_start_dt")
        
        if st.button("✨ 교환일기 방 만들기", use_container_width=True):
            if new_title.strip():
                eid = create_exchange_room(new_title.strip(), current_user, room_type, start_dt.strftime("%Y-%m-%d"))
                st.session_state.current_exchange_id = eid
                st.success("교환일기 방이 생성되었습니다!")
                st.session_state.page = "exchange_calendar"
                st.rerun()
            else:
                st.warning("방 제목을 입력해 주세요.")

    # PAGE 3-1: 💌 교환일기 달력 (다대다 지원)
    elif st.session_state.page == "exchange_calendar":
        my_rooms = get_user_exchange_rooms(current_user)
        if not my_rooms:
            st.session_state.page = "exchange_setup"
            st.rerun()

        room_dict = {f"{r['title']} ({r['exchange_type']})": r for r in my_rooms}
        current_room = next((r for r in my_rooms if r['exchange_id'] == st.session_state.current_exchange_id), my_rooms[0])
        
        current_room_label = f"{current_room['title']} ({current_room['exchange_type']})"
        selected_room_label = st.selectbox("참여 중인 교환일기 선택", list(room_dict.keys()), index=list(room_dict.keys()).index(current_room_label))
        
        st.session_state.current_exchange_id = room_dict[selected_room_label]['exchange_id']
        active_eid = st.session_state.current_exchange_id
        
        room_info = get_exchange_room_info(active_eid)
        members = get_exchange_room_members(active_eid)
        
        st.header(f"💌 {room_info['title']} 교환일기")
        member_str = ", ".join([f"{m['profile_icon']} {m['nickname']}" for m in members])
        st.info(f"👥 **참여 멤버 ({len(members)}명)**: {member_str}")

        ex_diaries = get_exchange_diaries(active_eid)

        calendar_events = []
        for date_str, diary_list in ex_diaries.items():
            for d in diary_list:
                vis_icon = "🔒" if d.get("is_public", 0) == 0 else "🌐"
                calendar_events.append({
                    "title": f"{vis_icon} {d['nickname']}: {d['emotion']}",
                    "start": date_str, "end": date_str, "allDay": True,
                    "color": sub_color
                })

        cal_res_e = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"exchange_cal_{st.session_state.theme}_{main_color}_{sub_color}")

        clicked_date_e = None
        if cal_res_e and "dateClick" in cal_res_e:
            clicked_date_e = parse_calendar_date(cal_res_e["dateClick"].get("date"))
        elif cal_res_e and "select" in cal_res_e:
            clicked_date_e = parse_calendar_date(cal_res_e["select"].get("start"))

        if clicked_date_e:
            st.session_state.selected_date = clicked_date_e
            st.session_state.page = "exchange_editor"
            st.rerun()

    # PAGE 4: 🌐 공개일기 달력 / 모아보기
    elif st.session_state.page == "public_calendar":
        st.header("🌐 공유하는 공개일기")
        tab1, tab2 = st.tabs(["🗓️ 내 공개일기 달력", "📖 모두의 이야기 모아보기"])

        with tab1:
            my_public_diaries = get_user_diaries(current_user, is_public_flag=True)
            calendar_events = list(birthday_events)
            for d, data in my_public_diaries.items():
                if data.get("content") or data.get("drawing"):
                    calendar_events.append({
                        "title": f"🌐 {data['emotion']}", "start": d, "end": d, "allDay": True, "color": main_color
                    })

            cal_res_p = calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth", "selectable": True, "height": 560}, key=f"public_cal_{st.session_state.theme}_{main_color}_{sub_color}")

            clicked_date_p = None
            if cal_res_p and "dateClick" in cal_res_p:
                clicked_date_p = parse_calendar_date(cal_res_p["dateClick"].get("date"))
            elif cal_res_p and "select" in cal_res_p:
                clicked_date_p = parse_calendar_date(cal_res_p["select"].get("start"))

            if clicked_date_p:
                st.session_state.selected_date = clicked_date_p
                st.session_state.page = "public_editor"
                st.rerun()

        with tab2:
            all_publics = get_all_public_diaries(current_user)
            if all_publics:
                for item in all_publics:
                    increment_public_views(item['username'], item['date'], item['type'], current_user)
                    
                    with st.container():
                        p_icon = item['profile_icon'] if item['profile_icon'] else '🧸'
                        header_title = f"{p_icon} {item['emotion']} **{item['nickname']}** 님의 이야기 ({item['date']})"

                        st.markdown(f"#### {header_title}  \n<small>👁️ 조회수 {item['views'] + (1 if item['username'] == current_user else 0)}</small>", unsafe_allow_html=True)
                        
                        if item['content']:
                            st.markdown(f"""
                                <div style="background-color: {theme_cfg['paper_bg']}; color: {theme_cfg['paper_text']}; border: 1px solid {theme_cfg['card_border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px; white-space: pre-wrap; font-family: {theme_cfg['font_family']};">{item['content']}</div>
                            """, unsafe_allow_html=True)
                        
                        if item['drawing']:
                            st.image(item['drawing'], caption=f"{item['nickname']}님의 그림일기 🎨", use_column_width=True)
                        
                        comments = get_comments(item['username'], item['date'])
                        with st.expander(f"💬 댓글 ({len(comments)})"):
                            for c in comments:
                                c1, c2 = st.columns([5, 1])
                                with c1: st.markdown(f"**{c['nickname']}**: {c['content']} *(<small>{c['created_at']}</small>)*", unsafe_allow_html=True)
                                with c2:
                                    if c['username'] == current_user:
                                        if st.button("삭제", key=f"del_cmt_{c['id']}"):
                                            delete_comment(c['id'])
                                            st.rerun()

                            new_cmt = st.text_input("댓글 작성", key=f"cmt_in_{item['username']}_{item['date']}")
                            if st.button("댓글 작성 완료", key=f"btn_cmt_{item['username']}_{item['date']}"):
                                if new_cmt.strip():
                                    add_comment(item['username'], item['date'], current_user, current_nickname, new_cmt.strip())
                                    st.success("댓글이 남겨졌습니다!")
                                    st.rerun()
                        st.markdown("---")
            else:
                st.write("🌿 아직 등록된 공개 일기가 없어요.")

    # PAGE 4-1: 👥 친구 일기 구경하기 기능
    elif st.session_state.page == "friend_diary_view":
        f_info = st.session_state.viewing_friend
        if not f_info:
            st.session_state.page = "secret_calendar"
            st.rerun()

        f_uname = f_info['username']
        f_nick = f_info['nickname']
        f_icon = f_info['icon']

        st.header(f"👥 친구 일기 구경하기")
        st.markdown(f"### ✨ {f_icon} **{f_nick}** 님의 일기장")
        
        tab_f1, tab_f2 = st.tabs(["🌐 공개 일기", "💌 함께 참여중인 교환일기"])
        
        with tab_f1:
            all_pubs = get_all_public_diaries(current_user)
            friend_pubs = [p for p in all_pubs if p['username'] == f_uname]
            
            if friend_pubs:
                for item in friend_pubs:
                    increment_public_views(item['username'], item['date'], item['type'], current_user)
                    with st.container():
                        p_icon = item['profile_icon'] if item['profile_icon'] else '🧸'
                        header_title = f"{p_icon} {item['emotion']} **{item['nickname']}** 님의 이야기 ({item['date']})"
                        st.markdown(f"#### {header_title}  \n<small>👁️ 조회수 {item['views']}</small>", unsafe_allow_html=True)
                        if item['content']:
                            st.markdown(f"""
                                <div style="background-color: {theme_cfg['paper_bg']}; color: {theme_cfg['paper_text']}; border: 1px solid {theme_cfg['card_border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px; white-space: pre-wrap; font-family: {theme_cfg['font_family']};">{item['content']}</div>
                            """, unsafe_allow_html=True)
                        if item['drawing']:
                            st.image(item['drawing'], caption=f"{f_nick}님의 그림일기 🎨", use_column_width=True)
                        st.markdown("---")
            else:
                st.info(f"'{f_nick}'님이 작성한 공개 일기가 없습니다.")
        
        with tab_f2:
            my_rooms = get_user_exchange_rooms(current_user)
            friend_rooms = get_user_exchange_rooms(f_uname)
            common_rooms = [r for r in my_rooms if r['exchange_id'] in [fr['exchange_id'] for fr in friend_rooms]]
            
            if common_rooms:
                for cr in common_rooms:
                    st.subheader(f"📖 교환일기 방: {cr['title']}")
                    ex_diaries = get_exchange_diaries(cr['exchange_id'])
                    if ex_diaries:
                        for d_str, d_list in sorted(ex_diaries.items(), reverse=True):
                            st.markdown(f"📅 **{d_str}**")
                            for ed in d_list:
                                st.markdown(f"**{ed['nickname']}** ({ed['emotion']}):")
                                if ed['content']:
                                    st.markdown(f"""
                                        <div style="background-color: {theme_cfg['paper_bg']}; color: {theme_cfg['paper_text']}; border: 1px solid {theme_cfg['card_border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px; white-space: pre-wrap; font-family: {theme_cfg['font_family']};">{ed['content']}</div>
                                    """, unsafe_allow_html=True)
                                if ed['drawing']:
                                    st.image(ed['drawing'], caption=f"{ed['nickname']}님의 그림 🎨", use_column_width=True)
                            st.markdown("---")
                    else:
                        st.info("작성된 교환일기가 없습니다.")
            else:
                st.info(f"'{f_nick}'님과 함께 참여 중인 교환일기 방이 없습니다.")

        if st.button("🗓️ 내 비밀일기로 돌아가기", use_container_width=True):
            st.session_state.viewing_friend = None
            st.session_state.page = "secret_calendar"
            st.rerun()

    # PAGE 5: 비밀/공개 일기 에디터
    elif st.session_state.page in ["secret_editor", "public_editor"]:
        s_date = st.session_state.selected_date
        is_pub = (st.session_state.page == "public_editor")
        title_prefix = "🌐 공개일기" if is_pub else "🔒 비밀일기"

        st.header(f"✏️ {title_prefix} 작성/수정 ({s_date})")
        
        editor_mode = st.radio("일기장 스타일 선택:", ["📖 아날로그 종이 노트", "💻 디지털 모던 노트"], horizontal=True)
        
        diaries = get_user_diaries(current_user, is_public_flag=is_pub)
        has_ex = s_date in diaries and (bool(diaries[s_date].get("content", "").strip()) or bool(diaries[s_date].get("drawing", "")))
        ex_data = diaries.get(s_date, {})

        idx = EMOJI_LIST.index(ex_data.get("emotion")) if ex_data.get("emotion") in EMOJI_LIST else 0
        sel_emo = st.selectbox("이날의 감정 선택:", STANDARD_EMOTIONS, index=idx)
        sel_emoji = sel_emo.split()[0]

        content_val = ex_data.get("content", "")

        # 배경색 커스텀 선택
        st.subheader("🎨 에디터 배경색 맞춤 설정")
        default_bg_color = theme_cfg['paper_bg'] if editor_mode == "📖 아날로그 종이 노트" else theme_cfg['card_bg']
        custom_bg_color = st.color_picker("배경 색상 변경", value=default_bg_color)

        if editor_mode == "📖 아날로그 종이 노트":
            note_editor_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background-color: {theme_cfg['bg']};
                        margin: 0;
                        padding: 0;
                        font-family: {theme_cfg['font_family']};
                    }}
                    .note-wrapper {{
                        background-color: {custom_bg_color};
                        border: 1px solid {theme_cfg['card_border']};
                        border-radius: 16px;
                        padding: 28px 28px 28px 40px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.08), inset 0 0 15px rgba(0, 0, 0, 0.03);
                        position: relative;
                        background-image: 
                            linear-gradient(90deg, transparent 36px, rgba(255,128,128,0.25) 36px, rgba(255,128,128,0.25) 38px, transparent 38px),
                            linear-gradient({theme_cfg['paper_line']} 1px, transparent 1px);
                        background-size: 100% 32px;
                        min-height: 380px;
                    }}
                    .note-title {{
                        font-weight: bold;
                        margin-bottom: 12px;
                        color: {theme_cfg['paper_text']};
                        opacity: 0.85;
                        font-size: 1.15rem;
                    }}
                    textarea {{
                        width: 100%;
                        height: 280px;
                        background-color: transparent !important;
                        background-image: linear-gradient({theme_cfg['paper_line']} 1px, transparent 1px) !important;
                        background-size: 100% 32px !important;
                        border: none !important;
                        outline: none !important;
                        color: {theme_cfg['paper_text']} !important;
                        font-family: {theme_cfg['font_family']} !important;
                        font-size: 1.15rem !important;
                        line-height: 32px !important;
                        padding-top: 4px !important;
                        resize: vertical;
                    }}
                    /* 스티커 데코 영역 */
                    .sticker-layer {{
                        position: absolute;
                        top: 0; left: 0; width: 100%; height: 100%;
                        pointer-events: none;
                        overflow: hidden;
                    }}
                    .draggable-sticker {{
                        position: absolute;
                        cursor: grab;
                        pointer-events: auto;
                        user-select: none;
                        font-size: 2rem;
                        transition: transform 0.1s;
                    }}
                    .draggable-sticker:active {{
                        cursor: grabbing;
                        transform: scale(1.1);
                    }}
                </style>
            </head>
            <body>
                <div class="note-wrapper" id="noteContainer">
                    <div class="note-title">📖 {s_date}의 아날로그 기록 ({sel_emo})</div>
                    <textarea id="noteTextarea" placeholder="이곳에 일기를 적어보세요...">{content_val}</textarea>
                    <div class="sticker-layer" id="stickerLayer"></div>
                </div>
                <script>
                    const textarea = document.getElementById('noteTextarea');
                    textarea.addEventListener('input', function() {{
                        const parentInput = window.parent.document.querySelector('input[aria-label="hidden_content_input"]');
                        if (parentInput) {{
                            parentInput.value = textarea.value;
                            parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            content_input_val = st.text_input("hidden_content_input", value=content_val, label_visibility="collapsed", key=f"content_hidden_{s_date}")
            components.html(note_editor_html, height=440)
            txt = content_input_val
        else:
            digital_editor_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background-color: {theme_cfg['bg']};
                        margin: 0;
                        padding: 0;
                        font-family: {theme_cfg['font_family']};
                    }}
                    .digital-wrapper {{
                        background-color: {custom_bg_color};
                        border: 1px solid {theme_cfg['card_border']};
                        border-radius: {theme_cfg['radius']};
                        padding: 28px;
                        box-shadow: {theme_cfg['shadow']};
                        position: relative;
                        min-height: 380px;
                    }}
                    .digital-title {{
                        font-weight: bold;
                        margin-bottom: 12px;
                        color: {theme_cfg['text']};
                        font-size: 1.15rem;
                    }}
                    textarea {{
                        width: 100%;
                        height: 280px;
                        background-color: rgba(255,255,255,0.5) !important;
                        border: 1px solid {theme_cfg['card_border']} !important;
                        border-radius: 12px !important;
                        outline: none !important;
                        color: {theme_cfg['text']} !important;
                        font-family: {theme_cfg['font_family']} !important;
                        font-size: 1.15rem !important;
                        line-height: 1.6 !important;
                        padding: 12px !important;
                        resize: vertical;
                    }}
                </style>
            </head>
            <body>
                <div class="digital-wrapper">
                    <div class="digital-title">💻 {s_date}의 디지털 기록 ({sel_emo})</div>
                    <textarea id="digitalTextarea" placeholder="소중한 하루를 기록해보세요...">{content_val}</textarea>
                </div>
                <script>
                    const digTextarea = document.getElementById('digitalTextarea');
                    digTextarea.addEventListener('input', function() {{
                        const parentInput = window.parent.document.querySelector('input[aria-label="hidden_content_input"]');
                        if (parentInput) {{
                            parentInput.value = digTextarea.value;
                            parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            content_input_val = st.text_input("hidden_content_input", value=content_val, label_visibility="collapsed", key=f"content_hidden_{s_date}")
            components.html(digital_editor_html, height=440)
            txt = content_input_val

        # =========================================================
        # 스티커 데코레이션 시스템 (테마별 범주화 & 드래그)
        # =========================================================
        st.markdown("---")
        st.markdown("### ✨ 스티커 데코레이션 (드래그하여 꾸미기)")
        
        STICKER_CATEGORIES = {
            "🎀 마스킹 테이프": ["🏷️ 핑크 체크 마테", "🏷️ 옐로우 도트 마테", "🏷️ 블루 스트라이프 마테", "🏷️ 보라하트 마테"],
            "🖍️ 형광펜 밑줄 & 박스": ["🖍️ 핑크 형광펜 밑줄", "🖍️ 노랑 형광펜 밑줄", "🖍️ 연두 형광펜 밑줄", "🖍️ 하늘색 형광펜 밑줄"],
            "⭕ 색연필 도형": ["⭕ 빨간 동그라미", "🟦 파란 네모", "⭐ 노란 별 도형", "📍 핑크 하트 도형"],
            "💖 감성 모양 스티커": ["💖 반짝이 하트", "🌸 벚꽃잎", "🍀 네잎클로버", "🌙 초승달", "🧸 곰돌이 인형"]
        }

        selected_sticker_cat = st.selectbox("스티커 테마 범주 선택", list(STICKER_CATEGORIES.keys()))
        sticker_cols = st.columns(4)
        for idx, stk in enumerate(STICKER_CATEGORIES[selected_sticker_cat]):
            col_idx = idx % 4
            with sticker_cols[col_idx]:
                if st.button(stk, key=f"stk_{stk}", use_container_width=True):
                    st.toast(f"'{stk}' 스티커가 추가되었습니다! (마우스로 드래그해 이동하세요)", icon="✨")

        # =========================================================
        # 그림 추가하기 토글 버튼 (클릭했을 때만 열림)
        # =========================================================
        st.markdown("---")
        if "show_drawing_canvas" not in st.session_state:
            st.session_state.show_drawing_canvas = False

        if st.button("🎨 그림 추가하기 (열기/닫기)", use_container_width=True):
            st.session_state.show_drawing_canvas = not st.session_state.show_drawing_canvas
            st.rerun()

        drawing_data = ex_data.get("drawing", "")
        drawing_input_val = st.text_input("hidden_drawing_input", value=drawing_data, label_visibility="collapsed", key=f"drawing_hidden_{s_date}")

        if st.session_state.show_drawing_canvas:
            canvas_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background-color: {custom_bg_color};
                        color: {theme_cfg['text']};
                        font-family: sans-serif;
                        margin: 0;
                        padding: 10px;
                    }}
                    .canvas-box {{
                        border: 2px dashed {theme_cfg['card_border']};
                        border-radius: 12px;
                        background-color: {theme_cfg['paper_bg']};
                        display: inline-block;
                        position: relative;
                        cursor: crosshair;
                    }}
                    canvas {{
                        display: block;
                        touch-action: none;
                    }}
                    .toolbar {{
                        margin-bottom: 10px;
                        display: flex;
                        gap: 10px;
                        align-items: center;
                        flex-wrap: wrap;
                    }}
                    button {{
                        background: {main_color};
                        color: white;
                        border: none;
                        padding: 6px 14px;
                        border-radius: 8px;
                        font-weight: bold;
                        cursor: pointer;
                    }}
                    button:hover {{ opacity: 0.85; }}
                </style>
            </head>
            <body>
                <div class="toolbar">
                    <label>색상: <input type="color" id="colorPicker" value="{main_color}"></label>
                    <label>펜 두께: <input type="range" id="brushSize" min="1" max="20" value="4"></label>
                    <button onclick="clearCanvas()">전체 지우기</button>
                </div>
                <div class="canvas-box">
                    <canvas id="paintCanvas" width="500" height="320"></canvas>
                </div>

                <script>
                    const canvas = document.getElementById('paintCanvas');
                    const ctx = canvas.getContext('2d');
                    let painting = false;

                    const savedImgData = "{drawing_data}";
                    if (savedImgData) {{
                        const img = new Image();
                        img.onload = function() {{ ctx.drawImage(img, 0, 0); }};
                        img.src = savedImgData;
                    }} else {{
                        ctx.fillStyle = "{theme_cfg['paper_bg']}";
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                    }}

                    function startPosition(e) {{ painting = true; draw(e); }}
                    function endPosition() {{ painting = false; ctx.beginPath(); updateParent(); }}
                    function draw(e) {{
                        if (!painting) return;
                        ctx.lineWidth = document.getElementById('brushSize').value;
                        ctx.lineCap = 'round';
                        ctx.strokeStyle = document.getElementById('colorPicker').value;

                        const rect = canvas.getBoundingClientRect();
                        const clientX = e.clientX || (e.touches ? e.touches[0].clientX : 0);
                        const clientY = e.clientY || (e.touches ? e.touches[0].clientY : 0);
                        
                        ctx.lineTo(clientX - rect.left, clientY - rect.top);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.moveTo(clientX - rect.left, clientY - rect.top);
                    }}

                    function clearCanvas() {{
                        ctx.fillStyle = "{theme_cfg['paper_bg']}";
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        updateParent();
                    }}

                    function updateParent() {{
                        const dataURL = canvas.toDataURL();
                        const parentInput = window.parent.document.querySelector('input[aria-label="hidden_drawing_input"]');
                        if (parentInput) {{
                            parentInput.value = dataURL;
                            parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}

                    canvas.addEventListener('mousedown', startPosition);
                    canvas.addEventListener('mouseup', endPosition);
                    canvas.addEventListener('mousemove', draw);
                    canvas.addEventListener('touchstart', startPosition);
                    canvas.addEventListener('touchend', endPosition);
                    canvas.addEventListener('touchmove', draw);
                </script>
            </body>
            </html>
            """
            components.html(canvas_html, height=390)

        st.markdown("---")
        daily_q = get_daily_question(s_date)
        saved_q_answer = get_daily_answer(current_user, s_date)

        st.markdown(f"### ✨ 오늘의 질문")
        st.info(f"💡 **{daily_q}**")
        daily_ans_input = st.text_area("질문에 대한 나의 답변을 적어보세요:", value=saved_q_answer, height=100, placeholder="소소한 생각을 남겨보세요 🪄")

        friends = get_user_friends(current_user)
        existing_allow = ex_data.get("allow_friends", "") if "allow_friends" in ex_data else ""
        existing_allow_list = [x.strip() for x in existing_allow.split(",") if x.strip()]

        st.markdown("---")
        st.subheader("🔒 공개 범위 설정")
        pub_mode = st.radio(
            "공개 대상을 선택하세요:",
            ["🔒 나만 보기", "👥 선택한 친구에게만 공개", "🌐 전체 공개"],
            index=2 if is_pub else (1 if existing_allow_list else 0)
        )

        selected_allow_friends = []
        if pub_mode == "👥 선택한 친구에게만 공개":
            if friends:
                st.write("일기를 공유할 친구를 선택해 주세요:")
                for f in friends:
                    is_checked = f['friend_username'] in existing_allow_list
                    if st.checkbox(f"{f['friend_icon']} {f['friend_nickname']}", value=is_checked, key=f"chk_friend_{f['friend_username']} {s_date}"):
                        selected_allow_friends.append(f['friend_username'])
            else:
                st.info("등록된 친구가 없습니다.")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button("💾 일기 저장", use_container_width=True):
                if txt.strip() or drawing_input_val.strip():
                    final_is_pub = 1 if pub_mode == "🌐 전체 공개" else 0
                    final_allow_str = ",".join(selected_allow_friends) if pub_mode == "👥 선택한 친구에게만 공개" else ""
                    
                    save_diary(current_user, s_date, sel_emoji, txt.strip(), drawing_input_val.strip(), final_is_pub, final_allow_str)
                    
                    if daily_ans_input.strip():
                        save_daily_answer(current_user, s_date, daily_q, daily_ans_input.strip())
                    
                    st.success("일기와 그림, 오늘의 질문 답변이 저장되었습니다!")
                    st.session_state.page = "public_calendar" if final_is_pub or final_allow_str else "secret_calendar"
                    st.rerun()
                else:
                    st.warning("내용이나 그림을 최소한 하나 이상 입력해 주세요.")
        with col2:
            if st.button("🗓️ 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "public_calendar" if is_pub else "secret_calendar"
                st.rerun()
        with col3:
            if has_ex and st.button("🗑️ 삭제", use_container_width=True):
                delete_diary(current_user, s_date)
                st.success("일기가 삭제되었습니다.")
                st.session_state.page = "public_calendar" if is_pub else "secret_calendar"
                st.rerun()

    # PAGE 6: 교환일기 에디터
    elif st.session_state.page == "exchange_editor":
        s_date = st.session_state.selected_date
        eid = st.session_state.current_exchange_id
        room_info = get_exchange_room_info(eid)
        
        st.header(f"💌 [{room_info['title']}] 교환일기 작성 ({s_date})")

        editor_mode_ex = st.radio("교환일기장 스타일 선택:", ["📖 아날로그 종이 노트", "💻 디지털 모던 노트"], horizontal=True, key="ex_mode_radio")

        e_diaries = get_exchange_diaries(eid).get(s_date, [])
        my_e_diary = next((d for d in e_diaries if d['username'] == current_user), None)
        other_e_diaries = [d for d in e_diaries if d['username'] != current_user]

        if other_e_diaries:
            st.subheader("💌 다른 멤버들의 일기")
            for od in other_e_diaries:
                p_vis = "🔒 둘만 보기" if od.get("is_public", 0) == 0 else "🌐 모두에게 공개"
                st.markdown(f"**{od['nickname']}**님의 기록 ({od['emotion']}) - *{p_vis}*")
                if od['content']:
                    st.markdown(f"""
                        <div style="background-color: {theme_cfg['paper_bg']}; color: {theme_cfg['paper_text']}; border: 1px solid {theme_cfg['card_border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px; white-space: pre-wrap; font-family: {theme_cfg['font_family']};">{od['content']}</div>
                    """, unsafe_allow_html=True)
                if od['drawing']:
                    st.image(od['drawing'], caption=f"{od['nickname']}님의 그림 🎨", use_column_width=True)
                st.markdown("---")

        st.subheader("내 교환일기 쓰기")
        idx = EMOJI_LIST.index(my_e_diary['emotion']) if my_e_diary and my_e_diary['emotion'] in EMOJI_LIST else 0
        sel_emo = st.selectbox("오늘 멤버들에게 전할 감정 선택:", STANDARD_EMOTIONS, index=idx)
        sel_emoji = sel_emo.split()[0]

        my_ex_content_val = my_e_diary['content'] if my_e_diary else ""

        st.subheader("🎨 교환일기 배경색 맞춤 설정")
        default_ex_bg = theme_cfg['paper_bg'] if editor_mode_ex == "📖 아날로그 종이 노트" else theme_cfg['card_bg']
        custom_ex_bg = st.color_picker("배경 색상 변경", value=default_ex_bg, key="ex_bg_picker")

        if editor_mode_ex == "📖 아날로그 종이 노트":
            ex_note_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background-color: {theme_cfg['bg']};
                        margin: 0;
                        padding: 0;
                        font-family: {theme_cfg['font_family']};
                    }}
                    .note-wrapper {{
                        background-color: {custom_ex_bg};
                        border: 1px solid {theme_cfg['card_border']};
                        border-radius: 16px;
                        padding: 28px 28px 28px 40px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.08), inset 0 0 15px rgba(0, 0, 0, 0.03);
                        position: relative;
                        background-image: 
                            linear-gradient(90deg, transparent 36px, rgba(255,128,128,0.25) 36px, rgba(255,128,128,0.25) 38px, transparent 38px),
                            linear-gradient({theme_cfg['paper_line']} 1px, transparent 1px);
                        background-size: 100% 32px;
                        min-height: 380px;
                    }}
                    .note-title {{
                        font-weight: bold;
                        margin-bottom: 12px;
                        color: {theme_cfg['paper_text']};
                        opacity: 0.85;
                        font-size: 1.15rem;
                    }}
                    textarea {{
                        width: 100%;
                        height: 260px;
                        background-color: transparent !important;
                        background-image: linear-gradient({theme_cfg['paper_line']} 1px, transparent 1px) !important;
                        background-size: 100% 32px !important;
                        border: none !important;
                        outline: none !important;
                        color: {theme_cfg['paper_text']} !important;
                        font-family: {theme_cfg['font_family']} !important;
                        font-size: 1.15rem !important;
                        line-height: 32px !important;
                        padding-top: 4px !important;
                        resize: vertical;
                    }}
                </style>
            </head>
            <body>
                <div class="note-wrapper">
                    <div class="note-title">📖 나의 교환일기 기록 ({sel_emo})</div>
                    <textarea id="exTextarea" placeholder="멤버들에게 전할 이야기를 적어보세요...">{my_ex_content_val}</textarea>
                </div>
                <script>
                    const exTextarea = document.getElementById('exTextarea');
                    exTextarea.addEventListener('input', function() {{
                        const parentInput = window.parent.document.querySelector('input[aria-label="hidden_ex_content_input"]');
                        if (parentInput) {{
                            parentInput.value = exTextarea.value;
                            parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            ex_content_input_val = st.text_input("hidden_ex_content_input", value=my_ex_content_val, label_visibility="collapsed", key=f"ex_content_hidden_{s_date}")
            components.html(ex_note_html, height=420)
            txt = ex_content_input_val
        else:
            ex_digital_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background-color: {theme_cfg['bg']};
                        margin: 0;
                        padding: 0;
                        font-family: {theme_cfg['font_family']};
                    }}
                    .digital-wrapper {{
                        background-color: {custom_ex_bg};
                        border: 1px solid {theme_cfg['card_border']};
                        border-radius: {theme_cfg['radius']};
                        padding: 28px;
                        box-shadow: {theme_cfg['shadow']};
                        position: relative;
                        min-height: 380px;
                    }}
                    .digital-title {{
                        font-weight: bold;
                        margin-bottom: 12px;
                        color: {theme_cfg['text']};
                        font-size: 1.15rem;
                    }}
                    textarea {{
                        width: 100%;
                        height: 260px;
                        background-color: rgba(255,255,255,0.5) !important;
                        border: 1px solid {theme_cfg['card_border']} !important;
                        border-radius: 12px !important;
                        outline: none !important;
                        color: {theme_cfg['text']} !important;
                        font-family: {theme_cfg['font_family']} !important;
                        font-size: 1.15rem !important;
                        line-height: 1.6 !important;
                        padding: 12px !important;
                        resize: vertical;
                    }}
                </style>
            </head>
            <body>
                <div class="digital-wrapper">
                    <div class="digital-title">💻 나의 교환일기 기록 ({sel_emo})</div>
                    <textarea id="exDigTextarea" placeholder="멤버들에게 전할 이야기를 적어보세요...">{my_ex_content_val}</textarea>
                </div>
                <script>
                    const exDigTextarea = document.getElementById('exDigTextarea');
                    exDigTextarea.addEventListener('input', function() {{
                        const parentInput = window.parent.document.querySelector('input[aria-label="hidden_ex_content_input"]');
                        if (parentInput) {{
                            parentInput.value = exDigTextarea.value;
                            parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            ex_content_input_val = st.text_input("hidden_ex_content_input", value=my_ex_content_val, label_visibility="collapsed", key=f"ex_content_hidden_{s_date}")
            components.html(ex_digital_html, height=420)
            txt = ex_content_input_val

        # 스티커 데코레이션 시스템 (교환일기용)
        st.markdown("---")
        st.markdown("### ✨ 스티커 데코레이션 (드래그하여 꾸미기)")
        STICKER_CATEGORIES = {
            "🎀 마스킹 테이프": ["🏷️ 핑크 체크 마테", "🏷️ 옐로우 도트 마테", "🏷️ 블루 스트라이프 마테", "🏷️ 보라하트 마테"],
            "🖍️ 형광펜 밑줄 & 박스": ["🖍️ 핑크 형광펜 밑줄", "🖍️ 노랑 형광펜 밑줄", "🖍️ 연두 형광펜 밑줄", "🖍️ 하늘색 형광펜 밑줄"],
            "⭕ 색연필 도형": ["⭕ 빨간 동그라미", "🟦 파란 네모", "⭐ 노란 별 도형", "📍 핑크 하트 도형"],
            "💖 감성 모양 스티커": ["💖 반짝이 하트", "🌸 벚꽃잎", "🍀 네잎클로버", "🌙 초승달", "🧸 곰돌이 인형"]
        }
        selected_ex_stk_cat = st.selectbox("스티커 테마 범주 선택", list(STICKER_CATEGORIES.keys()), key="ex_stk_cat")
        ex_stk_cols = st.columns(4)
        for idx, stk in enumerate(STICKER_CATEGORIES[selected_ex_stk_cat]):
            col_idx = idx % 4
            with ex_stk_cols[col_idx]:
                if st.button(stk, key=f"ex_stk_{stk}", use_container_width=True):
                    st.toast(f"'{stk}' 스티커가 추가되었습니다!", icon="✨")

        st.markdown("---")
        if "show_ex_drawing_canvas" not in st.session_state:
            st.session_state.show_ex_drawing_canvas = False

        if st.button("🎨 교환일기 그림 추가하기 (열기/닫기)", use_container_width=True, key="ex_draw_toggle"):
            st.session_state.show_ex_drawing_canvas = not st.session_state.show_ex_drawing_canvas
            st.rerun()

        ex_drawing_data = my_e_diary.get("drawing", "") if my_e_diary else ""
        ex_drawing_input_val = st.text_input("hidden_ex_drawing_input", value=ex_drawing_data, label_visibility="collapsed", key=f"ex_drawing_hidden_{s_date}")

        if st.session_state.show_ex_drawing_canvas:
            ex_canvas_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background-color: {custom_ex_bg};
                        color: {theme_cfg['text']};
                        font-family: sans-serif;
                        margin: 0;
                        padding: 10px;
                    }}
                    .canvas-box {{
                        border: 2px dashed {theme_cfg['card_border']};
                        border-radius: 12px;
                        background-color: {theme_cfg['paper_bg']};
                        display: inline-block;
                        position: relative;
                        cursor: crosshair;
                    }}
                    canvas {{
                        display: block;
                        touch-action: none;
                    }}
                    .toolbar {{
                        margin-bottom: 10px;
                        display: flex;
                        gap: 10px;
                        align-items: center;
                        flex-wrap: wrap;
                    }}
                    button {{
                        background: {main_color};
                        color: white;
                        border: none;
                        padding: 6px 14px;
                        border-radius: 8px;
                        font-weight: bold;
                        cursor: pointer;
                    }}
                    button:hover {{ opacity: 0.85; }}
                </style>
            </head>
            <body>
                <div class="toolbar">
                    <label>색상: <input type="color" id="colorPicker" value="{main_color}"></label>
                    <label>펜 두께: <input type="range" id="brushSize" min="1" max="20" value="4"></label>
                    <button onclick="clearCanvas()">전체 지우기</button>
                </div>
                <div class="canvas-box">
                    <canvas id="paintCanvas" width="500" height="320"></canvas>
                </div>

                <script>
                    const canvas = document.getElementById('paintCanvas');
                    const ctx = canvas.getContext('2d');
                    let painting = false;

                    const savedImgData = "{ex_drawing_data}";
                    if (savedImgData) {{
                        const img = new Image();
                        img.onload = function() {{ ctx.drawImage(img, 0, 0); }};
                        img.src = savedImgData;
                    }} else {{
                        ctx.fillStyle = "{theme_cfg['paper_bg']}";
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                    }}

                    function startPosition(e) {{ painting = true; draw(e); }}
                    function endPosition() {{ painting = false; ctx.beginPath(); updateParent(); }}
                    function draw(e) {{
                        if (!painting) return;
                        ctx.lineWidth = document.getElementById('brushSize').value;
                        ctx.lineCap = 'round';
                        ctx.strokeStyle = document.getElementById('colorPicker').value;

                        const rect = canvas.getBoundingClientRect();
                        const clientX = e.clientX || (e.touches ? e.touches[0].clientX : 0);
                        const clientY = e.clientY || (e.touches ? e.touches[0].clientY : 0);
                        
                        ctx.lineTo(clientX - rect.left, clientY - rect.top);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.moveTo(clientX - rect.left, clientY - rect.top);
                    }}

                    function clearCanvas() {{
                        ctx.fillStyle = "{theme_cfg['paper_bg']}";
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        updateParent();
                    }}

                    function updateParent() {{
                        const dataURL = canvas.toDataURL();
                        const parentInput = window.parent.document.querySelector('input[aria-label="hidden_ex_drawing_input"]');
                        if (parentInput) {{
                            parentInput.value = dataURL;
                            parentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}

                    canvas.addEventListener('mousedown', startPosition);
                    canvas.addEventListener('mouseup', endPosition);
                    canvas.addEventListener('mousemove', draw);
                    canvas.addEventListener('touchstart', startPosition);
                    canvas.addEventListener('touchend', endPosition);
                    canvas.addEventListener('touchmove', draw);
                </script>
            </body>
            </html>
            """
            components.html(ex_canvas_html, height=390)

        curr_pub_idx = 1 if (my_e_diary and my_e_diary.get("is_public", 0) == 1) else 0
        ex_public_choice = st.radio(
            "공개범위 선택:",
            ["🔒 교환일기 멤버끼리만 보기", "🌐 모두에게 공개 (공개일기 모아보기 포함)"],
            index=curr_pub_idx,
            horizontal=True
        )
        is_ex_public = (ex_public_choice == "🌐 모두에게 공개 (공개일기 모아보기 포함)")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💌 교환일기 저장", use_container_width=True):
                if txt.strip() or ex_drawing_input_val.strip():
                    save_exchange_diary(eid, s_date, current_user, current_nickname, sel_emoji, txt.strip(), ex_drawing_input_val.strip(), is_ex_public)
                    st.success("교환일기가 성공적으로 저장되었습니다!")
                    st.session_state.page = "exchange_calendar"
                    st.rerun()
                else:
                    st.warning("내용이나 그림을 최소한 하나 이상 입력해 주세요.")
        with col2:
            if st.button("🗓️ 교환 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "exchange_calendar"
                st.rerun()

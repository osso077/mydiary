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
                
                # 1. GitHub 저장소에 기존 diary_app.db 파일이 존재하는지 조회
                try:
                    file_info = repo.get_contents(DB_FILE)
                    # 기존 파일이 있다면 sha 값을 명시하여 update
                    repo.update_file(
                        path=DB_FILE,
                        message=commit_message,
                        content=content,
                        sha=file_info.sha
                    )
                except GithubException as ge:
                    # 404 에러(파일이 실제로 저장소에 없는 경우)일 때만 새 파일 생성
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
# 2. UI 및 드라마틱 테마 디자인 설정 (10종)
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

THEME_STYLES = {
    "포근함": {
        "title": "🧸 소소하고 포근한 일기장",
        "bg": "#FAF6F0", "text": "#4A3E3D", "header": "#6C5B52", 
        "card_bg": "#FFFFFF", "card_border": "#E3D5CA", "default_main": "#DDA15E",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
        "font_family": "'Gowun Dodum', sans-serif",
        "radius": "16px", "shadow": "0 4px 12px rgba(0,0,0,0.05)"
    },
    "공주": {
        "title": "👑 공주님의 비밀 다이어리 🎀",
        "bg": "#FFF0F5", "text": "#5C3D46", "header": "#D81B60", 
        "card_bg": "#FFFFFF", "card_border": "#FFB6C1", "default_main": "#FF69B4",
        "font_import": "https://fonts.googleapis.com/css2?family=Single+Day&display=swap",
        "font_family": "'Single Day', cursive",
        "radius": "24px", "shadow": "0 8px 20px rgba(255,105,180,0.15)"
    },
    "귀여움": {
        "title": "🐣 병아리의 자그마한 일기장 🐥",
        "bg": "#FFFBEA", "text": "#4A4438", "header": "#D97706", 
        "card_bg": "#FFFFFF", "card_border": "#FFE599", "default_main": "#FFB000",
        "font_import": "https://fonts.googleapis.com/css2?family=Gamja+Flower&display=swap",
        "font_family": "'Gamja Flower', cursive",
        "radius": "20px", "shadow": "0 6px 14px rgba(255,176,0,0.15)"
    },
    "심플": {
        "title": "MINIMAL DIARY",
        "bg": "#F8F9FA", "text": "#212529", "header": "#1A1D20", 
        "card_bg": "#FFFFFF", "card_border": "#DEE2E6", "default_main": "#343A40",
        "font_import": "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;500&display=swap",
        "font_family": "'Noto Sans KR', sans-serif",
        "radius": "4px", "shadow": "none"
    },
    "클래식": {
        "title": "📖 서재 속 양장본 일기장",
        "bg": "#F4F1EA", "text": "#2C2C2C", "header": "#3D312A", 
        "card_bg": "#FCFBF7", "card_border": "#D2C7B8", "default_main": "#8C6D53",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Batang&display=swap",
        "font_family": "'Gowun Batang', serif",
        "radius": "8px", "shadow": "0 2px 8px rgba(61,49,42,0.08)"
    },
    "🌙 다크(밤)": {
        "title": "🌙 한밤중의 비밀 기록",
        "bg": "#121216", "text": "#E2E8F0", "header": "#BB86FC", 
        "card_bg": "#1E1E24", "card_border": "#2D2D38", "default_main": "#BB86FC",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
        "font_family": "'Gowun Dodum', sans-serif",
        "radius": "12px", "shadow": "0 4px 16px rgba(0,0,0,0.4)"
    },
    "👾 레트로": {
        "title": "📟 Y2K 감성 다이어리 👾",
        "bg": "#E0F7FA", "text": "#004D40", "header": "#00838F", 
        "card_bg": "#FFFFFF", "card_border": "#80DEEA", "default_main": "#00ACC1",
        "font_import": "https://fonts.googleapis.com/css2?family=DungGeunMo&display=swap",
        "font_family": "'DungGeunMo', monospace",
        "radius": "0px", "shadow": "4px 4px 0px #004D40"
    },
    "🌊 바다": {
        "title": "🌊 푸른 바다 속 이야기 🐬",
        "bg": "#EBF4F6", "text": "#1E3E62", "header": "#0B2F9F", 
        "card_bg": "#FFFFFF", "card_border": "#B0C4DE", "default_main": "#0284C7",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
        "font_family": "'Gowun Dodum', sans-serif",
        "radius": "18px", "shadow": "0 8px 16px rgba(2,132,199,0.12)"
    },
    "🌲 숲": {
        "title": "🍃 울창한 숲속 비밀노트 🌲",
        "bg": "#F1F8F5", "text": "#1C352D", "header": "#2D5A27", 
        "card_bg": "#FFFFFF", "card_border": "#C2E0D2", "default_main": "#15803D",
        "font_import": "https://fonts.googleapis.com/css2?family=Gowun+Batang&display=swap",
        "font_family": "'Gowun Batang', serif",
        "radius": "14px", "shadow": "0 4px 12px rgba(21,128,61,0.08)"
    },
    "🔮 몽환": {
        "title": "🔮 달빛 아래 몽환 다이어리 🌙",
        "bg": "#F5EFFF", "text": "#3C2A4D", "header": "#6B21A8", 
        "card_bg": "#FFFFFF", "card_border": "#E9D5FF", "default_main": "#9333EA",
        "font_import": "https://fonts.googleapis.com/css2?family=Gamja+Flower&display=swap",
        "font_family": "'Gamja Flower', cursive",
        "radius": "22px", "shadow": "0 8px 24px rgba(147,51,234,0.15)"
    }
}

# 세션 상태 초기화
if "user" not in st.session_state:
    st.session_state.user = None
if "nickname" not in st.session_state:
    st.session_state.nickname = None
if "birthdate" not in st.session_state:
    st.session_state.birthdate = None
if "theme" not in st.session_state:
    st.session_state.theme = "포근함"
if "main_color" not in st.session_state:
    st.session_state.main_color = "#DDA15E"

current_theme_key = st.session_state.theme if st.session_state.theme in THEME_STYLES else "포근함"
theme_cfg = THEME_STYLES[current_theme_key]
main_color = st.session_state.main_color if st.session_state.main_color else theme_cfg["default_main"]
app_title = theme_cfg["title"]

# 동적 CSS 주입
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
    }}
    
    .stTextArea textarea, .stTextInput input, div[data-testid="stForm"] {{
        background-color: {theme_cfg['card_bg']} !important;
        border: 1px solid {theme_cfg['card_border']} !important;
        border-radius: {theme_cfg['radius']} !important;
        color: {theme_cfg['text']} !important;
        box-shadow: {theme_cfg['shadow']} !important;
        font-family: {theme_cfg['font_family']} !important;
    }}
    
    div.stButton > button {{
        background-color: {main_color} !important;
        color: white !important;
        border-radius: {theme_cfg['radius']} !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: bold !important;
        box-shadow: {theme_cfg['shadow']} !important;
        font-family: {theme_cfg['font_family']} !important;
        transition: all 0.2s ease-in-out;
    }}
    
    div.stButton > button:hover {{
        opacity: 0.88;
        transform: translateY(-2px);
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: {theme_cfg['card_bg']} !important;
        border-right: 1px solid {theme_cfg['card_border']} !important;
    }}
    </style>
""", unsafe_allow_html=True)

today_dt = datetime.date.today()
today_str = today_dt.strftime("%Y-%m-%d")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str
if "page" not in st.session_state:
    st.session_state.page = "secret_calendar"
if "editor_is_public" not in st.session_state:
    st.session_state.editor_is_public = False

STANDARD_EMOTIONS = ["😊 기쁨", "😌 평온", "😢 슬픔", "😡 화남", "😴 피곤"]
EMOJI_LIST = [e.split()[0] for e in STANDARD_EMOTIONS]


# =========================================================
# 3. 로그인 / 회원가입 화면
# =========================================================
if st.session_state.user is None:
    st.title(app_title)
    
    auth_mode = st.radio("서비스 이용을 위해 로그인해 주세요.", ["로그인", "회원가입"], horizontal=True)
    
    username_input = st.text_input("아이디", key="auth_user")
    password_input = st.text_input("비밀번호", type="password", key="auth_pw")

    if auth_mode == "로그인":
        if st.button("로그인하기", use_container_width=True):
            if username_input and password_input:
                is_success, nickname, birthdate, theme, m_color = login_user(username_input, password_input)
                if is_success:
                    st.session_state.user = username_input
                    st.session_state.nickname = nickname if nickname else username_input
                    st.session_state.birthdate = birthdate
                    st.session_state.theme = theme
                    st.session_state.main_color = m_color
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
    
    # 생일 축하 로직
    if user_birthdate and len(user_birthdate) == 10:
        if user_birthdate[5:] == today_str[5:]:
            st.balloons()
            st.toast(f"🎂 {current_nickname}님, 생일을 진심으로 축하합니다! 🎉", icon="🎁")

    # 사이드바 프로필 및 회원 정보/테마 수정
    st.sidebar.title(app_title.split()[0] + " 일기장")
    st.sidebar.write(f"👤 **{current_nickname}** 님")
    st.sidebar.caption(f"🎨 테마: {st.session_state.theme}")
    
    # 내 정보 & 테마 설정
    with st.sidebar.expander("✏️ 내 정보 & 테마 수정"):
        edit_nick = st.text_input("닉네임", value=current_nickname, key="edit_nick_input")
        
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

        st.markdown("---")
        st.markdown("##### 🎨 테마 분위기 변경 (10종)")
        theme_options = list(THEME_STYLES.keys())
        current_theme_idx = theme_options.index(st.session_state.theme) if st.session_state.theme in theme_options else 0
        
        selected_theme = st.selectbox(
            "테마 분위기",
            theme_options,
            index=current_theme_idx
        )
        
        suggested_color = THEME_STYLES[selected_theme]["default_main"] if selected_theme != st.session_state.theme else main_color
        selected_color = st.color_picker("포인트 메인 컬러", value=suggested_color)

        if st.button("설정 저장하기", use_container_width=True):
            cleaned_nick = edit_nick.strip()
            if cleaned_nick:
                update_user_profile(current_user, cleaned_nick, new_bday_str, selected_theme, selected_color)

import sqlite3
import datetime
import bcrypt
import streamlit as st
from streamlit_calendar import calendar

# =========================================================
# 1. DB 연동 및 테이블 생성 함수
# =========================================================
DB_FILE = "diary_app.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # 사용자 테이블 (아이디, 암호화된 비밀번호)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    
    # 일기 테이블 (사용자ID, 날짜, 감정, 내용)
    c.execute('''
        CREATE TABLE IF NOT EXISTS diaries (
            username TEXT,
            date TEXT,
            emotion TEXT,
            content TEXT,
            PRIMARY KEY (username, date),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    conn.commit()
    conn.close()

# DB 초기화 실행
init_db()

# DB 헬퍼 함수들
def register_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # 이미 존재하는 아이디
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        stored_pw = row[0]
        return bcrypt.checkpw(password.encode('utf-8'), stored_pw.encode('utf-8'))
    return False

def get_user_diaries(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, emotion, content FROM diaries WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    
    diaries = {}
    for r in rows:
        diaries[r[0]] = {"emotion": r[1], "content": r[2]}
    return diaries

def save_diary(username, date_str, emotion, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO diaries (username, date, emotion, content)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            emotion=excluded.emotion,
            content=excluded.content
    ''', (username, date_str, emotion, content))
    conn.commit()
    conn.close()

def delete_diary(username, date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM diaries WHERE username = ? AND date = ?", (username, date_str))
    conn.commit()
    conn.close()


# =========================================================
# 2. UI 및 테마 설정
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "user" not in st.session_state:
    st.session_state.user = None

today_str = datetime.date.today().strftime("%Y-%m-%d")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str

if "page" not in st.session_state:
    st.session_state.page = "calendar"

STANDARD_EMOTIONS = ["😊 기쁨", "😌 평온", "😢 슬픔", "😡 화남", "😴 피곤"]
EMOJI_LIST = [e.split()[0] for e in STANDARD_EMOTIONS]


# =========================================================
# 3. 로그인 / 회원가입 화면 (로그인 안 되어 있을 때)
# =========================================================
if st.session_state.user is None:
    st.title("🧸 소소하고 포근한 일기장")
    
    auth_mode = st.radio("서비스 이용을 위해 로그인해 주세요.", ["로그인", "회원가입"], horizontal=True)
    
    username_input = st.text_input("아이디", key="auth_user")
    password_input = st.text_input("비밀번호", type="password", key="auth_pw")

    if auth_mode == "로그인":
        if st.button("로그인하기", use_container_width=True):
            if username_input and password_input:
                if login_user(username_input, password_input):
                    st.session_state.user = username_input
                    st.success(f"{username_input}님 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해 주세요.")
                
    else:  # 회원가입
        if st.button("회원가입하기", use_container_width=True):
            if username_input and password_input:
                if register_user(username_input, password_input):
                    st.success("회원가입이 완료되었습니다! 로그인 탭에서 로그인해 주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해 주세요.")

# =========================================================
# 4. 메인 일기장 화면 (로그인 완료 시)
# =========================================================
else:
    current_user = st.session_state.user
    
    # 사이드바 (사용자 정보 및 로그아웃)
    st.sidebar.title("🧸 소소한 일기장")
    st.sidebar.write(f"👤 **{current_user}** 님")
    
    if st.sidebar.button("🔒 로그아웃"):
        st.session_state.user = None
        st.session_state.page = "calendar"
        st.rerun()

    st.sidebar.markdown("---")
    
    nav_choice = st.sidebar.radio(
        "메뉴 선택",
        ["🗓️ 달력 보기", "✏️ 일기 작성 / 수정 / 조회"],
        index=0 if st.session_state.page == "calendar" else 1
    )

    if nav_choice == "🗓️ 달력 보기" and st.session_state.page != "calendar":
        st.session_state.page = "calendar"
        st.rerun()
    elif nav_choice == "✏️ 일기 작성 / 수정 / 조회" and st.session_state.page != "diary":
        st.session_state.page = "diary"
        st.rerun()

    st.title("🧸 소소하고 포근한 일기장")

    # DB에서 현재 사용자의 일기 데이터 로드
    user_diaries = get_user_diaries(current_user)

    # ---------------------------------------------------------
    # PAGE 1: 달력 페이지
    # ---------------------------------------------------------
    if st.session_state.page == "calendar":
        st.subheader("🗓️ 달력에서 날짜를 선택하세요")
        st.caption("날짜를 클릭하면 해당 날짜의 일기 작성/수정 페이지로 이동합니다.")

        calendar_events = []
        for date_str, diary_data in user_diaries.items():
            if diary_data.get("content") and diary_data["content"].strip():
                calendar_events.append({
                    "title": f"{diary_data['emotion']} 일기",
                    "start": date_str,
                    "end": date_str,
                    "allDay": True,
                    "color": "#DDA15E"
                })

        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth"
            },
            "initialView": "dayGridMonth",
            "selectable": True,
        }

        cal_res = calendar(events=calendar_events, options=calendar_options, key="cozy_diary_calendar")

        clicked_date = None
        if cal_res and "dateClick" in cal_res:
            clicked_date = cal_res["dateClick"]["date"].split("T")[0]
        elif cal_res and "select" in cal_res:
            clicked_date = cal_res["select"]["start"].split("T")[0]

        if clicked_date:
            st.session_state.selected_date = clicked_date
            st.session_state.page = "diary"
            st.rerun()

    # ---------------------------------------------------------
    # PAGE 2: 일기 작성 및 수정 / 조회 페이지
    # ---------------------------------------------------------
    else:
        selected_date = st.session_state.selected_date
        is_today = (selected_date == today_str)

        if is_today:
            st.header(f"✏️ 오늘의 일기 ({selected_date})")
        else:
            st.header(f"📖 {selected_date}의 일기")

        has_existing = (
            selected_date in user_diaries and 
            bool(user_diaries[selected_date].get("content", "").strip())
        )
        
        existing_data = user_diaries.get(selected_date, {})
        saved_emotion = existing_data.get("emotion", "😊")
        saved_content = existing_data.get("content", "")

        default_emotion_index = 0
        if saved_emotion in EMOJI_LIST:
            default_emotion_index = EMOJI_LIST.index(saved_emotion)

        selected_emotion_label = st.radio(
            "오늘의 감정을 선택해 주세요:" if is_today else "이날의 감정을 선택해 주세요:",
            options=STANDARD_EMOTIONS,
            index=default_emotion_index,
            horizontal=True,
            key=f"emotion_radio_{selected_date}"
        )
        selected_emoji = selected_emotion_label.split()[0]

        diary_text = st.text_area(
            "내용을 작성하거나 수정해 주세요:",
            value=saved_content,
            height=200,
            placeholder="소소한 이야기라도 좋아요. 자유롭게 적어보세요...",
            key=f"text_area_{selected_date}"
        )

        col1, col2, col3 = st.columns([2, 2, 1])
        button_label = "💾 수정사항 저장하기" if has_existing else "🧸 마음 저장하기"
        
        # 1. 저장 버튼 (DB 저장)
        with col1:
            if st.button(button_label, use_container_width=True):
                if diary_text.strip():
                    save_diary(current_user, selected_date, selected_emoji, diary_text.strip())
                    st.success("일기가 성공적으로 DB에 저장되었습니다!")
                    st.rerun()
                else:
                    st.warning("내용을 입력해 주세요.")

        # 2. 달력으로 돌아가기 버튼
        with col2:
            if st.button("🗓️ 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "calendar"
                st.rerun()

        # 3. 삭제 버튼 (DB 삭제)
        with col3:
            if has_existing:
                if st.button("🗑️ 삭제", use_container_width=True):
                    delete_diary(current_user, selected_date)
                    st.success("일기가 삭제되었습니다.")
                    st.rerun()

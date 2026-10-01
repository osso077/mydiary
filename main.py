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
    """앱 시작 시 깃허브 저장소에서 최신 DB 파일을 다운로드하여 복원"""
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            file_content = repo.get_contents(DB_FILE)
            with open(DB_FILE, "wb") as f:
                f.write(file_content.decoded_content)
        except GithubException:
            pass
        except Exception as e:
            pass

def push_db_to_github(commit_message="Update database"):
    """데이터 변경 시 깃허브 저장소로 DB 파일 자동 업로드"""
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
            st.warning(f"깃허브 백업 중 오류 발생: {e}")

# 앱 시작 시 깃허브에서 DB 다운로드
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
            birthdate TEXT DEFAULT ''
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
    
    # 기존 사용자를 위한 DB 컬럼 마이그레이션
    try:
        c.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE users ADD COLUMN birthdate TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE diaries ADD COLUMN is_public INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

# DB 헬퍼 함수들
def register_user(username, password, nickname, birthdate=""):
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute("INSERT INTO users (username, password, nickname, birthdate) VALUES (?, ?, ?, ?)", 
                  (username, hashed_pw, nickname, birthdate))
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
    c.execute("SELECT password, nickname, birthdate FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        stored_pw, nickname, birthdate = row[0], row[1], row[2]
        if bcrypt.checkpw(password.encode('utf-8'), stored_pw.encode('utf-8')):
            return True, nickname, birthdate
    return False, None, None

def update_nickname(username, new_nickname):
    """사용자의 닉네임을 변경하는 함수"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET nickname = ? WHERE username = ?", (new_nickname, username))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update nickname for user {username}")

def get_user_diaries(username, is_public_flag):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, emotion, content FROM diaries WHERE username = ? AND is_public = ?", 
              (username, 1 if is_public_flag else 0))
    rows = c.fetchall()
    conn.close()
    
    diaries = {}
    for r in rows:
        diaries[r[0]] = {
            "emotion": r[1],
            "content": r[2]
        }
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
            "date": r[0],
            "emotion": r[1],
            "content": r[2],
            "nickname": r[3],
            "username": r[4]
        })
    return public_list

def save_diary(username, date_str, emotion, content, is_public):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO diaries (username, date, emotion, content, is_public)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username, date) DO UPDATE SET
            emotion=excluded.emotion,
            content=excluded.content,
            is_public=excluded.is_public
    ''', (username, date_str, emotion, content, 1 if is_public else 0))
    conn.commit()
    conn.close()
    push_db_to_github(f"Update diary entry for {date_str}")

def delete_diary(username, date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM diaries WHERE username = ? AND date = ?", (username, date_str))
    conn.commit()
    conn.close()
    push_db_to_github(f"Delete diary entry for {date_str}")


# =========================================================
# 2. UI 및 테마 설정
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "user" not in st.session_state:
    st.session_state.user = None
if "nickname" not in st.session_state:
    st.session_state.nickname = None
if "birthdate" not in st.session_state:
    st.session_state.birthdate = None

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
    st.title("🧸 소소하고 포근한 일기장")
    
    auth_mode = st.radio("서비스 이용을 위해 로그인해 주세요.", ["로그인", "회원가입"], horizontal=True)
    
    username_input = st.text_input("아이디", key="auth_user")
    password_input = st.text_input("비밀번호", type="password", key="auth_pw")

    if auth_mode == "로그인":
        if st.button("로그인하기", use_container_width=True):
            if username_input and password_input:
                is_success, nickname, birthdate = login_user(username_input, password_input)
                if is_success:
                    st.session_state.user = username_input
                    st.session_state.nickname = nickname if nickname else username_input
                    st.session_state.birthdate = birthdate
                    st.success(f"{st.session_state.nickname}님 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해 주세요.")
                
    else:  # 회원가입
        nickname_input = st.text_input("닉네임 (프로필 이름)", key="auth_nick")
        
        # 생일 입력 (선택사항)
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
    
    # 생일 축하 로직 (월-일 비교)
    if user_birthdate and len(user_birthdate) == 10:
        birth_month_day = user_birthdate[5:]  # "MM-DD"
        today_month_day = today_str[5:]      # "MM-DD"
        
        if birth_month_day == today_month_day:
            st.balloons()
            st.toast(f"🎂 {current_nickname}님, 생일을 진심으로 축하합니다! 🎉", icon="🎁")
            st.info(f"🎉 **오늘은 {current_nickname}님의 생일입니다!** 행복하고 따뜻한 하루 보내세요 🎂✨")

    # 사이드바 프로필 및 닉네임 수정
    st.sidebar.title("🧸 소소한 일기장")
    st.sidebar.write(f"👤 **{current_nickname}** 님")
    if user_birthdate:
        st.sidebar.caption(f"🎂 생일: {user_birthdate}")
    
    # 닉네임 수정 접이식 메뉴 (Expander)
    with st.sidebar.expander("✏️ 닉네임 변경하기"):
        new_nickname_input = st.text_input("새 닉네임", value=current_nickname, key="edit_nickname_input")
        if st.button("닉네임 저장", use_container_width=True):
            cleaned_nick = new_nickname_input.strip()
            if cleaned_nick and cleaned_nick != current_nickname:
                update_nickname(current_user, cleaned_nick)
                st.session_state.nickname = cleaned_nick
                st.success("닉네임이 변경되었습니다!")
                st.rerun()
            elif cleaned_nick == current_nickname:
                st.info("기존 닉네임과 동일합니다.")
            else:
                st.warning("닉네임을 입력해 주세요.")

    if st.sidebar.button("🔒 로그아웃"):
        st.session_state.user = None
        st.session_state.nickname = None
        st.session_state.birthdate = None
        st.session_state.page = "secret_calendar"
        st.rerun()

    st.sidebar.markdown("---")
    
    nav_index = 0 if st.session_state.page in ["secret_calendar", "diary_editor"] and not st.session_state.editor_is_public else 1
    
    nav_choice = st.sidebar.radio(
        "메뉴 선택",
        ["🔒 비밀일기", "🌐 공개일기"],
        index=nav_index
    )

    if nav_choice == "🔒 비밀일기" and (st.session_state.page != "secret_calendar" and (st.session_state.page == "diary_editor" and st.session_state.editor_is_public)):
        st.session_state.page = "secret_calendar"
        st.session_state.editor_is_public = False
        st.rerun()
    elif nav_choice == "🌐 공개일기" and (st.session_state.page != "public_calendar" and (st.session_state.page == "diary_editor" and not st.session_state.editor_is_public)):
        st.session_state.page = "public_calendar"
        st.session_state.editor_is_public = True
        st.rerun()

    st.title("🧸 소소하고 포근한 일기장")

    # PAGE 1: 🔒 비밀일기 페이지
    if st.session_state.page == "secret_calendar":
        st.header("🔒 나만의 비밀일기")
        st.caption("이곳의 일기는 오직 나에게만 보여집니다. 달력에서 날짜를 클릭하면 일기를 쓰고 수정할 수 있습니다.")

        secret_diaries = get_user_diaries(current_user, is_public_flag=False)

        calendar_events = []
        for date_str, diary_data in secret_diaries.items():
            if diary_data.get("content") and diary_data["content"].strip():
                calendar_events.append({
                    "title": f"🔒 {diary_data['emotion']} 비밀일기",
                    "start": date_str,
                    "end": date_str,
                    "allDay": True,
                    "color": "#6C5B52"
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

        cal_res = calendar(events=calendar_events, options=calendar_options, key="secret_diary_calendar")

        clicked_date = None
        if cal_res and "dateClick" in cal_res:
            clicked_date = cal_res["dateClick"]["date"].split("T")[0]
        elif cal_res and "select" in cal_res:
            clicked_date = cal_res["select"]["start"].split("T")[0]

        if clicked_date:
            st.session_state.selected_date = clicked_date
            st.session_state.editor_is_public = False
            st.session_state.page = "diary_editor"
            st.rerun()

    # PAGE 2: 🌐 공개일기 페이지
    elif st.session_state.page == "public_calendar":
        st.header("🌐 공유하는 공개일기")
        st.caption("내가 공개로 설정한 일기들과 다른 사람들의 공개 일기를 만날 수 있는 공간입니다.")

        public_tab1, public_tab2 = st.tabs(["🗓️ 내 공개일기 달력", "📖 모두의 이야기 모아보기"])

        with public_tab1:
            st.subheader("내 공개일기 달력")
            st.caption("날짜를 선택해 공개 일기를 작성하거나 수정해 보세요.")
            
            my_public_diaries = get_user_diaries(current_user, is_public_flag=True)

            calendar_events = []
            for date_str, diary_data in my_public_diaries.items():
                if diary_data.get("content") and diary_data["content"].strip():
                    calendar_events.append({
                        "title": f"🌐 {diary_data['emotion']} 공개일기",
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

            cal_res_pub = calendar(events=calendar_events, options=calendar_options, key="public_diary_calendar")

            clicked_date_pub = None
            if cal_res_pub and "dateClick" in cal_res_pub:
                clicked_date_pub = cal_res_pub["dateClick"]["date"].split("T")[0]
            elif cal_res_pub and "select" in cal_res_pub:
                clicked_date_pub = cal_res_pub["select"]["start"].split("T")[0]

            if clicked_date_pub:
                st.session_state.selected_date = clicked_date_pub
                st.session_state.editor_is_public = True
                st.session_state.page = "diary_editor"
                st.rerun()

        with public_tab2:
            st.subheader("모두가 남긴 공개 일기")
            all_publics = get_all_public_diaries()
            if all_publics:
                for item in all_publics:
                    with st.container():
                        st.markdown(f"#### {item['emotion']} **{item['nickname']}** 님의 이야기")
                        st.caption(f"날짜: {item['date']}")
                        st.info(item['content'])
                        st.markdown("---")
            else:
                st.write("🌿 아직 등록된 공개 일기가 없어요.")

    # PAGE 3: 일기 작성 / 수정 페이지
    elif st.session_state.page == "diary_editor":
        selected_date = st.session_state.selected_date
        is_public_mode = st.session_state.editor_is_public
        mode_icon = "🌐 공개일기" if is_public_mode else "🔒 비밀일기"

        st.header(f"✏️ {mode_icon} 작성/수정 ({selected_date})")

        user_diaries = get_user_diaries(current_user, is_public_flag=is_public_mode)
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
            "이날의 감정을 선택해 주세요:",
            options=STANDARD_EMOTIONS,
            index=default_emotion_index,
            horizontal=True,
            key=f"editor_emotion_{selected_date}_{is_public_mode}"
        )
        selected_emoji = selected_emotion_label.split()[0]

        diary_text = st.text_area(
            "내용을 작성하거나 수정해 주세요:",
            value=saved_content,
            height=200,
            placeholder="소소한 이야기라도 좋아요. 자유롭게 적어보세요...",
            key=f"editor_text_{selected_date}_{is_public_mode}"
        )

        col1, col2, col3 = st.columns([2, 2, 1])
        button_label = "💾 수정사항 저장하기" if has_existing else "🧸 마음 저장하기"
        
        with col1:
            if st.button(button_label, use_container_width=True):
                if diary_text.strip():
                    save_diary(current_user, selected_date, selected_emoji, diary_text.strip(), is_public_mode)
                    st.success("일기가 성공적으로 저장되었습니다!")
                    st.session_state.page = "public_calendar" if is_public_mode else "secret_calendar"
                    st.rerun()
                else:
                    st.warning("내용을 입력해 주세요.")

        with col2:
            if st.button("🗓️ 달력으로 돌아가기", use_container_width=True):
                st.session_state.page = "public_calendar" if is_public_mode else "secret_calendar"
                st.rerun()

        with col3:
            if has_existing:
                if st.button("🗑️ 삭제", use_container_width=True):
                    delete_diary(current_user, selected_date)
                    st.success("일기가 삭제되었습니다.")
                    st.session_state.page = "public_calendar" if is_public_mode else "secret_calendar"
                    st.rerun()

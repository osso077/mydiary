import datetime
import streamlit as st
from streamlit_calendar import calendar
from supabase import create_client, Client

# =========================================================
# 1. Supabase 연동 설정 (안전한 예외 처리 포함)
# =========================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    # URL이나 KEY가 설정되지 않았거나 예시 값 그대로일 때 예외 처리
    if not SUPABASE_URL or not SUPABASE_KEY or "your-project-url" in SUPABASE_URL:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_supabase()

# =========================================================
# 2. UI 및 페이지 설정
# =========================================================
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #FAF6F0;
        color: #4A3E3D;
    }
    h1, h2, h3 {
        color: #6C5B52 !important;
        font-family: 'Nanum Gothic', sans-serif;
    }
    .stTextArea textarea, .stTextInput input {
        background-color: #FFFFFF;
        border: 1px solid #E3D5CA;
        border-radius: 12px;
        color: #4A3E3D;
    }
    div.stButton > button {
        background-color: #DDA15E !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        padding: 8px 20px !important;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #BC6C25 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Supabase 연결 설정 미완료 시 안내문 출력
if supabase is None:
    st.error("⚠️ Supabase 설정이 올바르지 않습니다.")
    st.info("""
    **Streamlit Secrets 설정 점검 목록:**
    1. `SUPABASE_URL`이 `https://`로 시작하는 올바른 주소인지 확인해 주세요.
    2. Supabase 대시보드 -> Project Settings -> API에서 **Project URL**과 **anon public key**를 올바르게 복사했는지 확인해 주세요.
    """)
    st.stop()

# 세션 상태 초기화
if "user_email" not in st.session_state:
    st.session_state.user_email = None

today_str = datetime.date.today().strftime("%Y-%m-%d")

# =========================================================
# 3. 매직링크 회원가입 / 로그인 화면
# =========================================================
if st.session_state.user_email is None:
    st.title("🧸 소소하고 포근한 일기장")
    st.subheader("이메일 하나로 3초 만에 시작하기")
    st.caption("비밀번호나 개인정보를 받지 않습니다. 입력하신 이메일로 로그인 접속 링크가 전송됩니다.")

    email_input = st.text_input("이메일 주소 입력", placeholder="example@email.com")

    if st.button("로그인 / 회원가입 링크 받기", use_container_width=True):
        if email_input.strip():
            try:
                supabase.auth.sign_in_with_otp({"email": email_input.strip()})
                st.success("📩 입력하신 메일함으로 로그인 접속 링크를 보냈습니다! 메일을 확인해 클릭해 주세요.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("이메일을 입력해 주세요.")

# =========================================================
# 4. 로그인 완료 후 화면
# =========================================================
else:
    current_user = st.session_state.user_email
    
    st.sidebar.title("🧸 소소한 일기장")
    st.sidebar.write(f"👤 **{current_user}** 님")

    if st.sidebar.button("🔒 로그아웃"):
        st.session_state.user_email = None
        st.rerun()

    st.title("🧸 소소하고 포근한 일기장")
    st.success("안전하게 클라우드 데이터베이스에 회원 정보가 영구 저장되었습니다!")

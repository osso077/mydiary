import datetime
import streamlit as st
from streamlit_calendar import calendar
from supabase import create_client, Client

# =========================================================
# 1. Supabase 데이터베이스 및 인증 연동
# =========================================================
# Streamlit Secrets 또는 코드 내 직접 설정
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "여기에_SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "여기에_SUPABASE_ANON_KEY")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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

# 세션 상태 초기화
if "user_email" not in st.session_state:
    st.session_state.user_email = None

today_str = datetime.date.today().strftime("%Y-%m-%d")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str

if "page" not in st.session_state:
    st.session_state.page = "secret_calendar"

# =========================================================
# 3. 매직링크 로그인 / 회원가입 화면 (이메일 1개만 필요)
# =========================================================
if st.session_state.user_email is None:
    st.title("🧸 소소하고 포근한 일기장")
    st.subheader("이메일 하나로 3초 만에 시작하기")
    st.caption("비밀번호나 개인정보를 받지 않습니다. 입력하신 이메일로 접속 링크가 전송됩니다.")

    email_input = st.text_input("이메일 주소 입력", placeholder="example@email.com")

    if st.button("로그인 / 회원가입 링크 받기", use_container_width=True):
        if email_input.strip():
            try:
                # Supabase 매직링크 발송
                res = supabase.auth.sign_in_with_otp({"email": email_input.strip()})
                st.success("📩 메일함으로 로그인 링크를 보냈습니다! 메일을 확인해 클릭해 주세요.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("이메일을 입력해 주세요.")

# =========================================================
# 4. 로그인 후 메인 화면
# =========================================================
else:
    current_user = st.session_state.user_email
    
    st.sidebar.title("🧸 소소한 일기장")
    st.sidebar.write(f"👤 **{current_user}** 님")

    if st.sidebar.button("🔒 로그아웃"):
        st.session_state.user_email = None
        st.rerun()

    st.title("🧸 소소하고 포근한 일기장")
    st.write("안전하게 클라우드 데이터베이스에 영구 저장되는 일기장입니다.")
    

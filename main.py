달력에서 날짜를 클릭하면 자동으로 일기 작성/조회 페이지로 넘어가도록 개선하고, 이미 작성된 과거 일기는 삭제하지 않고 바로 내용을 수정 및 업데이트할 수 있도록 구현한 코드입니다.

Streamlit의 탭 구조는 클릭에 반응해 자동 전환되는 로직 구현 시 약간의 한계가 있어, 사이드바 메뉴 방식을 채택하여 더욱 직관적이고 자동 전환이 깔끔하게 동작하도록 제작했습니다.

📄 수정된 전체 코드 (app.py / main.py)
Python
import datetime
import streamlit as st
from streamlit_calendar import calendar

# 1. 페이지 설정 및 포근한 테마 CSS
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

# 2. 세션 상태 초기화
if "diaries" not in st.session_state:
    st.session_state.diaries = {}

today_str = datetime.date.today().strftime("%Y-%m-%d")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str

# 페이지 상태 관리 ('calendar' 또는 'diary')
if "page" not in st.session_state:
    st.session_state.page = "calendar"

# 표준 감정 목록 (인덱스 탐색용)
STANDARD_EMOTIONS = ["😊 기쁨", "😌 평온", "😢 슬픔", "😡 화남", "😴 피곤"]
EMOJI_LIST = [e.split()[0] for e in STANDARD_EMOTIONS]

# 3. 사이드바 메뉴 (상태에 따라 자동 연동)
st.sidebar.title("🧸 소소한 일기장")
nav_choice = st.sidebar.radio(
    "메뉴 선택",
    ["🗓️ 달력 보기", "✏️ 일기 작성 / 수정 / 조회"],
    index=0 if st.session_state.page == "calendar" else 1
)

# 사이드바 버튼 클릭 시 페이지 세션 업데이트
if nav_choice == "🗓️ 달력 보기" and st.session_state.page != "calendar":
    st.session_state.page = "calendar"
    st.rerun()
elif nav_choice == "✏️ 일기 작성 / 수정 / 조회" and st.session_state.page != "diary":
    st.session_state.page = "diary"
    st.rerun()

st.title("🧸 소소하고 포근한 일기장")

# =========================================================
# PAGE 1: 달력 페이지 (날짜 클릭 시 자동으로 일기 페이지로 전환)
# =========================================================
if st.session_state.page == "calendar":
    st.subheader("🗓️ 달력에서 날짜를 선택하세요")
    st.caption("날짜를 클릭하면 해당 날짜의 일기 작성/수정 페이지로 이동합니다.")

    # 달력 이벤트 등록 (작성된 일기가 있는 날짜만)
    calendar_events = []
    for date_str, diary_data in st.session_state.diaries.items():
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

    # 날짜 클릭 시 선택 날짜 업데이트 후 '일기 페이지'로 자동 화면 전환
    clicked_date = None
    if cal_res and "dateClick" in cal_res:
        clicked_date = cal_res["dateClick"]["date"].split("T")[0]
    elif cal_res and "select" in cal_res:
        clicked_date = cal_res["select"]["start"].split("T")[0]

    if clicked_date:
        st.session_state.selected_date = clicked_date
        st.session_state.page = "diary"  # 일기 페이지로 자동 넘어가기
        st.rerun()

# =========================================================
# PAGE 2: 일기 작성 및 수정 / 조회 페이지
# =========================================================
else:
    selected_date = st.session_state.selected_date
    is_today = (selected_date == today_str)

    # 헤더 문구 설정
    if is_today:
        st.header(f"✏️ 오늘의 일기 ({selected_date})")
    else:
        st.header(f"📖 {selected_date}의 일기")

    # 기존 저장된 일기 데이터 가져오기
    has_existing = (
        selected_date in st.session_state.diaries and 
        bool(st.session_state.diaries[selected_date].get("content", "").strip())
    )
    
    existing_data = st.session_state.diaries.get(selected_date, {})
    saved_emotion = existing_data.get("emotion", "😊")
    saved_content = existing_data.get("content", "")

    # 기존 저장된 감정 선택 위치 세팅
    default_emotion_index = 0
    if saved_emotion in EMOJI_LIST:
        default_emotion_index = EMOJI_LIST.index(saved_emotion)

    # 감정 선택 및 일기 작성/수정 Form
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

    col1, col2 = st.columns([1, 4])
    
    # 버튼 문구 (신규 작성 vs 기존 수정)
    button_label = "💾 수정사항 저장하기" if has_existing else "🧸 마음 저장하기"
    
    with col1:
        if st.button(button_label):
            if diary_text.strip():
                st.session_state.diaries[selected_date] = {
                    "emotion": selected_emoji,
                    "content": diary_text.strip()
                }
                st.success("일기가 성공적으로 저장되었습니다!")
                st.rerun()
            else:
                st.warning("내용을 입력해 주세요.")
                
    with col2:
        if has_existing:
            if st.button("🗑️ 일기 삭제"):
                del st.session_state.diaries[selected_date]
                st.success("일기가 삭제되었습니다.")
                st.rerun()

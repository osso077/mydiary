import datetime
import streamlit as st
from streamlit_calendar import calendar

# 1. 페이지 설정 및 포근한 테마 CSS
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

# 2. 세션 상태 초기화 (데이터 저장소 및 선택 날짜)
if "diaries" not in st.session_state:
    st.session_state.diaries = {}

today_str = datetime.date.today().strftime("%Y-%m-%d")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str

st.title("🧸 소소하고 포근한 일기장")
st.caption("오늘 하루의 마음을 이모티콘과 함께 기록해 보세요.")

# 3. 달력 이벤트 생성 (실제 작성된 일기가 있는 날짜만 등록)
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

# 표준 감정 5개
STANDARD_EMOTIONS = ["😊 기쁨", "😌 평온", "😢 슬픔", "😡 화남", "😴 피곤"]

# 4. 화면 구분 (탭 사용)
tab1, tab2 = st.tabs(["🗓️ 달력 보기", "✏️ 일기 작성 / 조회"])

# =========================================================
# TAB 1: 달력 페이지
# =========================================================
with tab1:
    st.subheader("달력")
    st.write("날짜를 클릭하면 해당 날짜가 선택됩니다.")

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

    # 클릭된 날짜를 세션 상태에 저장
    if cal_res and "dateClick" in cal_res:
        st.session_state.selected_date = cal_res["dateClick"]["date"].split("T")[0]
    elif cal_res and "select" in cal_res:
        st.session_state.selected_date = cal_res["select"]["start"].split("T")[0]

    st.info(f"현재 선택된 날짜: **{st.session_state.selected_date}** (일기를 쓰거나 보려면 상단의 '✏️ 일기 작성 / 조회' 탭을 눌러주세요)")

# =========================================================
# TAB 2: 일기 작성 및 조회 페이지
# =========================================================
with tab2:
    selected_date = st.session_state.selected_date

    # 1) 오늘 날짜인 경우 -> 일기 작성
    if selected_date == today_str:
        st.header(f"✏️ 오늘의 일기 쓰기 ({today_str})")
        
        selected_emotion_label = st.radio(
            "오늘의 감정을 선택해 주세요:",
            options=STANDARD_EMOTIONS,
            horizontal=True,
            key="today_emotion_radio"
        )
        selected_emoji = selected_emotion_label.split()[0]

        existing_content = ""
        if today_str in st.session_state.diaries:
            existing_content = st.session_state.diaries[today_str].get("content", "")

        diary_text = st.text_area(
            "오늘 어떤 일이 있었나요?",
            value=existing_content,
            height=200,
            placeholder="소소한 이야기라도 좋아요. 자유롭게 적어보세요..."
        )

        if st.button("🧸 마음 저장하기"):
            if diary_text.strip():
                st.session_state.diaries[today_str] = {
                    "emotion": selected_emoji,
                    "content": diary_text.strip()
                }
                st.success("오늘의 마음이 따뜻하게 저장되었습니다!")
                st.rerun()
            else:
                st.warning("내용을 입력해 주세요.")

    # 2) 선택한 날짜에 작성된 일기가 있는 경우 -> 조회 및 삭제
    elif selected_date in st.session_state.diaries and st.session_state.diaries[selected_date].get("content", "").strip():
        st.header(f"📖 {selected_date}의 기록")
        saved_diary = st.session_state.diaries[selected_date]
        
        st.markdown(f"### 당시의 감정: {saved_diary['emotion']}")
        st.info(saved_diary["content"])
        
        if st.button("🗑️ 일기 지우기"):
            del st.session_state.diaries[selected_date]
            st.success("일기가 삭제되었습니다.")
            st.rerun()

    # 3) 다른 날짜에 일기가 없는 경우 -> 작성 안내 및 과거 일기 기록
    else:
        st.header(f"📖 {selected_date}의 기록")
        st.write("🌿 이 날은 작성된 일기가 없어요. 지나간 날의 일기를 기록하고 싶다면 아래에서 작성할 수 있습니다.")
        
        past_emotion_label = st.radio(
            "이날의 감정:",
            options=STANDARD_EMOTIONS,
            horizontal=True,
            key="past_emotion_radio"
        )
        past_emoji = past_emotion_label.split()[0]
        
        past_diary_text = st.text_area(
            "지나간 날의 일기 적기:",
            height=180,
            placeholder="이날을 추억하며 일기를 적어보세요."
        )
        
        if st.button("지나간 일기 저장하기"):
            if past_diary_text.strip():
                st.session_state.diaries[selected_date] = {
                    "emotion": past_emoji,
                    "content": past_diary_text.strip()
                }
                st.success(f"{selected_date} 일기가 성공적으로 저장되었습니다!")
                st.rerun()
            else:
                st.warning("내용을 입력해 주세요.")

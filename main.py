import datetime
import streamlit as st
from streamlit_calendar import calendar

# 1. 페이지 설정 및 포근한 테마 CSS
st.set_page_config(page_title="소소한 일기장", page_icon="🧸", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

# 2. 세션 상태 초기화 (일기 데이터 저장소)
if "diaries" not in st.session_state:
    st.session_state.diaries = {}

st.title("🧸 소소하고 포근한 일기장")
st.caption("오늘 하루의 마음을 이모티콘과 함께 기록해 보세요.")

# 오늘 날짜 (YYYY-MM-DD)
today_str = datetime.date.today().strftime("%Y-%m-%d")

# 3. 달력 이벤트 생성 (실제 작성된 일기가 있는 날짜만 정확히 등록)
calendar_events = []
for date_str, diary_data in st.session_state.diaries.items():
    # 텍스트 내용이 비어있지 않고 실제 저장된 일기만 달력에 표시
    if diary_data.get("content") and diary_data["content"].strip():
        calendar_events.append({
            "title": f"{diary_data['emotion']} 일기",
            "start": date_str,
            "end": date_str,
            "allDay": True,
            "color": "#DDA15E"
        })

# 달력 세부 옵션
calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth"
    },
    "initialView": "dayGridMonth",
    "selectable": True,
}

st.subheader("🗓️ 달력")
cal_res = calendar(events=calendar_events, options=calendar_options, key="cozy_diary_calendar")

# 선택된 날짜 감지
selected_date = today_str
if cal_res and "dateClick" in cal_res:
    selected_date = cal_res["dateClick"]["date"].split("T")[0]
elif cal_res and "select" in cal_res:
    selected_date = cal_res["select"]["start"].split("T")[0]

st.markdown("---")

# 일반적인 5가지 기본 감정 목록
STANDARD_EMOTIONS = ["😊 기쁨", "😌 평온", "😢 슬픔", "😡 화남", "😴 피곤"]

# 4. 선택한 날짜에 따른 일기 작성/조회 화면
if selected_date == today_str:
    st.header(f"✏️ 오늘의 마음 적기 ({today_str})")
    
    selected_emotion_label = st.radio(
        "오늘의 감정을 선택해 주세요:",
        options=STANDARD_EMOTIONS,
        horizontal=True
    )
    selected_emoji = selected_emotion_label.split()[0]

    # 오늘 일기 불러오기 (이미 쓴 경우)
    existing_content = ""
    if today_str in st.session_state.diaries:
        existing_content = st.session_state.diaries[today_str].get("content", "")

    diary_text = st.text_area(
        "오늘 어떤 일이 있었나요?",
        value=existing_content,
        height=180,
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
            st.warning("내용을 조금이라도 입력해 주세요.")

else:
    st.header(f"📖 {selected_date}의 기록")

    # 해당 날짜에 작성된 일기가 존재하는지 검증
    has_diary = (
        selected_date in st.session_state.diaries and 
        bool(st.session_state.diaries[selected_date].get("content", "").strip())
    )

    if has_diary:
        saved_diary = st.session_state.diaries[selected_date]
        
        st.markdown(f"### 당시의 감정: {saved_diary['emotion']}")
        st.info(saved_diary["content"])
        
        if st.button("🗑️ 일기 지우기"):
            del st.session_state.diaries[selected_date]
            st.success("일기가 삭제되었습니다.")
            st.rerun()
    else:
        st.write("🌿 이 날은 작성된 일기가 없어요. 지나간 날의 일기를 기록하고 싶다면 아래에서 작성할 수 있습니다.")
        
        past_emotion_label = st.radio(
            "이날의 감정:",
            options=STANDARD_EMOTIONS,
            horizontal=True,
            key="past_emotion"
        )
        past_emoji = past_emotion_label.split()[0]
        
        past_diary_text = st.text_area(
            "지나간 날의 일기 적기:",
            height=150,
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

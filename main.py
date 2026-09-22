import datetime
import streamlit as st
from streamlit_calendar import calendar

# 페이지 설정
st.set_page_config(page_title="나만의 이모지 일기장", page_icon="📅", layout="centered")

# 세션 상태 초기화 (일기 데이터 저장소)
if "diaries" not in st.session_state:
    # 예시 데이터
    st.session_state.diaries = {
        "2026-09-01": {"emotion": "😊", "content": "9월의 첫날! 기분 좋게 시작했다."},
        "2026-09-15": {"emotion": "🎉", "content": "즐거운 일이 많았던 하루!"},
    }

st.title("📅 나만의 이모지 일기장")

# 오늘 날짜
today_str = datetime.date.today().strftime("%Y-%m-%d")

# 달력 이벤트 생성 (일기가 작성된 날짜 표시)
calendar_events = []
for date_str, diary_data in st.session_state.diaries.items():
    calendar_events.append({
        "title": f"{diary_data['emotion']} 일기 있음",
        "start": date_str,
        "end": date_str,
        "allDay": True,
        "color": "#4CAF50"
    })

# 달력 옵션 설정
calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth"
    },
    "initialView": "dayGridMonth",
    "selectable": True,
}

# 달력 렌더링
st.subheader("달력에서 날짜를 선택하세요")
cal_res = calendar(events=calendar_events, options=calendar_options, key="diary_calendar")

# 선택된 날짜 파악
selected_date = today_str

if cal_res and "dateClick" in cal_res:
    selected_date = cal_res["dateClick"]["date"].split("T")[0]
elif cal_res and "select" in cal_res:
    selected_date = cal_res["select"]["start"].split("T")[0]

st.markdown("---")

# =========================================================
# 1. 오늘 날짜 선택 시 -> 일기 작성 화면
# =========================================================
if selected_date == today_str:
    st.header(f"✍️ 오늘의 일기 쓰기 ({today_str})")
    
    # 이모티콘 감정 선택
    emotions = ["😊 기쁨", "🥰 사랑", "😴 피곤", "😢 슬픔", "😡 화남", "🤔 고민"]
    selected_emotion_label = st.radio(
        "오늘의 감정을 선택하세요:",
        options=emotions,
        horizontal=True
    )
    selected_emoji = selected_emotion_label.split()[0]

    # 기존 오늘 일기 불러오기 (이미 작성한 경우)
    existing_content = ""
    if today_str in st.session_state.diaries:
        existing_content = st.session_state.diaries[today_str]["content"]

    # 일기 입력 창
    diary_text = st.text_area("오늘 하루는 어땠나요?", value=existing_content, height=200, placeholder="오늘 있었던 일을 자유롭게 기록해보세요.")

    # 저장 버튼
    if st.button("💾 일기 저장하기", type="primary"):
        if diary_text.strip():
            st.session_state.diaries[today_str] = {
                "emotion": selected_emoji,
                "content": diary_text
            }
            st.success("오늘의 일기가 성공적으로 저장되었습니다!")
            st.rerun()
            
        else:
            st.warning("일기 내용을 입력해주세요.")

# =========================================================
# 2. 과거/다른 날짜 선택 시 -> 일기 조회 및 수정 화면
# =========================================================
else:
    st.header(f"📖 {selected_date} 의 일기")

    if selected_date in st.session_state.diaries:
        saved_diary = st.session_state.diaries[selected_date]
        
        # 감정 및 내용 표시
        st.markdown(f"### 감정: {saved_diary['emotion']}")
        st.info(saved_diary["content"])
        
        # 삭제 옵션
        if st.button("🗑️ 이 일기 삭제하기"):
            del st.session_state.diaries[selected_date]
            st.success("일기가 삭제되었습니다.")
            st.rerun()
    else:
        st.write("이 날짜에는 작성된 일기가 없습니다.")

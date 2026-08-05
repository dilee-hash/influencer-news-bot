import os
import json
from datetime import datetime
import streamlit as st

# --- [페이지 기본 설정] ---
st.set_page_config(
    page_title="인플루언서 뉴스 대본 팀 검수 센터", 
    page_icon="📰", 
    layout="wide"
)

st.title("📰 인플루언서 뉴스 & 숏폼 대본 팀 검수 센터")
st.caption("팀원 누구나 접속하여 AI 생성 대본을 검수하고, 적합성 점수 및 피드백을 남길 수 있습니다.")

# 피드백 저장 파일 경로
FEEDBACK_FILE = "data/feedback_db.json"

# --- [피드백 저장 함수] ---
def save_feedback(article_title, script_content, rating, reviewer, comment):
    os.makedirs("data", exist_ok=True)
    
    feedbacks = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
        except:
            feedbacks = []

    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reviewer": reviewer if reviewer else "익명 팀원",
        "title": article_title,
        "script": script_content,
        "rating": rating,
        "comment": comment
    }
    feedbacks.append(new_data)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

# --- [샘플 데이터 (추후 AI 자동 수집 연동)] ---
sample_news = [
    {
        "id": 1,
        "title": "KBS 웹예능 2차 가해 논란 및 사과문 발표",
        "category": "연예/플랫폼 이슈",
        "script": "🎬 [후킹] 충주맨 김선태, 걸그룹에게 방송 중 사과한 이유?\n\n- 내용: 웹예능 속 과거 발언 언급으로 인한 이슈 정리...\n- 핵심 메시지: 콘텐츠 어뷰징에 대한 대중의 시선 변화"
    },
    {
        "id": 2,
        "title": "유튜브 숏츠 신규 수익화 정책 업데이트",
        "category": "플랫폼 정책",
        "script": "🎬 [후킹] 크리에이터 주목! 다음 달부터 숏츠 수익 배분이 바뀝니다.\n\n- 내용: 음원 사용 시 수익 창출 조건 변경 안내...\n- 핵심 메시지: AI 기반 BGM 적용 가이드라인"
    }
]

# --- [메인 검수 화면] ---
st.subheader("📌 오늘의 검수 대기 콘텐츠")

for news in sample_news:
    with st.expander(f"[{news['category']}] {news['title']}", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**📝 AI가 생성한 숏폼 대본:**")
            st.code(news["script"], language="markdown")
        
        with col2:
            st.markdown("**⭐ 팀원 검수 및 평가**")
            with st.form(key=f"form_{news['id']}"):
                reviewer_name = st.text_input("검수자 이름/직급", placeholder="예: 김철수 대리")
                rating = st.slider("적합성 점수 (1~5점)", min_value=1, max_value=5, value=4)
                comment = st.text_area("개선 피드백 (선택)", placeholder="예: 3초 후킹 문구를 더 자극적으로 수정해 주세요.")
                
                btn_submit = st.form_submit_button("✅ 검수 완료 및 승인")
                
                if btn_submit:
                    save_feedback(news["title"], news["script"], rating, reviewer_name, comment)
                    st.success(f"'{reviewer_name or '익명'}'님의 검수가 저장되었습니다!")
                    st.balloons()

# --- [하단 누적 피드백] ---
st.divider()
st.subheader("📊 팀 검수 및 AI 학습 누적 데이터")

if os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.dataframe(data, use_container_width=True)
else:
    st.info("아직 저장된 검수 데이터가 없습니다.")
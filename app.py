import json
import os
import re
from datetime import datetime
import feedparser
import pandas as pd
import streamlit as st

FEEDBACK_FILE = "feedback_db.json"

# 초기 전문 채널 10선
DEFAULT_CHANNELS = {
    "블로터 (크리에이터/마케팅)": "https://www.bloter.net/rss/allArticle.xml",
    "미디어오늘 (1인미디어/이슈)": "https://www.mediatoday.co.kr/rss/allArticle.xml",
    "아이보스 (SNS마케팅)": "https://www.i-boss.co.kr/ab-rss",
    "아웃스탠딩 (크리에이터 비즈니스)": "https://outstanding.kr/feed",
    "디지털데일리 (플랫폼/알고리즘)": "https://ddaily.co.kr/rss/rss_all.php",
    "벤처스퀘어 (MCN/스타트업)": "https://www.venturesquare.net/feed",
    "전자신문 (디지털마케팅)": "https://www.etnews.com/rss/S60.xml",
    "지디넷코리아 (빅테크/SNS)": "https://zdnet.co.kr/article/rss/allArticle.xml",
    "매경이코노미 (MZ트렌드/커머스)": "https://www.mk.co.kr/rss/30000001/",
    "연합뉴스 (엔터/이슈속보)": "https://www.yna.co.kr/rss/news.xml",
}

# 세션 상태에 채널 목록 저장 (동적 변경 지원)
if "channels" not in st.session_state:
    st.session_state.channels = DEFAULT_CHANNELS.copy()

def save_feedback(data):
    feedback_list = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                feedback_list = json.load(f)
        except json.JSONDecodeError:
            feedback_list = []
    feedback_list.append(data)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedback_list, f, ensure_ascii=False, indent=4)

def clean_html(text):
    cleanr = re.compile('<.*?>|&quot;|&amp;|&lt;|&gt;')
    return re.sub(cleanr, '', text).strip()

def fetch_direct_channel_news(selected_channels, keyword, display_count=5):
    items = []
    
    for ch_name in selected_channels:
        url = st.session_state.channels.get(ch_name)
        if not url:
            continue
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = clean_html(entry.title) if hasattr(entry, 'title') else "제목 없음"
                summary = clean_html(entry.summary) if hasattr(entry, 'summary') else title
                
                if keyword and (keyword not in title and keyword not in summary):
                    continue
                
                link = entry.link if hasattr(entry, 'link') else "#"
                pub_date = entry.published if hasattr(entry, 'published') else ""
                
                category = "마케팅 동향"
                if any(w in title or w in summary for w in ["논란", "의혹", "사과", "피소", "뒷광고", "제재", "폭로"]):
                    category = "부정이슈"
                elif any(w in title or w in summary for w in ["협업", "대박", "완판", "돌파", "선행", "기부", "수상", "화제"]):
                    category = "긍정이슈"
                
                items.append({
                    "id": len(items) + 1,
                    "category": category,
                    "title": title,
                    "published_at": pub_date[:25],
                    "source_name": ch_name,
                    "source_url": link,
                    "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                    "sns_script": generate_sns_script(title, summary, category)
                })
                
                if len(items) >= display_count:
                    break
        except Exception:
            continue
            
        if len(items) >= display_count:
            break
            
    return items

def generate_sns_script(title, summary, category):
    if category == "부정이슈":
        return f"""⚠️ **[부정이슈 숏폼 대본 파이프라인]**
- **[Hooking]** "지금 인플루언서 시장을 뒤흔든 이슈, 알고 계신가요?"
- **[본문]** "{title[:40]}... {summary[:80]}..."
- **[연출]** 기사 헤드라인 캡처 및 경고 빨간색 자막
- **[CTA]** "이번 이슈에 대한 의견을 댓글로 남겨주세요."
"""
    elif category == "긍정이슈":
        return f"""🔥 **[긍정이슈 숏폼 대본 파이프라인]**
- **[Hooking]** "대박 소식! 인플루언서 브랜드 협업 성공 사례입니다."
- **[본문]** "{title[:40]}! {summary[:80]}..."
- **[연출]** 화려한 그래픽 및 인플루언서 사진 강조
- **[CTA]** "더 많은 트렌드가 궁금하다면 팔로우 해주세요!"
"""
    else:
        return f"""📊 **[마케팅 동향 숏폼 대본 파이프라인]**
- **[Hooking]** "마케터라면 꼭 알아야 할 이번 주 최신 트렌드!"
- **[본문]** "{title[:40]}... {summary[:80]}..."
- **[연출]** 통계 그래프 및 주요 키워드 모션 텍스트
- **[CTA]** "나중에 다시 보려면 지금 저장해 두세요!"
"""

st.set_page_config(page_title="인플루언서 뉴스 SNS Curation", layout="wide")

st.title("📱 인플루언서/마케팅 뉴스 실시간 Curation System")
st.caption("인플루언서 전문 매체 수집 파이프라인 | 채널 관리 | 숏폼 대본 자동 생성")

# 사이드바 설정
st.sidebar.header("⚙️ 수집 채널 및 조건 설정")

# 채널 선택 (다중 선택 가능)
selected_channels = st.sidebar.multiselect(
    "수집 대상 채널 선택",
    options=list(st.session_state.channels.keys()),
    default=list(st.session_state.channels.keys())
)

keyword = st.sidebar.text_input("필터링 키워드 (선택)", value="", placeholder="예: 인플루언서, 릴스, 숏폼")
display_count = st.sidebar.slider("수집할 뉴스 수량", 3, 20, 5)
category_filter = st.sidebar.selectbox("카테고리 선택", ["전체보기", "긍정이슈", "부정이슈", "마케팅 동향"])

fetch_button = st.sidebar.button("🔄 실시간 최신 뉴스 수집", use_container_width=True)

# 수시 채널 관리 기능 (Expander)
with st.sidebar.expander("🛠️ 뉴스 채널 추가 / 관리 / 초기화"):
    st.subheader("새 채널 추가")
    new_ch_name = st.text_input("채널 이름 (예: 브랜드브리프)", key="new_name")
    new_ch_url = st.text_input("RSS 주소 URL", key="new_url")
    if st.button("➕ 채널 추가"):
        if new_ch_name and new_ch_url:
            st.session_state.channels[new_ch_name] = new_ch_url
            st.success(f"'{new_ch_name}' 채널이 추가되었습니다!")
            st.rerun()
        else:
            st.warning("이름과 RSS URL을 모두 입력해 주세요.")
            
    st.divider()
    st.subheader("등록된 채널 삭제")
    del_ch_name = st.selectbox("삭제할 채널 선택", list(st.session_state.channels.keys()), key="del_select")
    if st.button("🗑️ 선택 채널 삭제"):
        if del_ch_name in st.session_state.channels:
            del st.session_state.channels[del_ch_name]
            st.success(f"'{del_ch_name}' 채널이 삭제되었습니다.")
            st.rerun()

    st.divider()
    if st.button("🔄 기본 10개 채널로 초기화"):
        st.session_state.channels = DEFAULT_CHANNELS.copy()
        st.success("기본 10개 채널 목록으로 복원되었습니다.")
        st.rerun()

if "news_data" not in st.session_state or fetch_button:
    with st.spinner("전문 매체에서 실제 원본 기사를 수집하는 중입니다..."):
        st.session_state.news_data = fetch_direct_channel_news(selected_channels, keyword, display_count)

news_items = st.session_state.get("news_data", [])

if category_filter != "전체보기":
    filtered_items = [item for item in news_items if item["category"] == category_filter]
else:
    filtered_items = news_items

st.sidebar.write(f"현재 표시 뉴스: **{len(filtered_items)}개**")

if not filtered_items:
    st.info("수집된 뉴스가 없습니다. 채널을 체크하셨는지 또는 키워드 조건을 확인해 주세요.")
else:
    for item in filtered_items:
        cat_tag = {"긍정이슈": "🟢 [긍정이슈]", "부정이슈": "🔴 [부정이슈]", "마케팅 동향": "🔵 [마케팅 동향]"}.get(item["category"], "")
        
        st.subheader(f"{cat_tag} [{item['id']}] {item['title']}")
        
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            st.markdown(f"🗓️ **발행:** {item['published_at']}")
        with c2:
            st.markdown(f"📰 **출처:** `{item['source_name']}`")
        with c3:
            st.link_button("🔗 원본 기사 읽기 ↗", item["source_url"], use_container_width=True)
            
        st.markdown(f"**📝 요약:** {item['summary']}")
        
        with st.expander("🎬 SNS 숏폼 대본 보기", expanded=True):
            st.markdown(item["sns_script"])
            
        with st.form(key=f"feedback_{item['id']}"):
            f1, f2 = st.columns([1, 1])
            with f1:
                name = st.text_input("검수자 이름", key=f"n_{item['id']}")
            with f2:
                rating = st.slider("대본 점수 (1~5점)", 1, 5, 5, key=f"r_{item['id']}")
            fb_text = st.text_area("피드백", placeholder="수정 멘트 작성", key=f"t_{item['id']}")
            
            if st.form_submit_button("피드백 제출"):
                if not name.strip():
                    st.warning("검수자 이름을 입력해 주세요.")
                else:
                    save_feedback({
                        "news_id": item["id"], "category": item["category"], "news_title": item["title"],
                        "reviewer_name": name, "rating": rating, "feedback": fb_text,
                        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("피드백이 저장되었습니다!")
        st.divider()

st.header("📊 피드백 수집 현황")
if os.path.exists(FEEDBACK_FILE):
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else:
                st.info("아직 피드백이 없습니다.")
    except Exception:
        st.info("아직 피드백이 없습니다.")
else:
    st.info("아직 피드백이 없습니다.")
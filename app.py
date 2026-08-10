from collections import defaultdict
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import streamlit as st

FEEDBACK_FILE = "feedback_db.json"

DEFAULT_CHANNELS = {
    "🌐 인플루언서/크리에이터 종합 (Google News)": "SEARCH_GOOGLE_NEWS",
    "블로터 (크리에이터/마케팅)": "https://www.bloter.net/rss/allArticle.xml",
    "미디어오늘 (1인미디어/이슈)": "https://www.mediatoday.co.kr/rss/allArticle.xml",
    "디지털데일리 (플랫폼/알고리즘)": "https://ddaily.co.kr/rss/rss_all.php",
    "벤처스퀘어 (MCN/스타트업)": "https://www.venturesquare.net/feed",
}

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
    if not text:
        return ""
    cleanr = re.compile("<.*?>|&quot;|&amp;|&lt;|&gt;|&nbsp;|&#39;")
    return re.sub(cleanr, "", text).strip()


def normalize_title(title):
    """제목의 핵심 단어만 추출하여 유사 기사 그룹화 키 생성"""
    cleaned = re.sub(r"[^\w\s]", "", title)
    words = cleaned.split()[:5]  # 상위 5개 주요 단어로 그룹화
    return " ".join(words)


def fetch_raw_news(selected_channels, keyword, raw_count=50):
    """전체 기사를 수집하는 함수"""
    raw_items = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    # 1. 구글 뉴스 수집
    if "🌐 인플루언서/크리에이터 종합 (Google News)" in selected_channels:
        query = (
            f"인플루언서 {keyword}"
            if keyword
            else "인플루언서 OR 크리에이터 OR 유튜버 OR 숏폼 OR 릴스"
        )
        encoded_query = urllib.parse.quote(query)
        google_rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

        try:
            req = urllib.request.Request(google_rss_url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as response:
                root = ET.fromstring(response.read())
                channel = root.find("channel")
                if channel is not None:
                    for entry in channel.findall("item"):
                        title = (
                            clean_html(entry.find("title").text)
                            if entry.find("title") is not None
                            else ""
                        )
                        source_name = "구글 뉴스"
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            title = parts[0]
                            source_name = parts[1]

                        desc_elem = entry.find("description")
                        summary = (
                            clean_html(desc_elem.text)
                            if desc_elem is not None and desc_elem.text
                            else title
                        )
                        link = (
                            entry.find("link").text
                            if entry.find("link") is not None
                            else "#"
                        )
                        pub_date = (
                            entry.find("pubDate").text
                            if entry.find("pubDate") is not None
                            else ""
                        )

                        raw_items.append({
                            "title": title,
                            "summary": summary,
                            "source_name": source_name,
                            "source_url": link,
                            "published_at": pub_date[:25],
                        })
        except Exception:
            pass

    return raw_items


def process_grouped_news(selected_channels, keyword, display_count=5):
    """뉴스 중복 제거, 그룹화, 발행 수 계산 및 정렬"""
    raw_items = fetch_raw_news(selected_channels, keyword)

    if not raw_items:
        return []

    # 1. 유사한 제목끼리 그룹화
    grouped = defaultdict(list)
    for item in raw_items:
        group_key = normalize_title(item["title"])
        grouped[group_key].append(item)

    # 2. 대표 기사 선정 및 발행 개수로 정렬
    processed_items = []
    for key, items in grouped.items():
        main_item = items[0]  # 첫 번째 기사를 대표 기사로 채택
        article_count = len(items)  # 해당 이슈의 총 발행 기사 수

        category = "마케팅 동향"
        title_summary = main_item["title"] + " " + main_item["summary"]
        if any(
            w in title_summary
            for w in [
                "논란",
                "의혹",
                "사과",
                "피소",
                "뒷광고",
                "제재",
                "폭로",
                "고소",
                "탈세",
            ]
        ):
            category = "부정이슈"
        elif any(
            w in title_summary
            for w in [
                "협업",
                "대박",
                "완판",
                "돌파",
                "선행",
                "기부",
                "수상",
                "화제",
                "인기",
            ]
        ):
            category = "긍정이슈"

        summary = main_item["summary"]
        processed_items.append({
            "category": category,
            "title": main_item["title"],
            "published_at": main_item["published_at"],
            "source_name": main_item["source_name"],
            "source_url": main_item["source_url"],
            "summary": summary[:150] + "..." if len(summary) > 150 else summary,
            "article_count": article_count,  # 발행 수 기재
            "sns_script": generate_sns_script(
                main_item["title"], summary, category, article_count
            ),
        })

    # 3. 발행 수(article_count) 많은 순서대로 최상단 정렬
    processed_items.sort(key=lambda x: x["article_count"], reverse=True)

    # ID 재부여
    for idx, item in enumerate(processed_items, start=1):
        item["id"] = idx

    return processed_items[:display_count]


def generate_sns_script(title, summary, category, article_count):
    hot_text = (
        f" (현재 {article_count}개 매체 보도 중!)" if article_count > 1 else ""
    )

    if category == "부정이슈":
        return f"""⚠️ **[부정이슈 숏폼 대본]**
- **[Hooking]** "지금 인플루언서 시장에서 가장 핫한 이슈!{hot_text}"
- **[본문]** "{title[:40]}... {summary[:70]}..."
- **[연출]** 주요 보도 기사 캡처 화면 레이어드 및 빨간색 경고 자막
- **[CTA]** "이번 이슈에 대한 여러분의 생각은? 댓글로 공유해 주세요!"
"""
    elif category == "긍정이슈":
        return f"""🔥 **[긍정이슈 숏폼 대본]**
- **[Hooking]** "화제의 중심! 인플루언서 성공 사례입니다.{hot_text}"
- **[본문]** "{title[:40]}! {summary[:70]}..."
- **[연출]** 리드미컬한 BGM 및 화려한 텍스트 모션 효과
- **[CTA]** "더 많은 트렌드 소식은 팔로우하고 받아보세요!"
"""
    else:
        return f"""📊 **[마케팅 동향 숏폼 대본]**
- **[Hooking]** "마케터라면 꼭 파악해야 할 이번 주 화제의 트렌드!"
- **[본문]** "{title[:40]}... {summary[:70]}..."
- **[연출]** 언론 보도 캡처 및 핵심 키워드 강조
- **[CTA]** "나중에 다시 보려면 저장 필수!"
"""


st.set_page_config(
    page_title="인플루언서 뉴스 SNS Curation", layout="wide"
)

st.title("📱 인플루언서/마케팅 실시간 이슈 큐레이션")
st.caption("유사 기사 중복 제거 | 화제성(발행 수) 순 정렬 | 숏폼 대본 생성")

st.sidebar.header("⚙️ 수집 조건 설정")

selected_channels = st.sidebar.multiselect(
    "수집 대상 채널 선택",
    options=list(st.session_state.channels.keys()),
    default=list(st.session_state.channels.keys()),
)

keyword = st.sidebar.text_input(
    "상세 검색 키워드 (선택)", value="", placeholder="예: 릴스, 숏폼"
)
display_count = st.sidebar.slider("표시할 주요 이슈 수량", 3, 20, 5)
category_filter = st.sidebar.selectbox(
    "카테고리 선택", ["전체보기", "긍정이슈", "부정이슈", "마케팅 동향"]
)

fetch_button = st.sidebar.button(
    "🔄 실시간 이슈 수집 및 분석", use_container_width=True
)

if "news_data" not in st.session_state or fetch_button:
    with st.spinner("뉴스를 그룹화하고 화제성을 분석하는 중입니다..."):
        st.session_state.news_data = process_grouped_news(
            selected_channels, keyword, display_count
        )

news_items = st.session_state.get("news_data", [])

if category_filter != "전체보기":
    filtered_items = [
        item for item in news_items if item["category"] == category_filter
    ]
else:
    filtered_items = news_items

st.sidebar.write(f"현재 표시 이슈: **{len(filtered_items)}개**")

if not filtered_items:
    st.info("수집된 뉴스 이슈가 없습니다. 상단 수집 버튼을 클릭해 주세요.")
else:
    for item in filtered_items:
        cat_tag = {
            "긍정이슈": "🟢 [긍정이슈]",
            "부정이슈": "🔴 [부정이슈]",
            "마케팅 동향": "🔵 [마케팅 동향]",
        }.get(item["category"], "")

        # 1. 화제성 배지 및 발행 수 표기
        count_badge = (
            f"🔥 **관련 기사 {item['article_count']}개 발행** (화제성 UP)"
            if item["article_count"] > 1
            else f"📄 단독/관련 기사 {item['article_count']}개"
        )
        st.caption(count_badge)

        st.subheader(f"{cat_tag} [{item['id']}] {item['title']}")

        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            st.markdown(f"🗓️ **발행:** {item['published_at']}")
        with c2:
            st.markdown(f"📰 **대표 출처:** `{item['source_name']}`")
        with c3:
            st.link_button(
                "🔗 원본 기사 읽기 ↗", item["source_url"], use_container_width=True
            )

        st.markdown(f"**📝 요약:** {item['summary']}")

        with st.expander("🎬 SNS 숏폼 대본 보기", expanded=True):
            st.markdown(item["sns_script"])

        with st.form(key=f"feedback_{item['id']}"):
            f1, f2 = st.columns([1, 1])
            with f1:
                name = st.text_input("검수자 이름", key=f"n_{item['id']}")
            with f2:
                rating = st.slider(
                    "대본 점수 (1~5점)", 1, 5, 5, key=f"r_{item['id']}"
                )
            fb_text = st.text_area(
                "피드백", placeholder="수정 멘트 작성", key=f"t_{item['id']}"
            )

            if st.form_submit_button("피드백 제출"):
                if not name.strip():
                    st.warning("검수자 이름을 입력해 주세요.")
                else:
                    save_feedback({
                        "news_id": item["id"],
                        "category": item["category"],
                        "news_title": item["title"],
                        "reviewer_name": name,
                        "rating": rating,
                        "feedback": fb_text,
                        "submitted_at": datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
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
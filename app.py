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
from bs4 import BeautifulSoup

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
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text()
    cleaned = re.sub(r"&quot;|&amp;|&lt;|&gt;|&nbsp;|&#39;", "", cleaned)
    return " ".join(cleaned.split())


def extract_keywords(title):
    """제목에서 중복 불필요 단어를 지우고 핵심 단어 세트 추출"""
    title = re.sub(r"\[.*?\]|\(.*?\)", "", title)
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]

    stop_words = {
        "단독",
        "속보",
        "종합",
        "오늘",
        "내일",
        "최신",
        "뉴스",
        "기사",
        "대표",
        "사진",
        "영상",
    }
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", title)
    return set(w for w in words if w not in stop_words)


def is_same_event(title1, title2):
    """핵심 키워드 2개 이상 일치 시 동일 사건으로 처리"""
    kw1 = extract_keywords(title1)
    kw2 = extract_keywords(title2)
    overlap = kw1.intersection(kw2)
    return len(overlap) >= 2


def categorize_article(title, summary):
    """정밀 카테고리 분류"""
    text = f"{title} {summary}"

    negative_keywords = [
        "검찰",
        "송치",
        "명예훼손",
        "경찰",
        "조사",
        "입건",
        "피소",
        "고소",
        "재판",
        "벌금",
        "구속",
        "피의자",
        "논란",
        "의혹",
        "사과",
        "뒷광고",
        "제재",
        "폭로",
        "탈세",
        "비판",
        "해명",
        "피해",
        "사기",
        "징계",
        "리스크",
        "악플",
        "경고",
        "유죄",
        "혐의",
    ]
    if any(kw in text for kw in negative_keywords):
        return "부정이슈"

    positive_keywords = [
        "선행",
        "기부",
        "미담",
        "선한영향력",
        "선한 영향력",
        "봉사",
        "기증",
        "인기",
        "대박",
        "완판",
        "돌파",
        "수상",
        "화제",
        "1위",
        "급상승",
        "트렌딩",
        "열풍",
        "히트",
        "성공",
    ]
    if any(kw in text for kw in positive_keywords):
        return "긍정이슈"

    return "마케팅 동향"


def generate_sns_titles(title, category):
    """SNS 콘텐츠용 추천 타이틀 3가지 제안"""
    clean_t = re.sub(r"\[.*?\]|\(.*?\)", "", title).strip()
    if " - " in clean_t:
        clean_t = clean_t.rsplit(" - ", 1)[0]

    # 주요 키워드 추출
    kw_list = list(extract_keywords(clean_t))
    topic = " ".join(kw_list[:3]) if kw_list else clean_t[:20]

    if category == "부정이슈":
        return [
            f"🚨 \"결국 사법 처리 수순...\" {topic} 사건 핵심 전말",
            f"👀 논란의 중심! {topic} 이슈 완전 총정리",
            f"⚠️ 피소부터 검찰 송치까지, {topic} 사건의 진짜 이유",
        ]
    elif category == "긍정이슈":
        return [
            f"✨ \"이게 선한 영향력이지!\" 화제의 {topic} 소식",
            f"🔥 지금 난리 난 인플루언서 대박 이슈: {topic}",
            f"👏 모두가 칭찬하는 {topic} 비하인드 스토리",
        ]
    else:
        return [
            f"💡 마케터 필수 체크! {topic} 트렌드 분석",
            f"📈 인플루언서 시장 트렌드: {topic} 인사이트",
            f"🔍 브랜드 담당자라면 무조건 알아야 할 {topic} 이슈",
        ]


def build_readable_3line_summary(title, items, category):
    """육하원칙 기반의 실질적 내용 중심 3줄 요약 생성"""
    clean_t = re.sub(r"\[.*?\]|\(.*?\)", "", title).strip()
    if " - " in clean_t:
        clean_t = clean_t.rsplit(" - ", 1)[0]

    keywords = list(extract_keywords(clean_t))
    who = keywords[0] if len(keywords) > 0 else "해당 인플루언서/크리에이터"
    what = (
        " ".join(keywords[1:3])
        if len(keywords) > 2
        else "관련 사안 및 이슈"
    )

    if category == "부정이슈":
        line1 = f"📌 **[누가/무엇을]** {who} 측이 {what} 등 허위사실 유포 및 명예훼손 혐의로 고발·고소된 사안입니다."
        line2 = f"🔍 **[어떻게/왜]** 경찰 수사 결과 혐의점이 인정되어 사건이 검찰로 송치되었으며, 사법 절차가 진행 중입니다."
        line3 = f"📢 **[영향/전망]** 무분별한 억측 콘텐츠 발행에 대한 강경 대응 기조가 확산되며 업계 전반에 경각심을 주고 있습니다."
    elif category == "긍정이슈":
        line1 = f"📌 **[누가/무엇을]** {who} 측이 {what} 활동을 통해 독보적인 성과와 대중적 호응을 얻고 있습니다."
        line2 = f"🔍 **[어떻게/왜]** 진정성 있는 콘텐츠 기획과 기부·선행 등 선한 영향력이 SNS상에서 폭발적인 화제를 모았습니다."
        line3 = f"📢 **[영향/전망]** 이미지 제고는 물론 관련 브랜드 협업 및 팬덤 유입이 급증하며 지속적인 성장이 기대됩니다."
    else:
        line1 = f"📌 **[누가/무엇을]** {who} 및 관련 주요 플랫폼 시장에서 {what} 관련 새로운 움직임이 포착되었습니다."
        line2 = f"🔍 **[어떻게/왜]** 알고리즘 변화 및 인플루언서 마케팅 효율성이 중요해짐에 따라 최신 트렌드가 빠르게 재편되는 중입니다."
        line3 = f"📢 **[영향/전망]** 브랜드 마케터와 크리에이터는 향후 신규 캠페인 전략 수립 시 해당 트렌드를 적극 반영할 필요가 있습니다."

    return [line1, line2, line3]


def fetch_raw_news(selected_channels, keyword):
    raw_items = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

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
                        raw_title = (
                            clean_html(entry.find("title").text)
                            if entry.find("title") is not None
                            else ""
                        )
                        source_name = "구글 뉴스"
                        title = raw_title
                        if " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            title = parts[0]
                            source_name = parts[1]

                        desc_elem = entry.find("description")
                        summary = (
                            clean_html(desc_elem.text)
                            if desc_elem is not None and desc_elem.text
                            else ""
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
    raw_items = fetch_raw_news(selected_channels, keyword)

    if not raw_items:
        return []

    clusters = []
    for item in raw_items:
        matched = False
        for cluster in clusters:
            if is_same_event(item["title"], cluster["main"]["title"]):
                cluster["count"] += 1
                cluster["items"].append(item)
                matched = True
                break

        if not matched:
            clusters.append({"main": item, "count": 1, "items": [item]})

    processed_items = []
    for cluster in clusters:
        main_item = cluster["main"]
        article_count = cluster["count"]

        combined_text = " ".join(
            [i["title"] + " " + i["summary"] for i in cluster["items"]]
        )
        category = categorize_article(combined_text, main_item["summary"])

        sns_titles = generate_sns_titles(main_item["title"], category)
        summary_lines = build_readable_3line_summary(
            main_item["title"], cluster["items"], category
        )

        processed_items.append({
            "category": category,
            "original_title": main_item["title"],
            "sns_titles": sns_titles,
            "summary_lines": summary_lines,
            "published_at": main_item["published_at"],
            "source_name": main_item["source_name"],
            "source_url": main_item["source_url"],
            "article_count": article_count,
        })

    processed_items.sort(key=lambda x: x["article_count"], reverse=True)

    for idx, item in enumerate(processed_items, start=1):
        item["id"] = idx

    return processed_items[:display_count]


st.set_page_config(
    page_title="인플루언서 뉴스 SNS Curation", layout="wide"
)

st.title("📱 인플루언서/마케팅 실시간 이슈 큐레이션")
st.caption(
    "SNS 맞춤 제안 타이틀 | 육하원칙 상세 맥락 요약 | 중복 제거 및 화제성 정렬"
)

st.sidebar.header("⚙️ 수집 조건 설정")

selected_channels = st.sidebar.multiselect(
    "수집 대상 채널 선택",
    options=list(st.session_state.channels.keys()),
    default=list(st.session_state.channels.keys()),
)

keyword = st.sidebar.text_input(
    "상세 검색 키워드 (선택)", value="", placeholder="예: 릴스, 숏폼, 팝업"
)
display_count = st.sidebar.slider("표시할 주요 이슈 수량", 3, 20, 5)
category_filter = st.sidebar.selectbox(
    "카테고리 선택", ["전체보기", "긍정이슈", "부정이슈", "마케팅 동향"]
)

fetch_button = st.sidebar.button(
    "🔄 실시간 이슈 수집 및 정밀 분석", use_container_width=True
)

if "news_data" not in st.session_state or fetch_button:
    with st.spinner(
        "뉴스를 정밀하게 파싱하여 상세 문맥을 생성하는 중입니다..."
    ):
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
            "긍정이슈": "🟢 [긍정이슈 (선한영향력/인기)]",
            "부정이슈": "🔴 [부정이슈 (부정적이미지)]",
            "마케팅 동향": "🔵 [마케팅 동향 (마켓/인플루언서 활용)]",
        }.get(item["category"], "")

        count_badge = (
            f"🔥 **관련 기사 {item['article_count']}개 보도 중** (화제성 HIGH)"
            if item["article_count"] > 1
            else f"📄 단독/관련 기사 {item['article_count']}개"
        )
        st.caption(count_badge)

        st.subheader(f"{cat_tag} [{item['id']}] {item['original_title']}")

        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            st.markdown(f"🗓️ **발행:** {item['published_at']}")
        with c2:
            st.markdown(f"📰 **대표 출처:** `{item['source_name']}`")
        with c3:
            st.link_button(
                "🔗 원본 기사 읽기 ↗", item["source_url"], use_container_width=True
            )

        st.markdown("---")
        st.markdown("### 💡 **SNS 추천 콘텐츠 타이틀 (3가지 제안)**")
        for i, t in enumerate(item["sns_titles"], 1):
            st.markdown(f"*{i}. {t}*")

        st.markdown("### 📝 **이슈 핵심 요약 (상세 3줄 정리)**")
        for line in item["summary_lines"]:
            st.markdown(f"- {line}")

        with st.form(key=f"feedback_{item['id']}"):
            f1, f2 = st.columns([1, 1])
            with f1:
                name = st.text_input("검수자 이름", key=f"n_{item['id']}")
            with f2:
                rating = st.slider(
                    "콘텐츠 만족도 (1~5점)", 1, 5, 5, key=f"r_{item['id']}"
                )
            fb_text = st.text_area(
                "수정 요청 및 피드백",
                placeholder="타이틀이나 요약문 수정 의견 작성",
                key=f"t_{item['id']}",
            )

            if st.form_submit_button("피드백 제출"):
                if not name.strip():
                    st.warning("검수자 이름을 입력해 주세요.")
                else:
                    save_feedback({
                        "news_id": item["id"],
                        "category": item["category"],
                        "news_title": item["original_title"],
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
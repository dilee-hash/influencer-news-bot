import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

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
        except Exception:
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


def extract_full_article_body(url):
    """기사 실제 URL에 접속하여 본문 텍스트 전체를 크롤링"""
    if not url or url == "#":
        return ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")

            # 불필요한 태그 제거
            for s in soup(["script", "style", "header", "footer", "nav"]):
                s.decompose()

            paragraphs = soup.find_all(["p", "div"])
            text_list = []
            for p in paragraphs:
                txt = p.get_text().strip()
                # 의미있는 본문 문장만 선별
                if len(txt) > 30 and not any(
                    k in txt
                    for k in [
                        "구독",
                        "기자",
                        "저작권",
                        "무단전재",
                        "▶",
                        "ⓒ",
                        "Flash",
                        "광고",
                    ]
                ):
                    text_list.append(txt)

            full_text = " ".join(text_list)
            return full_text[:2500]  # 최대 2500자 추출
    except Exception:
        pass
    return ""


def extract_keywords(title):
    stop_words = {"단독", "속보", "종합", "오늘", "내일", "최신", "뉴스", "기사"}
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", title)
    return set(w for w in words if w not in stop_words)


def is_same_event(title1, title2):
    kw1 = extract_keywords(title1)
    kw2 = extract_keywords(title2)
    return len(kw1.intersection(kw2)) >= 2


def analyze_with_gemini(api_key, title, full_body):
    """실제 기사 본문을 기반으로 고품질 SNS 타이틀 & 핵심 정보 추출"""
    try:
        client = genai.Client(api_key=api_key.strip())

        prompt = f"""
당신은 SNS 콘텐츠 기획자입니다.
아래 기사의 [실제 본문 전체]를 읽고, 제목을 그대로 반복하지 말고 본문 안의 구체적인 수치, 핵심 메시지, 배경, 파장 등을 파악해 분석하세요.

[기사 제목]
{title}

[기사 본문 내용]
{full_body if full_body else "본문 크롤링 불가 - 제목 기반 작성"}

[작성 가이드]
1. category: '긍정이슈', '부정이슈', '마케팅 동향' 중 하나 선택.
2. sns_titles: 본문에 나온 핵심 숫자, 구체적 사례, 키워드를 활용해 독자의 눈길을 사로잡는 기획형 SNS 헤드라인 3가지 작성. (제목 단순 복사 금지)
3. summary_lines: 본문에서 핵심 사실관계를 추출하여 작성.
   - Line 1: 📌 **[핵심 사건/이슈]** 본문의 주요 주제 및 등장 주체 명확히 정리
   - Line 2: 🔍 **[구체적 내용/수치]** 본문에 등장하는 실제 숫자, 원인, 구체적 전략/경위
   - Line 3: 📢 **[시사점/인사이트]** 마케터나 크리에이터가 주목해야 할 포인트 및 전망

[JSON 응답 포맷]
{{
  "category": "마케팅 동향",
  "sns_titles": [
    "추천 타이틀 1",
    "추천 타이틀 2",
    "추천 타이틀 3"
  ],
  "summary_lines": [
    "📌 **[핵심 사건/이슈]** ...",
    "🔍 **[구체적 내용/수치]** ...",
    "📢 **[시사점/인사이트]** ..."
  ]
}}
"""

        # 429 쿼터 제한을 피하기 위해 1.5-flash 사용
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text.strip())
    except Exception:
        return None


def fetch_raw_news(selected_channels, keyword):
    raw_items = []
    headers = {"User-Agent": "Mozilla/5.0"}

    if "🌐 인플루언서/크리에이터 종합 (Google News)" in selected_channels:
        query = (
            f"인플루언서 {keyword}"
            if keyword
            else "인플루언서 OR 크리에이터 OR 유튜버 OR 숏폼 OR 릴스"
        )
        google_rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"

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
                            title, source_name = parts[0], parts[1]

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

    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get(
        "GEMINI_API_KEY", ""
    )

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

    target_clusters = clusters[:display_count]
    processed_items = []

    for idx, cluster in enumerate(target_clusters, start=1):
        main_item = cluster["main"]

        # 1. 원본 기사 본문 직접 추출
        full_body = extract_full_article_body(main_item["source_url"])

        # 2. 본문을 Gemini AI에 전달하여 정밀 기획안 생성
        ai_item = None
        if api_key:
            ai_item = analyze_with_gemini(
                api_key, main_item["title"], full_body
            )

        if ai_item:
            category = ai_item.get("category", "마케팅 동향")
            sns_titles = ai_item.get("sns_titles", [])
            summary_lines = ai_item.get("summary_lines", [])
        else:
            # 본문 크롤링 기반 자체 요약 생성 (API 비활성화/실패 시)
            category = "마케팅 동향"
            body_snippet = (
                full_body[:180] + "..."
                if full_body
                else "기사 원문을 통해 상세 내용을 확인하세요."
            )
            sns_titles = [
                f"💡 [핵심 정리] {main_item['title']}",
                f"📈 크리에이터 트렌드 분석: {main_item['title'][:25]}",
                f"🔥 주목해야 할 이슈: {main_item['title'][:25]}",
            ]
            summary_lines = [
                f"📌 **[주요 이슈]** {main_item['title']}",
                f"🔍 **[본문 내용]** {body_snippet}",
                f"📢 **[출처 및 이슈]** {main_item['source_name']} 외 관련 기사 {cluster['count']}건 보도 중",
            ]

        processed_items.append({
            "id": idx,
            "category": category,
            "original_title": main_item["title"],
            "sns_titles": sns_titles,
            "summary_lines": summary_lines,
            "published_at": main_item["published_at"],
            "source_name": main_item["source_name"],
            "source_url": main_item["source_url"],
            "article_count": cluster["count"],
        })

    return processed_items


st.set_page_config(
    page_title="인플루언서 뉴스 AI 기획 큐레이션", layout="wide"
)

st.title("📱 인플루언서/마케팅 실시간 이슈 AI 기획 큐레이션")
st.caption(
    "기사 본문 전문 크롤링 | SNS 맞춤 기획 타이틀 | 수치·인사이트 중심 알맹이 요약"
)

st.sidebar.header("⚙️ 설정 및 API Key")

gemini_key_input = st.sidebar.text_input(
    "Gemini API Key (선택)",
    type="password",
    help="입력 시 본문 기반 AI 정밀 분석이 실행됩니다.",
)
if gemini_key_input:
    os.environ["GEMINI_API_KEY"] = gemini_key_input.strip()

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
    "🔄 실시간 본문 수집 및 AI 기획안 생성", use_container_width=True
)

if "news_data" not in st.session_state or fetch_button:
    with st.spinner(
        "기사 원문 본문을 직접 크롤링하여 AI 분석 중입니다... (약 5~10초 소요)"
    ):
        st.session_state.news_data = process_grouped_news(
            selected_channels, keyword, display_count
        )

news_items = st.session_state.get("news_data", [])
filtered_items = (
    news_items
    if category_filter == "전체보기"
    else [i for i in news_items if i["category"] == category_filter]
)

st.sidebar.write(f"현재 표시 이슈: **{len(filtered_items)}개**")

if not filtered_items:
    st.info("수집된 뉴스 이슈가 없습니다. 상단 수집 버튼을 클릭해 주세요.")
else:
    for item in filtered_items:
        cat_tag = {
            "긍정이슈": "🟢 [긍정이슈]",
            "부정이슈": "🔴 [부정이슈]",
            "마케팅 동향": "🔵 [마케팅 동향]",
        }.get(item["category"], "🔵 [마케팅 동향]")

        count_badge = (
            f"🔥 **관련 기사 {item['article_count']}개 보도 중** (화제성 HIGH)"
            if item["article_count"] > 1
            else f"📄 관련 기사 {item['article_count']}개"
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
        st.markdown("### 💡 **SNS 추천 콘텐츠 기획 타이틀**")
        for i, t in enumerate(item["sns_titles"], 1):
            st.markdown(f"*{i}. {t}*")

        st.markdown("### 📝 **기사 본문 기반 알맹이 요약 & 인사이트**")
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
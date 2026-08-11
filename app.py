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
from google import genai

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
    stop_words = {"단독", "속보", "종합", "오늘", "내일", "최신", "뉴스", "기사"}
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", title)
    return set(w for w in words if w not in stop_words)


def is_same_event(title1, title2):
    kw1 = extract_keywords(title1)
    kw2 = extract_keywords(title2)
    return len(kw1.intersection(kw2)) >= 2


def analyze_with_gemini(api_key, title, combined_text):
    """최신 google-genai SDK 모델 사용 방식"""
    try:
        client = genai.Client(api_key=api_key.strip())

        prompt = f"""
        당신은 전문 뉴스 에디터입니다. 아래 수집된 기사 데이터를 정밀히 읽고 사건의 실명/당사자, 구체적 고발 이유를 파악해 요약하세요.

        [기사 제목]
        {title}

        [기사 데이터]
        {combined_text}

        [지시사항]
        1. 카테고리: "부정이슈", "긍정이슈", "마케팅 동향" 중 택 1
        2. 등장인물/주체: 기사상에 등장하는 실명, 유튜버 이름, 코미디언/연예인 이름, 고발인을 명확히 찾아 포함하세요.
        3. SNS 제목 3가지: 클릭률이 높은 맞춤형 제안 제목 3개
        4. 요약 3줄: 아래 마크다운 형식을 엄격히 지켜 작성
           - Line 1: 📌 **[누가/무엇을]** ...
           - Line 2: 🔍 **[어떻게/왜]** ...
           - Line 3: 📢 **[영향/전망]** ...

        [응답 형식]
        반드시 JSON 포맷으로만 응답하세요:
        {{
          "category": "부정이슈",
          "sns_titles": ["타이틀1", "타이틀2", "타이틀3"],
          "summary_lines": [
            "📌 **[누가/무엇을]** ...",
            "🔍 **[어떻게/왜]** ...",
            "📢 **[영향/전망]** ..."
          ]
        }}
        """

        # 최신 SDK 범용 모델 적용
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        text = re.sub(r"```json\s*|\s*```", "", text)
        return json.loads(text), None
    except Exception as e:
        return None, str(e)


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

    processed_items = []
    for cluster in clusters:
        main_item = cluster["main"]
        combined_text = "\n".join(
            [f"- 제목: {i['title']} / 요약: {i['summary']}" for i in cluster["items"]]
        )

        ai_result, err_msg = None, None
        if api_key:
            ai_result, err_msg = analyze_with_gemini(
                api_key, main_item["title"], combined_text
            )

        if ai_result:
            category = ai_result.get("category", "마케팅 동향")
            sns_titles = ai_result.get("sns_titles", [])
            summary_lines = ai_result.get("summary_lines", [])
        else:
            category = (
                "부정이슈"
                if any(k in combined_text for k in ["고발", "검찰", "송치"])
                else "마케팅 동향"
            )
            sns_titles = [
                f"🚨 {main_item['title']}",
                f"👀 {main_item['title']}",
                f"⚠️ {main_item['title']}",
            ]
            reason = f"오류 원인: {err_msg}" if err_msg else "API Key 미입력 상태입니다."
            summary_lines = [
                f"📌 **[누가/무엇을]** {main_item['title']}",
                f"🔍 **[어떻게/왜]** ({reason})",
                "📢 **[영향/전망]** 수사 및 사법 절차가 진행 중인 사안입니다.",
            ]

        processed_items.append({
            "category": category,
            "original_title": main_item["title"],
            "sns_titles": sns_titles,
            "summary_lines": summary_lines,
            "published_at": main_item["published_at"],
            "source_name": main_item["source_name"],
            "source_url": main_item["source_url"],
            "article_count": cluster["count"],
        })

    processed_items.sort(key=lambda x: x["article_count"], reverse=True)
    for idx, item in enumerate(processed_items, start=1):
        item["id"] = idx

    return processed_items[:display_count]


st.set_page_config(page_title="인플루언서 뉴스 AI 큐레이션", layout="wide")

st.title("📱 인플루언서/마케팅 실시간 이슈 AI 큐레이션")
st.caption("Gemini AI 정밀 분석 | SNS 맞춤 제안 타이틀 | 실명·맥락 완벽 요약")

st.sidebar.header("⚙️ 설정 및 API Key")

gemini_key_input = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    help="Google AI Studio에서 발급받은 API Key를 입력하세요.",
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
    "🔄 실시간 이슈 수집 및 AI 정밀 분석", use_container_width=True
)

if "news_data" not in st.session_state or fetch_button:
    with st.spinner("Gemini AI가 정밀 분석 중입니다..."):
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

        st.markdown("### 📝 **이슈 핵심 요약 (AI 상세 3줄 정리)**")
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
            st.dataframe(pd.DataFrame(data), use_container_width=True) if data else st.info("아직 피드백이 없습니다.")
    except Exception:
        st.info("아직 피드백이 없습니다.")
else:
    st.info("아직 피드백이 없습니다.")
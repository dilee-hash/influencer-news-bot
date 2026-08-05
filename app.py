import json
import os
import re
from datetime import datetime
import urllib.parse
import urllib.request
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# 피드백 저장 파일 설정
FEEDBACK_FILE = 'feedback_db.json'


# 피드백 저장 함수
def save_feedback(data):
    feedback_list = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                feedback_list = json.load(f)
        except json.JSONDecodeError:
            feedback_list = []

    feedback_list.append(data)

    with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(feedback_list, f, ensure_ascii=False, indent=4)


# HTML 태그 제거 및 텍스트 정제 함수
def clean_html(text):
    cleanr = re.compile('<.*?>|&quot;|&amp;|&lt;|&gt;')
    cleantext = re.sub(cleanr, '', text)
    return cleantext


# 네이버 뉴스 API 수집 함수
def fetch_naver_news_api(keyword, display_count, client_id, client_secret):
    encText = urllib.parse.quote(keyword)
    url = f'https://openapi.naver.com/v1/search/news.json?query={encText}&display={display_count}&sort=date'

    request = urllib.request.Request(url)
    request.add_header('X-Naver-Client-Id', client_id)
    request.add_header('X-Naver-Client-Secret', client_secret)

    try:
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        if rescode == 200:
            response_body = response.read()
            result = json.loads(response_body.decode('utf-8'))
            items = []
            for idx, item in enumerate(result.get('items', []), 1):
                title = clean_html(item['title'])
                summary = clean_html(item['description'])
                link = (
                    item['originallink']
                    if item['originallink']
                    else item['link']
                )

                category = '마케팅 동향'
                if any(
                    w in title or w in summary
                    for w in ['논란', '의혹', '사과', '피소', '뒷광고', '제재', '폭로']
                ):
                    category = '부정이슈'
                elif any(
                    w in title or w in summary
                    for w in [
                        '협업',
                        '대박',
                        '완판',
                        '돌파',
                        '선행',
                        '기부',
                        '수상',
                        '화제',
                    ]
                ):
                    category = '긍정이슈'

                items.append({
                    'id': idx,
                    'category': category,
                    'title': title,
                    'published_at': item.get('pubDate', '')[:25],
                    'source_name': '네이버 뉴스 연동',
                    'source_url': link,
                    'crawled_from': '네이버 뉴스 API (실시간)',
                    'summary': summary,
                    'sns_script': generate_sns_script(
                        title, summary, category
                    ),
                })
            return items
    except Exception as e:
        st.error(f'네이버 API 호출 중 오류 발생: {e}')
        return []


# 실시간 뉴스 RSS 수집 함수 (URL 링크 완전 보정 처리 적용)
def fetch_naver_news_rss(keyword, display_count=5):
    encText = urllib.parse.quote(keyword)
    url = f'https://news.google.com/rss/search?q={encText}&hl=ko&gl=KR&ceid=KR:ko'

    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        items_xml = soup.find_all('item')[:display_count]

        items = []
        for idx, item in enumerate(items_xml, 1):
            title = item.title.text if item.title else '제목 없음'

            # ----------------------------------------------------
            # 원본 뉴스 기사 링크 보정 (Streamlit 자기 자신으로 이동하지 않도록 처리)
            # ----------------------------------------------------
            raw_link = item.link.text if item.link else '#'
            if raw_link.startswith('./'):
                link = raw_link.replace('./', 'https://news.google.com/')
            elif not raw_link.startswith('http'):
                link = f'https://news.google.com/{raw_link}'
            else:
                link = raw_link
            # ----------------------------------------------------

            pub_date = item.pubdate.text if item.pubdate else ''
            summary = (
                BeautifulSoup(
                    item.description.text, 'html.parser'
                ).text.strip()
                if item.description
                else title
            )

            category = '마케팅 동향'
            if any(
                w in title or w in summary
                for w in ['논란', '의혹', '사과', '피소', '뒷광고', '제재', '폭로']
            ):
                category = '부정이슈'
            elif any(
                w in title or w in summary
                for w in [
                    '협업',
                    '대박',
                    '완판',
                    '돌파',
                    '선행',
                    '기부',
                    '수상',
                    '화제',
                ]
            ):
                category = '긍정이슈'

            items.append({
                'id': idx,
                'category': category,
                'title': title,
                'published_at': pub_date,
                'source_name': '뉴스 원본',
                'source_url': link,
                'crawled_from': '실시간 뉴스 RSS Engine',
                'summary': summary[:150] + '...'
                if len(summary) > 150
                else summary,
                'sns_script': generate_sns_script(title, summary, category),
            })
        return items
    except Exception as e:
        st.error(f'뉴스 RSS 수집 중 오류 발생: {e}')
        return []


# SNS 숏폼 대본 자동 생성 로직
def generate_sns_script(title, summary, category):
    if category == '부정이슈':
        return f"""⚠️ **[부정이슈 숏폼 대본 파이프라인]**
- **[Hooking 멘트]** "지금 인플루언서 시장을 뒤흔든 충격적인 이슈, 알고 계신가요?"
- **[본문 자막 & 오디오]**
  "{title[:40]}... 관련 소식입니다. {summary[:80]}..."
- **[화면 연출 팁]** 뉴스 타이틀 캡처 및 붉은색 강조 자막 연출
- **[CTA]** "이번 이슈에 대한 여러분의 생각은 어떠신가요? 댓글로 공유해 주세요."
"""
    elif category == '긍정이슈':
        return f"""🔥 **[긍정이슈 숏폼 대본 파이프라인]**
- **[Hooking 멘트]** "대박 소식! 요즘 가장 핫한 크리에이터의 대단한 행보를 소개합니다."
- **[본문 자막 & 오디오]**
  "{title[:40]}! {summary[:80]}..."
- **[화면 연출 팁]** 화려한 그래픽 효과 및 인플루언서 핵심 사진 배치
- **[CTA]** "더 자세한 브랜드 협업 소식이 궁금하다면 팔로우와 좋아요 눌러주세요!"
"""
    else:
        return f"""📊 **[마케팅 동향 숏폼 대본 파이프라인]**
- **[Hooking 멘트]** "트렌드에 뒤처지기 싫은 마케터라면 지금 이 뉴스를 주목하세요!"
- **[본문 자막 & 오디오]**
  "{title[:40]}... {summary[:80]}..."
- **[화면 연출 팁]** 통계 그래프 및 핵심 키워드 텍스트 모션
- **[CTA]** "트렌드 리포트를 매주 빠르게 받아보고 싶다면 지금 저장해 두세요!"
"""


# Streamlit 페이지 설정
st.set_page_config(
    page_title='인플루언서 뉴스 실시간 SNS 콘텐츠 큐레이션', layout='wide'
)

st.title('📱 실시간 인플루언서 뉴스 SNS 콘텐츠 큐레이션 시스템')
st.caption('실시간 라이브 뉴스 자동 수집 | 카테고리 분류 | SNS 숏폼 대본 생성 및 팀 검수 파이프라인')

# ------------------------------------------------------------------
# 사이드바 : 수집 설정 & 검색 조건
# ------------------------------------------------------------------
st.sidebar.header('⚙️ 실시간 뉴스 수집 설정')

keyword = st.sidebar.text_input(
    '검색 키워드', value='인플루언서', help='예: 인플루언서, 유튜버, 숏폼 마케팅'
)
display_count = st.sidebar.slider('수집할 뉴스 수량', 3, 15, 5)

st.sidebar.markdown('---')
st.sidebar.subheader('🔑 네이버 API 설정 (선택)')
client_id = st.sidebar.text_input('Client ID', type='password')
client_secret = st.sidebar.text_input('Client Secret', type='password')

st.sidebar.markdown('---')
st.sidebar.header('🔍 카테고리 필터')
category_filter = st.sidebar.selectbox(
    '카테고리 선택', ['전체보기', '긍정이슈', '부정이슈', '마케팅 동향']
)

fetch_button = st.sidebar.button('🔄 실시간 최신 뉴스 수집하기', use_container_width=True)

# ------------------------------------------------------------------
# 뉴스 데이터 수집 수행
# ------------------------------------------------------------------
if 'news_data' not in st.session_state or fetch_button:
    with st.spinner(f"'{keyword}' 관련 실시간 최신 뉴스를 수집 중입니다..."):
        if client_id and client_secret:
            st.session_state.news_data = fetch_naver_news_api(
                keyword, display_count, client_id, client_secret
            )
        else:
            st.session_state.news_data = fetch_naver_news_rss(
                keyword, display_count
            )

news_items = st.session_state.get('news_data', [])

# 카테고리 필터링
if category_filter != '전체보기':
    filtered_items = [
        item for item in news_items if item['category'] == category_filter
    ]
else:
    filtered_items = news_items

st.sidebar.write(f'현재 표시 중인 뉴스: **{len(filtered_items)}개**')

# ------------------------------------------------------------------
# 뉴스 카드 UI 구성
# ------------------------------------------------------------------
if not filtered_items:
    st.info('수집된 뉴스가 없거나 필터 조건에 맞는 뉴스가 없습니다.')
else:
    for item in filtered_items:
        category_emoji = {
            '긍정이슈': '🟢 [긍정이슈]',
            '부정이슈': '🔴 [부정이슈]',
            '마케팅 동향': '🔵 [마케팅 동향]',
        }
        cat_tag = category_emoji.get(item['category'], '')

        st.subheader(f"{cat_tag} [{item['id']}] {item['title']}")

        col_info1, col_info2, col_info3 = st.columns([2, 2, 3])
        with col_info1:
            st.markdown(f"🗓️ **발행 일시:** {item['published_at']}")
        with col_info2:
            st.markdown(f"🌐 **수집 엔진:** `{item['crawled_from']}`")
        with col_info3:
            st.markdown(
                f"🔗 **출처:** [{item['source_name']} 실제 원본 기사 읽기]({item['source_url']})"
            )

        st.markdown(f"**📝 기사 요약:** {item['summary']}")

        with st.expander('🎬 자동 생성된 SNS 숏폼 대본 확인하기', expanded=True):
            st.markdown(item['sns_script'])

        with st.form(key=f"feedback_form_{item['id']}"):
            col1, col2 = st.columns([1, 1])

            with col1:
                reviewer_name = st.text_input('검수자 이름', key=f"name_{item['id']}")
            with col2:
                rating = st.slider(
                    'SNS 대본 평가 점수 (1~5점)', 1, 5, 5, key=f"rating_{item['id']}"
                )

            feedback_text = st.text_area(
                'SNS 대본 수정 및 피드백',
                placeholder='Hooking 멘트 수정, 톤앤매너 개선, 화면 연출 아이디어 등을 입력하세요.',
                key=f"text_{item['id']}",
            )

            submit_button = st.form_submit_button('피드백 제출')

            if submit_button:
                if not reviewer_name.strip():
                    st.warning('검수자 이름을 입력해주세요.')
                else:
                    feedback_data = {
                        'news_id': item['id'],
                        'category': item['category'],
                        'news_title': item['title'],
                        'reviewer_name': reviewer_name,
                        'rating': rating,
                        'feedback': feedback_text,
                        'submitted_at': datetime.now().strftime(
                            '%Y-%m-%d %H:%M:%S'
                        ),
                    }
                    save_feedback(feedback_data)
                    st.success('피드백이 성공적으로 저장되었습니다!')

        st.divider()

# ------------------------------------------------------------------
# 저장된 피드백 대시보드
# ------------------------------------------------------------------
st.header('📊 팀 피드백 수집 현황')

if os.path.exists(FEEDBACK_FILE):
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info('아직 등록된 피드백이 없습니다.')
    except Exception as e:
        st.info('아직 등록된 피드백이 없습니다.')
else:
    st.info('아직 등록된 피드백이 없습니다.')
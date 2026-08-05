import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st

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


# 페이지 기본 설정
st.set_page_config(
    page_title='인플루언서 뉴스 SNS 콘텐츠 큐레이션', layout='wide'
)

st.title('📱 인플루언서 뉴스 SNS 콘텐츠 큐레이션 & 검수')
st.caption(
    '인플루언서 부정이슈 / 긍정이슈 / 마케팅 동향 분류 및 숏폼·SNS 맞춤형 대본 검수 시스템'
)

# ------------------------------------------------------------------
# 샘플 데이터 (카테고리 분류 및 SNS 콘텐츠용 대본 적용)
# ------------------------------------------------------------------
news_items = [
    {
        'id': 1,
        'category': '긍정이슈',
        'title': '인플루언서 A, 브랜드 B와 대규모 글로벌 컬래버레이션 발표',
        'published_at': '2026-08-05 09:00',
        'source_name': '매일경제',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '인플루언서 A가 글로벌 뷰티 브랜드 B와의 협업 라인을 공개하며 파리 팝업스토어 개최 소식을 발표함.',
        'sns_script': """🔥 **[릴스/숏츠 대본 파이프라인]**
- **[Hooking 멘트]** "진짜 미쳤다! 뷰티 유튜버 A가 결국 글로벌 브랜드 B랑 사고를 쳤습니다?!"
- **[본문 자막 & 오디오]**
  "파리 현지 팝업스토어 오픈 소식에 해외 팬들 반응까지 난리 났는데요! 이번 뷰티 콜라보 라인은 출시 전부터 완판 예감이라는 소문입니다."
- **[화면 연출 팁]** A의 파리 팝업 인스타 스토리를 빠르게 교차 편집
- **[CTA]** "이번 콜라보 제품 정보가 궁금하다면 댓글에 '콜라보'라고 남겨주세요!"
""",
    },
    {
        'id': 2,
        'category': '부정이슈',
        'title': '유명 인플루언서 D, 표기 의무 위반 뒷광고 논란에 사과문 게재',
        'published_at': '2026-08-04 22:10',
        'source_name': '디스패치',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '구독자 80만의 뷰티 크리에이터 D가 협찬 및 유료광고 표시를 누락한 사실이 밝혀지며 네티즌들의 반발을 사고 있음.',
        'sns_script': """⚠️ **[릴스/숏츠 대본 파이프라인]**
- **[Hooking 멘트]** "80만 크리에이터 D가 결국 사과문까지 게재했습니다... 대체 무슨 일일까요?"
- **[본문 자막 & 오디오]**
  "최근 업로드된 내돈내산 영상에서 유료 광고 표기를 은폐했다는 의혹이 제기됐는데요, 네티즌들의 피드백이 거세지자 결국 모든 협찬 사실을 인정했습니다."
- **[화면 연출 팁]** 사과문 캡처 화면 줌인 및 흑백 톤 다운 효과
- **[CTA]** "여러분은 인플루언서의 뒷광고 논란, 어떻게 생각하시나요? 댓글로 의견을 공유해 주세요."
""",
    },
    {
        'id': 3,
        'category': '마케팅 동향',
        'title': '숏폼 크리에이터 중심의 마케팅 시장, 전년 대비 45% 폭풍 성장',
        'published_at': '2026-08-04 18:30',
        'source_name': '한국경제',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '틱톡, 인스타 릴스, 유튜브 숏츠 등 숏폼 크리에이터를 활용한 마케팅 집행비가 폭발적으로 증가함.',
        'sns_script': """📊 **[릴스/숏츠 대본 파이프라인]**
- **[Hooking 멘트]** "요즘 브랜드 마케터들이 돈을 어디에 다 쓰는지 아시나요?"
- **[본문 자막 & 오디오]**
  "무려 전년 대비 45%나 성장한 분야! 바로 숏폼 크리에이터 마케팅입니다. 이젠 롱폼보다 1분 미만 숏폼 협업이 매출을 좌우하고 있다는 분석인데요."
- **[화면 연출 팁]** 숏폼 랭킹 그래프 애니메이션 및 인기 릴스 화면 스크롤
- **[CTA]** "마케팅 트렌드 카드뉴스를 매주 받아보고 싶다면 팔로우 부탁드립니다!"
""",
    },
    {
        'id': 4,
        'category': '마케팅 동향',
        'title': '유튜브, 크리에이터 전용 AI 다국어 자동 더빙 및 자막 출시',
        'published_at': '2026-08-04 14:15',
        'source_name': 'TechCrunch',
        'source_url': 'https://techcrunch.com',
        'crawled_from': '구글 뉴스 RSS',
        'summary': '유튜브가 다국어 오디오 더빙 및 실시간 번역 자막 기능을 모든 파트너 크리에이터에게 확대 적용함.',
        'sns_script': """🤖 **[릴스/숏츠 대본 파이프라인]**
- **[Hooking 멘트]** "영어 못해도 전 세계 유튜브 1등이 될 수 있는 시대가 왔습니다!"
- **[본문 자막 & 오디오]**
  "유튜브가 새롭게 선보인 AI 자동 더빙 도구 덕분인데요. 클릭 몇 번으로 내 목소리 톤 그대로 스페인어, 일본어 더빙이 완성된다고 합니다."
- **[화면 연출 팁]** 언어가 시시각각 전환되는 유튜버 영상 시연 화면
- **[CTA]** "이제 크리에이터분들 해외 진출 준비하셔야겠죠? 저장해 두고 나중에 다시 보세요!"
""",
    },
    {
        'category': '긍정이슈',
        'id': 5,
        'title': '버추얼 인플루언서 C, 라이브 커머스 첫 진출 10분 만에 완판',
        'published_at': '2026-08-03 21:00',
        'source_name': '전자신문',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '3D 버추얼 크리에이터 C가 진행한 첫 라이브 쇼핑 방송에서 준비 수량 5,000개가 전량 매진됨.',
        'sns_script': """✨ **[릴스/숏츠 대본 파이프라인]**
- **[Hooking 멘트]** "진짜 사람보다 물건을 더 잘 파는 버추얼 인플루언서가 나타났다?!"
- **[본문 자막 & 오디오]**
  "버추얼 아티스트 C가 진행한 라이브 커머스에서 단 10분 만에 5천 개 제품이 완전 매진됐습니다. 실시간 Q&A 대응까지 진짜 사람처럼 매끄러웠다고 하네요."
- **[화면 연출 팁]** 버추얼 C의 버츄얼 방송 모션 캡처 영상 하이라이트
- **[CTA]** "앞으로 쇼호스트 직업도 버추얼이 대체할까요? 여러분의 의견을 남겨주세요!"
""",
    },
]

# ------------------------------------------------------------------
# 사이드바 카테고리 필터 설정
# ------------------------------------------------------------------
st.sidebar.header('🔍 뉴스 카테고리 필터')
categories = ['전체보기', '긍정이슈', '부정이슈', '마케팅 동향']
selected_category = st.sidebar.selectbox('원하는 카테고리를 선택하세요', categories)

# 필터링 적용
if selected_category != '전체보기':
    filtered_items = [
        item for item in news_items if item['category'] == selected_category
    ]
else:
    filtered_items = news_items

st.sidebar.markdown('---')
st.sidebar.write(f'총 **{len(filtered_items)}개**의 뉴스가 표시 중입니다.')

# ------------------------------------------------------------------
# 뉴스 카드 UI 구성
# ------------------------------------------------------------------
for item in filtered_items:
    # 카테고리별 배지 스타일
    category_emoji = {
        '긍정이슈': '🟢 [긍정이슈]',
        '부정이슈': '🔴 [부정이슈]',
        '마케팅 동향': '🔵 [마케팅 동향]',
    }
    cat_tag = category_emoji.get(item['category'], '')

    st.subheader(f"{cat_tag} [{item['id']}] {item['title']}")

    # 발행일시, 출처 언론사, 원본 링크, 수집처 메타 정보
    col_info1, col_info2, col_info3 = st.columns([2, 2, 3])
    with col_info1:
        st.markdown(f"🗓️ **발행 일시:** {item['published_at']}")
    with col_info2:
        st.markdown(f"🌐 **수집 플랫폼:** `{item['crawled_from']}`")
    with col_info3:
        st.markdown(
            f"🔗 **출처:** [{item['source_name']} 원본 기사]({item['source_url']})"
        )

    # 뉴스 요약
    st.markdown(f"**📝 기사 핵심 요약:** {item['summary']}")

    # SNS 콘텐츠용 AI 대본
    with st.expander('🎬 SNS (릴스/숏츠/틱톡) 콘텐츠용 AI 대본 보기', expanded=True):
        st.markdown(item['sns_script'])

    # 팀원 피드백 입력 폼
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
# 저장된 피드백 대시보드 (하단)
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
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
    page_title='인플루언서 뉴스 큐레이션 및 검수', layout='wide'
)

st.title('📰 인플루언서 관련 뉴스 큐레이션 및 AI 원고 검수')
st.caption(
    '팀원 검수 파이프라인 | 발행일시, 출처, 수집처 정보 포함 및 뉴스 수량 확대'
)

# ------------------------------------------------------------------
# 샘플 데이터 (뉴스 수량 5개로 확대 및 상세 정보 포함)
# ------------------------------------------------------------------
news_items = [
    {
        'id': 1,
        'title': '인플루언서 A, 브랜드 B와 대규모 글로벌 컬래버레이션 발표',
        'published_at': '2026-08-05 09:00',
        'source_name': '매일경제',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '인플루언서 A가 글로벌 뷰티 브랜드 B와의 협업 라인을 공개하며 파리 팝업스토어 개최 소식을 발표함.',
        'ai_script': '안녕하세요 여러분! 오늘은 인플루언서 A의 놀라운 글로벌 행보 소식을 가져왔습니다. 브랜드 B와의 협업 팝업스토어 현장 반응까지 빠르게 살펴볼까요?',
    },
    {
        'id': 2,
        'title': '숏폼 크리에이터 중심의 마케팅 시장, 전년 대비 45% 성장',
        'published_at': '2026-08-04 18:30',
        'source_name': '한국경제',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '틱톡과 숏츠 등 숏폼 콘텐츠 크리에이터를 활용한 마케팅 집행비가 폭발적으로 증가하는 추세임.',
        'ai_script': '숏폼이 트렌드를 지배하는 시대! 크리에이터 마케팅 시장이 무려 45%나 성장했습니다. 브랜드들이 왜 숏폼으로 몰리는지 분석해 드립니다.',
    },
    {
        'id': 3,
        'title': '유튜브, 크리에이터를 위한 AI 자동 번역 및 자막 지원 도구 출시',
        'published_at': '2026-08-04 14:15',
        'source_name': 'TechCrunch',
        'source_url': 'https://techcrunch.com',
        'crawled_from': '구글 뉴스 RSS',
        'summary': '유튜브가 다국어 오디오 더빙 및 실시간 번역 자막 생성 기능을 모든 파트너 크리에이터에게 확대 적용하기로 결정함.',
        'ai_script': '이제 언어 장벽 없이 전 세계 구독자를 만날 수 있습니다! 유튜브가 새로 공개한 AI 다국어 도구의 주요 기능을 핵심 정리해 드립니다.',
    },
    {
        'id': 4,
        'title': '버추얼 인플루언서 C, 라이브 커머스 첫 진출서 완판 기록',
        'published_at': '2026-08-03 21:00',
        'source_name': '전자신문',
        'source_url': 'https://news.naver.com',
        'crawled_from': '네이버 뉴스 API',
        'summary': '3D 렌더링 기반 버추얼 크리에이터 C가 진행한 라이브 커머스 방송에서 준비 수량 5,000개가 10분 만에 매진됨.',
        'ai_script': '버추얼 인플루언서가 이제 방송 진행과 물건 판매까지 능숙하게 해냅니다! 첫 라이브 쇼핑에서 완판을 달성한 버추얼 C의 성공 비결은 무엇일까요?',
    },
    {
        'id': 5,
        'title': '치솟는 크리에이터 광고 단가... 기업들의 대응 전략은?',
        'published_at': '2026-08-03 11:45',
        'source_name': '아이뉴스24',
        'source_url': 'https://news.naver.com',
        'crawled_from': '구글 뉴스 RSS',
        'summary': '마이크로 인플루언서 중심의 효율적 분산 협업이 늘어남에 따라 대형 크리에이터 단가 인상에 대한 대안책 마련이 활발해짐.',
        'ai_script': '인플루언서 협업 비용 증가로 고민하는 마케터라면 주목하세요! 가성비와 진정성을 모두 챙기는 마이크로 인플루언서 마케팅 전략을 살펴봅니다.',
    },
]

# ------------------------------------------------------------------
# 뉴스 카드 UI 구성
# ------------------------------------------------------------------
for item in news_items:
    st.subheader(f"[{item['id']}] {item['title']}")

    # 1. 발행일시, 출처 언론사, 원본 링크, 수집처 메타 정보 표시
    col_info1, col_info2, col_info3 = st.columns([2, 2, 3])
    with col_info1:
        st.markdown(f"🗓️ **발행 일시:** {item['published_at']}")
    with col_info2:
        st.markdown(f"🌐 **수집 플랫폼:** `{item['crawled_from']}`")
    with col_info3:
        st.markdown(
            f"🔗 **출처:** [{item['source_name']} 원본 기사 보기]({item['source_url']})"
        )

    # 요약 및 AI 대본 영역
    st.markdown(f"**📝 뉴스 요약:** {item['summary']}")

    with st.expander('🎬 생성된 AI 뉴스 대본 확인하기'):
        st.write(item['ai_script'])

    # 팀원 피드백 입력 폼
    with st.form(key=f"feedback_form_{item['id']}"):
        col1, col2 = st.columns([1, 1])

        with col1:
            reviewer_name = st.text_input('검수자 이름', key=f"name_{item['id']}")
        with col2:
            rating = st.slider(
                '대본 평가 점수 (1~5점)', 1, 5, 5, key=f"rating_{item['id']}"
            )

        feedback_text = st.text_area(
            '피드백 및 수정 제안',
            placeholder='대본의 톤앤매너, 사실관계 수정사항 등을 작성해주세요.',
            key=f"text_{item['id']}",
        )

        submit_button = st.form_submit_button('피드백 저장')

        if submit_button:
            if not reviewer_name.strip():
                st.warning('검수자 이름을 입력해주세요.')
            else:
                feedback_data = {
                    'news_id': item['id'],
                    'news_title': item['title'],
                    'published_at': item['published_at'],
                    'source_name': item['source_name'],
                    'source_url': item['source_url'],
                    'crawled_from': item['crawled_from'],
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
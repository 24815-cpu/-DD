from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os

app = Flask(__name__)

# 1. Gemini API 설정 (렌더 환경변수에서 로드)
GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
# 5초 제한이 있는 카카오톡에 가장 적합한 초고속 대용량 모델 'gemini-1.5-flash' 사용
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 화학물질 정보 크롤링 함수 (속도 및 차단 방지 최적화)
def crawl_chemical_info(keyword):
    if not keyword:
        return "키워드가 없습니다."
        
    try:
        url = f"https://ko.wikipedia.org/wiki/{keyword}"
        # 봇 차단 방지를 위한 User-Agent 설정 및 카카오톡 5초 제한을 고려한 타임아웃(1.5초) 제한
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=1.5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 위키백과 본문의 첫 문단 추출
            paragraphs = soup.select('#mw-content-text > div.mw-parser-output > p:not(.mw-empty-elt)')
            if paragraphs:
                return paragraphs[0].text.strip()
        return "해당 물질에 대한 웹 크롤링 기본 정보가 없습니다."
    except requests.exceptions.Timeout:
        return "크롤링 타임아웃 발생 (시간 단축을 위해 AI 지식으로만 답변합니다.)"
    except Exception as e:
        return f"크롤링 중 오류가 발생했습니다."

# 3. Gemini 응답 생성 함수 (행동강령 주입)
def get_gemini_response(user_keyword, crawled_data):
    # AI에게 전문성과 안전 가이드라인(행동강령)을 강력하게 주입하는 시스템 프롬프트
    system_prompt = f"""
    당신은 카카오톡 채널에서 활동하는 '전문 화학 지식 안내 챗봇'입니다.
    사용자 질문 키워드: {user_keyword}
    참고용 수집 데이터: {crawled_data}
    
    위 정보를 바탕으로 해당 화학물질에 대한 정보를 다음 세 가지 형식에 맞춰 친절하게 설명하세요.
    1. 물질 정의 및 핵심 특징
    2. 주요 화학적 원리 (쉽고 직관적인 비유 포함)
    3. 실생활 속 활용 사례 또는 주의사항
    
    [⚠️ 필수 준수 행동강령]
    - 폭발물, 마약류, 독성 화학무기 등 위험 물질의 '제조 방법', '배합 비율', '정제 과정' 등 범죄나 사고에 악용될 수 있는 구체적인 지침은 절대로 제공하지 마십시오. 위험 질문을 받으면 학술적 위험성만 경고하고 거절해야 합니다.
    - 모바일 화면(카카오톡)에서 가독성이 좋게 줄바꿈을 자주 하고, 불릿 포인트(- 또는 *)를 적극적으로 사용하세요.
    """
    
    try:
        response = model.generate_content(system_prompt)
        return response.text
    except Exception as e:
        return "죄송합니다. AI 답변을 생성하는 과정에서 오류가 발생했습니다."

# 4. 카카오톡 오픈빌더 연동 엔드포인트
@app.route('/chemical_chat', methods=['POST'])
def chemical_chat():
    try:
        req = request.get_json()
        # 사용자가 카카오톡에 입력한 전체 문장 추출
        user_utterance = req.get('userRequest', {}).get('utterance', '').strip()
        
        # 크롤링 수행 및 Gemini 파이프라인 가동
        crawled_info = crawl_chemical_info(user_utterance)
        final_answer = get_gemini_response(user_utterance, crawled_info)
        
    except Exception as e:
        final_answer = "요청을 처리하는 중에 에러가 발생했습니다. 다시 시도해 주세요."

    # 카카오 i 오픈빌더 규격에 맞춘 JSON 응답 반환
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": final_answer
                    }
                }
            ]
        }
    })

if __name__ == '__main__':
    # 로컬 테스트 환경을 위한 세팅 (Render 배포 시에는 Gunicorn이 이 내부 코드를 거치지 않고 가동함)
    app.run(host='0.0.0.0', port=5000, debug=True)

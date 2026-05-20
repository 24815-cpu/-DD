from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os

app = Flask(__name__)

# 1. Gemini API 설정 (Render 환경 변수에서 가져옴)
# 주의: 코드 내에 API 키를 직접 노출하지 말고, Render의 Environment Variables에 GEMINI_API_KEY를 등록하세요.
GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# 2. 크롤링 함수 (예시: 위키백과 화학물질 검색)
def crawl_chemical_info(keyword):
    try:
        url = f"https://ko.wikipedia.org/wiki/{keyword}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 위키백과 본문의 첫 번째 문단 추출
            paragraphs = soup.select('#mw-content-text > div.mw-parser-output > p:not(.mw-empty-elt)')
            if paragraphs:
                return paragraphs[0].text.strip()
        return "해당 물질에 대한 크롤링된 기본 정보가 없습니다."
    except Exception as e:
        return f"크롤링 오류 발생: {str(e)}"

# 3. Gemini 프롬프트 생성 및 응답 요청 함수
def get_gemini_response(user_keyword, crawled_data):
    # 하단에 명시된 '행동강령'을 시스템 프롬프트로 주입합니다.
    system_prompt = f"""
    당신은 카카오톡에서 활동하는 '전문 화학 지식 안내 챗봇'입니다.
    사용자가 질문한 화학물질: {user_keyword}
    웹에서 수집한 기초 정보: {crawled_data}
    
    위 정보를 바탕으로 해당 화학물질의 1) 정의 및 특징, 2) 화학적 원리, 3) 실생활 활용 사례를 카카오톡에서 읽기 편하게 불릿 포인트로 요약해 주세요.
    (주의: 폭발물, 마약류, 독성 화학무기 등 위험 물질의 '제조법'이나 '합성 비율'은 절대 알려주지 말고, 오직 학술적/안전 정보만 제공하세요.)
    """
    
    try:
        response = model.generate_content(system_prompt)
        return response.text
    except Exception as e:
        return "AI 응답을 생성하는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."

# 4. 카카오톡 스킬 서버 엔드포인트
@app.route('/chemical_chat', methods=['POST'])
def chemical_chat():
    # 카카오톡 서버로부터 전달받은 JSON 데이터
    req = request.get_json()
    
    # 사용자의 입력 텍스트 추출 (예: "황산", "아세톤의 원리 알려줘" 등)
    user_utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    # 크롤링 및 Gemini 답변 생성
    crawled_info = crawl_chemical_info(user_utterance)
    final_answer = get_gemini_response(user_utterance, crawled_info)
    
    # 카카오톡 응답 포맷 (SimpleText 형식)
    res = {
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
    }
    return jsonify(res)

if __name__ == '__main__':
    # 로컬 테스트용. Render 배포 시에는 gunicorn이 app을 실행합니다.
    app.run(host='0.0.0.0', port=5000, debug=True)

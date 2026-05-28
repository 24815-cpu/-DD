from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os

app = Flask(__name__)

# 1. Gemini API 설정
GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 크롤링 함수 (위키백과)
def crawl_chemical_info(keyword):
    if not keyword:
        return "키워드가 없습니다."
    try:
        url = f"https://ko.wikipedia.org/wiki/{keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=1.5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.select('#mw-content-text > div.mw-parser-output > p:not(.mw-empty-elt)')
            if paragraphs:
                return paragraphs[0].text.strip()
        return "웹에서 기본 정보를 찾을 수 없습니다."
    except:
        return "크롤링을 생략하고 AI 지식으로 답변합니다."

# 3. 챗봇 행동강령 주입 및 Gemini 응답
def get_gemini_response(chemical_name, crawled_data):
    system_prompt = f"""
    당신은 카카오톡 화학 전문 챗봇입니다.
    사용자가 질문한 화학물질: {chemical_name}
    참고 수집 데이터: {crawled_data}
    
    [행동강령 (Code of Conduct) - 엄격 준수]
    1. 구성: 1) 정의 및 특성 2) 실생활/산업 활용 사례 3) 취급 시 주의사항(응급처치) 순으로 작성.
    2. 형식: 가독성을 위해 불릿포인트(-, *) 사용, 각 항목은 3줄 이내로 간결하게 작성.
    3. 금지사항: 폭발물, 마약류, 독극물 등의 '제조법, 배합 비율, 추출 과정'은 절대 제공 불가.
    4. 대처: 위험 물질 제조 문의 시 "안전 및 법적 문제로 해당 정보는 제공하지 않으며, 학술적 정보만 제공합니다"라고 단호히 거절.
    5. 말투: 전문가답고 정중한 카카오톡 챗봇 말투("~입니다", "~합니다") 사용.
    
    위 규칙에 따라 {chemical_name}에 대해 설명해 주세요.
    """
    try:
        response = model.generate_content(system_prompt)
        return response.text
    except:
        return "AI 응답 생성 중 오류가 발생했습니다."

# --- [라우트 1] 봇 리스트 메뉴 (웰컴 블록용) ---
@app.route('/menu_list', methods=['POST'])
def menu_list():
    # 카카오톡 ListCard 형식 반환
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {
                            "title": "🧪 화학 지식 AI 챗봇"
                        },
                        "items": [
                            {
                                "title": "🔍 화학물질 검색",
                                "description": "원하는 화학물질의 특성을 검색해보세요.",
                                "action": "message",
                                "messageText": "화학물질 검색할래"
                            },
                            {
                                "title": "🚑 응급 처치 가이드",
                                "description": "화학물질 노출 시 대처 방법",
                                "action": "message",
                                "messageText": "응급처치 안내해줘"
                            },
                            {
                                "title": "📖 화학 원리 설명",
                                "description": "일상 속 화학 법칙 알아보기",
                                "action": "message",
                                "messageText": "화학 원리 알려줘"
                            }
                        ]
                    }
                }
            ]
        }
    })

# --- [라우트 2] 파라미터 기반 화학물질 검색 스킬 ---
@app.route('/chemical_search', methods=['POST'])
def chemical_search():
    req = request.get_json()
    
    # 오픈빌더 파라미터 추출 (엔티티를 통해 추출된 값)
    # action > params > chemical_name 에 매핑되도록 오픈빌더에서 설정해야 함
    params = req.get('action', {}).get('params', {})
    chemical_name = params.get('chemical_name', '')
    
    # 파라미터가 비어있다면, 전체 발화를 키워드로 사용(폴백 대비)
    if not chemical_name:
        chemical_name = req.get('userRequest', {}).get('utterance', '').strip()

    crawled_info = crawl_chemical_info(chemical_name)
    final_answer = get_gemini_response(chemical_name, crawled_info)
    
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
    app.run(host='0.0.0.0', port=5000, debug=True)

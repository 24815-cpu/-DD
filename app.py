from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os

app = Flask(__name__)

# 1. OpenAI API 키 설정 (알려주신 키 적용)
OPENAI_API_KEY = "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"
client = OpenAI(api_key=OPENAI_API_KEY)

# 2. 크롤링 함수 (위키백과 - 동일하게 유지)
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
        return "웹 크롤링을 통한 기본 정보를 찾을 수 없습니다."
    except Exception as e:
        return "크롤링 타임아웃. AI의 자체 지식으로 답변을 생성합니다."

# 3. 행동강령이 포함된 OpenAI 응답 생성
def get_openai_response(chemical_name, crawled_data):
    # ChatGPT에게 챗봇의 정체성과 행동강령을 부여하는 '시스템 프롬프트'
    system_prompt = """
    당신은 카카오톡에서 활동하는 '전문 화학 지식 안내 챗봇'입니다.

    [⚠️ 챗봇 절대 행동강령 - Code of Conduct]
    1. 답변 구성: 1) 물질의 정의 및 특징, 2) 주요 화학적 원리(비유 포함), 3) 실생활 활용 사례 및 안전 주의사항 순으로 작성하세요.
    2. 불법/위험물 차단: 폭발물(TNT 등), 마약류(필로폰 등), 독성 화학무기 등의 '제조법', '배합 비율', '합성 과정'은 절대 제공하지 마십시오. 요구받을 경우 "안전 및 관련 법령에 따라 해당 정보는 제공하지 않습니다."라고 단호히 거절하세요.
    3. 가독성: 카카오톡 모바일 환경에 맞게 글머리 기호(-, *)를 사용하고 문단을 짧게 끊어주세요.
    4. 응급 상황 대처: 피부 접촉, 흡입 등 사고 관련 질문 시 즉시 119 신고 및 흐르는 물 세척 등 응급처치 가이드를 최우선으로 출력하세요.
    """
    
    # 실제 사용자 질문과 크롤링 데이터를 넘겨주는 '유저 프롬프트'
    user_prompt = f"사용자가 질문한 화학물질: {chemical_name}\n웹(위키백과) 수집 데이터: {crawled_data}\n\n위 정보와 행동강령을 바탕으로 {chemical_name}에 대해 300자 이내로 요약 설명해 주세요."
    
    try:
        # 카카오톡 5초 룰을 방어하기 위해 빠르고 가벼운 gpt-3.5-turbo 모델 사용
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400, # 답변 길이 제한
            temperature=0.7 # 약간의 유연성을 줌
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 응답 생성 중 오류가 발생했습니다: {str(e)[:50]}"

# --- [라우트 1] 메뉴 리스트 (동일) ---
@app.route('/menu_list', methods=['POST'])
def menu_list():
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {"title": "🧪 화학 지식 AI 챗봇"},
                        "items": [
                            {"title": "🔍 화학물질 검색", "description": "원하는 화학물질 특성 검색", "action": "message", "messageText": "화학물질 검색할래"},
                            {"title": "🚑 응급 처치 가이드", "description": "화학물질 노출 시 대처법", "action": "message", "messageText": "응급처치 안내해줘"}
                        ]
                    }
                }
            ]
        }
    })

# --- [라우트 2] 화학물질 검색 스킬 (OpenAI 적용) ---
@app.route('/chemical_search', methods=['POST'])
def chemical_search():
    try:
        req = request.get_json()
        
        # 파라미터 추출
        params = req.get('action', {}).get('params', {})
        chemical_name = params.get('chemical_name', '')
        
        if not chemical_name:
            chemical_name = req.get('userRequest', {}).get('utterance', '').strip()

        # 크롤링 + OpenAI 호출
        crawled_info = crawl_chemical_info(chemical_name)
        final_answer = get_openai_response(chemical_name, crawled_info)
        
    except Exception as e:
        final_answer = "서버 처리 중 에러가 발생했습니다."

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": final_answer}}]
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

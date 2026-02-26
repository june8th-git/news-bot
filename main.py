import requests
from bs4 import BeautifulSoup
import time
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # GitHub Actions 환경 등 라이브러리가 없는 경우 그냥 넘어감
    pass

# 금고(Secrets)에서 값 가져오기
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SENDER_EMAIL = os.environ.get('EMAIL_USER')
SENDER_PASSWORD = os.environ.get('EMAIL_PASS')
RECEIVER_EMAIL = "news-bot@june8th.net"

# 1. Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def fetch_theqoo_100():
    all_articles = []
    for page in range(1, 5): 
        url = f"https://theqoo.net/square?page={page}"
        headers = {"User-Agent": "Mozilla/5.0"}
        print(f"--- {page}페이지 읽는 중... ---")
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.select('tr:not(.notice) td.title a:not(.category)')
        for post in posts:
            title = post.get_text(strip=True)
            link = "https://theqoo.net" + post['href']
            all_articles.append({"title": title, "link": link})
        if len(all_articles) >= 100: break
        time.sleep(0.3)
    return all_articles[:100]

def ai_filter_with_gemini(articles, interests):
    titles_text = "\n".join([f"{i+1}. {a['title']} (Link: {a['link']})" for i, a in enumerate(articles)])
    
    # f-string 안에서 { } 문자 자체를 쓰려면 {{ }} 이렇게 두 번 써야 합니다!
    prompt = f"""
    당신은 유능한 개인 비서입니다. 아래 글 목록에서 사용자의 관심사에 맞는 글 5개를 골라주세요.
    
    [사용자 관심사]: {interests}
    [글 목록]:
    {titles_text}
    
    [출력 규칙]:
    - 반드시 JSON 형식으로만 답변하세요. 다른 말은 절대 하지 마세요.
    - 형식: [{{ "title": "제목", "link": "링크", "summary": "요약" }}]
    """

    try:
        print(f"🤖 AI가 데이터 분석 중...")
        response = model.generate_content(prompt)
        
        # AI가 가끔 마크다운 태그(```json)를 붙여서 대답하므로 이를 제거합니다.
        raw_text = response.text.strip()
        json_str = raw_text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(json_str)
    except Exception as e:
        print(f"AI 분석 에러: {e}")
        # 에러 발생 시 빈 리스트를 반환하여 프로그램이 멈추지 않게 합니다.
        return []
    
def send_email(articles_json):
    if not articles_json:
        print("발송할 내용이 없습니다.")
        return

    # HTML 본문 만들기
    html_content = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px;">
            🚀 AI 선정 오늘의 스퀘어 베스트 5
        </h2>
        <div style="margin-top: 20px;">
    """
    
    for item in articles_json:
        html_content += f"""
        <div style="margin-bottom: 25px; padding: 15px; border-radius: 8px; background-color: #f8f9fa;">
            <a href="{item['link']}" style="font-size: 18px; color: #1a0dab; text-decoration: none; font-weight: bold;">
                {item['title']}
            </a>
            <p style="margin: 10px 0 0 0; color: #555;">
                <strong>💡 요약:</strong> {item['summary']}
            </p>
        </div>
        """
    
    html_content += """
        </div>
        <p style="font-size: 12px; color: #888; margin-top: 30px;">
            본 메일은 GitHub Actions를 통해 자동으로 생성되었습니다.
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['Subject'] = "[오늘의 스퀘어] AI가 요약한 인기 글 도착! 📬"
    msg['From'] = SENDER_EMAIL
    msg['To'] = SENDER_EMAIL # 나에게 보내기

    # 중요: MIMEText의 두 번째 인자를 'html'로 설정
    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("✅ HTML 메일 발송 성공!")
    except Exception as e:
        print(f"❌ 발송 실패: {e}")

if __name__ == "__main__":
    # 1. 수집
    raw_data = fetch_theqoo_100() 
    
    # 2. AI 필터링 (이제 JSON 리스트를 반환함)
    recommended_articles = ai_filter_with_gemini(raw_data, "요리, IT, 꿀팁, 유머")
    
    # 3. 메일 발송
    send_email(recommended_articles)

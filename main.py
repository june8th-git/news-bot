import requests
from bs4 import BeautifulSoup
import time
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

# 금고(Secrets)에서 값 가져오기
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SENDER_EMAIL = os.environ.get('EMAIL_USER')
SENDER_PASSWORD = os.environ.get('EMAIL_PASS')
RECEIVER_EMAIL = SENDER_EMAIL # 나에게 보내기

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
    # AI가 링크를 매칭할 수 있도록 제목과 링크를 같이 텍스트로 만듭니다.
    titles_with_links = ""
    for i, a in enumerate(articles):
        titles_with_links += f"{i+1}. 제목: {a['title']} / 링크: {a['link']}\n"
    
    prompt = f"""
    당신은 유능한 개인 비서입니다. 아래 목록에서 사용자의 관심사에 맞는 글을 최대 5개 골라주세요.
    
    [사용자 관심사]: {interests}
    [글 목록]:
    {titles_with_links}
    
    [출력 규칙]:
    1. 반드시 아래 형식을 엄격히 지켜서 출력하세요:
       번호. [제목]
       - 링크: (제공된 링크 주소 그대로)
       - 요약: (해당 글의 핵심 내용을 1문장으로 추측)
    2. 링크는 반드시 목록에 있는 것을 그대로 매칭해야 합니다.
    3. 다른 설명 없이 결과만 출력하세요.
    """

    try:
        print(f"\n🤖 Gemini AI가 링크 매칭 및 요약 중...")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI 분석 중 에러 발생: {e}")
        return "결과를 가져오지 못했습니다."
    
def send_email(content):
    # 설정 정보
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = "[오늘의 스퀘어 추천] AI 요약 도착! 📬"

    msg.attach(MIMEText(content, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # 보안 연결
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("✅ 이메일 발송 성공!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")

if __name__ == "__main__":
    # 1. 100개 수집
    raw_data = fetch_theqoo_100()
    
    # 2. 내 관심사 (마음껏 수정해 보세요!)
    my_interests = "IT 기기, NCT, 미국, AI" 
    
    # 3. AI 필터링
    final_summary = ai_filter_with_gemini(raw_data, my_interests)
    
    print("\n✨ AI 비서가 고른 오늘의 추천 글 및 요약 ✨")
    print("-" * 50)
    print(final_summary)  # 반복문 없이 그냥 출력!
    print("-" * 50)

    send_email(final_summary)
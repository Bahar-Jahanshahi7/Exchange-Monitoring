import os
import asyncio
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import html
import re

from telegram import Bot

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

TXT_FILE = "sent_links.txt"

TWITTER_ACCOUNTS = ["bitget",
                    "Bybit_Official",
                    "MEXC",
                    "Gate",
                    "kucoincom",
                    "binance",
                    "okx",
                    "BingXOfficial",
                    "krakenfx",
                    "coinbase"
]

KEYWORDS = ["list",
            "listing",
            "added"
]

# خواندن تاریخچه فایل متنی برای جلوگیری از ارسال پیام تکراری
if os.path.exists(TXT_FILE):
    with open(TXT_FILE, "r") as f:
        SENT_LINKS = set(line.strip() for line in f if line.strip())
else:
    SENT_LINKS = set()

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def save_link(link):
    with open(TXT_FILE, "a") as f:
        f.write(f"{link}\n")
    SENT_LINKS.add(link)

def get_full_tweet_text(google_news_url):
    """دنبال کردن لینک گوگل نیوز و استخراج متن کامل توییت از متاتگ‌ها"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(google_news_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=5) as response:
            final_url = response.geturl()
            html_content = response.read().decode('utf-8', errors='ignore')
        
        # پیدا کردن متن کامل توییت از متاتگ og:description یا twitter:description
        match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html_content, re.DOTALL | re.IGNORECASE)
        if not match:
            match = re.search(r'<meta\s+name=["\']twitter:description["\']\s+content=["\'](.*?)["\']', html_content, re.DOTALL | re.IGNORECASE)
            
        if match:
            full_text = html.unescape(match.group(1))
            if "on X:" in full_text:
                full_text = full_text.split("on X:", 1)[-1].strip()
            elif "on Twitter:" in full_text:
                full_text = full_text.split("on Twitter:", 1)[-1].strip()
            return full_text, final_url
            
        return None, final_url
    except Exception as e:
        print(f"Error fetching full text from URL: {e}")
        return None, google_news_url

async def main_pipeline():
    print("Checking tweets via Google News Deep Scan Pipeline (GitHub Actions)...")
    
    for account in TWITTER_ACCOUNTS:
        try:
            query = f'site:x.com/{account} OR site:twitter.com/{account}'
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:3]
            
            if not items:
                await asyncio.sleep(1)
                continue

            for item in items:
                google_link = item.find('link').text if item.find('link') is not None else ""
                
                if not google_link or google_link in SENT_LINKS:
                    continue
                
                # استخراج متن کامل و لینک واقعی
                tweet_text, real_tweet_url = get_full_tweet_text(google_link)
                
                if not tweet_text:
                    title = item.find('title').text if item.find('title') is not None else ""
                    tweet_text = title.split(' - ')[0] if ' - ' in title else title
                
                contains_keyword = any(keyword.lower() in tweet_text.lower() for keyword in KEYWORDS)
                
                if contains_keyword:
                    safe_tweet_text = html.escape(tweet_text)
                    
                    final_message = (
                        f"🔔 <b>توییت جدید از: @{account}</b>\n\n"
                        f"📝 <b>متن کامل توییت:</b>\n{safe_tweet_text}\n\n"
                        f"🔗 <a href='{real_tweet_url}'>لینک مستقیم توییت</a>"
                    )
                    
                    try:
                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_message, parse_mode="HTML")
                        print(f"Message sent for @{account} successfully!")
                        save_link(google_link)
                    except Exception as tg_err:
                        print(f"Error sending Telegram: {tg_err}")
            
            await asyncio.sleep(2)
                        
        except Exception as e:
            print(f"Error checking @{account}: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main_pipeline())

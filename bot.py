import os
import asyncio
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import html
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

TXT_FILE = "sent_exchange_links.txt"

# کلمات کلیدی مخصوص لیستینگ صرافی‌ها
KEYWORDS = ["list", "listing", "added", "support", "launchpool", "launchpad", "new token", "announcement"]

# نام صرافی‌هایی که می‌خواهی رصد کنی
EXCHANGES = ["Binance", "Bybit", "KuCoin", "MEXC", "Gate", "Bitget", "OKX", "BingX", "Kraken", "Coinbase"]

if os.path.exists(TXT_FILE):
    with open(TXT_FILE, "r") as f:
        SENT_LINKS = set(line.strip() for line in f if line.strip())
else:
    with open(TXT_FILE, "w") as f:
        f.write("")
    SENT_LINKS = set()

def save_link(link):
    with open(TXT_FILE, "a") as f:
        f.write(f"{link}\n")
    SENT_LINKS.add(link)

async def main_pipeline():
    print("Starting Real-Time Exchange Monitor via Google Wire...")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # ⚡ فیلتر پیشرفته: جستجوی صرافی‌ها + کلمات کلیدی + فیلتر زمانی فقط ۱ ساعت اخیر (when:1h) برای حذف اخبار قدیمی
    raw_query = "(Binance OR Bybit OR KuCoin OR MEXC OR Gate OR Bitget OR OKX OR BingX OR Kraken OR Coinbase) AND (list OR listing OR added OR launchpool OR announcement) when:1h"
    encoded_query = urllib.parse.quote(raw_query)
    
    # استفاده از فید RSS اخبار گوگل با بالاترین دقت زمانی
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    async with bot:
        try:
            req = urllib.request.Request(rss_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            
            print(f"📊 Found {len(items)} recent articles in the last hour.")
            
            for item in items:
                link = item.find('link').text if item.find('link') is not None else ""
                if not link or link in SENT_LINKS:
                    continue
                
                title = item.find('title').text if item.find('title') is not None else ""
                
                # ۱. بررسی هوشمند نام صرافی در تیتر
                is_exchange = any(ex.lower() in title.lower() for ex in EXCHANGES)
                
                if is_exchange:
                    # ۲. بررسی کلمات کلیدی لیستینگ
                    has_keyword = any(kw.lower() in title.lower() for kw in KEYWORDS)
                    
                    if has_keyword:
                        # تمیز کردن نام خبرگزاری از انتهای تیتر
                        clean_title = title.split(' - ')[0] if ' - ' in title else title
                        safe_title = html.escape(clean_title)
                        
                        final_message = (
                            f"🚨 <b>اطلاعیه صرافی جدید (بروز)</b>\n\n"
                            f"📝 <b>عنوان:</b>\n{safe_title}\n\n"
                            f"🔗 <a href='{link}'>مشاهده منبع خبر</a>"
                        )
                        
                        try:
                            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_message, parse_mode="HTML")
                            print(f"✅ Exchange Alert sent: {clean_title[:30]}")
                            save_link(link)
                            await asyncio.sleep(1) # تاخیر بسیار کوتاه برای عدم اسپم تلگرام
                        except Exception as tg_err:
                            print(f"❌ Telegram Error: {tg_err}")
                            
        except Exception as e:
            print(f"⚠️ Error in Exchange Monitor: {e}")

if __name__ == "__main__":
    asyncio.run(main_pipeline())

import os
import asyncio
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import html
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

TXT_FILE = "sent_exchange_links.txt" # یک فایل تاریخچه مجزا برای صرافی‌ها

# کلمات کلیدی مخصوص لیستینگ صرافی‌ها
KEYWORDS = ["list", "listing", "added", "support", "launchpool", "launchpad", "new token"]

# نام صرافی‌هایی که می‌خواهی رصد کنی
EXCHANGES = ["Binance", "Bybit", "KuCoin", "MEXC", "Gate.io", "Bitget", "OKX", "BingX", "Kraken", "Coinbase"]

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
    print("Starting Safe Exchange Monitor via Google Wire (Anti-Block)...")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # سرور سرچ گوگل برای پیدا کردن آخرین اطلاعیه‌های صرافی‌ها در کل وب
    query = "site:binance.com/en/support/announcement OR site:bybit.com OR site:kucoin.com"
    # برای سادگی و پوشش همه صرافی‌ها، یک سرچ هوشمند کریپتویی در گوگل می‌زنیم:
    encoded_query = urllib.parse.quote("binance list OR bybit listing OR OKX announcement OR bitget listed")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    async with bot:
        try:
            req = urllib.request.Request(rss_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:30]
            
            for item in items:
                link = item.find('link').text if item.find('link') is not None else ""
                if not link or link in SENT_LINKS:
                    continue
                
                title = item.find('title').text if item.find('title') is not None else ""
                
                # ۱. بررسی اینکه آیا نام یکی از صرافی‌ها در تیتر خبر گوگل هست؟
                is_exchange = any(ex.lower() in title.lower() for ex in EXCHANGES)
                
                if is_exchange:
                    # ۲. بررسی کلمات کلیدی مربوط به لیستینگ
                    has_keyword = any(kw.lower() in title.lower() for kw in KEYWORDS)
                    
                    if has_keyword:
                        clean_title = title.split(' - ')[0] if ' - ' in title else title
                        safe_title = html.escape(clean_title)
                        
                        final_message = (
                            f"🚨 <b>اطلاعیه صرافی جدید</b>\n\n"
                            f"📝 <b>عنوان:</b>\n{safe_title}\n\n"
                            f"🔗 <a href='{link}'>مشاهده منبع خبر در گوگل</a>"
                        )
                        
                        try:
                            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_message, parse_mode="HTML")
                            print(f"✅ Exchange Alert sent: {clean_title[:30]}")
                            save_link(link)
                        except Exception as tg_err:
                            print(f"❌ Telegram Error: {tg_err}")
                            
        except Exception as e:
            print(f"⚠️ Error in Exchange Monitor: {e}")

if __name__ == "__main__":
    asyncio.run(main_pipeline())

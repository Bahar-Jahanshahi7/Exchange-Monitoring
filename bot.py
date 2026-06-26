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

# کلمات کلیدی لیستینگ و اطلاعیه‌های مهم
KEYWORDS = ["list", "listing", "added", "support", "launchpool", "launchpad", "new token", "announcement", "delist"]
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
    print("Starting Multi-Channel 6-Hour Exchange Monitor via Google Wire...")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    async with bot:
        for exchange in EXCHANGES:
            print(f"🔍 Scanning last 6 hours news for {exchange}...")
            
            # تغییر فیلتر زمانی به 6 ساعت اخیر (when:6h) برای پوشش تاخیرهای گیت‌هاب
            raw_query = f'"{exchange}" AND (list OR listing OR added OR launchpool OR announcement OR delist) when:6h'
            encoded_query = urllib.parse.quote(raw_query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            try:
                req = urllib.request.Request(rss_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()
                
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')[:10] # بررسی تا 10 خبر اخیر برای هر صرافی
                
                for item in items:
                    link = item.find('link').text if item.find('link') is not None else ""
                    if not link or link in SENT_LINKS:
                        continue
                    
                    title = item.find('title').text if item.find('title') is not None else ""
                    
                    if any(kw.lower() in title.lower() for kw in KEYWORDS):
                        clean_title = title.split(' - ')[0] if ' - ' in title else title
                        safe_title = html.escape(clean_title)
                        
                        final_message = (
                            f"🚨 <b>اطلاعیه جدید صرافی ({exchange})</b>\n\n"
                            f"📝 <b>عنوان:</b>\n{safe_title}\n\n"
                            f"🔗 <a href='{link}'>مشاهده منبع خبر</a>"
                        )
                        
                        try:
                            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_message, parse_mode="HTML")
                            print(f"✅ Alert sent for {exchange}: {clean_title[:30]}")
                            save_link(link)
                            await asyncio.sleep(1)
                        except Exception as tg_err:
                            print(f"❌ Telegram Error: {tg_err}")
                            
            except Exception as e:
                print(f"⚠️ Skip {exchange} due to network timing: {e}")
            
            await asyncio.sleep(2) # تاخیر برای رعایت قوانین گوگل

if __name__ == "__main__":
    asyncio.run(main_pipeline())

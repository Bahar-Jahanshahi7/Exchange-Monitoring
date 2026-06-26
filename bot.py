import os
import re
import html
import asyncio
import xml.etree.ElementTree as ET
import urllib.request
import json
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

TXT_FILE = "sent_links.txt"

# لیست کامل هر ۱۰ صرافی درخواستی با متدهای پایدار RSS یا API اختصاصی
EXCHANGES_FEEDS = {
    "Binance": {"type": "json_binance", "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=5"},
    "Bybit": {"type": "json_bybit", "url": "https://api.bybit.com/v5/announcements/index?locale=en-US&limit=5"},
    "KuCoin": {"type": "json_kucoin", "url": "https://www.kucoin.com/kiwi/v1/notice/list?pageNo=1&pageSize=5&category=listing"},
    "MEXC": {"type": "json_mexc", "url": "https://www.mexc.com/api/platform/spot/cms/article/list?page=1&size=5&catalogId=93"},
    "Gate.io": {"type": "json_gate", "url": "https://www.gate.io/api2/v1/announcement/list?page=1&limit=5"},
    "Bitget": {"type": "rss", "url": "https://www.bitget.com/ru/support/rss/listings"},
    "OKX": {"type": "rss", "url": "https://www.okx.com/support/hc/en-us/categories/115000275131-Latest-Announcements.rss"},
    "BingX": {"type": "rss", "url": "https://support.bingx.com/hc/en-us/sections/360000032948-Latest-News.rss"},
    "Kraken": {"type": "rss", "url": "https://blog.kraken.com/category/product-updates/feed/"},
    "Coinbase": {"type": "rss", "url": "https://blog.coinbase.com/feed"}
}

KEYWORDS = ["list", "listing", "added", "launchpool", "launchpad", "will list", "support","live"]

if os.path.exists(TXT_FILE):
    with open(TXT_FILE, "r") as f:
        SENT_LINKS = set(line.strip() for line in f if line.strip())
else:
    SENT_LINKS = set()

def save_link(link):
    with open(TXT_FILE, "a") as f:
        f.write(f"{link}\n")
    SENT_LINKS.add(link)

async def main_pipeline():
    print("Starting Complete 10-Exchange Announcement Monitor...")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, application/xml, text/xml, */*'
    }

    async with bot:
        for exchange, config in EXCHANGES_FEEDS.items():
            try:
                req = urllib.request.Request(config["url"], headers=headers)
                articles = []
                
                with urllib.request.urlopen(req, timeout=12) as response:
                    raw_data = response.read()

                # پردازش بر اساس نوع فرمت خروجی (JSON یا RSS XML)
                if config["type"] == "rss":
                    root = ET.fromstring(raw_data)
                    items = root.findall('.//item')[:5]
                    for item in items:
                        title = item.find('title').text if item.find('title') is not None else ""
                        link = item.find('link').text if item.find('link') is not None else ""
                        articles.append({"title": title, "url": link})
                        
                else:
                    # پردازش صرافی‌های دارای API اختصاصی جی‌سان
                    data = json.loads(raw_data.decode('utf-8'))
                    if config["type"] == "json_binance":
                        articles = [{"title": x["title"], "url": f"https://www.binance.com/en/support/announcement/{x['code']}"} for x in data.get("data", {}).get("catalogs", [{}])[0].get("articles", [])]
                    elif config["type"] == "json_bybit":
                        articles = [{"title": x["title"], "url": x["url"]} for x in data.get("result", {}).get("list", [])]
                    elif config["type"] == "json_kucoin":
                        articles = [{"title": x["title"], "url": x["url"]} for x in data.get("data", {}).get("items", [])]
                    elif config["type"] == "json_mexc":
                        articles = [{"title": x["title"], "url": f"https://support.mexc.com/hc/en-001/articles/{x['id']}"} for x in data.get("data", {}).get("list", [])]
                    elif config["type"] == "json_gate":
                        articles = [{"title": x["title"], "url": x["url"]} for x in data.get("data", [])]

                # بررسی و فیلتر کردن مقالات دریافت شده
                for article in articles:
                    title = article["title"]
                    link = article["url"]
                    
                    if not link or link in SENT_LINKS:
                        continue
                    
                    contains_keyword = any(keyword.lower() in title.lower() for keyword in KEYWORDS)
                    
                    if contains_keyword:
                        safe_title = html.escape(title)
                        
                        final_message = (
                            f"📢 <b>اطلاعیه جدید از صرافی: {exchange}</b>\n\n"
                            f"📌 <b>عنوان:</b> {safe_title}\n\n"
                            f"🔗 <a href='{link}'>مشاهده کامل اطلاعیه</a>"
                        )
                        
                        try:
                            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_message, parse_mode="HTML")
                            print(f"✅ Alert sent for {exchange}: {title[:30]}...")
                            save_link(link)
                        except Exception as tg_err:
                            print(f"❌ Telegram Error for {exchange}: {tg_err}")
                            
                await asyncio.sleep(2) # تاخیر ایمن بین صرافی‌ها
                
            except Exception as e:
                print(f"⚠️ Error checking {exchange}: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main_pipeline())

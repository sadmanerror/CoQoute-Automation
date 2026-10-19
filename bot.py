import os
import time
import feedparser
import requests
from groq import Groq

# --- Configuration & Credentials ---
TELEGRAM_BOT_TOKEN = "8812845138:AAfZbE0wsZTtdQ-MRdCTbctWgH38LzpMkjc"
TELEGRAM_CHAT_ID = "-1004413991519"
GROQ_API_KEY = "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"

TARGET_POST_COUNT = 30      # Deliver top 30 trendy news items per run
SLEEP_INTERVAL_MINUTES = 30 # Run every 30 minutes

# Priority Category Feeds (Sports, Movies, Celebrity buzz, Discovery, Tech)
RSS_FEEDS = [
    # Top Global Real-time Trending
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    
    # Entertainment, Movies & Celebrity Talks
    "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=celebrity+OR+hollywood+OR+movie+news+when:1h&hl=en-US&gl=US&ceid=US:en",
    "https://variety.com/feed/",
    "https://deadline.com/feed/",

    # Sports (Milestones, Scores, Major Events)
    "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=sports+breaking+news+when:1h&hl=en-US&gl=US&ceid=US:en",

    # Science, Research & Discovery
    "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=scientific+research+OR+breakthrough+when:24h&hl=en-US&gl=US&ceid=US:en",
    "https://phys.org/rss-feed/",

    # Technology & Innovations
    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=technology+innovation+when:1h&hl=en-US&gl=US&ceid=US:en"
]

SEEN_FILE = "seen_urls.txt"
client = Groq(api_key=GROQ_API_KEY)

def load_seen_urls():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def append_seen_url(url):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url}\n")

def summarize_trending_story(title, summary):
    prompt = f"""
    You are a high-energy social media news anchor tracking trending topics across the globe.
    
    News Item:
    Title: {title}
    Snippet: {summary}

    TASK:
    - Cover this breaking/trending story in an engaging, viral, and easily digestible format.
    - Priority genres: Sports, Movies, Celebrity buzz/talks, Science/Discoveries, and Major Research.
    - If the item is purely spam, an advertisement, or unreadable code, respond ONLY with: SKIP.

    FORMAT REQUIRED:
    🔥 **[Catchy, Impactful 1-Line Headline]**

    • **The Big News:** [What just happened or what is everyone talking about?]
    • **Key Details:** [Crucial context, scores, quotes, or box office / research metrics]
    • **Why It's Buzzing:** [Why people are reacting or what comes next]

    Tags: #[Genre] #[RelatedKeyword] #Trending
    """

    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API Error: {e}")
        return "SKIP"

def send_telegram_alert(text, link):
    message = f"{text}\n\n🔗 **Read Full Story:** {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload, timeout=10)

def run_news_cycle():
    seen_urls = load_seen_urls()
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting news cycle. Loaded {len(seen_urls)} cached URLs.")

    posted_count = 0

    for feed_url in RSS_FEEDS:
        if posted_count >= TARGET_POST_COUNT:
            print(f"Reached batch target of {TARGET_POST_COUNT} posts.")
            break

        try:
            feed = feedparser.parse(feed_url)
            # Scan top 6 newest entries per feed
            for entry in feed.entries[:6]:
                if posted_count >= TARGET_POST_COUNT:
                    break

                url = entry.link
                if url in seen_urls:
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", "")

                result = summarize_trending_story(title, summary)
                if result and "SKIP" not in result:
                    send_telegram_alert(result, url)
                    posted_count += 1
                    print(f"[{posted_count}/{TARGET_POST_COUNT} POSTED] {title}")
                else:
                    print(f"[SKIPPED] {title}")

                append_seen_url(url)
                seen_urls.add(url)

                # 2.5-second pause keeps you at ~24 requests/min (well under Groq's 30 RPM limit)
                time.sleep(2.5)

        except Exception as feed_err:
            print(f"Error reading feed {feed_url}: {feed_err}")

    print(f"Finished cycle. Total {posted_count} new posts sent to Telegram.")

def main():
    while True:
        run_news_cycle()
        print(f"Sleeping for {SLEEP_INTERVAL_MINUTES} minutes until the next batch...")
        time.sleep(SLEEP_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
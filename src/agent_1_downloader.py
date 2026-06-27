import os
import json
import asyncio
import sys
from dotenv import load_dotenv

# Prevent encoding crashes when printing Chinese characters to standard output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

load_dotenv()
HISTORY_FILE = 'downloaded_history.txt'
QUEUE_FILE = 'workspace/queue.json'

# Chinese craft keywords for filtering
CRAFT_KEYWORDS = ["竹编", "木工", "陶瓷", "手工", "非遗", "手工艺", "编织", "木雕",
                   "陶艺", "竹艺", "匠心", "传统", "craft", "woodwork", "pottery",
                   "bamboo", "handmade", "artisan"]


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()


def save_to_history(video_id):
    with open(HISTORY_FILE, 'a') as f:
        f.write(f"{video_id}\n")


def load_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_queue(queue):
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


async def scan_kuaishou_craft_videos():
    print("Scanning Kuaishou for satisfying craft videos...")
    history = load_history()
    queue = load_queue()
    queued_ids = {item['id'] for item in queue}
    new_candidates = []

    try:
        from playwright.async_api import async_playwright

        # Target URLs: Kuaishou recommendation feed and craft-related searches
        target_urls = [
            "https://www.kuaishou.com/new-reco",
            "https://www.kuaishou.com/search/video?searchKey=%E7%AB%B9%E7%BC%96",
            "https://www.kuaishou.com/search/video?searchKey=%E6%9C%A8%E5%B7%A5",
            "https://www.kuaishou.com/search/video?searchKey=%E9%99%B6%E7%93%B7",
            "https://www.kuaishou.com/search/video?searchKey=%E6%89%8B%E5%B7%A5",
            "https://www.kuaishou.com/search/video?searchKey=%E9%9D%9E%E9%81%97",
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()

            for target_url in target_urls:
                try:
                    print(f"Playwright scraping: {target_url}")
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(5000)

                    # Extract links containing short-video or Kwai video patterns
                    links = await page.query_selector_all('a')
                    for link in links:
                        href = await link.get_attribute('href')
                        if href and ('/short-video/' in href or '/video/' in href or '/f/' in href):
                            vid = href.split('/')[-1].split('?')[0]
                            if vid and vid not in history and vid not in queued_ids:
                                text = await link.inner_text()
                                text_cleaned = ' '.join(text.split())

                                # Check if the text or URL matches craft keywords
                                is_craft = any(kw in text_cleaned.lower() for kw in CRAFT_KEYWORDS)
                                is_craft = is_craft or any(kw in href.lower() for kw in CRAFT_KEYWORDS)

                                # Also accept videos from craft search pages
                                is_craft = is_craft or 'searchKey' in target_url

                                if is_craft:
                                    full_url = f"https://www.kuaishou.com/short-video/{vid}" if not href.startswith('http') else href
                                    new_candidates.append({
                                        "id": vid,
                                        "title": text_cleaned[:120] if text_cleaned else f"Kuaishou Craft Video {vid}",
                                        "source_url": full_url,
                                        "status": "PENDING"
                                    })
                                    print(f"Discovered Kuaishou craft video: ID={vid} | Title={text_cleaned[:50] if text_cleaned else vid}")

                except Exception as e:
                    print(f"Error scraping {target_url} with Playwright: {e}")

            await browser.close()

    except Exception as err:
        print(f"Playwright scraper skipped/failed: {err}")

    # Save unique new candidates to queue
    if new_candidates:
        unique_candidates = []
        seen_ids = set(queued_ids)
        for c in new_candidates:
            if c['id'] not in seen_ids:
                unique_candidates.append(c)
                seen_ids.add(c['id'])

        if unique_candidates:
            queue.extend(unique_candidates)
            save_queue(queue)
            print(f"Added {len(unique_candidates)} new craft videos to the queue.")
        else:
            print("No new unique craft videos discovered in this scan.")
    else:
        print("No new unique craft videos discovered in this scan.")


def run_downloader():
    print("Running Downloader: Scanning Kuaishou for craft videos...")
    try:
        asyncio.run(scan_kuaishou_craft_videos())
    except Exception as e:
        print(f"Async scan failed: {e}")

    # Return the first PENDING video in the queue if available
    queue = load_queue()
    pending = [item for item in queue if item['status'] == 'PENDING']
    if pending:
        item = pending[0]
        print(f"Next pending video: {item['title']} ({item['source_url']})")
        return item
    return None


if __name__ == "__main__":
    run_downloader()

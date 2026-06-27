import os
import re
import json
import urllib.parse
import requests

HISTORY_FILE = 'downloaded_history.txt'
QUEUE_FILE = 'workspace/queue.json'

CRAFT_KEYWORDS = ["手工", "木工", "陶艺", "竹编", "非遗", "木雕", "编织", "锻造"]

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_to_history(video_id):
    with open(HISTORY_FILE, 'a') as f:
        f.write(f"{video_id}\n")

def load_queue():
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
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

def scan_bilibili_crafts():
    print("Scanning Bilibili for craft videos...")
    history = load_history()
    queue = load_queue()
    queued_ids = {item['id'] for item in queue}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com/"
    }
    
    new_candidates = []
    for kw in CRAFT_KEYWORDS:
        try:
            url = f"https://api.bilibili.com/x/web-interface/wbi/search/all/v2?keyword={urllib.parse.quote(kw)}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('code') == 0:
                    result = data.get('data', {}).get('result', [])
                    video_result = None
                    if isinstance(result, list):
                        for item in result:
                            if isinstance(item, dict) and item.get('result_type') == 'video':
                                video_result = item
                                break
                    if video_result:
                        for v in video_result.get('data', [])[:3]:
                            bvid = v.get('bvid')
                            if not bvid or bvid in history or bvid in queued_ids:
                                continue
                            title_clean = re.sub(r'<[^>]+>', '', v.get('title', ''))
                            new_candidates.append({
                                "id": bvid,
                                "title": title_clean[:120],
                                "source_url": f"https://www.bilibili.com/video/{bvid}",
                                "status": "PENDING"
                            })
                            print(f"Found: {bvid} | {title_clean[:50]}")
        except Exception as e:
            print(f"Error scanning '{kw}': {e}")
    
    if new_candidates:
        seen_ids = {c['id'] for c in queue}
        unique = [c for c in new_candidates if c['id'] not in seen_ids]
        if unique:
            queue.extend(unique)
            save_queue(queue)
            print(f"Added {len(unique)} videos to queue.")

def download_bilibili_video(bilibili_url, output_filename, max_retries=3):
    """Download Bilibili video using playurl API with retry"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }
    try:
        match = re.search(r'video/(BV[a-zA-Z0-9]+)', bilibili_url)
        if not match:
            print("Invalid Bilibili URL")
            return False
        bvid = match.group(1)
        
        view_api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        res = requests.get(view_api, headers=headers, timeout=15).json()
        if res.get('code') != 0:
            return False
        cid = res['data']['cid']
        print(f"  Got CID: {cid}")
        
        play_api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=16"
        play_res = requests.get(play_api, headers=headers, timeout=15).json()
        if 'durl' not in play_res.get('data', {}):
            print("No video stream found")
            return False
        video_cdn_url = play_res['data']['durl'][0]['url']
        print(f"  Got stream URL")
        
        # Download with retry
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        for attempt in range(max_retries):
            try:
                print(f"  Downloading video (attempt {attempt+1}/{max_retries})...")
                response = requests.get(video_cdn_url, headers=headers, timeout=120, stream=True)
                with open(output_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = os.path.getsize(output_filename)
                if file_size > 10000:  # At least 10KB
                    print(f"  Downloaded: {output_filename} ({file_size/1024/1024:.1f} MB)")
                    return True
                else:
                    print(f"  File too small ({file_size} bytes), retrying...")
                    os.remove(output_filename)
            except Exception as e:
                print(f"  Attempt {attempt+1} failed: {e}")
                if os.path.exists(output_filename):
                    os.remove(output_filename)
        
        print("  All download attempts failed")
        return False
    except Exception as e:
        print(f"Download error: {e}")
        return False

def run_downloader():
    print("Running Bilibili Craft Downloader...")
    scan_bilibili_crafts()
    
    queue = load_queue()
    pending = [item for item in queue if item['status'] == 'PENDING']
    
    if pending:
        item = pending[0]
        output_path = "workspace/raw_video.mp4"
        print(f"\nDownloading: {item['source_url']}")
        
        if download_bilibili_video(item['source_url'], output_path):
            item['status'] = 'DOWNLOADED'
            item['local_path'] = output_path
            save_queue(queue)
            save_to_history(item['id'])
            return item
        else:
            print("Download failed.")
            return None
    
    print("No pending videos.")
    return None

if __name__ == "__main__":
    run_downloader()

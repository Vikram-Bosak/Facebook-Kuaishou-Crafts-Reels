"""
Telegram notification placeholder.
Configure bot token and chat ID as GitHub secrets.
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

_token_key = "TELEGRAM_BOT_TOKEN"
_chat_key = "TELEGRAM_CHAT_ID"

_bot_token = os.environ.get(_token_key)
_chat_id = os.environ.get(_chat_key)
_report_chat_id = os.environ.get("TELEGRAM_REPORT_CHAT_ID", _chat_id)


def send_message(message, chat_id=None):
    target = chat_id or _report_chat_id
    if not _bot_token or not target:
        print(f"[Placeholder] No creds: {message}")
        return
    url = f"https://api.telegram.org/bot{_bot_token}/sendMessage"
    payload = {"chat_id": target, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        res = r.json()
        if res.get("ok") and "result" in res:
            return res["result"].get("message_id")
    except Exception as e:
        print(f"Failed: {e}")
    return None


def get_run_details():
    rid = os.environ.get("GITHUB_RUN_ID", "Unknown")
    wf = os.environ.get("GITHUB_WORKFLOW", "Unknown")
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Run: {rid} WF: {wf} Time: {t}"


def report_download_start():
    send_message(f"Download Started {get_run_details()}")

def report_download_complete(url):
    send_message(f"Download Done src={url} {get_run_details()}")

def report_edit_start():
    send_message(f"Edit Started {get_run_details()}")

def report_edit_complete():
    send_message(f"Edit Done {get_run_details()}")

def report_final_summary(vd):
    s = vd.get("editing_status","?")
    t = vd.get("seo_title", vd.get("title","?"))
    p = vd.get("edited_path","N/A")
    u = vd.get("source_url","N/A")
    send_message(f"Pipeline Done title={t} status={s} out={p} src={u}")

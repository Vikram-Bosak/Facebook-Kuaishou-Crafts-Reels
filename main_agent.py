import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent_1_downloader import run_downloader
from src.agent_2_editor import process_video
from src.common.limits import can_download, can_edit, increment_download, increment_edit
from src.common.telegram import (
    report_download_start,
    report_download_complete,
    report_edit_start,
    report_edit_complete,
    send_message,
    report_final_summary
)

def run_single_sequence():
    print("\n--- STARTING KUAISHOU CRAFTS PIPELINE (SINGLE RUN) ---")

    if not can_download():
        print("Daily download limit reached. Exiting.")
        send_message("⚠️ <b>Daily download limit reached.</b> No more videos today.")
        return False

    if not can_edit():
        print("Daily edit limit reached. Exiting.")
        send_message("⚠️ <b>Daily edit limit reached.</b> No more edits today.")
        return False

    # 1. Download from Kuaishou
    report_download_start()
    video_data = run_downloader()
    if not video_data:
        print("No craft video found.")
        send_message("⚠️ <b>Download Skipped:</b> No new craft videos found on Kuaishou.")
        return False

    task_id = video_data['id']
    print(f"Downloaded Video: {task_id}")
    report_download_complete(video_data['source_url'])
    send_message(f"🆔 <b>Unique ID generated:</b> {task_id}")
    increment_download()

    # 2. Edit
    report_edit_start()
    try:
        print(f"Editing Video {task_id}...")
        video_data = process_video(video_data)
        if video_data.get('editing_status') == 'Success':
            report_edit_complete()
            increment_edit()
        else:
            send_message(f"❌ <b>Editing Failed for {task_id}</b>")
            return False
    except Exception as e:
        print(f"Editing failed: {e}")
        send_message(f"❌ <b>Editing Failed for {task_id}:</b>\n{e}")
        return False

    # Final Report
    report_final_summary(video_data)

    print("Pipeline run completed.")
    return True


if __name__ == "__main__":
    run_single_sequence()

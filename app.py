# app.py
import streamlit as st
import tempfile
from apscheduler.schedulers.background import BackgroundScheduler
from TikTokApi import TikTokApi

# --- CONFIG ---
TIKTOK_USERNAME = "greatone.02"
TIKTOK_PASSWORD = "hebhor-xacgy0-hegtAp"

def upload_to_tiktok(video_path: str, title: str):
    api = TikTokApi.get_instance()
    # NOTE: you may need to authenticate via cookies/session rather than username/password
    api.login(username=TIKTOK_USERNAME, password=TIKTOK_PASSWORD)
    upload_resp = api.upload_video(video_path)
    api.post_video(video_file=upload_resp, title=title)
    print("✅ Uploaded to TikTok")

def schedule_jobs(video_path: str, title: str):
    scheduler = BackgroundScheduler()
    def job():
        upload_to_tiktok(video_path, title)
    scheduler.add_job(job, "interval", hours=2)
    scheduler.start()

def main():
    st.title("🎬 TikTok Scheduler")
    uploaded = st.file_uploader("Upload your short video", type=["mp4", "mov"], help="Max 60 s")
    title = st.text_input("Video Title")
    if st.button("Start Scheduling"):
        if not uploaded or not title:
            st.error("Please upload a video and enter a title.")
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(uploaded.read())
            tmp.flush()
            schedule_jobs(tmp.name, title)
            st.success("✅ Scheduled TikTok uploads every 2 hours!")

if __name__ == "__main__":
    main()

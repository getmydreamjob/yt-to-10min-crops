# app.py
import streamlit as st
import tempfile
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from TikTokApi import TikTokApi

# --- CONFIG ---
TIKTOK_USERNAME = "greatone.02"
TIKTOK_PASSWORD = "hebhor-xacgy0-hegtAp"

def upload_to_tiktok(video_path: str, title: str):
    api = TikTokApi()
    # If your TikTokApi version needs login, uncomment:
    # api.login(username=TIKTOK_USERNAME, password=TIKTOK_PASSWORD)
    upload_resp = api.upload_video(video_path)
    api.post_video(video_file=upload_resp, title=title)
    st.success(f"✅ Uploaded “{title}” at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", key="success_msg")

def schedule_jobs(video_path: str, title: str):
    scheduler = BackgroundScheduler()
    def job():
        upload_to_tiktok(video_path, title)
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler

def main():
    st.title("🎬 TikTok Scheduler", anchor="header")

    # --- UPLOAD & INPUT ---
    uploaded = st.file_uploader(
        "Upload your short video", 
        type=["mp4", "mov"], 
        help="Max 60 s", 
        key="video_uploader"
    )
    title = st.text_input(
        "Video Title", 
        key="video_title"
    )

    # --- START SCHEDULER ---
    if st.button("Start Scheduling", key="start_sched"):
        if not uploaded or not title:
            st.error("Please upload a video and enter a title.", key="input_error")
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(uploaded.read())
            tmp.flush()
            st.session_state.scheduler = schedule_jobs(tmp.name, title)
            # immediate test run:
            upload_to_tiktok(tmp.name, title)

    # --- SHOW NEXT RUN & MANUAL TRIGGER ---
    sched = st.session_state.get("scheduler")
    if sched:
        job = sched.get_job("tiktok_job")
        if job:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            st.write("**Next scheduled upload:**", next_run, key="next_run")
            if st.button("Run Now", key="run_now"):
                job.func()

if __name__ == "__main__":
    main()

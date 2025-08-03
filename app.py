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
    api = TikTokApi.get_instance()
    api.login(username=TIKTOK_USERNAME, password=TIKTOK_PASSWORD)
    upload_resp = api.upload_video(video_path)
    api.post_video(video_file=upload_resp, title=title)
    st.success(f"✅ Uploaded “{title}” at {datetime.now().strftime('%H:%M:%S')}")

def schedule_jobs(video_path: str, title: str):
    scheduler = BackgroundScheduler()
    def job():
        upload_to_tiktok(video_path, title)
    # schedule every 2 hours
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler

def main():
    st.title("🎬 TikTok Scheduler")
    uploaded = st.file_uploader("Upload your short video", type=["mp4", "mov"], help="Max 60s")
    title = st.text_input("Video Title")
    if st.button("Start Scheduling"):
        if not uploaded or not title:
            st.error("Please upload a video and enter a title.")
        else:
            # save to temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(uploaded.read())
            tmp.flush()

            # schedule and store scheduler in session state
            st.session_state.scheduler = schedule_jobs(tmp.name, title)

            # immediately run one test
            upload_to_tiktok(tmp.name, title)

    # once scheduled, show next run time and allow manual trigger
    if st.session_state.get("scheduler"):
        sched = st.session_state.scheduler
        job = sched.get_job("tiktok_job")
        if job:
            st.write("**Next scheduled upload:**", job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))
            if st.button("Run Now"):
                job.func()  # trigger upload immediately

if __name__ == "__main__":
    main()

# app.py
import streamlit as st
import tempfile
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video

# --- CONFIG ---
COOKIES_FILE = "cookies.txt"   # your TikTok session cookies (Netscape format)

def do_upload(video_path: str, title: str) -> (bool, str):
    """
    Perform the actual upload. Returns (success, message).
    """
    try:
        upload_video(video_path, description=title, cookies=COOKIES_FILE)
        return True, f"Uploaded “{title}” at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return False, str(e)

def upload_and_report(video_path: str, title: str):
    """
    Wrapper for the immediate (UI) upload: shows st.success or st.error.
    """
    ok, msg = do_upload(video_path, title)
    if ok:
        st.success(f"✅ {msg}", key="immediate_success")
    else:
        st.error(f"❌ Upload failed: {msg}", key="immediate_error")

def schedule_jobs(video_path: str, title: str):
    """
    Schedule do_upload() every 2 hours (no st.* calls here).
    """
    scheduler = BackgroundScheduler()
    def job():
        ok, msg = do_upload(video_path, title)
        print("TikTok scheduler:", "OK" if ok else "FAIL", msg)
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler

def main():
    st.title("🎬 TikTok Scheduler", anchor="header")

    uploaded = st.file_uploader(
        "Upload your short video",
        type=["mp4", "mov"],
        help="Max 60 s",
        key="video_uploader"
    )
    title = st.text_input("Video Title", key="video_title")

    if st.button("Start Scheduling", key="start_sched"):
        if not uploaded or not title:
            st.error("Please upload a video and enter a title.", key="input_error")
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(uploaded.read())
            tmp.flush()

            # schedule the background job
            st.session_state.scheduler = schedule_jobs(tmp.name, title)
            # run one immediate upload and report
            upload_and_report(tmp.name, title)

    # show next run & manual trigger
    sched = st.session_state.get("scheduler")
    if sched:
        job = sched.get_job("tiktok_job")
        if job:
            st.write("**Next scheduled upload:**", 
                     job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"),
                     key="next_run")
            if st.button("Run Now", key="run_now"):
                # manual trigger
                ok, msg = do_upload(tmp.name, title)
                if ok:
                    st.success(f"✅ {msg}", key="manual_success")
                else:
                    st.error(f"❌ Upload failed: {msg}", key="manual_error")

if __name__ == "__main__":
    main()

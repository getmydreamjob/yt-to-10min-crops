# app.py
import streamlit as st
import tempfile
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video

def do_upload(video_path: str, title: str, cookies_path: str) -> (bool, str):
    """
    Perform the actual upload. Returns (success, message).
    """
    try:
        upload_video(video_path, description=title, cookies=cookies_path)
        return True, f"Uploaded “{title}” at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return False, str(e)

def upload_and_report(video_path: str, title: str, cookies_path: str):
    """
    Wrapper for the immediate (UI) upload: shows st.success or st.error.
    """
    ok, msg = do_upload(video_path, title, cookies_path)
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ Upload failed: {msg}")

def schedule_jobs(video_path: str, title: str, cookies_path: str):
    """
    Schedule do_upload() every 2 hours (no st.* calls here).
    """
    scheduler = BackgroundScheduler()
    def job():
        ok, msg = do_upload(video_path, title, cookies_path)
        print("TikTok scheduler:", "OK" if ok else "FAIL", msg)
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler

def main():
    st.title("🎬 TikTok Scheduler")

    # Upload cookies.txt
    cookies_upload = st.file_uploader(
        "Upload your TikTok cookies.txt (Netscape format)",
        type=["txt"],
        key="cookies_uploader"
    )
    # Upload video
    uploaded = st.file_uploader(
        "Upload your short video",
        type=["mp4", "mov"],
        key="video_uploader"
    )
    title = st.text_input("Video Title", key="video_title")

    if st.button("Start Scheduling", key="start_sched"):
        if not cookies_upload:
            st.error("Please upload your cookies.txt first.")
        elif not uploaded or not title:
            st.error("Please upload a video and enter a title.")
        else:
            # write cookies to temp file
            cookies_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            cookies_tmp.write(cookies_upload.read())
            cookies_tmp.flush()
            cookies_path = cookies_tmp.name

            # write video to temp file
            video_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            video_tmp.write(uploaded.read())
            video_tmp.flush()
            video_path = video_tmp.name

            # schedule background uploads
            st.session_state.scheduler = schedule_jobs(video_path, title, cookies_path)
            # immediate test upload
            upload_and_report(video_path, title, cookies_path)

    # Show next run & manual trigger
    sched = st.session_state.get("scheduler")
    if sched:
        job = sched.get_job("tiktok_job")
        if job:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            st.write("**Next scheduled upload:**", next_run)
            if st.button("Run Now", key="run_now"):
                ok, msg = do_upload(video_path, title, cookies_path)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ Upload failed: {msg}")

if __name__ == "__main__":
    main()

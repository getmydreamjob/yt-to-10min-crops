# app.py
import streamlit as st
import tempfile
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video

# Selenium + WebDriver imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def create_driver():
    """Launch a headless Chromium instance with matching ChromeDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Point at the system-installed Chromium
    options.binary_location = "/usr/bin/chromium"

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def do_upload(video_path: str, title: str, cookies_path: str) -> (bool, str):
    """
    Perform the actual upload via tiktok-uploader + Selenium.
    Returns (success, message).
    """
    driver = create_driver()
    try:
        upload_video(
            video_path,
            description=title,
            cookies=cookies_path,
            driver=driver,          # pass our driver
        )
        driver.quit()
        return True, f"Uploaded “{title}” at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        driver.quit()
        return False, str(e)

def upload_and_report(video_path: str, title: str, cookies_path: str):
    ok, msg = do_upload(video_path, title, cookies_path)
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ Upload failed: {msg}")

def schedule_jobs(video_path: str, title: str, cookies_path: str):
    scheduler = BackgroundScheduler()
    def job():
        ok, msg = do_upload(video_path, title, cookies_path)
        print("TikTok scheduler:", "OK" if ok else "FAIL", msg)
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler

def main():
    st.title("🎬 TikTok Scheduler")

    # 1) cookies.txt uploader
    cookies_upload = st.file_uploader(
        "Upload your TikTok cookies.txt (Netscape format)",
        type=["txt"],
        key="cookies_uploader"
    )
    # 2) video uploader
    video_upload = st.file_uploader(
        "Upload your short video",
        type=["mp4", "mov"],
        key="video_uploader"
    )
    title = st.text_input("Video Title", key="video_title")

    if st.button("Start Scheduling", key="start_sched"):
        if not cookies_upload:
            st.error("Please upload your cookies.txt first.")
        elif not video_upload or not title:
            st.error("Please upload a video and enter a title.")
        else:
            # write cookies to temp file
            ck = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            ck.write(cookies_upload.read())
            ck.flush()
            cookies_path = ck.name

            # write video to temp file
            vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            vid.write(video_upload.read())
            vid.flush()
            video_path = vid.name

            # schedule and run test
            st.session_state.scheduler = schedule_jobs(video_path, title, cookies_path)
            upload_and_report(video_path, title, cookies_path)

    # show next run & manual trigger
    sched = st.session_state.get("scheduler")
    if sched:
        job = sched.get_job("tiktok_job")
        if job:
            st.write("**Next scheduled upload:**", job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))
            if st.button("Run Now", key="run_now"):
                ok, msg = do_upload(video_path, title, cookies_path)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ Upload failed: {msg}")

if __name__ == "__main__":
    main()

# app.py
import streamlit as st
import tempfile
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def create_driver():
    """Launch a headless Chromium instance using the system chromedriver."""
    options = webdriver.ChromeOptions()
    # new headless mode for Chrome 109+
    options.add_argument("--headless=new")  
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    # point at the system-installed Chromium
    options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

def do_upload(video_path: str, title: str, cookies_path: str) -> (bool, str):
    driver = create_driver()
    try:
        upload_video(
            video_path,
            description=title,
            cookies=cookies_path,
            driver=driver,
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

    cookies_upload = st.file_uploader(
        "Upload your TikTok cookies.txt (Netscape format)",
        type=["txt"], key="cookies_uploader"
    )
    video_upload = st.file_uploader(
        "Upload your short video",
        type=["mp4", "mov"], key="video_uploader"
    )
    title = st.text_input("Video Title", key="video_title")

    if st.button("Start Scheduling", key="start_sched"):
        if not cookies_upload:
            st.error("Please upload your cookies.txt first.")
        elif not video_upload or not title:
            st.error("Please upload a video and enter a title.")
        else:
            ck = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            ck.write(cookies_upload.read())
            ck.flush()
            cookies_path = ck.name

            vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            vid.write(video_upload.read())
            vid.flush()
            video_path = vid.name

            st.session_state.scheduler = schedule_jobs(video_path, title, cookies_path)
            upload_and_report(video_path, title, cookies_path)

    if sched := st.session_state.get("scheduler"):
        if job := sched.get_job("tiktok_job"):
            st.write("**Next scheduled upload:**", job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))
            if st.button("Run Now", key="run_now"):
                ok, msg = do_upload(video_path, title, cookies_path)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ Upload failed: {msg}")

if __name__ == "__main__":
    main()

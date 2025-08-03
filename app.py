import os
import tempfile
import streamlit as st
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def create_driver():
    """Launch a headless Chromium instance matching the system driver."""
    options = webdriver.ChromeOptions()
    # Standard headless flags
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    # Process isolation flags
    options.add_argument("--single-process")
    options.add_argument("--no-zygote")
    # Avoid /dev/shm issues
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-data-dir=/tmp/chrome_user_data")

    # Pick the correct chromium binary
    if os.path.exists("/usr/bin/chromium-browser"):
        options.binary_location = "/usr/bin/chromium-browser"
    else:
        options.binary_location = "/usr/bin/chromium"

    # Point at the system-installed chromedriver
    svc = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=svc, options=options)

def do_upload(video_path: str, title: str, cookies_path: str):
    """Run the tiktok-uploader with our Selenium driver."""
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
    sched = BackgroundScheduler()
    def job():
        ok, msg = do_upload(video_path, title, cookies_path)
        print("Scheduler:", "OK" if ok else "FAIL", msg)
    sched.add_job(job, "interval", hours=2, id="tiktok_job")
    sched.start()
    return sched

def main():
    st.title("🎬 TikTok Scheduler")

    cookies_file = st.file_uploader(
        "Upload your TikTok cookies.txt (Netscape format)",
        type=["txt"], key="cookies"
    )
    video_file = st.file_uploader(
        "Upload your short video",
        type=["mp4", "mov"], key="video"
    )
    title = st.text_input("Video Title", key="title")

    if st.button("Start Scheduling", key="start"):
        if not cookies_file:
            st.error("Please upload your cookies.txt first.")
            return
        if not video_file or not title:
            st.error("Please upload a video and enter a title.")
            return

        # Save cookies to temp file
        ck = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        ck.write(cookies_file.read()); ck.flush()
        cookies_path = ck.name

        # Save video to temp file
        vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        vid.write(video_file.read()); vid.flush()
        video_path = vid.name

        # Schedule & test
        st.session_state.scheduler = schedule_jobs(video_path, title, cookies_path)
        upload_and_report(video_path, title, cookies_path)

    # Show next-run and manual trigger
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

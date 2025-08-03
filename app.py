import os
import tempfile
import streamlit as st
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video
import undetected_chromedriver as uc

# --- CONFIG ---
# No changes needed in packages.txt (chromium, chromium-driver) or requirements.txt (streamlit, tiktok-uploader, APScheduler, selenium, undetected-chromedriver)

def create_driver():
    """Launch a headless Chromium instance using undetected_chromedriver with robust flags."""
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-software-rasterizer")
    # Select the correct system Chromium binary
    chrome_binary = "/usr/bin/chromium-browser" if os.path.exists("/usr/bin/chromium-browser") else "/usr/bin/chromium"
    options.binary_location = chrome_binary
    # Create the driver with explicit paths to avoid mismatches
    driver = uc.Chrome(
        options=options,
        driver_executable_path="/usr/bin/chromedriver",
        browser_executable_path=chrome_binary
    )
    return driver


def do_upload(video_path: str, title: str, cookies_path: str) -> (bool, str):
    """Run the tiktok-uploader with our undetected-chromedriver."""
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

        # Save cookies.txt to a temp file
        ck = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        ck.write(cookies_file.read()); ck.flush()
        cookies_path = ck.name

        # Save video to a temp file
        vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        vid.write(video_file.read()); vid.flush()
        video_path = vid.name

        # Schedule background uploads and run initial test
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

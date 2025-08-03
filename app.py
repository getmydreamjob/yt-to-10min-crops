import os
import tempfile
import streamlit as st
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from http.cookiejar import MozillaCookieJar
from playwright.sync_api import sync_playwright

# --- CONFIG ---
# Ensure 'packages.txt' includes:
# chromium
# (Playwright will use this system Chromium binary)
# Ensure 'requirements.txt' includes:
# streamlit
# playwright
# apscheduler


def parse_netscape_cookies(path):
    cj = MozillaCookieJar()
    cj.load(path, ignore_discard=True, ignore_expires=True)
    cookies = []
    for c in cj:
        cookies.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "expires": c.expires or -1,
            "httpOnly": c._rest.get("HttpOnly", False),
            "secure": c.secure,
            "sameSite": "Lax",
        })
    return cookies


def find_chromium():
    # Locate system-installed Chromium
    for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium"]:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Chromium binary not found on system")


def do_upload(video_path, title, cookies_path):
    """
    Upload via Playwright using the system Chromium binary.
    """
    chromium_path = find_chromium()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chromium_path,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = browser.new_context()
        context.add_cookies(parse_netscape_cookies(cookies_path))
        page = context.new_page()
        page.goto("https://www.tiktok.com/upload?lang=en")

        # Upload video file
        page.set_input_files("input[type='file']", video_path)
        # Wait for description box to appear
        page.wait_for_selector("textarea[placeholder*='Describe']", timeout=30000)
        page.fill("textarea[placeholder*='Describe']", title)
        # Click Publish
        page.click("button[data-e2e='publish-button']")
        # Wait for success indicator
        page.wait_for_selector("div[data-e2e='publish-success']", timeout=60000)
        browser.close()

    return True, f"Uploaded '{title}' at {datetime.now():%Y-%m-%d %H:%M:%S}'"


def upload_and_report(video_path, title, cookies_path):
    try:
        ok, msg = do_upload(video_path, title, cookies_path)
    except Exception as e:
        st.error(f"❌ Upload error: {e}")
        return
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ {msg}")


def schedule_jobs(video_path, title, cookies_path):
    scheduler = BackgroundScheduler()
    def job():
        do_upload(video_path, title, cookies_path)
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler


def main():
    st.title("🎬 TikTok Scheduler")

    cookies_file = st.file_uploader(
        "1) Upload your TikTok cookies.txt (Netscape format)",
        type=["txt"]
    )
    video_file = st.file_uploader(
        "2) Upload your short video",
        type=["mp4", "mov"]
    )
    title = st.text_input("3) Video Title")

    if st.button("Start Scheduling"):
        if not cookies_file:
            st.error("Please upload cookies.txt first.")
            return
        if not video_file or not title:
            st.error("Please upload a video and enter a title.")
            return

        ck = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        ck.write(cookies_file.read()); ck.flush()
        vp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        vp.write(video_file.read()); vp.flush()

        st.session_state.scheduler = schedule_jobs(vp.name, title, ck.name)
        upload_and_report(vp.name, title, ck.name)

    if "scheduler" in st.session_state:
        job = st.session_state.scheduler.get_job("tiktok_job")
        if job:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            st.write("**Next scheduled upload:**", next_run)
            if st.button("Run Now"):
                upload_and_report(vp.name, title, ck.name)

if __name__ == "__main__":
    main()

import sys
import subprocess
import tempfile
import streamlit as st
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from http.cookiejar import MozillaCookieJar
from playwright.sync_api import sync_playwright

# ─── Bootstrap Playwright at runtime ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _ensure_playwright():
    try:
        # Try to import to see if browsers are already installed
        import playwright._impl._connection
        return
    except ImportError:
        pass

    st.sidebar.info("Installing Playwright browsers (this may take ~60s)…")
    # 1) Ensure the package is installed
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "playwright"], check=True)
    # 2) Install the browser binaries
    subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps"], check=True)

# Run the above at startup (cached)
try:
    _ensure_playwright()
except subprocess.CalledProcessError as e:
    st.sidebar.error(f"Playwright install failed ({e.returncode}), uploads may not work.")


# ─── TikTok Upload Logic via Playwright ───────────────────────────────────────

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

def do_upload(video_path, title, cookies_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage"]
        )
        ctx = browser.new_context()
        ctx.add_cookies(parse_netscape_cookies(cookies_path))
        page = ctx.new_page()
        page.goto("https://www.tiktok.com/upload?lang=en")

        page.set_input_files("input[type='file']", video_path)
        page.wait_for_selector("textarea[placeholder*='Describe']", timeout=30000)
        page.fill("textarea[placeholder*='Describe']", title)
        page.click("button[data-e2e='publish-button']")
        page.wait_for_selector("div[data-e2e='publish-success']", timeout=60000)
        browser.close()

    return True, f"Uploaded '{title}' @ {datetime.now():%Y-%m-%d %H:%M:%S}"

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
    sched = BackgroundScheduler()
    def job():
        do_upload(video_path, title, cookies_path)
    sched.add_job(job, "interval", hours=2, id="tiktok_job")
    sched.start()
    return sched


# ─── Streamlit UI ─────────────────────────────────────────────────────────────

def main():
    st.title("🎬 TikTok Scheduler")

    cookies_file = st.file_uploader(
        "1) Upload your TikTok cookies.txt (Netscape format)", type="txt"
    )
    video_file = st.file_uploader(
        "2) Upload your short video", type=["mp4","mov"]
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

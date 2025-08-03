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
        # already installed?
        import playwright._impl._connection  # noqa
        return
    except ImportError:
        pass

    st.sidebar.info("⚙️ Installing Playwright and browsers (may take ~60s)...")
    # use same Python interpreter
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps"], check=True)
    st.sidebar.success("✅ Playwright ready!")

try:
    _ensure_playwright()
except Exception as e:
    st.sidebar.error(f"Playwright installation failed: {e}")

# ─── Cookie Parsing ────────────────────────────────────────────────────────────
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

# ─── TikTok Upload ────────────────────────────────────────────────────────────
def do_upload(video_path, title, cookies_path):
    st.sidebar.write(f"🕒 {datetime.now():%H:%M:%S} Starting upload job")
    print(f"[{datetime.now():%H:%M:%S}] do_upload() → loading cookies & launching browser", flush=True)
    cookies = parse_netscape_cookies(cookies_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = browser.new_context()
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto("https://www.tiktok.com/upload?lang=en")

        page.set_input_files("input[type='file']", video_path)
        page.wait_for_selector("textarea[placeholder*='Describe']", timeout=30000)
        page.fill("textarea[placeholder*='Describe']", title)
        page.click("button[data-e2e='publish-button']")
        page.wait_for_selector("div[data-e2e='publish-success']", timeout=60000)
        browser.close()

    print(f"[{datetime.now():%H:%M:%S}] do_upload() → success", flush=True)
    return True, f"Uploaded '{title}' at {datetime.now():%Y-%m-%d %H:%M:%S}"

def upload_and_report(video_path, title, cookies_path):
    with st.spinner("🚀 Uploading now…"):
        try:
            ok, msg = do_upload(video_path, title, cookies_path)
        except Exception as e:
            st.error(f"❌ Upload error: {e}")
            print(f"[{datetime.now():%H:%M:%S}] ERROR during do_upload(): {e}", flush=True)
            return
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ {msg}")

# ─── Scheduler ────────────────────────────────────────────────────────────────
def schedule_jobs(video_path, title, cookies_path):
    st.sidebar.write("⏲️ Scheduling uploads every 2 hours")
    scheduler = BackgroundScheduler()
    def job():
        print(f"[{datetime.now():%H:%M:%S}] Running scheduled job…", flush=True)
        do_upload(video_path, title, cookies_path)
    scheduler.add_job(job, "interval", hours=2, id="tiktok_job")
    scheduler.start()
    return scheduler

# ─── Streamlit UI ─────────────────────────────────────────────────────────────
def main():
    st.title("🎬 TikTok Scheduler")

    cookies_file = st.file_uploader(
        "1) Upload your TikTok cookies.txt (Netscape format)", type="txt", help="Export via your browser extension"
    )
    video_file = st.file_uploader(
        "2) Upload your short video", type=["mp4","mov"], help="Max 60s"
    )
    title = st.text_input("3) Video Title")

    if st.button("Start Scheduling"):
        st.write("---")
        if not cookies_file:
            st.error("Please upload **cookies.txt** first.")
            return
        if not video_file or not title:
            st.error("Please upload a video and enter a title.")
            return

        # Save to temp
        ck = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        ck.write(cookies_file.read()); ck.flush()
        vp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        vp.write(video_file.read()); vp.flush()

        # Schedule + immediate run
        st.session_state.scheduler = schedule_jobs(vp.name, title, ck.name)
        upload_and_report(vp.name, title, ck.name)

    # Show next-run & manual trigger
    if "scheduler" in st.session_state:
        job = st.session_state.scheduler.get_job("tiktok_job")
        if job:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            st.write(f"**Next scheduled upload:** {next_run}")
            if st.button("Run Now"):
                upload_and_report(vp.name, title, ck.name)

if __name__ == "__main__":
    main()

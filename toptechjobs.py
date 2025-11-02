import os, json, requests, datetime, traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- CONFIG ---
API_KEY = os.getenv("RAPIDAPI_KEY") or "841dbe29d5msh790ecbf1042fa50p14de78jsn602f79fdbc8c"
TITLE = "Top Tech Jobs of the Week – India 🇮🇳"
REPO_PATH = Path(__file__).parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SESSION_FILE = "linkedin_session.json"
BASE_URL = "https://nishantshinde2503.github.io/JobLoop"  # 👈 change if using Netlify/custom domain

# --- UTILS ---
def log(msg, level="info"):
    colors = {"info": "\033[94m", "ok": "\033[92m", "warn": "\033[93m", "error": "\033[91m", "end": "\033[0m"}
    print(f"{colors.get(level, '')}{msg}{colors['end']}")

# --- FETCH JOBS ---
def fetch_jobs():
    log("📡 Fetching latest jobs from API...")
    try:
        r = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": "jsearch.p.rapidapi.com"},
            params={"query": "data engineer in india", "num_pages": 1, "date_posted": "week"},
            timeout=15
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            raise ValueError("No data returned from API.")
        jobs = [
            {"title": j["job_title"], "company": j["employer_name"], "loc": j.get("job_city", ""), "url": j["job_apply_link"]}
            for j in data[:6]
        ]
        REPO_PATH.joinpath("jobs.json").write_text(json.dumps(jobs, indent=2))
        log(f"✅ Fetched {len(jobs)} jobs successfully!")
        return jobs
    except Exception as e:
        log(f"❌ Error fetching jobs: {e}", "error")
        traceback.print_exc()
        return []

# --- GENERATE HTML ---
def make_html(jobs):
    try:
        html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>{TITLE}</title>
        <style>
            body{{font-family:sans-serif;max-width:700px;margin:auto;padding:20px}}
            .job{{border:1px solid #ddd;padding:10px;border-radius:8px;margin:10px 0;transition:background 0.5s}}
            .highlight{{background: #fff7a1 !important;}}
            a{{color:#0073b1;text-decoration:none}}
            a:hover{{text-decoration:underline}}
        </style>
        <script>
            window.onload = function() {{
                const hash = window.location.hash;
                if (hash) {{
                    const el = document.querySelector(hash);
                    if (el) {{
                        el.classList.add('highlight');
                        el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        setTimeout(() => el.classList.remove('highlight'), 4000);
                    }}
                }}
            }}
        </script>
        </head><body>
        <h1>🚀 {TITLE}</h1>"""
        for i, j in enumerate(jobs):
            html += f"<div id='job-{i}' class='job'><a href='{j['url']}' target='_blank'><b>{j['title']}</b></a><br>{j['company']} – {j['loc']}</div>"
        html += f"<footer><hr>Updated {datetime.datetime.now().strftime('%d %b %Y')}</footer></body></html>"
        REPO_PATH.joinpath("index.html").write_text(html)
        log("📄 HTML updated successfully!", "ok")
    except Exception as e:
        log(f"❌ Failed to write HTML: {e}", "error")
        traceback.print_exc()

# --- IMAGE GENERATOR ---
def make_image(jobs):
    try:
        W, H = 1080, 1080
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        for y in range(H):
            r = int(245 - (y / H) * 60)
            g = int(245 - (y / H) * 100)
            b = int(255 - (y / H) * 120)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        title_font = ImageFont.truetype(FONT, 70)
        job_font = ImageFont.truetype(FONT, 40)
        footer_font = ImageFont.truetype(FONT, 30)

        draw.text((60, 70), "🚀 Top Tech Jobs of the Week", font=title_font, fill=(15, 15, 15))
        draw.line([(60, 150), (1020, 150)], fill=(50, 50, 50), width=3)

        y = 200
        for j in jobs[:5]:
            text = f"💼 {j['title']} @ {j['company']}"
            draw.text((70, y), text[:55] + ("..." if len(text) > 55 else ""), font=job_font, fill=(20, 20, 20))
            y += 90

        draw.text((60, 950), "Follow @TopTechJobs for weekly updates 💼", font=footer_font, fill=(40, 40, 40))

        img_path = REPO_PATH / "top_jobs_post.png"
        img.save(img_path)
        log(f"🖼️ Generated image saved to {img_path}", "ok")
        return img_path
    except Exception as e:
        log(f"❌ Error generating image: {e}", "error")
        traceback.print_exc()
        return None

# --- LINKEDIN POST ---
def post_linkedin(jobs):
    text = "🚀 Top Tech Jobs of the Week 🇮🇳\n\n"
    for i, j in enumerate(jobs):
        job_link = f"{BASE_URL}/#job-{i}"
        text += f"💼 {j['title']} at {j['company']} ({j['loc']})\n🔗 {job_link}\n\n"
    text += "#TopTechJobs #India #TechCareers #AI #Developers"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context(storage_state=SESSION_FILE)
        page = ctx.new_page()
        log("🌐 Opening LinkedIn feed...", "info")
        page.goto("https://www.linkedin.com/feed/", timeout=60000)

        try:
            page.wait_for_selector("div[data-id]", timeout=30000)
            log("✅ Feed loaded successfully.", "ok")
        except Exception:
            log("⚠️ Might not fully load feed — proceeding anyway.", "warn")

        clicked = False
        for sel in [
            "button:has-text('Start a post')",
            "div:has-text('Start a post')",
            "button[aria-label='Start a post']",
            "span:has-text('Start a post')"
        ]:
            try:
                page.locator(sel).first.click(timeout=5000)
                log(f"🪄 Clicked '{sel}' button.", "info")
                clicked = True
                break
            except Exception as e:
                log(f"⚠️ Selector {sel} failed: {e}", "warn")

        if not clicked:
            log("❌ Could not find the 'Start a post' button. Exiting.", "error")
            browser.close()
            return

        try:
            textbox = page.wait_for_selector("div[role='textbox']", timeout=20000)
            textbox.click()
            textbox.fill(text)
            log("✍️ Filled post text.", "ok")
        except Exception as e:
            log(f"❌ Failed to fill textbox: {e}", "error")
            browser.close()
            return

        try:
            log("👀 Checking visibility settings...", "info")
            page.wait_for_timeout(1000)
            if page.is_visible("button:has-text('Anyone')"):
                log("✅ Visibility already set to Public.", "ok")
            elif page.is_visible("button:has-text('Connections')"):
                log("🔄 Changing visibility to Public...", "warn")
                page.locator("button:has-text('Connections')").click()
                page.wait_for_selector("div[role='menu'] >> text=Anyone", timeout=5000)
                page.locator("div[role='menu'] >> text=Anyone").click()
                log("🌍 Set visibility to 'Anyone'.", "ok")
        except Exception as e:
            log(f"⚠️ Skipping visibility check: {e}", "warn")

        posted = False
        for sel in [
            "button.share-actions__primary-action",
            "button:has-text('Post')",
            "button[aria-label='Post']",
            "button[role='button']:has-text('Post')"
        ]:
            try:
                page.wait_for_selector(sel, timeout=10000)
                page.locator(sel).first.click(timeout=5000)
                log(f"✅ Clicked '{sel}' button.", "ok")
                posted = True
                break
            except Exception as e:
                log(f"⚠️ Selector {sel} failed: {e}", "warn")

        if posted:
            log("🎉 Text-only post created successfully!", "ok")
        else:
            log("❌ Could not click Post button — layout may have changed.", "error")

        page.wait_for_timeout(5000)
        browser.close()

# --- MAIN ---
if __name__ == "__main__":
    log("🚀 Starting Top Tech Jobs Automation...")
    try:
        jobs = fetch_jobs()
        if jobs:
            make_html(jobs)
            img = make_image(jobs)
            log("✅ Updated website + image successfully!", "ok")
            post_linkedin(jobs)
        else:
            log("⚠️ No jobs found, skipping HTML/image generation.", "warn")
    except Exception as e:
        log(f"💥 Unexpected error: {e}", "error")
        traceback.print_exc()

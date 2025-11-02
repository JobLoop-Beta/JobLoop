import os, json, requests, datetime, traceback, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- CONFIG ---
API_KEY = os.getenv("RAPIDAPI_KEY") or "841dbe29d5msh790ecbf1042fa50p14de78jsn602f79fdbc8c"
TITLE = "Top Tech Jobs of the Week – India 🇮🇳"
REPO_PATH = Path(__file__).parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SESSION_FILE = "linkedin_session.json"
BASE_URL = "https://jobloop-beta.github.io/JobLoop/"  # 👈 change if using Netlify/custom domain

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
            params={"query": "data scientist jobs in pune", "num_pages": 1, "date_posted": "week"},
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
def post_single_job(job, index, page):
    """Helper function to create a single job post"""
    job_link = f"https://jobloop-beta.github.io/JobLoop/#job-{index}"
    
    text = f"""🚀 Featured Tech Job of the Week 🇮🇳

💼 {job['title']}
🏢 {job['company']}
📍 {job['loc']}

👉 View details and apply: {job_link}

#TechJobs #India #Hiring #Technology"""

    try:
        # Click start post button
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
                continue

        if not clicked:
            raise Exception("Could not find 'Start a post' button")

        # Fill post text
        textbox = page.wait_for_selector("div[role='textbox']", timeout=20000)
        textbox.click()
        textbox.fill(text)
        
        # Set visibility if needed
        if page.is_visible("button:has-text('Connections')"):
            page.locator("button:has-text('Connections')").click()
            page.wait_for_selector("div[role='menu'] >> text=Anyone", timeout=5000)
            page.locator("div[role='menu'] >> text=Anyone").click()

        # Post
        for sel in [
            "button.share-actions__primary-action",
            "button:has-text('Post')",
            "button[aria-label='Post']",
            "button[role='button']:has-text('Post')"
        ]:
            try:
                page.wait_for_selector(sel, timeout=10000)
                page.locator(sel).first.click(timeout=5000)
                log(f"✅ Posted job {index + 1}: {job['title']}", "ok")
                page.wait_for_timeout(3000)  # Wait between posts
                return True
            except Exception:
                continue
                
        return False
    except Exception as e:
        log(f"❌ Failed to post job {index + 1}: {e}", "error")
        return False

def post_linkedin(jobs):
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

        # Post each job individually
        successful_posts = 0
        for i, job in enumerate(jobs):
            if post_single_job(job, i, page):
                successful_posts += 1
            page.wait_for_timeout(2000)  # Small delay between posts

        log(f"🎉 Created {successful_posts} individual job posts!", "ok")
        page.wait_for_timeout(3000)
        browser.close()

# --- MAIN ---
if __name__ == "__main__":
    log("🚀 Starting Top Tech Jobs Automation...")
    try:
        jobs = fetch_jobs()
        if jobs:
            make_html(jobs)
            img = make_image(jobs)
            
            # Only post to LinkedIn if running locally and session file exists
            if os.path.exists(SESSION_FILE):
                post_linkedin(jobs)
                
            log("✅ Process completed successfully!", "ok")
        else:
            log("⚠️ No jobs found, skipping updates.", "warn")
    except Exception as e:
        log(f"💥 Unexpected error: {e}", "error")
        traceback.print_exc()

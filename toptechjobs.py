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
            params={"query": "data engineer jobs in london", "num_pages": 1, "date_posted": "week"},
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
        # Read existing jobs from index.html if it exists
        existing_jobs = []
        html_file = REPO_PATH / "index.html"
        if html_file.exists():
            existing_content = html_file.read_text()
            try:
                # Extract existing jobs from the HTML content
                existing_jobs = [
                    {
                        "title": line.split('data-title="')[1].split('"')[0],
                        "company": line.split('data-company="')[1].split('"')[0],
                        "loc": line.split('data-location="')[1].split('"')[0],
                        "url": line.split('data-url="')[1].split('"')[0],
                    }
                    for line in existing_content.split('<article class="job-card"')[1:]
                ]
            except:
                # Fallback for old format
                pass

        # Combine new jobs with existing jobs (new jobs first)
        all_jobs = jobs + [job for job in existing_jobs if job not in jobs]

        # Generate HTML content
        html = f"""<!DOCTYPE html><html><head>
        <meta charset='utf-8'>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Top Tech Jobs India</title>
        <style>
            :root {{
                --primary-color: #2557a7;
                --border-color: #e4e4e4;
                --text-primary: #2d2d2d;
                --text-secondary: #505050;
                --background: #f9fafb;
            }}
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: var(--background);
                color: var(--text-primary);
                line-height: 1.6;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                width: 100%;
                max-width: 800px;
                margin: 0 auto;
                padding: 16px;
            }}
            header {{
                background: white;
                border-bottom: 1px solid var(--border-color);
                position: sticky;
                top: 0;
                z-index: 100;
            }}
            .header-content {{
                max-width: 800px;
                margin: 0 auto;
                padding: 24px 16px;
            }}
            h1 {{
                font-size: 24px;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 8px;
            }}
            .subtitle {{
                color: var(--text-secondary);
                font-size: 16px;
            }}
            .job-grid {{
                display: grid;
                gap: 16px;
                margin: 24px 0;
            }}
            .job-card {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                padding: 24px;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                border: 1px solid var(--border-color);
            }}
            .job-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            }}
            .job-title {{
                font-size: 18px;
                font-weight: 600;
                color: var(--primary-color);
                margin-bottom: 8px;
                text-decoration: none;
            }}
            .job-title:hover {{
                text-decoration: underline;
            }}
            .job-company {{
                font-weight: 500;
                color: var(--text-primary);
                margin-bottom: 4px;
            }}
            .job-location {{
                color: var(--text-secondary);
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            .ad-space {{
                background: white;
                border-radius: 12px;
                padding: 24px;
                margin: 24px 0;
                text-align: center;
                border: 1px solid var(--border-color);
            }}
            .visitor-count {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: var(--primary-color);
                color: white;
                padding: 4px 12px;
                border-radius: 16px;
                font-size: 14px;
                margin-top: 8px;
            }}
            #visits {{
                font-weight: 600;
            }}
            .highlight {{
                background: #fff7a1 !important;
            }}
            @media (min-width: 640px) {{
                .job-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
                h1 {{
                    font-size: 32px;
                }}
            }}
        </style>
        <script>
            window.onload = function() {{
                // Handle hash highlighting
                const hash = window.location.hash;
                if (hash) {{
                    const el = document.querySelector(hash);
                    if (el) {{
                        el.classList.add('highlight');
                        el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        setTimeout(() => el.classList.remove('highlight'), 4000);
                    }}
                }}
                
                // Initialize visitor counter
                const getVisitorCount = async () => {{
                    try {{
                        const response = await fetch('https://api.countapi.xyz/hit/jobloop-jobs/visits');
                        const data = await response.json();
                        document.getElementById('visits').textContent = data.value.toLocaleString();
                    }} catch (error) {{
                        console.error('Error fetching visitor count:', error);
                    }}
                }};
                getVisitorCount();
            }}
        </script>
        </head>
        <body>
        <header>
            <div class="header-content">
                <h1>Top Tech Jobs India</h1>
                <p class="subtitle">Latest opportunities in technology</p>
                <div class="visitor-count">
                    <span id="visits">0</span> visitors
                </div>
            </div>
        </header>
        <main class="container">
            <div class="ad-space">
                <p>Advertisement Space</p>
            </div>
            <div class="job-grid">"""

        for i, j in enumerate(all_jobs):
            html += f"""
            <article class="job-card" id="job-{i}"
                data-title="{j['title']}"
                data-company="{j['company']}"
                data-location="{j['loc']}"
                data-url="{j['url']}">
                <a href="{j['url']}" class="job-title" target="_blank">{j['title']}</a>
                <div class="job-company">{j['company']}</div>
                <div class="job-location">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                        <circle cx="12" cy="10" r="3"></circle>
                    </svg>
                    {j['loc'] if j['loc'] else 'Location Flexible'}
                </div>
            </article>"""

        html += """
            </div>
            <div class="ad-space">
                <p>Advertisement Space</p>
            </div>
        </main>
        <footer style="text-align: center; padding: 24px; color: var(--text-secondary); font-size: 14px; border-top: 1px solid var(--border-color);">
            <p>Updated {}</p>
        </footer>
        </body></html>""".format(datetime.datetime.now().strftime('%d %b %Y'))
        html_file.write_text(html)
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
    location = job['loc'] if job['loc'] else 'Location Flexible'
    
    text = f"""We're hiring at {job['company']}!

Position: {job['title']}
Location: {location}
Employment Type: Full-time

Are you passionate about technology and looking for your next challenge? We have an exciting opportunity that might be perfect for you.

Learn more and apply here: {job_link}

Share with someone who might be interested.

#CareerOpportunity #JobSearch #TechCareers #India"""

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

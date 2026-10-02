import html
import re
from datetime import datetime, timezone
import httpx
from src.models import (
    JobListing, classify_specialization, classify_experience,
    classify_work_mode, classify_region, extract_tags, evaluate_immigration_clearance
)

def clean_html(text: str) -> str:
    if not text: return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    return html.unescape(' '.join(clean.split()))

async def collect_workday(client: httpx.AsyncClient, comp: dict, semaphore) -> list:
    async with semaphore:
        instance = comp.get("wday_instance", comp["slug"])
        path = comp.get("wday_path", "External")
        url = f"https://{instance}.wd1.myworkdayjobs.com/wday/cxs/{instance}/{path}/jobs"
        
        # Workday expects a POST request with pagination & search payload
        payload = {
            "appliedFacets": {},
            "limit": 50,
            "offset": 0,
            "searchText": "Security Engineer"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            res = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if res.status_code != 200:
                # Try wd5 tenant fallback common in US East
                url_wd5 = f"https://{instance}.wd5.myworkdayjobs.com/wday/cxs/{instance}/{path}/jobs"
                res = await client.post(url_wd5, json=payload, headers=headers, timeout=15.0)
                if res.status_code != 200:
                    return []

            data = res.json()
            postings = data.get("jobPostings", [])
            results = []

            for p in postings:
                title = p.get("title", "")
                loc = p.get("locationsText", "Remote")
                job_path = p.get("externalPath", "")
                full_url = f"https://{instance}.wd1.myworkdayjobs.com/en-US/{instance}/{path}{job_path}"
                posted_date = p.get("postedOn", "")
                
                # Fetch basic description or construct overview
                desc = f"{title} position at {comp['name']} in {loc}."
                h1b, opt, clearance = evaluate_immigration_clearance(desc)
                exp = classify_experience(title)

                # Target strictly Entry-Level (0-2 yrs) and Mid-Level (3-5 yrs)
                if exp in ["Senior (5+ yrs)", "Lead / Staff / Principal"]:
                    continue

                results.append(JobListing(
                    id=f"wday-{comp['slug']}-{p.get('bulletFields', [''])[0] or abs(hash(job_path))}",
                    company=comp["name"],
                    title=title,
                    location=loc,
                    url=full_url,
                    description=desc,
                    ats="workday",
                    posted_at=datetime.now(timezone.utc).isoformat(),
                    tags=extract_tags(f"{title} {desc}"),
                    specialization=classify_specialization(title, desc),
                    experience_level=exp,
                    work_mode=classify_work_mode(loc, title, desc),
                    region=classify_region(loc),
                    h1b_available=h1b,
                    opt_friendly=opt,
                    clearance_required=clearance
                ))

            return results
        except Exception:
            return []

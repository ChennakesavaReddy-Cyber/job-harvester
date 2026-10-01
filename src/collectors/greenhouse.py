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

async def collect_greenhouse(client: httpx.AsyncClient, comp: dict, semaphore) -> list:
    async with semaphore:
        url = f"https://boards-api.greenhouse.io/v1/boards/{comp['slug']}/jobs?content=true"
        try:
            res = await client.get(url, timeout=12.0)
            if res.status_code != 200: return []
            raw_jobs = res.json().get("jobs", [])
            results = []
            for j in raw_jobs:
                title = j.get("title", "")
                desc = clean_html(j.get("content", ""))
                loc = j.get("location", {}).get("name", "Remote")
                updated = j.get("updated_at") or datetime.now(timezone.utc).isoformat()
                
                h1b, opt, clearance = evaluate_immigration_clearance(desc)
                combined = f"{title} {desc}"

                results.append(JobListing(
                    id=f"gh-{comp['slug']}-{j['id']}",
                    company=comp["name"],
                    title=title,
                    location=loc,
                    url=j.get("absolute_url"),
                    description=desc,
                    ats="greenhouse",
                    posted_at=updated,
                    tags=extract_tags(combined),
                    specialization=classify_specialization(title, desc),
                    experience_level=classify_experience(title),
                    work_mode=classify_work_mode(loc, title, desc),
                    region=classify_region(loc),
                    h1b_available=h1b,
                    opt_friendly=opt,
                    clearance_required=clearance
                ))
            return results
        except Exception:
            return []
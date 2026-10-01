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

async def collect_lever(client: httpx.AsyncClient, comp: dict, semaphore) -> list:
    async with semaphore:
        url = f"https://api.lever.co/v0/postings/{comp['slug']}?mode=json"
        try:
            res = await client.get(url, timeout=12.0)
            if res.status_code != 200: return []
            raw_jobs = res.json()
            results = []
            for j in raw_jobs:
                title = j.get("text", "")
                desc = j.get("descriptionPlain", "") or clean_html(j.get("description", ""))
                loc = j.get("categories", {}).get("location", "Remote")
                
                created_ts = j.get("createdAt")
                posted_at = datetime.fromtimestamp(created_ts / 1000.0, timezone.utc).isoformat() if created_ts else datetime.now(timezone.utc).isoformat()

                h1b, opt, clearance = evaluate_immigration_clearance(desc)
                combined = f"{title} {desc}"

                results.append(JobListing(
                    id=f"lev-{comp['slug']}-{j['id']}",
                    company=comp["name"],
                    title=title,
                    location=loc,
                    url=j.get("hostedUrl"),
                    description=desc,
                    ats="lever",
                    posted_at=posted_at,
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
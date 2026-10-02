import httpx
from datetime import datetime, timezone
from src.models import (
    JobListing, classify_specialization, classify_experience,
    classify_work_mode, classify_region, extract_tags, evaluate_immigration_clearance
)

async def collect_enterprise(client: httpx.AsyncClient, comp: dict, semaphore) -> list:
    async with semaphore:
        slug = comp["slug"]
        results = []

        try:
            # 1. Amazon Jobs Public API
            if slug == "amazon":
                url = "https://www.amazon.jobs/en/search.json?base_query=Security+Engineer&result_limit=40"
                res = await client.get(url, timeout=12.0)
                if res.status_code == 200:
                    for j in res.json().get("jobs", []):
                        title = j.get("title", "")
                        exp = classify_experience(title)
                        if exp in ["Senior (5+ yrs)", "Lead / Staff / Principal"]:
                            continue
                        loc = f"{j.get('city', '')}, {j.get('state', '')}"
                        desc = j.get("description_short", "")
                        h1b, opt, clearance = evaluate_immigration_clearance(desc)
                        results.append(JobListing(
                            id=f"amz-{j.get('id_icims', '')}",
                            company="Amazon",
                            title=title,
                            location=loc or "Seattle / Washington",
                            url=f"https://www.amazon.jobs{j.get('job_path')}",
                            description=desc,
                            ats="amazon-enterprise",
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

            # 2. Uber Public Careers
            elif slug == "uber":
                url = "https://www.uber.com/api/loadSearchJobsResults?localeCode=en"
                payload = {"params": {"searchKeyword": "Security", "limit": 40}}
                res = await client.post(url, json=payload, timeout=12.0)
                if res.status_code == 200:
                    for j in res.json().get("data", {}).get("results", []):
                        title = j.get("title", "")
                        exp = classify_experience(title)
                        if exp in ["Senior (5+ yrs)", "Lead / Staff / Principal"]:
                            continue
                        loc = j.get("location", {}).get("city", "San Francisco")
                        results.append(JobListing(
                            id=f"uber-{j.get('id')}",
                            company="Uber Technologies",
                            title=title,
                            location=loc,
                            url=f"https://www.uber.com/global/en/careers/list/{j.get('id')}/",
                            description=title,
                            ats="uber-enterprise",
                            posted_at=datetime.now(timezone.utc).isoformat(),
                            tags=extract_tags(title),
                            specialization=classify_specialization(title, ""),
                            experience_level=exp,
                            work_mode=classify_work_mode(loc, title, ""),
                            region=classify_region(loc),
                            h1b_available=True,
                            opt_friendly=True,
                            clearance_required=False
                        ))

            return results
        except Exception:
            return []

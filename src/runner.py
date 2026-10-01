# src/runner.py
import asyncio
import json
import os
import shutil
import httpx
from src.collectors.greenhouse import collect_greenhouse
from src.collectors.lever import collect_lever
from src.collectors.ashby import collect_ashby

TARGET_KEYWORDS = [
    "security", "infosec", "appsec", "cloud security", "cyber",
    "threat", "soc", "vulnerability", "detection", "incident response",
    "iam", "cryptograph", "penetration", "devsecops", "sre", "platform engineer"
]

async def main():
    if not os.path.exists("data/companies.json"):
        print("Missing data/companies.json")
        return

    with open("data/companies.json", "r") as f:
        companies = json.load(f)

    semaphore = asyncio.Semaphore(25)
    headers = {"User-Agent": "SecOpsJobEngine/2.0"}
    all_jobs = []

    print(f"Starting collection across {len(companies)} company endpoints...")
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = []
        for comp in companies:
            ats = comp.get("ats", "").lower()
            if ats == "greenhouse":
                tasks.append(collect_greenhouse(client, comp, semaphore))
            elif ats == "lever":
                tasks.append(collect_lever(client, comp, semaphore))
            elif ats == "ashby":
                tasks.append(collect_ashby(client, comp, semaphore))

        batches = await asyncio.gather(*tasks)
        for batch in batches:
            all_jobs.extend(batch)

    # Filter for security / tech alignment
    filtered = []
    seen_ids = set()
    for j in all_jobs:
        if j.id in seen_ids:
            continue
        seen_ids.add(j.id)
        text_check = f"{j.title} {j.specialization}".lower()
        if any(k in text_check for k in TARGET_KEYWORDS):
            filtered.append(j.model_dump())

    os.makedirs("data", exist_ok=True)
    os.makedirs("web", exist_ok=True)

    with open("data/jobs.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2)

    # Copy to web/ for local and GitHub Pages hosting
    shutil.copy("data/jobs.json", "web/jobs.json")
    print(f"Ingested and normalized {len(filtered)} targeted listings into data/jobs.json and web/jobs.json.")

if __name__ == "__main__":
    asyncio.run(main())
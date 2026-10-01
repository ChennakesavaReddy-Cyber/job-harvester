# src/models.py
import re
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field

class JobListing(BaseModel):
    id: str
    company: str
    title: str
    location: str
    url: str
    description: str
    ats: str
    posted_at: str
    tags: List[str] = Field(default_factory=list)
    specialization: str
    experience_level: str
    work_mode: str
    region: str
    h1b_available: bool
    opt_friendly: bool
    clearance_required: bool

TECH_TAG_KEYWORDS = [
    "splunk", "python", "siem", "aws", "falcon", "dfir", "kubernetes",
    "docker", "burp suite", "tenable", "nessus", "bash", "powershell",
    "azure", "gcp", "iam", "sast", "sca", "owasp", "threat modeling",
    "suricata", "zeek", "wireshark", "terraform", "sql", "linux"
]

def classify_specialization(title: str, desc: str) -> str:
    text = f"{title} {desc}".lower()
    title_lower = title.lower()

    if any(k in title_lower for k in ["soc", "detection", "secops", "dfir", "incident response", "threat hunt", "blue team"]):
        return "SOC, Detection & SecOps"
    if any(k in title_lower for k in ["appsec", "application security", "product security", "vulnerability", "red team", "penetration", "iam", "crypto", "infosec", "security engineer"]):
        return "Cybersecurity & AppSec"
    if any(k in title_lower for k in ["ai", "machine learning", "ml", "llm", "data engineer", "data scientist"]):
        return "Data & Machine Learning"
    if any(k in title_lower for k in ["devops", "cloud", "sre", "infrastructure", "platform engineer", "site reliability"]):
        return "Cloud & DevOps / SRE"
    if any(k in title_lower for k in ["product manager", "tpm", "program manager", "systems design", "ux"]):
        return "Product & Systems Design"
    if any(k in title_lower for k in ["software engineer", "backend", "frontend", "full stack", "fullstack", "developer"]):
        return "Software Engineering"
    
    # Fallback checking description
    if any(k in text for k in ["siem", "soc analyst", "soar", "threat intelligence"]):
        return "SOC, Detection & SecOps"
    return "Cybersecurity & AppSec"

def classify_experience(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["staff", "principal", "lead", "architect", "director", "vp", "head of"]):
        return "Lead / Staff / Principal"
    if any(k in t for k in ["senior", "sr.", "sr ", "tier 3", "tier iii", "l3", "l4"]):
        return "Senior (5+ yrs)"
    if any(k in t for k in ["intern", "new grad", "associate", "junior", "jr.", "tier 1", "tier i", "l1", "entry"]):
        return "Entry Level / New Grad (0–2 yrs)"
    return "Mid-Level (3–5 yrs)"

def classify_work_mode(location: str, title: str, desc: str) -> str:
    combined = f"{location} {title} {desc[:500]}".lower()
    if "hybrid" in combined:
        return "Hybrid"
    if any(k in combined for k in ["remote", "virtual", "work from home", "anywhere"]):
        return "100% Remote"
    return "On-site"

def classify_region(location: str) -> str:
    loc = location.lower()
    if any(k in loc for k in ["ca", "california", "san francisco", "sf", "bay area", "silicon valley", "los angeles", "sunnyvale", "mountain view"]):
        return "California (SF, Silicon Valley, LA)"
    if any(k in loc for k in ["ny", "new york", "nyc", "manhattan", "brooklyn"]):
        return "New York, NY"
    if any(k in loc for k in ["wa", "washington", "seattle", "bellevue", "redmond"]):
        return "Seattle / Washington"
    if any(k in loc for k in ["tx", "texas", "austin", "dallas", "houston"]):
        return "Austin / Texas"
    if any(k in loc for k in ["va", "virginia", "dc", "district of columbia", "maryland", "mclean", "arlington", "reston", "fairfax"]):
        return "Virginia / DC Metro"
    return "Other / Remote"

def extract_tags(text: str) -> List[str]:
    lower_text = text.lower()
    return [tag for tag in TECH_TAG_KEYWORDS if re.search(rf"\b{re.escape(tag)}\b", lower_text)]

def evaluate_immigration_clearance(desc: str):
    d = desc.lower()
    
    # Clearance check
    clearance_patterns = [
        "security clearance", "secret clearance", "top secret", "ts/sci",
        "u.s. citizen only", "us citizenship required", "must be a u.s. citizen",
        "active clearance", "polygraph", "itar"
    ]
    clearance_required = any(k in d for k in clearance_patterns)

    # Visa sponsorship check
    no_sponsor_patterns = [
        "without sponsorship", "will not sponsor", "no visa sponsorship",
        "unable to sponsor", "not offering sponsorship", "no sponsorship now or in the future"
    ]
    has_no_sponsorship = any(k in d for k in no_sponsor_patterns)

    h1b_available = not has_no_sponsorship and not clearance_required
    opt_friendly = not clearance_required and ("opt" in d or "f-1" in d or not has_no_sponsorship)

    return h1b_available, opt_friendly, clearance_required
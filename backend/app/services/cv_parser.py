import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import fitz
import pdfplumber
from docx import Document


KNOWN_SKILLS = {
    "python",
    "fastapi",
    "django",
    "flask",
    "sql",
    "sql server",
    "postgresql",
    "mysql",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "node.js",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "redis",
    "celery",
    "playwright",
    "selenium",
    "machine learning",
    "data analysis",
    "power bi",
    "excel",
    "git",
    "linux",
    "tailwind",
}

KNOWN_LANGUAGES = {
    "english",
    "spanish",
    "portuguese",
    "french",
    "german",
    "inglés",
    "español",
    "portugués",
    "francés",
    "alemán",
}

ROLE_KEYWORDS = [
    "software engineer",
    "full stack engineer",
    "backend engineer",
    "frontend engineer",
    "data engineer",
    "data analyst",
    "data scientist",
    "devops engineer",
    "machine learning engineer",
    "product manager",
    "project manager",
    "qa engineer",
    "developer",
    "analyst",
    "engineer",
    "desarrollador",
    "ingeniero de software",
    "analista de datos",
]

LOCATION_KEYWORDS = [
    "lima",
    "peru",
    "perú",
    "bogota",
    "bogotá",
    "colombia",
    "santiago",
    "chile",
    "buenos aires",
    "argentina",
    "mexico",
    "méxico",
    "remote",
    "remoto",
]


def parse_resume_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        raw_text = extract_pdf_text(file_path)
    elif suffix == ".docx":
        raw_text = extract_docx_text(file_path)
    else:
        raise ValueError("Unsupported resume file type")

    normalized_text = normalize_text(raw_text)
    work_experience_items = extract_section_items(normalized_text, ["experience", "experiencia", "work history"])
    skills = extract_keywords(normalized_text, KNOWN_SKILLS)
    languages = extract_keywords(normalized_text, KNOWN_LANGUAGES)
    candidate_profile = extract_candidate_profile(normalized_text, work_experience_items, skills, languages)

    return {
        "raw_text": normalized_text,
        "work_experience": [{"text": item} for item in work_experience_items],
        "skills": skills,
        "education": [{"text": item} for item in extract_section_items(normalized_text, ["education", "educación", "formación"])],
        "certifications": extract_section_items(normalized_text, ["certifications", "certificaciones", "certificados"]),
        "languages": languages,
        "metadata": {
            "source_filename": file_path.name,
            "character_count": len(normalized_text),
            "parser": "pymupdf/pdfplumber/python-docx",
            "candidate_profile": candidate_profile,
        },
        "candidate_profile": candidate_profile,
    }


def extract_pdf_text(path: Path) -> str:
    try:
        with fitz.open(path) as document:
            return "\n".join(page.get_text("text") for page in document)
    except Exception:
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_docx_text(path: Path) -> str:
    document = Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_candidate_profile(
    text: str,
    work_experience: list[str],
    skills: list[str],
    languages: list[str],
) -> dict[str, Any]:
    urls = extract_urls(text)
    return {
        "full_name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": extract_location(text),
        "linkedin_url": find_url(urls, "linkedin.com"),
        "github_url": find_url(urls, "github.com"),
        "portfolio_url": extract_portfolio_url(urls),
        "experience_summary": summarize_experience(work_experience, text),
        "skills": skills,
        "languages": languages,
        "seniority": infer_seniority(text),
        "target_roles": infer_target_roles(text),
    }


def extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    match = re.search(r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,5}\d{2,4}", text)
    if not match:
        return None
    phone = re.sub(r"\s+", " ", match.group(0)).strip(" .-")
    digits = re.sub(r"\D", "", phone)
    return phone if len(digits) >= 7 else None


def extract_urls(text: str) -> list[str]:
    pattern = r"(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s,;)]*)?"
    urls = []
    for match in re.finditer(pattern, text):
        if match.start() > 0 and text[match.start() - 1] == "@":
            continue
        if match.end() < len(text) and text[match.end()] == "@":
            continue
        url = match.group(0).rstrip(".")
        if "@" in url:
            continue
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        urls.append(url)
    return list(dict.fromkeys(urls))


def find_url(urls: list[str], domain: str) -> str | None:
    for url in urls:
        if domain in urlparse(url).netloc.lower():
            return url
    return None


def extract_portfolio_url(urls: list[str]) -> str | None:
    blocked_domains = {"linkedin.com", "github.com", "gmail.com", "hotmail.com", "outlook.com", "yahoo.com"}
    for url in urls:
        netloc = urlparse(url).netloc.lower().removeprefix("www.")
        if not any(domain in netloc for domain in blocked_domains):
            return url
    return None


def extract_name(text: str) -> str | None:
    for line in [line.strip() for line in text.splitlines()[:12] if line.strip()]:
        lowered = line.lower()
        if any(token in lowered for token in ["@", "http", "linkedin", "github", "curriculum", "resume", "cv"]):
            continue
        if re.search(r"\d", line):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(len(word.strip(".,:;")) > 1 for word in words):
            return line.strip(" -|")
    return None


def extract_location(text: str) -> str | None:
    label_match = re.search(r"(?:location|ubicaci[oó]n|ciudad|city)\s*[:|-]\s*(.+)", text, re.IGNORECASE)
    if label_match:
        return label_match.group(1).splitlines()[0].strip(" .,-")

    lowered = text.lower()
    found = [keyword.title() for keyword in LOCATION_KEYWORDS if keyword in lowered]
    return ", ".join(found[:2]) if found else None


def summarize_experience(work_experience: list[str], text: str) -> str | None:
    if work_experience:
        return "\n".join(work_experience[:6])
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 40]
    return "\n".join(lines[:4]) if lines else None


def infer_seniority(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"\b(lead|principal|staff|manager|arquitecto|architect)\b", lowered):
        return "lead"
    if re.search(r"\b(senior|sr\.?|semi senior|semisenior)\b", lowered):
        return "senior"
    if re.search(r"\b(mid|middle|intermediate|intermedio)\b", lowered):
        return "mid"
    if re.search(r"\b(junior|jr\.?|trainee|intern|practicante)\b", lowered):
        return "junior"

    years = [int(value) for value in re.findall(r"(\d{1,2})\+?\s*(?:years|años|anos)", lowered)]
    if not years:
        return None
    max_years = max(years)
    if max_years >= 7:
        return "senior"
    if max_years >= 3:
        return "mid"
    return "junior"


def infer_target_roles(text: str) -> list[str]:
    lowered = text.lower()
    roles = [role.title() for role in ROLE_KEYWORDS if role in lowered]
    if roles:
        return list(dict.fromkeys(roles))[:5]

    first_lines = " ".join(line.strip() for line in text.splitlines()[:8])
    fallback = re.findall(r"\b(?:developer|engineer|analyst|desarrollador|ingeniero|analista)\b", first_lines, re.IGNORECASE)
    return list(dict.fromkeys(item.title() for item in fallback))[:3]


def extract_keywords(text: str, keywords: set[str]) -> list[str]:
    lowered = text.lower()
    found = []
    for keyword in sorted(keywords):
        if re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", lowered):
            found.append(keyword)
    return found


def extract_section_items(text: str, headings: list[str], limit: int = 10) -> list[str]:
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    section_lines: list[str] = []
    collecting = False

    for line in lines:
        lowered = line.lower().rstrip(":")
        is_heading = any(heading in lowered for heading in headings)
        if is_heading:
            collecting = True
            continue
        if collecting and looks_like_new_section(line):
            break
        if collecting:
            section_lines.append(line)

    if not section_lines:
        section_lines = lines[:limit]
    return section_lines[:limit]


def looks_like_new_section(line: str) -> bool:
    cleaned = line.strip().rstrip(":")
    if len(cleaned.split()) > 5:
        return False
    return cleaned.isupper() or cleaned.lower() in {
        "skills",
        "habilidades",
        "education",
        "educación",
        "certifications",
        "certificaciones",
        "languages",
        "idiomas",
        "projects",
        "proyectos",
    }

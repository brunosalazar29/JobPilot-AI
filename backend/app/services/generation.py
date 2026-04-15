from app.models import Job, ParsedResume, Profile


def generate_document_content(
    kind: str,
    profile: Profile | None,
    job: Job | None,
    parsed_resume: ParsedResume | None,
) -> tuple[str, str]:
    full_name = profile.full_name if profile and profile.full_name else "Candidate"
    role = job.title if job else "the role"
    company = job.company if job else "your company"
    skills = collect_skills(profile, parsed_resume)
    skills_sentence = ", ".join(skills[:8]) if skills else "relevant technical and product skills"

    if kind == "cover_letter":
        title = f"Cover letter - {company}"
        content = (
            f"Dear {company} team,\n\n"
            f"I am excited to apply for {role}. My background combines {skills_sentence}, "
            "with a practical focus on shipping reliable software and collaborating across teams.\n\n"
            "I would bring structured execution, clear communication and ownership of production outcomes. "
            "I am particularly interested in this opportunity because the role aligns with the problems I have solved "
            "and the kind of product impact I want to keep building.\n\n"
            f"Sincerely,\n{full_name}"
        )
        return title, content

    if kind == "professional_summary":
        title = "Professional summary"
        content = (
            f"{full_name} is a technology professional with experience in {skills_sentence}. "
            "They focus on building maintainable systems, improving workflows and turning requirements into usable products."
        )
        return title, content

    if kind == "tell_us_about_yourself":
        title = "Tell us about yourself"
        content = (
            f"I am {full_name}, a professional focused on {skills_sentence}. "
            "I enjoy solving practical problems, working with clear priorities and building systems that users can trust."
        )
        return title, content

    if kind == "why_this_company":
        title = f"Why {company}"
        content = (
            f"I want to work at {company} because the {role} position matches my experience in {skills_sentence}. "
            "The role looks like a strong fit for my interest in building useful software with measurable outcomes."
        )
        return title, content

    title = f"{kind.replace('_', ' ').title()} - {company}"
    content = (
        f"Suggested response for {role} at {company}: "
        f"My experience with {skills_sentence} is relevant to this requirement, and I can adapt the response to the form context."
    )
    return title, content


def generate_application_responses(profile: Profile | None, job: Job | None, parsed_resume: ParsedResume | None) -> dict[str, str]:
    return {
        "professional_summary": generate_document_content("professional_summary", profile, job, parsed_resume)[1],
        "tell_us_about_yourself": generate_document_content("tell_us_about_yourself", profile, job, parsed_resume)[1],
        "why_this_company": generate_document_content("why_this_company", profile, job, parsed_resume)[1],
        "short_pitch": generate_document_content("short_pitch", profile, job, parsed_resume)[1],
    }


def collect_skills(profile: Profile | None, parsed_resume: ParsedResume | None) -> list[str]:
    values = []
    if profile and profile.skills:
        values.extend(profile.skills)
    if parsed_resume and parsed_resume.skills:
        values.extend(parsed_resume.skills)
    seen = set()
    result = []
    for value in values:
        normalized = value.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(value.strip())
    return result

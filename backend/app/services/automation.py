from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from app.core.config import settings


async def prepare_application_form(
    url: str,
    profile_data: dict[str, Any],
    resume_path: str | None = None,
) -> dict[str, Any]:
    logs: list[dict[str, Any]] = []
    filled_fields: list[str] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=settings.playwright_headless)
        page = await browser.new_page()
        try:
            logs.append({"level": "info", "message": f"Opening {url}"})
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)

            candidates = {
                "full_name": profile_data.get("full_name"),
                "email": profile_data.get("email"),
                "phone": profile_data.get("phone"),
                "location": profile_data.get("location"),
                "linkedin": profile_data.get("linkedin_url"),
                "github": profile_data.get("github_url"),
                "portfolio": profile_data.get("portfolio_url"),
            }
            selectors = {
                "full_name": ["input[name*='name' i]", "input[id*='name' i]"],
                "email": ["input[type='email']", "input[name*='email' i]"],
                "phone": ["input[type='tel']", "input[name*='phone' i]", "input[id*='phone' i]"],
                "location": ["input[name*='location' i]", "input[id*='location' i]"],
                "linkedin": ["input[name*='linkedin' i]", "input[id*='linkedin' i]"],
                "github": ["input[name*='github' i]", "input[id*='github' i]"],
                "portfolio": ["input[name*='portfolio' i]", "input[id*='portfolio' i]", "input[name*='website' i]"],
            }

            for field, value in candidates.items():
                if not value:
                    continue
                for selector in selectors[field]:
                    locator = page.locator(selector).first
                    try:
                        await locator.fill(str(value), timeout=1200)
                        filled_fields.append(field)
                        logs.append({"level": "info", "message": f"Filled {field}", "selector": selector})
                        break
                    except Exception:
                        continue

            if resume_path and Path(resume_path).exists():
                file_inputs = page.locator("input[type='file']")
                input_count = await file_inputs.count()
                if input_count:
                    await file_inputs.nth(0).set_input_files(resume_path)
                    logs.append({"level": "info", "message": "Attached resume file"})

            logs.append({"level": "info", "message": "Application prepared. Final submission was not attempted."})
            return {
                "status": "ready_for_review",
                "filled_fields": sorted(set(filled_fields)),
                "logs": logs,
                "requires_manual_review": True,
            }
        except Exception as exc:
            logs.append({"level": "error", "message": str(exc)})
            return {"status": "needs_manual_action", "filled_fields": filled_fields, "logs": logs, "error": str(exc)}
        finally:
            await browser.close()

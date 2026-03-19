import os
import time
import threading
from typing import List, Optional, Union

import html2text
import tiktoken
from playwright.sync_api import sync_playwright, Browser, Playwright
from qwen_agent.tools.base import BaseTool, register_tool

BROWSE_PAGE_TIMEOUT = int(os.getenv("BROWSE_PAGE_TIMEOUT", 30000))
BROWSE_MAX_TOKENS = int(os.getenv("BROWSE_MAX_TOKENS", 95000))

_pw_lock = threading.Lock()
_pw_instance: Optional[Playwright] = None
_browser_instance: Optional[Browser] = None


def _get_browser() -> Browser:
    global _pw_instance, _browser_instance
    with _pw_lock:
        if _browser_instance is None or not _browser_instance.is_connected():
            if _pw_instance is not None:
                try:
                    _pw_instance.stop()
                except Exception:
                    pass
            _pw_instance = sync_playwright().start()
            _browser_instance = _pw_instance.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
            )
        return _browser_instance


def _truncate_to_tokens(text: str, max_tokens: int = BROWSE_MAX_TOKENS) -> str:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return encoding.decode(tokens[:max_tokens])


def _html_to_markdown(html: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.ignore_emphasis = False
    converter.body_width = 0
    converter.skip_internal_links = True
    converter.inline_links = True
    return converter.handle(html)


def _render_url(url: str, timeout_ms: int = BROWSE_PAGE_TIMEOUT, max_retries: int = 2) -> str:
    for attempt in range(max_retries):
        context = None
        try:
            browser = _get_browser()
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 15000))
            except Exception:
                pass
            raw_html = page.content()
            markdown = _html_to_markdown(raw_html)
            markdown = _truncate_to_tokens(markdown)
            return f"## Content of {url}\n\n{markdown}"
        except Exception as e:
            print(f"[browse] Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    return f"[browse] Failed to render {url} after {max_retries} attempts."


@register_tool("browse", allow_overwrite=True)
class Browse(BaseTool):
    name = "browse"
    description = (
        "Render a webpage in a real browser and return the full page content as markdown. "
        "Use this when visit fails on JavaScript-heavy pages or when you need "
        "the raw unstructured content without summarization."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": ["string", "array"],
                "items": {"type": "string"},
                "minItems": 1,
                "description": "The URL(s) of the webpage(s) to render in the browser.",
            },
        },
        "required": ["url"],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            url = params["url"]
        except (KeyError, TypeError):
            return "[browse] Invalid request format: Input must be a JSON object containing a 'url' field."

        start_time = time.time()

        if isinstance(url, str):
            result = _render_url(url)
        else:
            assert isinstance(url, list)
            results: List[str] = []
            for u in url:
                if time.time() - start_time > 300:
                    results.append(f"[browse] Skipped {u} — total browse time exceeded 5 minutes.")
                else:
                    results.append(_render_url(u))
            result = "\n=======\n".join(results)

        print(f"[browse] Result length: {len(result)} chars")
        return result.strip()

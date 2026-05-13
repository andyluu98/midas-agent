"""Auto-fallback search backend cho News/Sentiment/Fundamental Analyst.

Vấn đề: Yahoo + Alpha Vantage không có tin live cho XAUUSD/forex commodity.
LLM tự bịa data → quyết định trên thông tin sai.

Giải pháp: 4 backend chain tự động chọn theo key/CLI có sẵn:
  1. Tavily API     (best — TAVILY_API_KEY trong .env, free 1000/tháng)
  2. Anthropic web  (good — ANTHROPIC_API_KEY, tool web_search native)
  3. Claude CLI     (subprocess `claude --print`)
  4. Gemini CLI     (subprocess `gemini --prompt`)
  5. Skip (warn)    — không có backend, trả message yêu cầu set key.

Mỗi backend trả `list[SearchResult]` cùng format → analyst dùng đồng nhất.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    content: str             # snippet/summary
    published: Optional[str] = None  # ISO date or 'unknown'
    score: float = 0.0       # relevance 0-1


@dataclass
class SearchResponse:
    backend: str             # 'tavily' | 'anthropic' | 'claude_cli' | 'gemini_cli' | 'none'
    query: str
    results: list[SearchResult] = field(default_factory=list)
    summary: str = ''        # optional aggregated text from backend
    error: Optional[str] = None

    def format_for_llm(self) -> str:
        """Format kết quả thành text gọn để inject vào prompt LLM."""
        if self.error:
            return f"[Search backend: {self.backend}] LỖI: {self.error}"
        if not self.results and not self.summary:
            return f"[Search backend: {self.backend}] Không có kết quả cho '{self.query}'."
        lines = [f"[Search backend: {self.backend}] Query: {self.query}"]
        if self.summary:
            lines.append(f"\nTÓM TẮT:\n{self.summary}\n")
        if self.results:
            lines.append("KẾT QUẢ:")
            for i, r in enumerate(self.results[:10], 1):
                date_str = f" ({r.published})" if r.published else ""
                lines.append(f"\n{i}. {r.title}{date_str}")
                lines.append(f"   {r.url}")
                if r.content:
                    snippet = r.content[:300].replace("\n", " ")
                    lines.append(f"   {snippet}")
        return "\n".join(lines)


# ============================================================================
# Backend 1: Tavily
# ============================================================================
def _search_tavily(query: str, max_results: int = 8) -> SearchResponse:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return SearchResponse(backend="tavily", query=query, error="TAVILY_API_KEY missing")
    try:
        from tavily import TavilyClient
    except ImportError:
        return SearchResponse(
            backend="tavily", query=query,
            error="Install: pip install tavily-python"
        )
    try:
        client = TavilyClient(api_key=api_key)
        resp = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            topic="news",
        )
        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                published=r.get("published_date"),
                score=r.get("score", 0.0),
            )
            for r in resp.get("results", [])
        ]
        return SearchResponse(
            backend="tavily",
            query=query,
            results=results,
            summary=resp.get("answer", ""),
        )
    except Exception as exc:
        return SearchResponse(backend="tavily", query=query, error=str(exc))


# ============================================================================
# Backend 2: Anthropic web_search native tool
# ============================================================================
def _search_anthropic(query: str, max_results: int = 8) -> SearchResponse:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return SearchResponse(backend="anthropic", query=query, error="ANTHROPIC_API_KEY missing")
    try:
        import anthropic
    except ImportError:
        return SearchResponse(
            backend="anthropic", query=query,
            error="Install: pip install anthropic"
        )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{
                "role": "user",
                "content": f"Search for: {query}. Return {max_results} relevant articles "
                           f"with title, URL, date, and 2-3 sentence summary each."
            }],
        )
        # Parse text blocks + tool_use results
        summary_text = ""
        results: list[SearchResult] = []
        for block in msg.content:
            if hasattr(block, "text"):
                summary_text += block.text + "\n"
            elif hasattr(block, "type") and block.type == "web_search_tool_result":
                for item in getattr(block, "content", []):
                    results.append(SearchResult(
                        title=getattr(item, "title", ""),
                        url=getattr(item, "url", ""),
                        content=getattr(item, "encrypted_content", "")[:500],
                    ))
        return SearchResponse(
            backend="anthropic",
            query=query,
            results=results,
            summary=summary_text.strip(),
        )
    except Exception as exc:
        return SearchResponse(backend="anthropic", query=query, error=str(exc))


# ============================================================================
# Backend 3: Claude CLI subprocess
# ============================================================================
def _search_claude_cli(query: str, max_results: int = 8) -> SearchResponse:
    if not shutil.which("claude"):
        return SearchResponse(backend="claude_cli", query=query, error="claude CLI not in PATH")
    try:
        prompt = (
            f"Search the web for: {query}\n"
            f"Return {max_results} most relevant recent articles. Format each as:\n"
            f"TITLE: <title>\nURL: <url>\nDATE: <date>\nSUMMARY: <2-3 sentences>\n---\n"
            f"Just the search results, no preamble."
        )
        res = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True, timeout=90, encoding="utf-8",
        )
        if res.returncode != 0:
            return SearchResponse(
                backend="claude_cli", query=query,
                error=f"exit {res.returncode}: {res.stderr[:200]}"
            )
        # Parse blocks separated by ---
        results = _parse_cli_blocks(res.stdout)
        return SearchResponse(
            backend="claude_cli",
            query=query,
            results=results,
            summary=res.stdout[:1000] if not results else "",
        )
    except subprocess.TimeoutExpired:
        return SearchResponse(backend="claude_cli", query=query, error="timeout 90s")
    except Exception as exc:
        return SearchResponse(backend="claude_cli", query=query, error=str(exc))


# ============================================================================
# Backend 4: Gemini CLI subprocess
# ============================================================================
def _search_gemini_cli(query: str, max_results: int = 8) -> SearchResponse:
    if not shutil.which("gemini"):
        return SearchResponse(backend="gemini_cli", query=query, error="gemini CLI not in PATH")
    try:
        prompt = (
            f"Search Google for: {query}\n"
            f"Return {max_results} most relevant recent articles. Format each as:\n"
            f"TITLE: <title>\nURL: <url>\nDATE: <date>\nSUMMARY: <2-3 sentences>\n---"
        )
        res = subprocess.run(
            ["gemini", "--prompt", prompt],
            capture_output=True, text=True, timeout=90, encoding="utf-8",
        )
        if res.returncode != 0:
            return SearchResponse(
                backend="gemini_cli", query=query,
                error=f"exit {res.returncode}: {res.stderr[:200]}"
            )
        results = _parse_cli_blocks(res.stdout)
        return SearchResponse(
            backend="gemini_cli",
            query=query,
            results=results,
            summary=res.stdout[:1000] if not results else "",
        )
    except subprocess.TimeoutExpired:
        return SearchResponse(backend="gemini_cli", query=query, error="timeout 90s")
    except Exception as exc:
        return SearchResponse(backend="gemini_cli", query=query, error=str(exc))


def _parse_cli_blocks(text: str) -> list[SearchResult]:
    """Parse output CLI dạng 'TITLE: ... \\n URL: ... \\n DATE: ... \\n SUMMARY: ...'."""
    results = []
    for block in text.split("---"):
        block = block.strip()
        if not block:
            continue
        fields = {"TITLE": "", "URL": "", "DATE": "", "SUMMARY": ""}
        for line in block.splitlines():
            for key in fields:
                if line.startswith(f"{key}:"):
                    fields[key] = line[len(key) + 1:].strip()
        if fields["TITLE"] or fields["URL"]:
            results.append(SearchResult(
                title=fields["TITLE"],
                url=fields["URL"],
                content=fields["SUMMARY"],
                published=fields["DATE"] or None,
            ))
    return results


# ============================================================================
# Auto-fallback dispatcher
# ============================================================================
_BACKEND_ORDER = ("tavily", "anthropic", "claude_cli", "gemini_cli")

_BACKEND_FUNCS = {
    "tavily": _search_tavily,
    "anthropic": _search_anthropic,
    "claude_cli": _search_claude_cli,
    "gemini_cli": _search_gemini_cli,
}


def detect_available_backend() -> Optional[str]:
    """Return tên backend đầu tiên có thể dùng, hoặc None nếu không có gì."""
    if os.getenv("TAVILY_API_KEY"):
        return "tavily"
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic  # noqa: F401
            return "anthropic"
        except ImportError:
            pass
    if shutil.which("claude"):
        return "claude_cli"
    if shutil.which("gemini"):
        return "gemini_cli"
    return None


def search(query: str, max_results: int = 8, prefer: Optional[str] = None) -> SearchResponse:
    """Search web với auto-fallback chain.

    Args:
        query: Câu query (vd "XAUUSD gold news Fed CPI latest 24h").
        max_results: Số kết quả tối đa (default 8).
        prefer: Backend ưu tiên ('tavily'/'anthropic'/'claude_cli'/'gemini_cli').
                Nếu None, auto-detect theo thứ tự _BACKEND_ORDER.

    Returns: SearchResponse — luôn trả về object, kể cả khi không có backend.
    """
    order = (prefer,) + _BACKEND_ORDER if prefer else _BACKEND_ORDER
    seen = set()
    last_error = None
    for backend in order:
        if backend in seen or backend not in _BACKEND_FUNCS:
            continue
        seen.add(backend)
        # Skip nếu backend không available trước khi gọi (tiết kiệm subprocess)
        if backend == "tavily" and not os.getenv("TAVILY_API_KEY"):
            continue
        if backend == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            continue
        if backend == "claude_cli" and not shutil.which("claude"):
            continue
        if backend == "gemini_cli" and not shutil.which("gemini"):
            continue

        logger.info(f"[search] Trying backend: {backend} | query: {query[:80]}")
        resp = _BACKEND_FUNCS[backend](query, max_results)
        if resp.error is None and (resp.results or resp.summary):
            logger.info(f"[search] Success with {backend}: {len(resp.results)} results")
            return resp
        last_error = resp.error
        logger.warning(f"[search] {backend} failed: {resp.error}")

    # Hết backend
    return SearchResponse(
        backend="none",
        query=query,
        error=(
            "Không có search backend khả dụng. "
            "Thêm TAVILY_API_KEY (free 1000/tháng tại tavily.com), "
            "ANTHROPIC_API_KEY, hoặc cài Claude/Gemini CLI. "
            f"Last error: {last_error}"
        ),
    )


def print_active_backend() -> None:
    """In ra console backend đang active — gọi khi khởi động script."""
    backend = detect_available_backend()
    if backend:
        print(f"🔍 Search backend: {backend.upper()}")
    else:
        print(
            "⚠️  Search backend: NONE — News/Sentiment/Fundamental sẽ bị hạn chế.\n"
            "    Thêm TAVILY_API_KEY=... vào .env để bật search realtime."
        )

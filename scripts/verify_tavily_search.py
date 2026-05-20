from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.core.config import load_local_env
from backend.eva.tools.tavily_search import tavily_search, tavily_status


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


async def _verify_search() -> None:
    load_local_env(ROOT / ".env")
    status = tavily_status()
    configured = bool(status.get("tavily_configured"))
    _print_json(
        {
            "tavily_configured": configured,
            "max_results": status.get("max_results"),
            "search_depth": status.get("search_depth"),
            "include_answer": status.get("include_answer"),
            "browser_fallback_enabled": status.get("browser_fallback_enabled"),
        }
    )

    if not configured:
        _print_json(
            {
                "ok": False,
                "warning": "TAVILY_API_KEY is not configured. Skipping live Tavily request.",
                "fallback_would_be_needed": True,
            }
        )
        return

    result = await tavily_search("best github repos for AI agents")
    results = result.get("results") if isinstance(result.get("results"), list) else []
    _print_json(
        {
            "ok": bool(result.get("ok")),
            "provider": result.get("provider"),
            "error": result.get("error"),
            "rate_limited": bool(result.get("rate_limited")),
            "result_count": len(results),
            "first_3": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                }
                for item in results[:3]
                if isinstance(item, dict)
            ],
            "fallback_would_be_needed": not bool(result.get("ok")),
        }
    )


def _verify_browser_fallback() -> None:
    from backend.eva.tools.desktop import web_search

    original_key = os.environ.pop("TAVILY_API_KEY", None)
    try:
        result = web_search("best github repos for AI agents")
    finally:
        if original_key is not None:
            os.environ["TAVILY_API_KEY"] = original_key
    _print_json(
        {
            "browser_fallback_test": True,
            "ok": bool(result.get("browser_opened")) if isinstance(result, dict) else False,
            "fallback": result.get("fallback") if isinstance(result, dict) else None,
            "error": result.get("error") if isinstance(result, dict) else None,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Eva Tavily web search without exposing secrets.")
    parser.add_argument("--fallback-browser", action="store_true", help="Also open a browser search to test fallback behavior.")
    args = parser.parse_args()

    asyncio.run(_verify_search())
    if args.fallback_browser:
        _verify_browser_fallback()


if __name__ == "__main__":
    main()

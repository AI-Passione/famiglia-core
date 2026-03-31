import json
import os
import urllib.error
import urllib.request
from typing import List, Dict, Optional


class WebSearchClient:
    """Wraps the Ollama Web Search API (https://ollama.com/api/web_search)."""

    BASE_URL = "https://ollama.com/api/web_search"

    def __init__(self):
        self.api_key = os.getenv("OLLAMA_API_KEY", "")

    def search(self, query: str, agent_name: str = "", user_prompt: Optional[str] = None) -> str:
        """
        Execute a web search and return a formatted string of results.
        Checks cache first.
        """
        if not self.api_key:
            return "[Web Search] OLLAMA_API_KEY is not set. Cannot perform web search."

        # Cache Check
        from famiglia_core.db.agents.context_store import context_store
        cached_results = context_store.get_web_search_cache(query)
        if cached_results:
            print(f"[{agent_name or 'WebSearch'}] Cache HIT for: {query!r}")
            return self._format_results(query, cached_results)

        print(f"[{agent_name or 'WebSearch'}] Cache MISS. Querying Ollama web search: {query!r}")

        payload = json.dumps({"query": query}).encode("utf-8")
        req = urllib.request.Request(
            self.BASE_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return f"[Web Search] HTTP {exc.code} from Ollama API: {exc.reason}"
        except urllib.error.URLError as exc:
            return f"[Web Search] Network error reaching Ollama API: {exc.reason}"
        except Exception as exc:
            return f"[Web Search] Unexpected error: {exc}"

        results: List[Dict] = body.get("results", [])
        if not results:
            return f"[Web Search] No results found for: {query!r}"

        # Persist to cache with agent and prompt metadata
        context_store.set_web_search_cache(
            query=query, 
            results=results, 
            agent_name=agent_name, 
            user_prompt=user_prompt
        )

        return self._format_results(query, results)

    def _format_results(self, query: str, results: List[Dict]) -> str:
        lines = [f"Web search results for: {query!r}\n"]
        for i, r in enumerate(results, start=1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "").strip()
            lines.append(f"{i}. **{title}**")
            lines.append(f"   URL: {url}")
            if content:
                snippet = content[:400] + ("..." if len(content) > 400 else "")
                lines.append(f"   {snippet}")
            lines.append("")

        return "\n".join(lines)


# Singleton
web_search_client = WebSearchClient()

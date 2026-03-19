import os
import json
import time
import requests
from typing import Dict, List, Optional, Union
from qwen_agent.tools.base import BaseTool, register_tool


X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")

X_API_V2_BASE = "https://api.x.com/2"
X_API_V1_BASE = "https://api.x.com/1.1"


def _x_headers() -> dict:
    return {
        "Authorization": f"Bearer {X_BEARER_TOKEN}",
        "Content-Type": "application/json",
    }


def _request_with_retries(method: str, url: str, params: Optional[dict] = None,
                           max_retries: int = 5, timeout: int = 30) -> Optional[dict]:
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, headers=_x_headers(),
                                    params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"[x_trending] Rate limited, sleeping {retry_after}s")
                time.sleep(retry_after)
                continue
            print(f"[x_trending] HTTP {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            print(f"[x_trending] Request error (attempt {attempt + 1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            time.sleep(min(2 ** attempt, 10))
    return None


def _fetch_trending(woeid: int = 1) -> str:
    url = f"{X_API_V1_BASE}/trends/place.json"
    data = _request_with_retries("GET", url, params={"id": woeid})
    if data is None:
        return "[x_trending] Failed to fetch trending topics. Please try again later."

    try:
        trends = data[0]["trends"]
    except (IndexError, KeyError, TypeError):
        return "[x_trending] Unexpected response format from trending API."

    location = data[0].get("locations", [{}])[0].get("name", "Unknown")
    lines = [f"Current trending topics on X ({location}):\n"]
    for idx, trend in enumerate(trends, 1):
        name = trend.get("name", "Unknown")
        volume = trend.get("tweet_volume")
        volume_str = f" - {volume:,} tweets" if volume else ""
        query_url = trend.get("url", "")
        lines.append(f"{idx}. {name}{volume_str}")
        if query_url:
            lines.append(f"   URL: {query_url}")

    return "\n".join(lines)


def _search_posts(query: str, max_results: int = 20) -> str:
    if not query:
        return "[x_trending] 'query' parameter is required for the 'search' action."

    max_results = max(10, min(max_results, 100))

    url = f"{X_API_V2_BASE}/tweets/search/recent"
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,author_id,lang",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    data = _request_with_retries("GET", url, params=params)
    if data is None:
        return f"[x_trending] Failed to search posts for '{query}'. Please try again later."

    tweets = data.get("data", [])
    if not tweets:
        return f"[x_trending] No posts found for '{query}'. Try a broader query."

    users_map: Dict[str, str] = {}
    for user in data.get("includes", {}).get("users", []):
        users_map[user["id"]] = user.get("username", user.get("name", "unknown"))

    lines = [f"Search results for '{query}' on X ({len(tweets)} posts):\n"]
    for idx, tweet in enumerate(tweets, 1):
        author_id = tweet.get("author_id", "")
        username = users_map.get(author_id, "unknown")
        text = tweet.get("text", "").replace("\n", "\n   ")
        created = tweet.get("created_at", "")
        metrics = tweet.get("public_metrics", {})
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)

        lines.append(f"{idx}. @{username} ({created})")
        lines.append(f"   {text}")
        lines.append(f"   [Likes: {likes} | Retweets: {retweets} | Replies: {replies}]")
        lines.append("")

    return "\n".join(lines)


@register_tool("x_trending", allow_overwrite=True)
class XTrending(BaseTool):
    name = "x_trending"
    description = (
        "Fetch trending topics on X (Twitter) or search recent X posts. "
        "Use action 'trending' to see what is currently trending, "
        "or 'search' to find posts about a specific topic."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["trending", "search"],
                "description": "Action to perform: 'trending' to get current trending topics, 'search' to search posts.",
            },
            "query": {
                "type": "string",
                "description": "Search query (required for 'search' action, ignored for 'trending').",
            },
            "woeid": {
                "type": "number",
                "description": "Where On Earth ID for trending location. Defaults to 1 (worldwide). US=23424977.",
            },
            "max_results": {
                "type": "number",
                "description": "Max posts to return for search (10-100). Defaults to 20.",
            },
        },
        "required": ["action"],
    }

    def __init__(self, cfg: Optional[dict] = None):
        super().__init__(cfg)

    def call(self, params: Union[str, dict], **kwargs) -> str:
        if not X_BEARER_TOKEN:
            return "[x_trending] X_BEARER_TOKEN environment variable is not set."

        try:
            params = self._verify_json_format_args(params)
            action = params["action"]
        except Exception:
            return "[x_trending] Invalid request format: Input must be a JSON object containing an 'action' field."

        if action == "trending":
            woeid = int(params.get("woeid", 1))
            return _fetch_trending(woeid)
        elif action == "search":
            query = params.get("query", "")
            max_results = int(params.get("max_results", 20))
            return _search_posts(query, max_results)
        else:
            return f"[x_trending] Unknown action '{action}'. Use 'trending' or 'search'."

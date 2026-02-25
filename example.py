
"""
Fallback script to extract REAL outbound Hacker News links using only standard Python (no installs).

Why this is needed:
- Sometimes outputs contain wrong links (HN discussion links, placeholders, or homepage-only URLs).
- This script parses HN pages directly and takes the exact title-link href as article_url.
- It helps ensure report links point to the original news page.

What it does:
1) Reads HN /news pages (+ pagination).
2) Extracts title, outbound article_url, hn_discussion_url, points, comments, age.
3) Filters by recency window.
4) Ranks with simple metadata/title heuristics.
5) Prints JSON with validated real links.
"""

import argparse
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

HN_BASE = "https://news.ycombinator.com"
NEWS_URL = f"{HN_BASE}/news"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0"


def age_to_hours(age_text: str) -> float:
    m = re.match(r"(\d+)\s+(\w+)", age_text.strip().lower())
    if not m:
        return 9999.0
    n = int(m.group(1))
    unit = m.group(2)
    if "minute" in unit:
        return n / 60.0
    if "hour" in unit:
        return float(n)
    if "day" in unit:
        return n * 24.0
    if "month" in unit:
        return n * 24.0 * 30
    if "year" in unit:
        return n * 24.0 * 365
    return 9999.0


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


class HNParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_athing = False
        self.cur_story = None
        self.stories = []

        self.in_titleline = False
        self.capture_title = False

        self.in_subtext = False
        self.capture_score = False
        self.capture_age = False
        self.capture_comment_link_text = False

        self._last_row_class = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        classes = cls.split()

        if tag == "tr" and "athing" in classes:
            self.in_athing = True
            sid = a.get("id")
            self.cur_story = {
                "id": int(sid) if sid and sid.isdigit() else None,
                "title": "",
                "article_url": "",
                "hn_discussion_url": "",
                "points": 0,
                "comments": 0,
                "age_text": "",
            }
            self._last_row_class = "athing"
            return

        if tag == "span" and "titleline" in classes and self.cur_story:
            self.in_titleline = True
            return

        if tag == "a" and self.in_titleline and self.cur_story:
            href = a.get("href", "").strip()
            self.cur_story["article_url"] = urljoin(HN_BASE, href)
            self.capture_title = True
            return

        if tag == "td" and "subtext" in classes and self.cur_story:
            self.in_subtext = True
            self._last_row_class = "subtext"
            return

        if tag == "span" and "score" in classes and self.in_subtext:
            self.capture_score = True
            return

        if tag == "span" and "age" in classes and self.in_subtext:
            self.capture_age = True
            return

        if tag == "a" and self.capture_age and self.cur_story:
            href = a.get("href", "")
            m = re.search(r"id=(\d+)", href)
            if m:
                item_id = int(m.group(1))
                self.cur_story["id"] = item_id
                self.cur_story["hn_discussion_url"] = f"{HN_BASE}/item?id={item_id}"
            return

        # comments are usually last link in subtext; we capture any comment-like text
        if tag == "a" and self.in_subtext:
            self.capture_comment_link_text = True

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_athing:
            self.in_athing = False
            # keep story object until subtext is parsed (next row)
            return

        if tag == "span" and self.in_titleline:
            self.in_titleline = False
            return

        if tag == "a" and self.capture_title:
            self.capture_title = False
            return

        if tag == "span" and self.capture_score:
            self.capture_score = False
            return

        if tag == "span" and self.capture_age:
            self.capture_age = False
            return

        if tag == "a" and self.capture_comment_link_text:
            self.capture_comment_link_text = False
            return

        # subtext row ends: finalize current story
        if tag == "td" and self.in_subtext and self.cur_story:
            self.in_subtext = False
            if self.cur_story.get("id") and self.cur_story.get("title") and self.cur_story.get("article_url"):
                self.stories.append(self.cur_story)
            self.cur_story = None
            return

    def handle_data(self, data):
        text = data.strip()
        if not text or not self.cur_story:
            return

        if self.capture_title:
            self.cur_story["title"] += (" " + text).strip() if self.cur_story["title"] else text
            return

        if self.capture_score:
            m = re.search(r"(\d+)", text)
            if m:
                self.cur_story["points"] = int(m.group(1))
            return

        if self.capture_age:
            # e.g. "2 hours ago"
            self.cur_story["age_text"] = text
            return

        if self.capture_comment_link_text:
            # e.g. "53 comments" or "discuss"
            m = re.search(r"(\d+)\s+comment", text.lower())
            if m:
                self.cur_story["comments"] = int(m.group(1))
            return


def parse_hn_page(html: str):
    p = HNParser()
    p.feed(html)
    out = []
    for s in p.stories:
        s["age_hours"] = age_to_hours(s.get("age_text", ""))
        out.append(s)
    return out


def title_signal(title: str) -> float:
    score = 0.0
    if ":" in title:
        score += 0.7
    if "?" in title:
        score += 0.7
    score += min(1.2, sum(1 for w in title.split() if len(w) >= 7) * 0.1)
    return score


def personal_interest(title: str) -> float:
    kw = {
        "ai": 2.0,
        "rust": 2.0,
        "security": 1.8,
        "performance": 1.5,
        "database": 1.5,
        "linux": 1.3,
        "open source": 1.4,
    }
    t = title.lower()
    s = 0.0
    for k, w in kw.items():
        if k in t:
            s += w
    return min(3.0, s)


def final_score(item: dict) -> float:
    freshness = max(0.0, 24.0 - item["age_hours"]) / 24.0
    points_score = min(1.0, item["points"] / 200.0)
    comments_score = min(1.0, item["comments"] / 100.0)
    title_score = min(1.0, title_signal(item["title"]) / 2.0)
    interest_score = min(1.0, personal_interest(item["title"]) / 3.0)

    raw = (
        0.45 * points_score +
        0.20 * comments_score +
        0.20 * freshness +
        0.10 * title_score +
        0.05 * interest_score
    )
    return round(raw * 10, 2)


def is_valid_article_url(url: str) -> bool:
    u = url.lower()
    if not u.startswith(("http://", "https://")):
        return False
    if "news.ycombinator.com/item?id=" in u:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--hours", type=float, default=24.0)
    args = ap.parse_args()

    candidates = []
    visited = []
    page = 1

    while len(candidates) < args.top * 6 and page <= 10:
        url = NEWS_URL if page == 1 else f"{NEWS_URL}?p={page}"
        visited.append(url)
        html = fetch(url)
        items = parse_hn_page(html)

        for it in items:
            if it["age_hours"] > args.hours:
                continue
            if not is_valid_article_url(it["article_url"]):
                continue
            candidates.append(it)

        page += 1

    ranked = sorted(candidates, key=final_score, reverse=True)[: args.top]

    result = []
    for i, it in enumerate(ranked, start=1):
        result.append({
            "rank": i,
            "id": it["id"],
            "title": it["title"],
            "article_url": it["article_url"],            # primary real external link
            "hn_discussion_url": it["hn_discussion_url"],
            "final_score": final_score(it),
            "points": it["points"],
            "comments": it["comments"],
            "age_text": it["age_text"],
        })

    print(json.dumps({
        "source": "https://news.ycombinator.com/news",
        "visited_pages": visited,
        "window_hours": args.hours,
        "requested_top": args.top,
        "returned": len(result),
        "items": result
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


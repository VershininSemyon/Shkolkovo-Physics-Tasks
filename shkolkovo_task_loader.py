
import asyncio
import aiohttp
import argparse
import json
import logging
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Optional

BASE = "https://3.shkolkovo.online"
API = f"{BASE}/api/test/v1"

IMAGE_BASE_URL = f"{BASE}/api/latex-service/v1/GetSession"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    ),
    "Origin": BASE,
    "Referer": f"{BASE}/catalog?SubjectId=4",
}

PER_PAGE_THEMES = 2000
PER_PAGE_QUESTIONS = 100
REQUEST_DELAY = 0.15
MAX_RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
log = logging.getLogger("shkolkovo")

async def _post(
    session: aiohttp.ClientSession,
    url: str,
    payload: dict,
    *,
    retries: int = MAX_RETRIES,
) -> dict:
    for attempt in range(1, retries + 1):
        try:
            async with session.post(url, json=payload, headers=HEADERS) as r:
                if r.status == 200:
                    await asyncio.sleep(REQUEST_DELAY)
                    return await r.json()
                body = await r.text()
                log.warning("HTTP %s  %s  (attempt %d/%d)  %s",
                            r.status, url, attempt, retries, body[:200])
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            log.warning("Network error: %s  (attempt %d/%d)", exc, attempt, retries)
        if attempt < retries:
            await asyncio.sleep(1.0 * attempt)
    raise RuntimeError(f"Failed to get {url}")

async def _get(
    session: aiohttp.ClientSession,
    url: str,
    *,
    retries: int = MAX_RETRIES,
) -> dict:
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, headers=HEADERS) as r:
                if r.status == 200:
                    await asyncio.sleep(REQUEST_DELAY)
                    return await r.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            log.warning("Network error: %s  (attempt %d/%d)", exc, attempt, retries)
        if attempt < retries:
            await asyncio.sleep(1.0 * attempt)
    raise RuntimeError(f"Failed to get {url}")

async def find_root_themes(
    session: aiohttp.ClientSession,
    subject_id: int,
    exam_position: int,
) -> list[dict]:
    url = f"{API}/theme/list"

    payload = {
        "Condition": [
            {"Column": "Theme.SubjectId",    "Operator": "=", "Value": [subject_id]},
            {"Column": "Theme.ParentId",     "Operator": "=", "Value": [0]},
            {"Column": "Theme.ExamPosition", "Operator": "=", "Value": [exam_position]},
            {"Column": "Theme.IsHidden",     "Operator": "=", "Value": [0]},
            {"Column": "Theme.IsDeactivated","Operator": "=", "Value": [0]},
        ],
        "Order": [{"Column": "Theme.SortOrder", "Desc": False}],
        "Pagination": {"PerPage": PER_PAGE_THEMES, "Page": 1},
    }
    data = await _post(session, url, payload)
    themes = data.get("result", [])
    if isinstance(themes, dict):
        themes = themes.get("result", [])
    if themes:
        log.info("Found root themes for #%d: %d", exam_position, len(themes))
        return themes

    log.info("ExamPosition filter failed, fetching all root themes...")
    payload["Condition"] = [
        {"Column": "Theme.SubjectId",  "Operator": "=", "Value": [subject_id]},
        {"Column": "Theme.ParentId",   "Operator": "=", "Value": [0]},
        {"Column": "Theme.IsHidden",   "Operator": "=", "Value": [0]},
    ]
    data = await _post(session, url, payload)
    all_themes = data.get("result", [])
    if isinstance(all_themes, dict):
        all_themes = all_themes.get("result", [])
    themes = [t for t in all_themes if t.get("ExamPosition") == exam_position]
    log.info("Found root themes for #%d: %d", exam_position, len(themes))
    return themes

async def fetch_child_themes(
    session: aiohttp.ClientSession,
    parent_id: int,
) -> list[dict]:
    url = f"{API}/theme/list"
    payload = {
        "Condition": [
            {"Column": "Theme.ParentId",  "Operator": "=", "Value": [parent_id]},
            {"Column": "Theme.IsHidden",  "Operator": "=", "Value": [0]},
        ],
        "Order": [
            {"Column": "Theme.SortOrder", "Desc": False},
            {"Column": "Theme.Name",      "Desc": False},
        ],
        "Pagination": {"PerPage": PER_PAGE_THEMES, "Page": 1},
    }
    data = await _post(session, url, payload)
    result = data.get("result", [])
    if isinstance(result, dict):
        result = result.get("result", [])
    return result

async def collect_theme_tree(
    session: aiohttp.ClientSession,
    root: dict,
) -> dict:
    node = dict(root)
    node["children"] = []
    children = await fetch_child_themes(session, root["Id"])
    for child in children:
        subtree = await collect_theme_tree(session, child)
        node["children"].append(subtree)
    return node

def flatten_theme_ids(tree: dict) -> list[int]:
    ids = [tree["Id"]]
    for ch in tree.get("children", []):
        ids.extend(flatten_theme_ids(ch))
    return ids

def flatten_theme_list(tree: dict) -> list[dict]:
    out = []
    def _walk(node, path):
        cur_path = path + [node["Name"]]
        out.append({
            "id": node["Id"],
            "name": node["Name"],
            "parent_id": node.get("ParentId", 0),
            "path": " -> ".join(cur_path),
        })
        for ch in node.get("children", []):
            _walk(ch, cur_path)
    _walk(tree, [])
    return out

async def fetch_questions_for_theme(
    session: aiohttp.ClientSession,
    theme_id: int,
) -> tuple[list[dict], list[dict], dict]:
    url = f"{API}/question/public/list"
    all_questions: list[dict] = []
    all_tex: list[dict] = []
    merged_deps: dict = {}
    page = 1

    while True:
        payload = {
            "Condition": [
                {"Column": "QuestionTheme.ThemeId", "Operator": "=", "Value": [theme_id]},
            ],
            "Order": [
                {"Column": "Question.SortOrder", "Desc": False},
                {"Column": "Question.Id",        "Desc": False},
            ],
            "Pagination": {"PerPage": PER_PAGE_QUESTIONS, "Page": page},
        }
        data = await _post(session, url, payload)

        result = data.get("result") or {}
        questions = result.get("questions") or []
        deps = result.get("dependencies") or {}
        tex_sessions = deps.get("TexSessions") or []
        pagination = data.get("pagination") or {}

        all_questions.extend(questions)
        all_tex.extend(tex_sessions)

        for key, val in deps.items():
            if key == "TexSessions" or val is None:
                continue
            if key not in merged_deps:
                merged_deps[key] = {}
            if isinstance(val, dict):
                merged_deps[key].update(val)
            elif isinstance(val, list):
                merged_deps[key] = merged_deps.get(key, []) + val

        total_pages = pagination.get("TotalPages", 1) or 1
        total_records = pagination.get("TotalRecords", 0) or 0
        log.info("  Theme %d  page %d/%d  (%d questions)",
                 theme_id, page, total_pages, total_records)

        if page >= total_pages:
            break
        page += 1

    return all_questions, all_tex, merged_deps

class ImgExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            for name, val in attrs:
                if name == "src" and val:
                    self.images.append(val)

def extract_images(html: str) -> list[str]:
    p = ImgExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    return p.images

def clean_html(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r"<!--\s*l\.\s*\d+\s*-->", "", html)
    html = re.sub(r'<br class="newline"\s*/?>', "<br/>", html)
    html = re.sub(r">\s{2,}<", "> <", html)
    return html.strip()

def build_image_map(
    tex_sessions: list[dict],
    session_id: int,
) -> dict[str, str]:
    result = {}
    found = False
    for ts in tex_sessions:
        if ts.get("Id") == session_id:
            found = True
            imgs = extract_images(ts.get("Html", ""))
            for img in imgs:
                if img.startswith("http"):
                    result[img] = img
                else:
                    fname = os.path.basename(img)
                    result[fname] = f"{IMAGE_BASE_URL}/{session_id}/{fname}"
    if not found and session_id:
        log.warning("TexSession %d not found in dependencies", session_id)
    return result

def get_tex_html(tex_sessions: list[dict], session_id: int) -> str:
    if not session_id:
        return ""
    for ts in tex_sessions:
        if ts.get("Id") == session_id:
            return clean_html(ts.get("Html", ""))
    return ""

async def download_images(
    session: aiohttp.ClientSession,
    image_map: dict[str, str],
    out_dir: str,
    sem: asyncio.Semaphore,
) -> dict[str, str]:
    if not out_dir or not image_map:
        return {}

    os.makedirs(out_dir, exist_ok=True)
    local_map: dict[str, str] = {}

    async def _dl(src: str, url: str):
        fname = os.path.basename(url.split("?")[0])
        if not fname:
            return
        dest = os.path.join(out_dir, fname)
        if os.path.exists(dest):
            local_map[src] = dest
            return
        async with sem:
            try:
                async with session.get(url, headers=HEADERS) as r:
                    if r.status == 200:
                        data = await r.read()
                        Path(dest).write_bytes(data)
                        local_map[src] = dest
                    else:
                        log.debug("Image failed (%d): %s", r.status, url)
            except Exception as exc:
                log.debug("Download error %s: %s", url, exc)

    tasks = [_dl(src, url) for src, url in image_map.items()]
    await asyncio.gather(*tasks)
    return local_map

def build_task_record(
    q: dict,
    tex_sessions: list[dict],
    deps: dict,
    theme_path: str,
) -> dict:
    q_id = q["Id"]

    question_html = get_tex_html(tex_sessions, q.get("QuestionTexSessionId", 0))
    solution_html = get_tex_html(tex_sessions, q.get("SolutionTexSessionId", 0))
    answer_html   = get_tex_html(tex_sessions, (q.get("Answer") or {}).get("TexSessionId", 0))
    criteria_html = get_tex_html(tex_sessions, q.get("GradeCriteriaTexSessionId", 0))

    all_imgs: dict[str, str] = {}
    for sid_field in ("QuestionTexSessionId", "SolutionTexSessionId",
                      "GradeCriteriaTexSessionId"):
        sid = q.get(sid_field, 0)
        if sid:
            all_imgs.update(build_image_map(tex_sessions, sid))
    ans_sid = (q.get("Answer") or {}).get("TexSessionId", 0)
    if ans_sid:
        all_imgs.update(build_image_map(tex_sessions, ans_sid))

    tag_ids = q.get("Tags", [])
    tags_map = deps.get("Tags", {})
    tag_names = [tags_map[str(t)]["Name"] for t in tag_ids if str(t) in tags_map]

    src_ids = q.get("Sources", [])
    src_map = deps.get("QuestionSources", {})
    src_names = [src_map[str(s)]["Source"] for s in src_ids if str(s) in src_map]

    return {
        "id": q_id,
        "name": q.get("Name", ""),
        "theme_path": theme_path,
        "question_html": question_html,
        "solution_html": solution_html,
        "answer_html": answer_html,
        "grade_criteria_html": criteria_html,
        "images": all_imgs,
        "tags": tag_names,
        "sources": src_names,
        "created_at": q.get("CreatedAt", ""),
        "updated_at": q.get("UpdatedAt", ""),
    }

async def run(task_number: int, subject_id: int, images_dir: str):
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:

        roots = await find_root_themes(session, subject_id, task_number)
        if not roots:
            log.error("Root theme for #%d not found!", task_number)
            return

        all_tasks: list[dict] = []
        seen_question_ids: set[int] = set()
        themes_index: list[dict] = []

        for root in roots:
            log.info("Root theme: %d  '%s'", root["Id"], root["Name"])

            tree = await collect_theme_tree(session, root)
            flat_themes = flatten_theme_list(tree)
            theme_ids = flatten_theme_ids(tree)
            themes_index.extend(flat_themes)
            log.info("Total subthemes in tree: %d", len(theme_ids))

            sem = asyncio.Semaphore(5)

            for tinfo in flat_themes:
                tid = tinfo["id"]
                log.info("Fetching questions for theme %d  '%s'", tid, tinfo["path"])

                questions, tex_sessions, deps = await fetch_questions_for_theme(
                    session, tid
                )

                for q in questions:
                    if q["Id"] in seen_question_ids:
                        continue
                    seen_question_ids.add(q["Id"])

                    record = build_task_record(q, tex_sessions, deps, tinfo["path"])

                    if images_dir and record["images"]:
                        local = await download_images(
                            session, record["images"], images_dir, sem
                        )
                        for orig_src, local_path in local.items():
                            for field in ("question_html", "solution_html",
                                          "answer_html", "grade_criteria_html"):
                                record[field] = record[field].replace(
                                    f'src="{orig_src}"',
                                    f'src="{local_path}"',
                                )
                        record["images_local"] = local

                    all_tasks.append(record)

        output = {
            "task_number": task_number,
            "subject_id": subject_id,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "themes": themes_index,
            "total_questions": len(all_tasks),
            "questions": all_tasks,
        }

        filename = f"tasks_{task_number}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        log.info("Done!  %d questions -> %s", len(all_tasks), filename)

def main():
    parser = argparse.ArgumentParser(
        description="Download EGE physics questions from Shkolkovo API"
    )
    parser.add_argument("task", type=int, help="EGE question number (1-26)")
    parser.add_argument("--subject", type=int, default=4,
                        help="Subject ID (4 = Physics)")
    parser.add_argument("--images-dir", type=str, default="",
                        help="Directory for images (e.g. images_26)")
    args = parser.parse_args()

    if not 1 <= args.task <= 26:
        parser.error("Question number must be from 1 to 26")

    asyncio.run(run(args.task, args.subject, args.images_dir))

if __name__ == "__main__":
    main()

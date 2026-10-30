"""
노션 DB → 고정 구간 간트 차트(index.html) 생성기

사용법
  python build.py                  # 노션 API에서 읽어 public/index.html 생성 (환경변수 NOTION_TOKEN 필요)
  python build.py --sample x.json  # 노션 대신 로컬 JSON으로 미리보기 생성

외부 라이브러리 없이 파이썬 표준 라이브러리만 사용합니다.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
NOTION_VERSION = "2022-06-28"


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


def resolve_props(pages, cfg):
    """설정한 속성 이름이 DB에 없으면 자동으로 찾아서 맞춤"""
    if not pages:
        return cfg
    props = pages[0]["properties"]
    types = {k: v.get("type") for k, v in props.items()}
    cfg = dict(cfg)
    if types.get(cfg.get("title_property")) != "title":
        cfg["title_property"] = next(k for k, t in types.items() if t == "title")
    dates = [k for k, t in types.items() if t == "date"]
    for key in ("start_property", "end_property", "fallback_range_property"):
        if cfg.get(key) not in dates:
            cfg[key] = None
    if not (cfg.get("start_property") or cfg.get("fallback_range_property")) and dates:
        # 날짜 범위가 가장 많이 채워진 속성을 기간으로 사용
        def score(k):
            return sum(1 for p in pages if (p["properties"][k].get("date") or {}).get("start"))
        cfg["fallback_range_property"] = max(dates, key=score)
    if types.get(cfg.get("category_property")) not in ("select", "multi_select"):
        cfg["category_property"] = None
    print("사용 속성:", {k: cfg.get(k) for k in ("title_property", "start_property", "end_property", "fallback_range_property", "category_property")})
    return cfg


def notion_query(database_id, token):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            hint = {
                401: "노션 키(NOTION_TOKEN)가 틀렸어요. GitHub Secret 값을 다시 확인하세요.",
                404: "노션 DB에 통합(gantt)이 연결되지 않았어요. DB 페이지 ••• → 연결에서 추가하세요.",
            }.get(e.code, "")
            sys.exit(f"노션 API 오류 {e.code}: {body}\n{hint}")
        results += data["results"]
        if not data.get("has_more"):
            return results
        cursor = data["next_cursor"]


def prop_date(props, name):
    p = props.get(name) if name else None
    if not p or p.get("type") != "date" or not p.get("date"):
        return None, None
    return p["date"].get("start"), p["date"].get("end")


def page_to_item(page, cfg):
    props = page["properties"]
    tp = props.get(cfg["title_property"], {})
    title = "".join(t["plain_text"] for t in tp.get("title", [])) or "제목 없음"

    s1, e1 = prop_date(props, cfg.get("start_property"))
    s2, _ = prop_date(props, cfg.get("end_property"))
    fs, fe = prop_date(props, cfg.get("fallback_range_property"))

    start = s1 or fs
    end = s2 or e1 or fe
    icon = page.get("icon") or {}
    cat_prop = props.get(cfg.get("category_property") or "", {})
    cats = [o["name"] for o in cat_prop.get("multi_select", [])] if cat_prop.get("type") == "multi_select" else []
    if cat_prop.get("type") == "select" and cat_prop.get("select"):
        cats = [cat_prop["select"]["name"]]
    return {
        "category": cats[0] if cats else None,
        "title": title,
        "start": start[:10] if start else None,
        "end": end[:10] if end else None,
        "icon": icon.get("emoji") if icon.get("type") == "emoji" else None,
        "url": page.get("url"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", help="노션 대신 사용할 로컬 JSON (items 배열)")
    args = ap.parse_args()
    cfg = load_config()

    if args.sample:
        items = json.load(open(args.sample, encoding="utf-8"))
    else:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            sys.exit("NOTION_TOKEN 환경변수가 없습니다.")
        pages = notion_query(cfg["database_id"], token)
        cfg = resolve_props(pages, cfg)
        items = [page_to_item(p, cfg) for p in pages]

    items = [i for i in items if i.get("start")]  # 날짜 없는 항목 제외

    payload = {
        "title": cfg.get("title", ""),
        "rangeStart": cfg["range_start"],
        "rangeEnd": cfg["range_end"],
        "hideOutside": cfg.get("hide_items_outside_range", True),
        "sort": cfg.get("sort", "start_desc"),
        "items": items,
        "updated": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M (KST)"),
    }
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False))
    root = ROOT / "public"
    root.mkdir(exist_ok=True)
    # 검색엔진 수집 차단
    (root / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    # 차트는 비밀 경로(GitHub Secret CHART_PATH)에만 둔다. 기본 주소에는 빈 페이지만 둔다.
    secret = os.environ.get("CHART_PATH", "").strip().strip("/")
    if secret:
        (root / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
            "<title>404</title><p>Not found</p>", encoding="utf-8")
        out = root / secret
        out.mkdir(parents=True, exist_ok=True)
    else:
        out = root
    (out / "index.html").write_text(html, encoding="utf-8")
    print(f"차트 생성 완료 ({len(items)}개 항목)")  # 경로는 로그에 남기지 않는다


if __name__ == "__main__":
    main()

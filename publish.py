#!/usr/bin/env python3
"""
MoFIT / adidas Sports Studio — automatsko objavljivanje.

Cita queue/*.json, objavljuje sve sto je dospjelo, i biljezi rezultat u state/.
Pokrece se iz GitHub Actions (cron) ili rucno: python3 publish.py [--dry-run]
"""
import json, os, sys, time, urllib.parse, urllib.request, datetime as dt, pathlib

ROOT = pathlib.Path(__file__).parent
API = os.environ.get("GRAPH_VERSION", "v25.0")
BASE = f"https://graph.facebook.com/{API}"
DRY = "--dry-run" in sys.argv

# Javni URL na kojem Meta cita medije. Postavlja ga workflow.
MEDIA_BASE = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")


def log(*a):
    print(dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), *a, flush=True)


def call(method, path, params, retries=3):
    url = f"{BASE}/{path.lstrip('/')}"
    data = urllib.parse.urlencode(params).encode()
    last = None
    for attempt in range(retries):
        try:
            if method == "GET":
                req = urllib.request.Request(url + "?" + data.decode())
            else:
                req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:600]
            last = f"HTTP {e.code}: {body}"
            # 4xx osim 429 nema smisla ponavljati
            if 400 <= e.code < 500 and e.code != 429:
                raise RuntimeError(last)
        except Exception as e:  # mreza
            last = str(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(last)


def media_url(rel):
    if rel.startswith("http://") or rel.startswith("https://"):
        return rel
    if not MEDIA_BASE:
        raise RuntimeError("MEDIA_BASE_URL nije postavljen")
    return f"{MEDIA_BASE}/{rel.lstrip('/')}"


# ---------------------------------------------------------------- Instagram
def ig_container(ig_id, token, params):
    r = call("POST", f"{ig_id}/media", {**params, "access_token": token})
    return r["id"]


def ig_wait(container_id, token, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = call("GET", container_id,
                 {"fields": "status_code,status", "access_token": token})
        s = r.get("status_code")
        if s == "FINISHED":
            return
        if s == "ERROR":
            raise RuntimeError(f"container ERROR: {r.get('status')}")
        time.sleep(6)
    raise RuntimeError("container nije zavrsio u zadanom vremenu")


def ig_publish(ig_id, token, container_id):
    r = call("POST", f"{ig_id}/media_publish",
             {"creation_id": container_id, "access_token": token})
    return r["id"]


_IG_CACHE = {}


def resolve_ig_id(acc, token):
    """IG korisnicki ID. Ako nije upisan, dohvati ga iz povezane Facebook stranice."""
    if acc.get("ig_user_id") and acc["ig_user_id"] != "POPUNITI":
        return acc["ig_user_id"]
    page = acc.get("page_id")
    if not page:
        raise RuntimeError("nema ni ig_user_id ni page_id")
    if page in _IG_CACHE:
        return _IG_CACHE[page]
    r = call("GET", page, {"fields": "instagram_business_account", "access_token": token})
    iba = r.get("instagram_business_account") or {}
    if not iba.get("id"):
        raise RuntimeError(
            f"Facebook stranica {page} nema povezan Instagram poslovni racun. "
            "Poveži ga u postavkama stranice (Linked accounts) pa pokreni ponovno."
        )
    _IG_CACHE[page] = iba["id"]
    log("   IG id za stranicu", page, "->", iba["id"])
    return iba["id"]


def post_instagram(acc, item, token):
    ig = resolve_ig_id(acc, token)
    kind = item["type"]
    media = item.get("media", [])
    caption = item.get("caption", "")

    if kind == "story":
        ids = []
        for m in media:
            p = {"media_type": "STORIES"}
            p["video_url" if m.lower().endswith((".mp4", ".mov")) else "image_url"] = media_url(m)
            cid = ig_container(ig, token, p)
            ig_wait(cid, token)
            ids.append(ig_publish(ig, token, cid))
            time.sleep(3)
        return ids

    if kind == "reel":
        p = {"media_type": "REELS", "video_url": media_url(media[0]), "caption": caption}
        if item.get("share_to_feed") is False:
            p["share_to_feed"] = "false"
        cid = ig_container(ig, token, p)
        ig_wait(cid, token)
        return [ig_publish(ig, token, cid)]

    if kind == "post":
        if len(media) == 1:
            m = media[0]
            p = {"caption": caption}
            p["video_url" if m.lower().endswith((".mp4", ".mov")) else "image_url"] = media_url(m)
            cid = ig_container(ig, token, p)
        else:
            children = []
            for m in media:
                cp = {"is_carousel_item": "true"}
                cp["video_url" if m.lower().endswith((".mp4", ".mov")) else "image_url"] = media_url(m)
                c = ig_container(ig, token, cp)
                ig_wait(c, token)
                children.append(c)
            cid = ig_container(ig, token, {
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
            })
        ig_wait(cid, token)
        return [ig_publish(ig, token, cid)]

    raise RuntimeError(f"nepoznat tip za Instagram: {kind}")


# ---------------------------------------------------------------- Facebook
def post_facebook(acc, item, token):
    page = acc["page_id"]
    kind = item["type"]
    media = item.get("media", [])
    caption = item.get("caption", "")

    if kind == "post" and media:
        vids = [m for m in media if m.lower().endswith((".mp4", ".mov"))]
        if vids:
            r = call("POST", f"{page}/videos", {
                "file_url": media_url(vids[0]),
                "description": caption,
                "access_token": token,
            })
            return [r.get("id")]
        if len(media) == 1:
            r = call("POST", f"{page}/photos", {
                "url": media_url(media[0]),
                "caption": caption,
                "access_token": token,
            })
            return [r.get("post_id") or r.get("id")]
        # vise slika: prvo unpublished photo id-evi, pa feed
        ids = []
        for m in media:
            r = call("POST", f"{page}/photos", {
                "url": media_url(m), "published": "false", "access_token": token,
            })
            ids.append(r["id"])
        params = {"message": caption, "access_token": token}
        for i, pid in enumerate(ids):
            params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
        r = call("POST", f"{page}/feed", params)
        return [r["id"]]

    if kind == "post":  # samo tekst
        r = call("POST", f"{page}/feed", {"message": caption, "access_token": token})
        return [r["id"]]

    if kind == "story":
        # Facebook Page story: foto se prvo uploada unpublished, pa se objavi kao story
        m = media[0]
        if m.lower().endswith((".mp4", ".mov")):
            raise RuntimeError("FB video story nije podrzan ovim skriptom")
        up = call("POST", f"{page}/photos",
                  {"url": media_url(m), "published": "false", "access_token": token})
        r = call("POST", f"{page}/photo_stories",
                 {"photo_id": up["id"], "access_token": token})
        return [r.get("post_id") or r.get("id")]

    raise RuntimeError(f"nepoznat tip za Facebook: {kind}")


# ---------------------------------------------------------------- glavni dio
def main():
    accounts = json.loads((ROOT / "accounts.json").read_text())
    now = dt.datetime.now(dt.timezone.utc)
    state_dir = ROOT / "state"
    state_dir.mkdir(exist_ok=True)

    items = []
    for f in sorted((ROOT / "queue").glob("*.json")):
        it = json.loads(f.read_text())
        it["_file"] = f.name
        items.append(it)

    todo = []
    for it in items:
        if (state_dir / f"{it['id']}.json").exists():
            continue
        when = dt.datetime.fromisoformat(it["when"])
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        if when <= now:
            todo.append((when, it))

    if not todo:
        log("nema nista za objaviti")
        return 0

    todo.sort(key=lambda x: x[0])
    failed = 0

    for when, it in todo:
        for target in it["targets"]:
            acc = accounts.get(target)
            if not acc:
                log(f"!! nepoznat target {target} ({it['id']})")
                failed += 1
                continue
            token = os.environ.get(acc.get("token_env", "META_TOKEN"), "")
            if not token:
                log(f"!! nema tokena za {target}")
                failed += 1
                continue
            label = f"{it['id']} -> {target} ({it['type']})"
            if DRY:
                log("DRY", label, [media_url(m) for m in it.get("media", [])])
                continue
            try:
                ids = (post_instagram if target.startswith("ig:") else post_facebook)(acc, it, token)
                log("OK ", label, ids)
                (state_dir / f"{it['id']}.json").write_text(json.dumps({
                    "id": it["id"], "target": target, "ids": ids,
                    "published_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }, ensure_ascii=False, indent=2))
            except Exception as e:
                log("FAIL", label, e)
                failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

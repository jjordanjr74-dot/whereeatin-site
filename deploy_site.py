#!/usr/bin/env python3
"""Publish the Where We Eatin'? launch site to GitHub Pages without git push.

Why this exists: `git push` hangs indefinitely on this host (Git Credential Manager
prompts with no terminal attached), which silently blocked the first deployment for
over 12 minutes. The GitHub Git Data API does the same job in ~30s and cannot prompt.
It preserves history — it builds on the remote's current tree and commits a child.

Usage:
    python deploy_site.py "commit message"
"""
import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "jjordanjr74-dot/whereeatin-site"
SITE = pathlib.Path(__file__).resolve().parent
# Never publish local bookkeeping into the public site.
# 2026-09-28: build_reviews.py was missing here, so it was being PUBLISHED to the public site (it showed up in the
# deploy set). Also dropped a duplicated "deploy_site.py" entry.
SKIP_NAMES = {".hold", "deploy_site.py", "build_site.py", "build_radar.py", "build_reviews.py"}
SKIP_SUFFIX = {".hold", ".bak", ".pyc", ".py"}
SKIP_DIRS = {"pages_src"}  # promo is now public; the desk bot (@Sheba_telegram_bot) is live for signup intake
# Future promo release is explicit: exclude launch kit, storyboard, manifest, source notes, unused social assets,
# and every unapproved file by default. Remove "promo" from SKIP_DIRS only after the dedicated intake path is live.
PROMO_PUBLIC_FILES = {
    "promo/index.html", "promo/assets/hero.jpg", "promo/assets/og.png",
    "promo/fonts/ArchivoBlack-Regular.ttf", "promo/fonts/ArchivoBlack-OFL.txt",
    "promo/fonts/DMSans.ttf", "promo/fonts/DMSans-OFL.txt",
    "promo/video/wwe_16x9.mp4", "promo/video/wwe_16x9.jpg", "promo/video/wwe_9x16.mp4",
}
# Build-cache directories that must never be published, and must be PRUNED from the remote tree if a previous
# deploy let them through (entries already published are not removed by deleting them locally - see the prune
# step below the tree build).
CACHE_PARTS = {".ruff_cache", "__pycache__", ".pytest_cache", ".mypy_cache"}
# 2026-09-29: ".py" is skipped by SUFFIX, not by name. This directory is walked and published, so every build
# script dropped here was one forgotten SKIP_NAMES entry away from being served publicly -- build_reviews.py was
# published that way once, and make_icons.py would have been the next. A suffix rule cannot be forgotten.
# 2026-09-19: GitHub Pages redirects the github.io URL to the CNAME domain whenever a CNAME file
# exists. whereeatin.com's DNS still points at Porkbun (207.207.210.x) with an EXPIRED certificate,
# so every visitor — and every URL probe — dead-ends on a parking page and the site reads as "not
# live". Removing the CNAME makes the github.io address serve directly (200, real page); the domain
# value is preserved in CNAME.hold, so restoring the custom domain later is one file.
# 2026-09-28: this used to be {"CNAME"} -- the CNAME was stripped on every deploy because GitHub Pages redirects
# the github.io URL to the domain named in it, and whereeatin.com was still pointing at Porkbun parking. The
# domain is now live on Pages (A records -> 185.199.108-111.153, www -> jjordanjr74-dot.github.io), so stripping
# the CNAME would DETACH the custom domain on the next publish. Keep it.
REMOVE_PATHS = set()


def token() -> str:
    t = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=60).stdout.strip()
    if not t:
        sys.exit("no GitHub token available from `gh auth token`")
    return t


def api(tok: str, method: str, path: str, payload=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Authorization": f"bearer {tok}", "Accept": "application/vnd.github+json",
                 "User-Agent": "hermes-deploy", "Content-Type": "application/json"},
    )
    # GitHub flakes 401 "Bad credentials" on an otherwise-good token under load (seen 2026-10-22: the
    # identical request passed on retry). The intake->publish loop runs unattended, so a transient 401
    # must not silently fail a publish. Retry only the codes that are known to be transient; a real 401
    # on a revoked token exits after the last attempt unchanged.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            sys.exit(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:400]}")


def publish(message: str) -> str:
    tok = token()
    parent = api(tok, "GET", f"/repos/{REPO}/git/refs/heads/main")["object"]["sha"]
    parent_commit = api(tok, "GET", f"/repos/{REPO}/git/commits/{parent}")
    base_tree = parent_commit["tree"]["sha"]
    remote_blobs = {}
    known_shas = set()
    # Harvest blob SHAs from both current HEAD tree and parent commit tree so a previously uploaded
    # large asset (e.g. promo/*.mp4) can be referenced by SHA in POST /git/trees without re-uploading 45MB.
    tree_shas = [base_tree]
    for p_entry in parent_commit.get("parents", [])[:1]:
        try:
            gp = api(tok, "GET", f"/repos/{REPO}/git/commits/{p_entry['sha']}")
            tree_shas.append(gp["tree"]["sha"])
        except Exception:
            pass
    for idx_t, t_sha in enumerate(tree_shas):
        for e in api(tok, "GET", f"/repos/{REPO}/git/trees/{t_sha}?recursive=1").get("tree", []):
            if e.get("type") == "blob":
                known_shas.add(e["sha"])
                if idx_t == 0:
                    remote_blobs[e["path"]] = e["sha"]

    entries, nbytes, files = [], 0, []
    for p in sorted(SITE.rglob("*")):
        if p.is_dir() or ".git" in p.parts:
            continue
        # A dot-DIRECTORY skipped by name does NOT stop rglob descending into it: skipping ".ruff_cache" above
        # still yielded ".ruff_cache/0.16.9/<hash>" and published it to the public site (seen 2026-09-30, 48
        # files shipped including .ruff_cache). So test every parent part, not just the leaf name.
        rel = p.relative_to(SITE).parts
        if any(part.startswith(".") and part not in (".nojekyll", ".well-known") for part in rel[:-1]):
            continue
        if p.name in SKIP_NAMES or p.name.startswith(".") and p.name != ".nojekyll":
            continue
        # 2026-10-18 audit: promo/ (owner-review marketing kit, 40MB video + internal LAUNCH_KIT/manifest with D:/ paths)
        # and dated backups like venues.json.bak-honesty-20261015 (suffix rule missed them) would have shipped.
        rel_path = p.relative_to(SITE).as_posix()
        if any(part in SKIP_DIRS for part in p.parts) or ("promo" in p.relative_to(SITE).parts and rel_path not in PROMO_PUBLIC_FILES):
            continue
        if ".bak" in p.name or p.suffix in {".md"} and p.name != "README.md":
            continue
        if p.suffix in SKIP_SUFFIX:
            continue
        raw = p.read_bytes()
        git_sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if remote_blobs.get(rel_path) == git_sha:
            continue
        if git_sha in known_shas:
            blob_sha = git_sha
        else:
            blob = api(tok, "POST", f"/repos/{REPO}/git/blobs",
                       {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
            blob_sha = blob["sha"]
            known_shas.add(blob_sha)
        entries.append({"path": rel_path, "mode": "100644",
                        "type": "blob", "sha": blob_sha})
        nbytes += len(raw)
        files.append(rel_path)

    tree = (
        api(tok, "POST", f"/repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": entries})
        if entries else {"sha": base_tree}
    )
    # Prune build-cache paths from the remote tree. Because the new tree is built on base_tree, a file deleted
    # LOCALLY stays published forever - .ruff_cache was served live this way (2026-09-30). Matching cache dir
    # NAMES rather than listing paths means it cannot recur under a new name.
    present = {e["path"] for e in api(tok, "GET", f"/repos/{REPO}/git/trees/{tree['sha']}?recursive=1")["tree"] if e.get("type") == "blob"}
    def _never_public(rp: str) -> bool:
        # Same rules as the publish filter, applied to what is ALREADY live: anything the filter would refuse
        # today is pruned, so a past leak (AGENTS.md, a .bak-* data file - both served 200 on 2026-10-18) heals
        # on the next publish instead of staying public forever.
        parts = rp.split("/"); name = parts[-1]
        return (bool(CACHE_PARTS & set(parts)) or bool(SKIP_DIRS & set(parts[:-1]))
                or ("promo" in parts[:-1] and rp not in PROMO_PUBLIC_FILES)
                or ".bak" in name or (name.endswith(".md") and name != "README.md")
                or name.endswith((".py", ".pyc", ".hold")))
    junk = sorted(p for p in present if _never_public(p))
    if junk:
        tree = api(tok, "POST", f"/repos/{REPO}/git/trees",
                   {"base_tree": tree["sha"],
                    "tree": [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in junk]})
        print(f"pruned {len(junk)} never-public path(s): {', '.join(junk[:8])}")
    # tombstones: a null sha deletes a path from the tree (used for CNAME, see REMOVE_PATHS).
    # Only paths that ACTUALLY exist may be tombstoned - asking GitHub to delete a path that is
    # already gone fails the whole commit with `422 GitRPC::BadObjectState`.
    if REMOVE_PATHS:
        remaining = {e["path"] for e in api(tok, "GET", f"/repos/{REPO}/git/trees/{tree['sha']}?recursive=1")["tree"]}
        targets = sorted(p for p in REMOVE_PATHS if p in remaining)
        if targets:
            tree = api(tok, "POST", f"/repos/{REPO}/git/trees",
                       {"base_tree": tree["sha"],
                        "tree": [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in targets]})
            print(f"removed from tree: {', '.join(targets)}")
        else:
            print(f"nothing to remove (already absent): {', '.join(sorted(REMOVE_PATHS))}")
    if tree["sha"] == base_tree:
        print(f"already up to date at {parent[:7]} — 0 changed files")
        return parent
    commit = api(tok, "POST", f"/repos/{REPO}/git/commits",
                 {"message": message, "tree": tree["sha"], "parents": [parent]})
    api(tok, "PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": commit["sha"], "force": False})
    print(f"published {commit['sha'][:7]} — {len(files)} files, {nbytes/1024:.0f} KB")
    for f in files[:6]:
        print("   ", f)
    if len(files) > 6:
        print(f"    ... and {len(files)-6} more")
    return commit["sha"]


if __name__ == "__main__":
    publish(sys.argv[1] if len(sys.argv) > 1 else "Update launch site")

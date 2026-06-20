#!/usr/bin/env python3
"""Download all repositories of a GitHub owner as ZIPs.

Usage: gh_dl.py <owner> [--out <dir>] [--token <ghp_xxx>] [--filter <glob>]
"""
import io, json, os, re, sys, zipfile, urllib.request, urllib.error, argparse
from urllib.parse import quote

def fetch(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "gh_dl.py/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    ap = argparse.ArgumentParser(description="Download all repos of a GitHub owner")
    ap.add_argument("owner", help="GitHub username or organization")
    ap.add_argument("--out", "-o", default=".", help="Output directory (default: .)")
    ap.add_argument("--token", help="GitHub token (raises rate limit to 5000/h)")
    ap.add_argument("--filter", default="*", help="Glob pattern to filter repos (default: *)")
    args = ap.parse_args()

    owner = args.owner.strip("/")
    out = os.path.join(args.out, owner)

    print(f"Fetching repos for {owner} ...")
    page = 1
    repos = []
    while True:
        url = f"https://api.github.com/users/{quote(owner)}/repos?per_page=100&page={page}&type=all&sort=full_name"
        try:
            batch = fetch(url, args.token)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Might be an org
                url = f"https://api.github.com/orgs/{quote(owner)}/repos?per_page=100&page={page}&type=all&sort=full_name"
                batch = fetch(url, args.token)
            else:
                raise
        if not batch:
            break
        repos.extend(batch)
        page += 1

    print(f"Found {len(repos)} repos")
    pat = re.compile(args.filter.replace("*", ".*").replace("?", ".") + "$", re.I)

    ok = total = 0
    for repo in repos:
        name = repo["name"]
        if not pat.match(name):
            continue
        total += 1
        branch = repo.get("default_branch", "main")
        zip_url = f"https://api.github.com/repos/{quote(owner)}/{quote(name)}/zipball/{quote(branch)}"
        print(f"  {name} @ {branch} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(zip_url)
            req.add_header("User-Agent", "gh_dl.py/1.0")
            if args.token:
                req.add_header("Authorization", f"Bearer {args.token}")
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
        except Exception as e:
            print(f"✗ {e}")
            continue
        dst = os.path.join(out, name)
        os.makedirs(dst, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            members = zf.namelist()
            top = os.path.commonpath(members).split("/", 1)[0] if members else ""
            extracted = 0
            for name_in_zip in members:
                if name_in_zip.endswith("/"):
                    continue
                rel = os.path.relpath(name_in_zip, top) if top else name_in_zip
                local = os.path.join(dst, rel)
                os.makedirs(os.path.dirname(local), exist_ok=True)
                with zf.open(name_in_zip) as src, open(local, "wb") as dst_f:
                    dst_f.write(src.read())
                extracted += 1
            print(f"✓ {extracted} files")
            ok += 1

    print(f"\nDone: {ok}/{total} repos → {out}")

if __name__ == "__main__":
    main()

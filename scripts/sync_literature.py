"""Keep a local copy of the literature next to the code, without putting PDFs into git.

The list of sources is literature/sources.yaml (tracked). The PDFs go to literature/pdf/<key>.pdf,
a git-ignored folder, so they never end up in the public repository.

Usage
-----
    uv run scripts/sync_literature.py                     # show which sources are present
    uv run scripts/sync_literature.py sync --from DIR     # copy matching PDFs from DIR (recursive)
    uv run scripts/sync_literature.py download            # fetch the freely available PDFs
    uv run scripts/sync_literature.py which src/gcm/netlogo   # sources used by a path

A file in DIR counts as a match if its SHA-256 is listed for a source or its name contains one
of the source's `match` substrings (case-insensitive). Existing files are never overwritten
unless --force is given.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIT = ROOT / "literature"
PDF_DIR = LIT / "pdf"
MANIFEST = LIT / "sources.yaml"


def load_sources() -> list[dict]:
    with MANIFEST.open(encoding="utf-8") as fh:
        sources = yaml.safe_load(fh)["sources"]
    keys = [s["key"] for s in sources]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        sys.exit(f"duplicate keys in {MANIFEST.name}: {sorted(dupes)}")
    return sources


def target(src: dict) -> Path:
    return PDF_DIR / f"{src['key']}.pdf"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def identify(path: Path, sources: list[dict]) -> dict | None:
    """Return the source a local file belongs to, by checksum first and file name second."""
    digest = sha256(path)
    for src in sources:
        if digest in (src.get("sha256") or []):
            return src
    name = path.name.lower()
    hits = [s for s in sources if any(m.lower() in name for m in (s.get("match") or []))]
    return hits[0] if len(hits) == 1 else None


def cmd_status(sources: list[dict]) -> int:
    width = max(len(s["key"]) for s in sources)
    missing = 0
    for src in sources:
        present = target(src).exists()
        missing += not present
        flag = "ok     " if present else ("missing" if not src.get("open_pdf") else "missing (download)")
        print(f"{src['key']:<{width}}  {flag:<18}  {src['citation']}")
    print(f"\n{len(sources) - missing} of {len(sources)} sources present in {PDF_DIR.relative_to(ROOT)}/")
    return 0


def cmd_sync(sources: list[dict], source_dir: Path, force: bool) -> int:
    if not source_dir.is_dir():
        sys.exit(f"not a folder: {source_dir}")
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for path in sorted(source_dir.rglob("*.pdf")):
        if PDF_DIR in path.resolve().parents:
            continue
        src = identify(path, sources)
        if src is None:
            continue
        dest = target(src)
        if dest.exists() and not force:
            skipped += 1
            continue
        shutil.copy2(path, dest)
        copied += 1
        print(f"{src['key']:<20} <- {path.name}")
    print(f"\ncopied {copied}, already present {skipped}")
    return cmd_status(sources)


def cmd_download(sources: list[dict], force: bool) -> int:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for src in sources:
        url = src.get("open_pdf")
        dest = target(src)
        if not url or (dest.exists() and not force):
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "gcm-simulation literature sync"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
        except OSError as exc:
            failed += 1
            print(f"{src['key']:<20} failed: {exc}")
            continue
        if not data.startswith(b"%PDF"):
            failed += 1
            print(f"{src['key']:<20} failed: {url} did not return a PDF")
            continue
        dest.write_bytes(data)
        print(f"{src['key']:<20} <- {url}")
    cmd_status(sources)
    return 1 if failed else 0


def cmd_which(sources: list[dict], path: str) -> int:
    want = path.rstrip("/")
    for src in sources:
        for used in src.get("used_in") or []:
            used = used.rstrip("/")
            if want.startswith(used) or used.startswith(want):
                print(f"{src['key']:<20} {src['citation']}  ({used})")
                break
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status", help="list sources and whether a local PDF exists")
    p_sync = sub.add_parser("sync", help="copy matching PDFs from a folder")
    p_sync.add_argument("--from", dest="source_dir", type=Path, required=True)
    p_sync.add_argument("--force", action="store_true", help="overwrite existing files")
    p_dl = sub.add_parser("download", help="fetch PDFs that are freely available (open_pdf)")
    p_dl.add_argument("--force", action="store_true", help="overwrite existing files")
    p_which = sub.add_parser("which", help="sources used by a file or folder of the repository")
    p_which.add_argument("path")
    args = parser.parse_args(argv)

    sources = load_sources()
    if args.cmd == "sync":
        return cmd_sync(sources, args.source_dir, args.force)
    if args.cmd == "download":
        return cmd_download(sources, args.force)
    if args.cmd == "which":
        return cmd_which(sources, args.path)
    return cmd_status(sources)


if __name__ == "__main__":
    raise SystemExit(main())

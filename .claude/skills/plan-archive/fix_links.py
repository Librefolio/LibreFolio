#!/usr/bin/env python3
"""Rewrite relative Markdown links in the developer journal after folders were moved.

Run it AFTER the `git mv`, from anywhere:

    python3 fix_links.py --journal <journal root> --moved OLD_DIR=NEW_DIR [--moved ...] [--dry-run]

OLD_DIR and NEW_DIR are relative to the journal root (e.g.
`Release_2/Phase_1=Release_2/phases/Phase_1`). Every `.md` file of the journal is scanned:
a link is resolved from where the file USED to be, its target is mapped through the moves,
and the link is rewritten relative to where the file is NOW. Links whose target does not
exist after the move were already broken: they are left alone and listed at the end.
External links, anchors-only and absolute paths are never touched.
"""

import argparse
import os
import re
import sys

LINK = re.compile(r"\]\(([^)\s]+)\)")


def parse_moves(items, root):
    moves = []
    for item in items:
        old, new = item.split("=", 1)
        moves.append((os.path.normpath(os.path.join(root, old)), os.path.normpath(os.path.join(root, new))))
    return moves


def remap(path, moves, reverse=False):
    for old, new in moves:
        src, dst = (new, old) if reverse else (old, new)
        if path == src or path.startswith(src + os.sep):
            return dst + path[len(src):]
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--moved", action="append", required=True, metavar="OLD=NEW")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.journal)
    moves = parse_moves(args.moved, root)
    changed_files, rewritten, broken = 0, 0, []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if not name.endswith(".md"):
                continue
            f_new = os.path.join(dirpath, name)
            f_old = remap(f_new, moves, reverse=True)
            text = open(f_new, encoding="utf-8").read()

            def fix(m):
                nonlocal rewritten
                target = m.group(1)
                if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith(("#", "/")):
                    return m.group(0)
                path, frag = (target.split("#", 1) + [""])[:2]
                if not path:
                    return m.group(0)
                abs_target = remap(os.path.normpath(os.path.join(os.path.dirname(f_old), path)), moves)
                if not os.path.exists(abs_target):
                    if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f_new), path))):
                        broken.append(f"{os.path.relpath(f_new, root)} -> {target}")
                    return m.group(0)
                rel = os.path.relpath(abs_target, os.path.dirname(f_new))
                if os.path.normpath(os.path.join(os.path.dirname(f_new), path)) == abs_target:
                    return m.group(0)
                rewritten += 1
                return "](" + rel + ("#" + frag if frag else "") + ")"

            new_text = LINK.sub(fix, text)
            if new_text != text:
                changed_files += 1
                if not args.dry_run:
                    open(f_new, "w", encoding="utf-8").write(new_text)

    print(f"files changed: {changed_files}, links rewritten: {rewritten}{' (dry run)' if args.dry_run else ''}")
    if broken:
        print(f"already broken, left alone: {len(broken)}")
        for b in broken[:40]:
            print("  " + b)
    return 0


if __name__ == "__main__":
    sys.exit(main())

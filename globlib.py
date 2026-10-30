#!/usr/bin/env python3
"""Search the filesystem for files matching the GigaGlobs glob lists."""

import argparse
import csv
import glob
import json
import os
import re
import shutil
import stat
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIRS = [os.path.join(os.getcwd(), "lib"), os.path.join(SCRIPT_DIR, "lib")]
DEFAULT_EXCLUDES = ["/proc", "/sys", "/dev", "/run"]
SIZE_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Style:
    CODES = {"bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33", "cyan": "36"}

    def __init__(self, enabled):
        self.enabled = enabled

    def __call__(self, text, *styles):
        if not self.enabled or not styles:
            return str(text)
        codes = ";".join(self.CODES[s] for s in styles)
        return f"\033[{codes}m{text}\033[0m"


class Progress:
    """Single status line on stderr while the filesystem is walked."""

    def __init__(self, enabled, style):
        self.enabled = enabled
        self.style = style
        self.last = 0.0
        self.frame = 0

    def update(self, scanned, current):
        now = time.monotonic()
        if not self.enabled or now - self.last < 0.1:
            return
        self.last = now
        self.frame = (self.frame + 1) % len(SPINNER)
        width = shutil.get_terminal_size().columns
        label = f"  {SPINNER[self.frame]} Scanning {scanned:,} paths  "
        current = current[-max(width - len(label) - 1, 0):] if width > len(label) else ""
        sys.stderr.write(f"\r\033[K{self.style(label, 'cyan')}{self.style(current, 'dim')}")
        sys.stderr.flush()

    def clear(self):
        if self.enabled:
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()


def parse_size(text):
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMGT]?)i?B?", text.strip(), re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid size '{text}' (examples: 512, 10K, 5M, 1G)")
    return int(float(match[1]) * SIZE_UNITS[match[2].upper()])


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def available_lists():
    found = {}
    for lib in LIB_DIRS:
        for path in sorted(glob.glob(os.path.join(lib, "*.json"))):
            found.setdefault(os.path.splitext(os.path.basename(path))[0], path)
    return found


def resolve_lists(names):
    """Turn list names, file paths and the 'all' keyword into JSON file paths."""
    available = available_lists()
    paths = []
    for name in names:
        if name == "all":
            paths.extend(available.values())
        elif os.path.isfile(name):
            paths.append(name)
        elif name in available:
            paths.append(available[name])
        else:
            options = ", ".join([*available, "all"])
            sys.exit(f"error: no glob list named '{name}' (available: {options})")
    return list(dict.fromkeys(paths))  # Remove duplicates, keep order


def load_lists(paths, name_filter, types):
    lists = []
    for path in paths:
        with open(path, "r") as f:
            data = json.load(f)
        items = [
            item for item in data["items"]
            if (not name_filter or name_filter.lower() in item["name"].lower())
            and (not types or item["type"] in types)
        ]
        lists.append({
            "name": os.path.splitext(os.path.basename(path))[0],
            "description": data.get("description", ""),
            "items": items,
        })
    return lists


def compile_item(item):
    patterns = [glob.translate(p.lstrip("/"), recursive=True, include_hidden=True) for p in item["glob"]]
    return re.compile("|".join(patterns))


def is_excluded(path, args):
    return any(s in path for s in args.exclude) or any(r.search(path) for r in args.regex)


def should_prune(path, args, skip_dirs):
    # Only plain substrings prune safely: every path below a matching folder matches too
    return path in skip_dirs or any(s in path for s in args.exclude)


def scan(root, entries, args, progress):
    """Walk the tree once and test every path against every entry's patterns."""
    skip_dirs = set() if args.no_default_excludes else set(DEFAULT_EXCLUDES)
    prefix = len(root.rstrip("/")) + 1
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_prune(os.path.join(dirpath, d), args, skip_dirs)]
        progress.update(scanned, dirpath)
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            scanned += 1
            relative = path[prefix:]
            for entry in entries:
                if entry["regex"].match(relative):
                    entry["paths"].add(path)
    return scanned


def describe(path, args):
    """Stat a matched path and apply the filters. Returns None if it is filtered out."""
    if is_excluded(path, args):
        return None
    try:
        info = os.stat(path)
    except OSError:
        try:
            info = os.lstat(path)  # Broken symlink
        except OSError:
            return None
    is_dir = stat.S_ISDIR(info.st_mode)
    if not is_dir:
        if args.min_size is not None and info.st_size < args.min_size:
            return None
        if args.max_size is not None and info.st_size > args.max_size:
            return None
    if args.readable and not os.access(path, os.R_OK):
        return None
    if args.writable and not os.access(path, os.W_OK):
        return None
    return {"path": path, "is_dir": is_dir, "size": None if is_dir else info.st_size, "modified": info.st_mtime}


def sort_matches(matches, newest):
    if newest:
        return sorted(matches, key=lambda m: m["modified"], reverse=True)
    return sorted(matches, key=lambda m: m["path"])


def collect(lists, entries, args):
    results = []
    for lst in lists:
        found = []
        for entry in (e for e in entries if e["list"] is lst):
            matches = [m for m in map(lambda p: describe(p, args), entry["paths"]) if m]
            if matches:
                found.append({**entry["item"], "matches": sort_matches(matches, args.newest)})
        results.append({"list": lst["name"], "description": lst["description"], "entries": found})
    return results


def format_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def print_text(results, root, total_entries, scanned, elapsed, args, style):
    names = ", ".join(r["list"] for r in results)
    print()
    print(f"  {style('GigaGlobs', 'bold')}  {style(root, 'cyan')}  {style('·', 'dim')}  {names}  "
          f"{style(f'· {total_entries} entries', 'dim')}")

    match_count = entry_count = 0
    for result in results:
        if not result["entries"]:
            continue
        print()
        print(f"  {style(result['list'], 'bold', 'cyan')}  {style(result['description'], 'dim')}")
        for entry in result["entries"]:
            count = len(entry["matches"])
            match_count += count
            entry_count += 1
            label = f"{entry['type']} · {count} {'match' if count == 1 else 'matches'}"
            print(f"  {style('●', 'green')} {style(entry['name'], 'bold')}  {style(label, 'dim')}")
            for match in entry["matches"]:
                size = "dir" if match["is_dir"] else format_size(match["size"])
                columns = [style(f"{size:>8}", "dim")]
                if args.newest:
                    columns.append(style(format_date(match["modified"]), "yellow"))
                path = match["path"] + ("/" if match["is_dir"] else "")
                columns.append(path)
                print("    " + "  ".join(columns))

    summary = f"{scanned:,} paths scanned in {elapsed:.1f}s"
    print()
    if match_count:
        found = f"{match_count} {'match' if match_count == 1 else 'matches'} in {entry_count} " \
                f"{'entry' if entry_count == 1 else 'entries'}"
        print(f"  {style('✓', 'green', 'bold')} {style(found, 'bold')}  {style('· ' + summary, 'dim')}")
    else:
        print(f"  {style('○', 'yellow')} No matches  {style('· ' + summary, 'dim')}")
    print()


def print_quiet(results, newest):
    unique = {}
    for result in results:
        for entry in result["entries"]:
            for match in entry["matches"]:
                unique[match["path"]] = match
    for match in sort_matches(unique.values(), newest):
        print(match["path"])


def print_json(results, root):
    for result in results:
        for entry in result["entries"]:
            for match in entry["matches"]:
                match["modified"] = datetime.fromtimestamp(match["modified"]).isoformat(timespec="seconds")
    print(json.dumps({"root": root, "results": results}, indent=2))


def print_csv(results):
    writer = csv.writer(sys.stdout)
    writer.writerow(["list", "name", "type", "path", "is_dir", "size", "modified"])
    for result in results:
        for entry in result["entries"]:
            for match in entry["matches"]:
                modified = datetime.fromtimestamp(match["modified"]).isoformat(timespec="seconds")
                writer.writerow([result["list"], entry["name"], entry["type"], match["path"],
                                 match["is_dir"], match["size"] if match["size"] is not None else "", modified])


def print_listing(names, args, style):
    """Show available lists, or the entries of the given lists."""
    if not names:
        available = available_lists()
        if args.quiet:
            print("\n".join(available))
            return
        print()
        for name, path in available.items():
            with open(path, "r") as f:
                data = json.load(f)
            count = f"{len(data['items'])} entries"
            print(f"  {style(f'{name:<12}', 'bold', 'cyan')} {style(f'{count:>11}', 'dim')}  {data.get('description', '')}")
        print()
        return

    lists = load_lists(resolve_lists(names), args.name, args.type)
    for lst in lists:
        if args.quiet:
            print("\n".join(item["name"] for item in lst["items"]))
            continue
        print()
        print(f"  {style(lst['name'], 'bold', 'cyan')}  {style(lst['description'], 'dim')}")
        for item in lst["items"]:
            print(f"  {style('●', 'green')} {style(item['name'], 'bold')}  {style(item['type'], 'dim')}")
            for pattern in item["glob"]:
                print(f"      {style(pattern, 'dim')}")
    if not args.quiet:
        print()


def parse_args():
    parser = argparse.ArgumentParser(
        prog="search.py",
        description="Search the filesystem for files matching GigaGlobs glob lists.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python search.py secrets\n"
               "  python search.py secrets databases -r /home -e node_modules\n"
               "  python search.py all --readable --newest -q\n"
               "  python search.py -l\n",
    )
    parser.add_argument("lists", nargs="*", metavar="LIST",
                        help="list names from ./lib (e.g. secrets), paths to JSON lists, or 'all'")
    parser.add_argument("-r", "--root", default="/", help="folder to search from (default: /)")
    parser.add_argument("-e", "--exclude", action="append", default=[], metavar="TEXT",
                        help="drop matches whose path contains TEXT (repeatable)")
    parser.add_argument("-E", "--regex", action="append", default=[], metavar="REGEX", type=re.compile,
                        help="drop matches whose path matches REGEX (repeatable)")
    parser.add_argument("-n", "--name", metavar="TEXT", help="only run entries whose name contains TEXT")
    parser.add_argument("-t", "--type", action="append", default=[], metavar="TYPE",
                        help="only run entries of this type (repeatable)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="show available lists, or the entries of the given lists, without searching")
    parser.add_argument("-q", "--quiet", action="store_true", help="print only the matched paths")
    parser.add_argument("-f", "--format", choices=["text", "json", "csv"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--readable", action="store_true", help="only show paths the current user can read")
    parser.add_argument("--writable", action="store_true", help="only show paths the current user can write")
    parser.add_argument("--min-size", type=parse_size, metavar="SIZE", help="skip files smaller than SIZE (e.g. 1K)")
    parser.add_argument("--max-size", type=parse_size, metavar="SIZE", help="skip files larger than SIZE (e.g. 10M)")
    parser.add_argument("--newest", action="store_true",
                        help="sort matches from newest to oldest and show when they were last modified")
    parser.add_argument("--no-default-excludes", action="store_true",
                        help=f"also search {', '.join(DEFAULT_EXCLUDES)}")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    args = parser.parse_args()
    if not args.lists and not args.list:
        parser.error("specify at least one list name, or 'all' (see available lists with -l)")
    return args


def main():
    args = parse_args()
    style = Style(sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ)

    if args.list:
        print_listing(args.lists, args, style)
        return

    root = os.path.abspath(os.path.expanduser(args.root))
    if not os.path.isdir(root):
        sys.exit(f"error: root folder '{args.root}' does not exist")

    lists = load_lists(resolve_lists(args.lists), args.name, args.type)
    entries = [{"list": lst, "item": item, "regex": compile_item(item), "paths": set()}
               for lst in lists for item in lst["items"]]
    if not entries:
        sys.exit("error: no entries left to search after applying --name/--type")

    show_progress = sys.stderr.isatty() and not args.quiet and args.format == "text"
    progress = Progress(show_progress, Style(show_progress and not args.no_color and "NO_COLOR" not in os.environ))
    start = time.monotonic()
    try:
        scanned = scan(root, entries, args, progress)
    except KeyboardInterrupt:
        progress.clear()
        sys.exit(130)
    progress.clear()
    elapsed = time.monotonic() - start

    results = collect(lists, entries, args)
    if args.quiet:
        print_quiet(results, args.newest)
    elif args.format == "json":
        print_json(results, root)
    elif args.format == "csv":
        print_csv(results)
    else:
        print_text(results, root, len(entries), scanned, elapsed, args, style)


if __name__ == "__main__":
    main()

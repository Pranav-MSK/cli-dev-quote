#!/usr/bin/env python3
"""fetcher.py - fetch random programming quotes and tech jokes from the CLI.

Primary sources (no authentication needed):
  * Jokes:  JokeAPI   (https://v2.jokeapi.dev), "Programming" category
  * Quotes: Quotable  (https://api.quotable.io), "technology" tag

If a request fails for any reason (offline, timeout, HTTP error, malformed
JSON, unexpected payload), the tool falls back to a small built-in collection
so it always prints something useful. Standard library only.

Usage:
    python fetcher.py                 # one random joke or quote
    python fetcher.py --type joke     # jokes only
    python fetcher.py -n 3 -t quote   # three quotes
    python fetcher.py --offline       # skip the network entirely
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

__version__ = "1.0.0"

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
JOKE_URL = "https://v2.jokeapi.dev/joke/Programming?safe-mode"
QUOTE_URL = "https://api.quotable.io/quotes/random?tags=technology"
REQUEST_TIMEOUT = 5  # seconds
MAX_COUNT = 10
USER_AGENT = f"fetcher-cli/{__version__} (+python-urllib)"


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Item:
    """A single displayable item: either a quote or a joke."""

    kind: str  # "quote" or "joke"
    text: str  # quote body, joke body, or joke setup
    author: Optional[str] = None  # quotes only
    delivery: Optional[str] = None  # punchline of two-part jokes only


class FetchError(Exception):
    """Raised when an API call fails or returns unusable data."""


# --------------------------------------------------------------------------- #
# Built-in fallback content
# --------------------------------------------------------------------------- #
FALLBACK_QUOTES: List[Item] = [
    Item("quote", "Premature optimization is the root of all evil.",
         author="Donald Knuth"),
    Item("quote", "Talk is cheap. Show me the code.",
         author="Linus Torvalds"),
    Item("quote", "Programs must be written for people to read, and only "
                  "incidentally for machines to execute.",
         author="Harold Abelson"),
    Item("quote", "Any fool can write code that a computer can understand. "
                  "Good programmers write code that humans can understand.",
         author="Martin Fowler"),
    Item("quote", "Debugging is twice as hard as writing the code in the "
                  "first place. Therefore, if you write the code as cleverly "
                  "as possible, you are, by definition, not smart enough to "
                  "debug it.",
         author="Brian Kernighan"),
]

FALLBACK_JOKES: List[Item] = [
    Item("joke", "Why do programmers prefer dark mode?",
         delivery="Because light attracts bugs."),
    Item("joke", "How many programmers does it take to change a light bulb?",
         delivery="None. That's a hardware problem."),
    Item("joke", "There are only 10 kinds of people in the world.",
         delivery="Those who understand binary and those who don't."),
]


# --------------------------------------------------------------------------- #
# Networking
# --------------------------------------------------------------------------- #
def http_get_json(url: str, timeout: float = REQUEST_TIMEOUT) -> Any:
    """GET *url* and return the decoded JSON body.

    Every network, HTTP and parsing failure is converted to ``FetchError`` so
    callers only have to handle a single exception type.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} from server") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"network error ({exc.reason})") from exc
    except TimeoutError as exc:  # socket.timeout is an alias on Python 3.10+
        raise FetchError("request timed out") from exc
    except OSError as exc:  # connection reset, SSL problems, etc.
        raise FetchError(f"connection problem ({exc})") from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError("server returned malformed JSON") from exc


# --------------------------------------------------------------------------- #
# Parsers & fetchers (one per API)
# --------------------------------------------------------------------------- #
def parse_joke(payload: Any) -> Item:
    """Convert a JokeAPI v2 payload into an ``Item``."""
    if not isinstance(payload, dict) or payload.get("error"):
        raise FetchError("JokeAPI returned an error payload")
    try:
        if payload["type"] == "twopart":
            return Item("joke", str(payload["setup"]).strip(),
                        delivery=str(payload["delivery"]).strip())
        return Item("joke", str(payload["joke"]).strip())
    except KeyError as exc:
        raise FetchError(f"JokeAPI payload missing field {exc}") from exc


def parse_quote(payload: Any) -> Item:
    """Convert a Quotable payload (object or one-element list) into an ``Item``."""
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        raise FetchError("quote API returned an unexpected payload")
    try:
        return Item("quote", str(payload["content"]).strip(),
                    author=str(payload["author"]).strip())
    except KeyError as exc:
        raise FetchError(f"quote payload missing field {exc}") from exc


def fetch_joke() -> Item:
    """Fetch one programming joke from JokeAPI."""
    return parse_joke(http_get_json(JOKE_URL))


def fetch_quote() -> Item:
    """Fetch one technology quote from Quotable."""
    return parse_quote(http_get_json(QUOTE_URL))


# --------------------------------------------------------------------------- #
# Orchestration with fallback
# --------------------------------------------------------------------------- #
def pick_fallback(kind: str, used: List[Item]) -> Item:
    """Choose a built-in item of *kind*, avoiding repeats when possible."""
    pool = FALLBACK_JOKES if kind == "joke" else FALLBACK_QUOTES
    fresh = [item for item in pool if item not in used]
    return random.choice(fresh or pool)


def collect_items(item_type: str, count: int, offline: bool = False) -> List[Item]:
    """Return *count* items, using the network first and the fallback second.

    After the first network failure for a given kind, we stop retrying that
    API for the rest of the run so users aren't made to wait on N timeouts.
    """
    fetchers: dict[str, Callable[[], Item]] = {
        "joke": fetch_joke,
        "quote": fetch_quote,
    }
    broken: set[str] = set(fetchers) if offline else set()
    items: List[Item] = []
    warned = offline  # don't warn if the user asked for offline mode

    for _ in range(count):
        kind = item_type if item_type != "any" else random.choice(list(fetchers))
        item: Optional[Item] = None

        if kind not in broken:
            try:
                item = fetchers[kind]()
            except FetchError as exc:
                broken.add(kind)
                if not warned:
                    print(f"[warn] {kind} API unavailable: {exc}. "
                          "Using built-in content.", file=sys.stderr)
                    warned = True

        items.append(item or pick_fallback(kind, items))
    return items


# --------------------------------------------------------------------------- #
# Presentation
# --------------------------------------------------------------------------- #
def format_item(item: Item) -> str:
    """Render an ``Item`` as printable text."""
    if item.kind == "quote":
        return f"\u201c{item.text}\u201d\n    \u2014 {item.author or 'Unknown'}"
    if item.delivery:
        return f"{item.text}\n\n    {item.delivery}"
    return item.text


def render(items: List[Item]) -> str:
    """Join formatted items with a visual separator."""
    separator = "\n\n" + "\u2500" * 40 + "\n\n"
    return separator.join(format_item(item) for item in items)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def positive_int(value: str) -> int:
    """argparse type: integer between 1 and MAX_COUNT."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
    if not 1 <= number <= MAX_COUNT:
        raise argparse.ArgumentTypeError(f"must be between 1 and {MAX_COUNT}")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="fetcher.py",
        description="Fetch random programming quotes and tech jokes.",
    )
    parser.add_argument("-t", "--type", choices=("joke", "quote", "any"),
                        default="any", help="what to fetch (default: any)")
    parser.add_argument("-n", "--count", type=positive_int, default=1,
                        metavar="N",
                        help=f"number of items, 1-{MAX_COUNT} (default: 1)")
    parser.add_argument("--offline", action="store_true",
                        help="skip the network and use built-in content")
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)

    # Make sure curly quotes / dashes never crash on legacy terminals.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        items = collect_items(args.type, args.count, offline=args.offline)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    print(render(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())

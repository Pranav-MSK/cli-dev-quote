# cli-dev-quote [work under progress]

A tiny terminal tool that fetches and displays a random programming quote from a public API.

## fetcher.py

A lightweight command-line tool that fetches a random programming quote or tech joke from a public API. Standard library only, no installation required.
 
## Requirements
 
- Python 3.9 or newer
- No third-party packages
## Project structure
 
```
quote-fetcher/
├── fetcher.py
└── README.md
```
 
## Usage
 
```bash
python fetcher.py                  # one random joke or quote
python fetcher.py --type joke      # jokes only
python fetcher.py --type quote     # quotes only
python fetcher.py -t quote -n 3    # three quotes
python fetcher.py -n 5             # five mixed items
python fetcher.py --offline        # skip the network, use built-in content
python fetcher.py --help
python fetcher.py --version
```
 
### Options
 
| Flag | Description | Default |
|------|-------------|---------|
| `-t`, `--type` | `joke`, `quote`, or `any` | `any` |
| `-n`, `--count` | Number of items to fetch (1 to 10) | `1` |
| `--offline` | Skip the network and use built-in content | off |
| `-V`, `--version` | Show the version and exit | |
| `-h`, `--help` | Show help and exit | |
 
### Output format
 
Quotes:
 
```
“Talk is cheap. Show me the code.”
    — Linus Torvalds
```
 
Two-part jokes:
 
```
Why do programmers prefer dark mode?
 
    Because light attracts bugs.
```
 
When several items are requested, they are separated by a horizontal rule.
 
## Data sources
 
| Content | API | Authentication |
|---------|-----|----------------|
| Jokes | [JokeAPI](https://v2.jokeapi.dev) (`Programming` category, safe mode) | None |
| Quotes | [Quotable](https://api.quotable.io) (`technology` tag) | None |
 
## Fallback and error handling
 
- If an API call fails (offline, timeout, HTTP error, malformed JSON, unexpected payload), the tool prints a built-in item instead and shows one `[warn]` line on stderr.
- The built-in collection holds 5 classic programming quotes and 3 jokes.
- After the first failure for a given type, that API is not retried during the same run, so a multi-item request offline does not wait through repeated timeouts.
- Users never see a raw Python traceback.
### Exit codes
 
| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid command-line arguments |
| 130 | Interrupted with Ctrl-C |
 
## Configuration
 
Edit the constants at the top of `fetcher.py`:
 
- `JOKE_URL` and `QUOTE_URL`: API endpoints
- `REQUEST_TIMEOUT`: seconds to wait per request (default 5)
- `MAX_COUNT`: upper limit for `--count` (default 10)
- `FALLBACK_QUOTES` and `FALLBACK_JOKES`: the built-in content
 

"""Downloads with retries, atomic writes and SHA-256 hashes."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

USER_AGENT = "sulteng-remote-sensing/0.1"


class FetchError(RuntimeError):
    """A download failed after every retry, failed with a permanent HTTP error, or returned no bytes."""


@dataclass(frozen=True)
class ManifestEntry:
    url: str  # the display label; never contains a secret
    file: str
    bytes: int
    sha256: str
    retrieved_at: str
    last_modified: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def download(
    url: str,
    dest: Path | str,
    *,
    label: str | None = None,
    timeout: float = 120,
    retries: int = 2,
    backoff: float = 2.0,
) -> ManifestEntry:
    """Fetch `url` into `dest`. `label` stands in for the URL in errors and in the returned entry."""
    dest = Path(dest)
    shown = label or url
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                digest, size = hashlib.sha256(), 0
                with tmp.open("wb") as fh:
                    while chunk := response.read(1 << 20):
                        fh.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                last_modified = _http_date(response.headers.get("Last-Modified"))
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as exc:
            last_error = exc
            tmp.unlink(missing_ok=True)
            if _permanent(exc):
                break
            if attempt < retries:
                time.sleep(backoff * 2**attempt)
            continue
        if size == 0:
            tmp.unlink(missing_ok=True)
            raise FetchError(f"{shown}: empty response")
        os.replace(tmp, dest)
        return ManifestEntry(
            url=shown,
            file=dest.name,
            bytes=size,
            sha256=digest.hexdigest(),
            retrieved_at=utc_now_iso(),
            last_modified=last_modified,
        )
    raise FetchError(f"{shown}: {_describe(last_error, secret=label is not None)}") from None


def _permanent(exc: Exception) -> bool:
    """A client error that another try cannot fix (a bad key, a wrong URL). 408 and 429 can pass on retry."""
    return isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500 and exc.code not in (408, 429)


def _describe(exc: Exception | None, *, secret: bool) -> str:
    """Short reason. With a label, echo nothing that could contain the real URL or path."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if secret:
        return type(exc).__name__
    return f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"


def _http_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def stale_inputs(entries: list[dict], min_last_modified: str) -> list[str]:
    """Files whose server date is missing or earlier than `min_last_modified` (YYYY-MM-DD, 00:00 UTC)."""
    cutoff = datetime.fromisoformat(min_last_modified).replace(tzinfo=timezone.utc)
    return [
        e["file"] for e in entries
        if not e.get("last_modified") or datetime.fromisoformat(e["last_modified"]) < cutoff
    ]


def load_manifest(path: Path | str) -> dict[str, dict]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_manifest(path: Path | str, manifest: dict[str, dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")

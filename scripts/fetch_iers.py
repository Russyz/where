"""Fetch the IERS Fortran sources listed by kartverket/where."""

from __future__ import annotations

import configparser
from pathlib import Path
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "iers2010-dll-github-actions/1.0"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                data = response.read()
            if not data:
                raise ValueError(f"Empty response: {url}")
            target.write_bytes(data)
            return
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError(f"Could not download {url}") from exc
            time.sleep(2 ** attempt)


def main(repo: Path) -> None:
    config_path = repo / "config" / "download_iers_2010.conf"
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    if not config.read(config_path, encoding="utf-8"):
        raise FileNotFoundError(config_path)

    # The upstream configuration still uses HTTP; the source server also serves HTTPS.
    base = config["library"]["source_url"].replace("http://", "https://").rstrip("/")
    target_root = repo / config["library"]["target_dir"]
    count = 0
    for section in config.sections():
        if not section.startswith("files"):
            continue
        subdir = config[section].get("__target__", "")
        for name, source_dir in config[section].items():
            if name.startswith("__"):
                continue
            url = f"{base}/{source_dir.strip('/')}/{name}"
            target = target_root / subdir / name
            print(f"{url} -> {target}", flush=True)
            download(url, target)
            count += 1
    print(f"Downloaded {count} IERS source and data files")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())

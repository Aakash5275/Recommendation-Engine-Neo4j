"""Download the MovieLens 32M export from GroupLens."""

from __future__ import annotations

import argparse
import urllib.request
import zipfile
from pathlib import Path

from src.config import ROOT

DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-32m.zip"


def download_dataset(dest: Path, force: bool = False) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    extracted = dest / "ml-32m"
    if (extracted / "movies.csv").is_file() and not force:
        print(f"Already present: {extracted}")
        return extracted

    zip_path = dest / "ml-32m.zip"
    if not zip_path.is_file() or force:
        print(f"Downloading {DATASET_URL}")

        def _progress(block_count: int, block_size: int, total_size: int) -> None:
            if total_size <= 0:
                return
            done = min(block_count * block_size, total_size)
            percent = done * 100 / total_size
            if block_count % 200 == 0 or done == total_size:
                print(f"  {percent:5.1f}% ({done / 1_000_000:,.1f} MB)")

        urllib.request.urlretrieve(DATASET_URL, zip_path, _progress)

    print(f"Extracting {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(dest)
    if not (extracted / "movies.csv").is_file():
        raise FileNotFoundError(f"movies.csv was not found under {dest} after extract")
    return extracted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download MovieLens 32M")
    parser.add_argument("--dest", type=Path, default=ROOT / "data")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    dest = args.dest if args.dest.is_absolute() else Path.cwd() / args.dest
    try:
        path = download_dataset(dest, force=args.force)
    except Exception as exc:
        print(f"Download failed: {exc}")
        return 1
    print(f"Dataset ready at {path}")
    print("Next: python -m src.ingest --data-dir data/ml-32m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

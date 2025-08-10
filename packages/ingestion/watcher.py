"""Folder watch ingestion using watchfiles.
Run: python -m packages.ingestion.watcher --path ./docs --interval 2
"""
from watchfiles import awatch
from pathlib import Path
import asyncio, argparse, time
from packages.ingestion.ingest import ingest_path, ALLOWED_EXT

async def watch(path: Path, interval: float, tags):
    print(f"[watcher] watching {path} interval={interval}s")
    seen = {}
    while True:
        async for changes in awatch(path, stop_event=None, watch_filter=None):
            for change, file_path in changes:
                p = Path(file_path)
                if p.suffix.lower() not in ALLOWED_EXT:
                    continue
                try:
                    print(f"[watcher] change detected {p}")
                    ingest_path(str(p.parent), tags=tags)
                except Exception as e:
                    print(f"[watcher] error ingesting {p}: {e}")
        await asyncio.sleep(interval)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--path', default='./docs')
    ap.add_argument('--interval', type=float, default=5)
    ap.add_argument('--tags', default='')
    args = ap.parse_args()
    tags = [t for t in args.tags.split(',') if t]
    asyncio.run(watch(Path(args.path), args.interval, tags))

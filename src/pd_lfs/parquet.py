import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


MANIFEST_NAME = "_manifest.json"


def write_parquet(df, path, group=None, max_bytes=50 * 1024**2,
                  compression="zstd", rows_per_check=50_000, n_jobs=None):
    """Write df to path/ as part-*.parquet with a _manifest.json index.
    The manifest enables read_parquet over plain HTTPS (no directory listing).
    """
    if not path.endswith('/'):
        path = path + '/'
    path = Path(path)

    if group is None:
        if path.exists():
            for old in path.glob("part-*.parquet"):
                old.unlink()
            (path / MANIFEST_NAME).unlink(missing_ok=True)
        written = _write_flat(df, path, max_bytes, compression, rows_per_check)
        entries = [_entry(w, "", {}) for w in written]
        _write_manifest(path, None, entries)
        return

    group_cols = [group] if isinstance(group, str) else list(group)
    missing = set(group_cols) - set(df.columns)
    if missing:
        raise KeyError(f"group columns not in df: {missing}")

    if path.exists():
        for old in path.rglob("part-*.parquet"):
            old.unlink()
        (path / MANIFEST_NAME).unlink(missing_ok=True)

    jobs = []
    for keys, sub in df.groupby(group_cols, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        rel_dir = "/".join(f"{c}={v}" for c, v in zip(group_cols, keys))
        subdir = path / rel_dir
        sub = sub.drop(columns=group_cols).reset_index(drop=True)
        partition = {c: _json_safe(v) for c, v in zip(group_cols, keys)}
        jobs.append((sub, subdir, rel_dir, partition))

    if not jobs:
        _write_manifest(path, group_cols, [])
        return

    if n_jobs is None:
        try:
            available = len(os.sched_getaffinity(0))
        except AttributeError:
            available = os.cpu_count() or 1
        n_jobs = min(available, len(jobs))

    all_entries = []
    if n_jobs <= 1 or len(jobs) == 1:
        for sub, subdir, rel_dir, partition in jobs:
            written = _write_flat(sub, subdir, max_bytes, compression, rows_per_check)
            all_entries.extend(_entry(w, rel_dir, partition) for w in written)
    else:
        with ThreadPoolExecutor(max_workers=n_jobs) as pool:
            futures = {
                pool.submit(_write_flat, sub, subdir,
                            max_bytes, compression, rows_per_check):
                    (rel_dir, partition)
                for sub, subdir, rel_dir, partition in jobs
            }
            for fut in as_completed(futures):
                rel_dir, partition = futures[fut]
                all_entries.extend(
                    _entry(w, rel_dir, partition) for w in fut.result()
                )

    _write_manifest(path, group_cols, all_entries)


def _entry(written, rel_dir, partition):
    rel_path = f"{rel_dir}/{written['name']}" if rel_dir else written["name"]
    return {
        "path": rel_path,
        "partition": partition,
        "size": written["size"],
        "num_rows": written["num_rows"],
    }


def _json_safe(v):
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return str(v)


def _write_manifest(path, group_cols, entries):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "group_cols": group_cols, "files": entries}
    with open(path / MANIFEST_NAME, "w") as f:
        json.dump(manifest, f, indent=2)


def _write_flat(df, path, max_bytes, compression, rows_per_check):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    for old in path.glob("part-*.parquet"):
        old.unlink()

    table = pa.Table.from_pandas(df, preserve_index=False)
    if len(table) == 0:
        return []

    schema = table.schema
    threshold = int(max_bytes * 0.9)
    file_idx, offset, n = 0, 0, len(table)
    written = []

    while offset < n:
        start = offset
        file_path = path / f"part-{file_idx:05d}.parquet"
        writer = pq.ParquetWriter(file_path, schema, compression=compression)
        try:
            while offset < n:
                chunk = table.slice(offset, rows_per_check)
                writer.write_table(chunk)
                offset += len(chunk)
                if file_path.stat().st_size >= threshold:
                    break
        finally:
            writer.close()
        written.append({
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "num_rows": offset - start,
        })
        file_idx += 1

    over = [(w["name"], w["size"]) for w in written if w["size"] > max_bytes]
    if over:
        raise RuntimeError(
            f"File(s) exceeded {max_bytes} bytes: {over}. Lower rows_per_check."
        )
    return written


def read_parquet(path, **kwargs):
    """Read a dataset written by write_parquet. Accepts local paths or https URLs.
    Falls back to pandas' directory discovery if no manifest is present.
    """
    if not path.endswith('/'):
        path = path + '/'
    if isinstance(path, str) and path.startswith(("http://", "https://")):
        base = path if path.endswith("/") else path + "/"
        with urlopen(urljoin(base, MANIFEST_NAME)) as resp:
            manifest = json.load(resp)
        frames = []
        for entry in manifest["files"]:
            with urlopen(urljoin(base, entry["path"])) as resp:
                buf = BytesIO(resp.read())
            part = pd.read_parquet(buf, engine="pyarrow", **kwargs)
            for col, val in entry.get("partition", {}).items():
                part[col] = val
            frames.append(part)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    base = Path(path)
    manifest_path = base / MANIFEST_NAME
    if not manifest_path.exists():
        return pd.read_parquet(base, engine="pyarrow", **kwargs)

    with open(manifest_path) as f:
        manifest = json.load(f)
    frames = []
    for entry in manifest["files"]:
        part = pd.read_parquet(base / entry["path"], engine="pyarrow", **kwargs)
        for col, val in entry.get("partition", {}).items():
            part[col] = val
        frames.append(part)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

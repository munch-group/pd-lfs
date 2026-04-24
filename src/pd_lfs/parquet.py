import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


MANIFEST_NAME = "_manifest.json"


def optimize_dataframe(df, precision=None, float_decimals=None,
                       category_threshold=0.2):
    """Reduce a dataframe's memory/disk footprint in-place-safe fashion.

    Integer columns are always downcast to the smallest signed/unsigned int
    that fits the data. Object columns whose fraction of unique values is
    below ``category_threshold`` are converted to ``category``.

    Floats are left untouched unless ``precision`` or ``float_decimals`` is
    given. ``precision`` sets a single dtype for all float columns based on
    required significant digits. ``float_decimals`` is applied per column:
    each column is cast to the smallest float dtype that preserves the
    requested number of digits *after the decimal point*, given the column's
    actual magnitude.

    Parameters
    ----------
    df : pandas.DataFrame
        Input dataframe.
    precision : int or None, default None
        Required significant decimal digits for all float columns. Typical
        values: 6 (float32), 15 (float64). Mutually exclusive with
        ``float_decimals``.
    float_decimals : int or None, default None
        Required digits after the decimal point, evaluated per column using
        the column's maximum absolute value. A column with max ``|x|=1234``
        and ``float_decimals=6`` needs ~10 significant digits (float64).
    category_threshold : float, default 0.2
        Object columns with ``nunique / len < category_threshold`` become
        categorical. Set to 0 to disable.
    """
    return _optimize(df, precision, float_decimals, category_threshold,
                     copy=True)


def _optimize_for_write(df, precision=None, float_decimals=None,
                        category_threshold=0.2):
    """Internal optimizer that avoids the upfront df.copy() of the public API.

    Unchanged columns are referenced, not copied. Only transformed columns
    materialize new arrays. The caller must treat the input df as consumed.
    """
    return _optimize(df, precision, float_decimals, category_threshold,
                     copy=False)


def _optimize(df, precision, float_decimals, category_threshold, copy):
    if precision is not None and float_decimals is not None:
        raise ValueError("Pass either precision or float_decimals, not both.")

    if copy:
        out = df.copy()
    else:
        out = pd.DataFrame({c: df[c] for c in df.columns}, copy=False)

    int_cols = out.select_dtypes(include=["integer"]).columns
    for col in int_cols:
        s = pd.to_numeric(out[col], downcast="integer")
        if s.min() >= 0:
            s = pd.to_numeric(s, downcast="unsigned")
        out[col] = s

    if precision is not None:
        target = _smallest_float_dtype(precision)
        for col in out.select_dtypes(include=["floating"]).columns:
            if out[col].dtype.itemsize > np.dtype(target).itemsize:
                out[col] = out[col].astype(target)

    if float_decimals is not None:
        for col in out.select_dtypes(include=["floating"]).columns:
            max_abs = out[col].abs().max()
            if not np.isfinite(max_abs) or max_abs == 0:
                continue
            int_digits = max(0, int(np.floor(np.log10(max_abs))) + 1)
            target = _smallest_float_dtype(int_digits + float_decimals)
            if out[col].dtype.itemsize > np.dtype(target).itemsize:
                out[col] = out[col].astype(target)

    if category_threshold > 0:
        n = len(out)
        for col in out.select_dtypes(include=["object"]).columns:
            if n and out[col].nunique(dropna=True) / n < category_threshold:
                out[col] = out[col].astype("category")

    return out


def _smallest_float_dtype(precision):
    """Return the smallest numpy float dtype with at least ``precision`` digits."""
    for dtype in (np.float16, np.float32, np.float64):
        if np.finfo(dtype).precision >= precision:
            return dtype
    raise ValueError(f"No float dtype provides {precision} decimal digits.")


def write_parquet(df, path, group=None, max_bytes=50 * 1024**2,
                  compression="zstd", rows_per_check=50_000, n_jobs=None,
                  optimize=True, precision=None, float_decimals=None,
                  category_threshold=0.2):
    """Write df to path/ as part-*.parquet with a _manifest.json index.
    The manifest enables read_parquet over plain HTTPS (no directory listing).

    When ``optimize=True`` (default) columns are downcast on the way out —
    ints shrunk, low-cardinality objects made categorical, floats reduced
    only if ``precision`` or ``float_decimals`` is set. The original per-
    column dtypes are stored in the manifest so ``read_parquet`` restores
    them transparently.
    """
    if not path.endswith('/'):
        path = path + '/'
    path = Path(path)

    original_dtypes = {c: str(df[c].dtype) for c in df.columns}

    if optimize:
        df = _optimize_for_write(df, precision=precision,
                                 float_decimals=float_decimals,
                                 category_threshold=category_threshold)

    if group is None:
        if path.exists():
            for old in path.glob("part-*.parquet"):
                old.unlink()
            (path / MANIFEST_NAME).unlink(missing_ok=True)
        written = _write_flat(df, path, max_bytes, compression, rows_per_check)
        entries = [_entry(w, "", {}) for w in written]
        _write_manifest(path, None, entries, original_dtypes)
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
    for keys, sub in df.groupby(group_cols, sort=False, observed=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        rel_dir = "/".join(f"{c}={v}" for c, v in zip(group_cols, keys))
        subdir = path / rel_dir
        sub = sub.drop(columns=group_cols).reset_index(drop=True)
        partition = {c: _json_safe(v) for c, v in zip(group_cols, keys)}
        jobs.append((sub, subdir, rel_dir, partition))

    del df

    if not jobs:
        _write_manifest(path, group_cols, [], original_dtypes)
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

    _write_manifest(path, group_cols, all_entries, original_dtypes)


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


def _write_manifest(path, group_cols, entries, dtypes=None):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 2,
        "group_cols": group_cols,
        "dtypes": dtypes or {},
        "files": entries,
    }
    with open(path / MANIFEST_NAME, "w") as f:
        json.dump(manifest, f, indent=2)


def _write_flat(df, path, max_bytes, compression, rows_per_check):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    for old in path.glob("part-*.parquet"):
        old.unlink()

    n = len(df)
    if n == 0:
        return []

    schema = pa.Table.from_pandas(df.iloc[:0], preserve_index=False).schema
    threshold = int(max_bytes * 0.9)
    file_idx, offset = 0, 0
    written = []

    while offset < n:
        start = offset
        file_path = path / f"part-{file_idx:05d}.parquet"
        writer = pq.ParquetWriter(file_path, schema, compression=compression)
        try:
            while offset < n:
                end = min(offset + rows_per_check, n)
                chunk = pa.Table.from_pandas(
                    df.iloc[offset:end], preserve_index=False, schema=schema
                )
                writer.write_table(chunk)
                offset = end
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

    If the manifest records original dtypes (version >= 2), columns are cast
    back to those dtypes so that optimization done at write time is
    transparent to the caller.
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
        result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        _restore_dtypes(result, manifest.get("dtypes", {}))
        return result

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
    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    _restore_dtypes(result, manifest.get("dtypes", {}))
    return result


def _restore_dtypes(frame, dtypes):
    for col, dt in dtypes.items():
        if col in frame.columns and str(frame[col].dtype) != dt:
            try:
                frame[col] = frame[col].astype(dt)
            except (TypeError, ValueError):
                pass

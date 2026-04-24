import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pd_lfs.parquet import read_parquet, write_parquet


def _mixed_df(n=1000):
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "chrom": pd.Categorical(["chr1"] * (n // 2) + ["chr2"] * (n // 2)),
        "pos": np.arange(n, dtype="int64"),
        "signed_small": rng.integers(-10, 10, size=n, dtype="int64"),
        "unsigned_small": rng.integers(0, 250, size=n, dtype="int64"),
        "score": rng.random(n),
        "label_low_card": [f"peak_{i % 4}" for i in range(n)],
        "label_high_card": [f"id_{i}" for i in range(n)],
        "flag": rng.integers(0, 2, size=n).astype(bool),
    })


def test_flat_roundtrip_preserves_dtypes(tmp_path):
    df = _mixed_df()
    write_parquet(df, str(tmp_path))
    out = read_parquet(str(tmp_path))

    assert list(out.columns) == list(df.columns) or set(out.columns) == set(df.columns)
    out = out[df.columns]
    for col in df.columns:
        assert str(out[col].dtype) == str(df[col].dtype), col
    pd.testing.assert_frame_equal(
        out.reset_index(drop=True),
        df.reset_index(drop=True),
        check_categorical=False,
    )


def test_grouped_roundtrip_preserves_group_dtype(tmp_path):
    df = _mixed_df()
    write_parquet(df, str(tmp_path), group="chrom")
    out = read_parquet(str(tmp_path))

    assert str(out["chrom"].dtype) == str(df["chrom"].dtype)
    out = out[df.columns].sort_values("pos").reset_index(drop=True)
    expected = df.sort_values("pos").reset_index(drop=True)
    pd.testing.assert_frame_equal(out, expected, check_categorical=False)


def test_optimize_reduces_disk_size(tmp_path):
    rng = np.random.default_rng(0)
    n = 100_000
    df = pd.DataFrame({
        "small": rng.integers(0, 100, size=n, dtype="int64"),
        "signed": rng.integers(-10, 10, size=n, dtype="int64"),
        "score": rng.random(n),
    })
    raw_dir = tmp_path / "raw"
    opt_dir = tmp_path / "opt"

    write_parquet(df, str(raw_dir), optimize=False)
    write_parquet(df, str(opt_dir), optimize=True, precision=6)

    def total_bytes(d):
        return sum(p.stat().st_size for p in Path(d).glob("part-*.parquet"))

    assert total_bytes(opt_dir) < total_bytes(raw_dir)


def test_float_downcast_via_precision(tmp_path):
    df = pd.DataFrame({"x": np.linspace(0, 1, 1000, dtype="float64")})
    write_parquet(df, str(tmp_path), precision=6)

    with open(Path(tmp_path) / "_manifest.json") as f:
        manifest = json.load(f)
    assert manifest["dtypes"]["x"] == "float64"

    out = read_parquet(str(tmp_path))
    assert str(out["x"].dtype) == "float64"
    assert np.allclose(out["x"].to_numpy(), df["x"].to_numpy(), atol=1e-6)


def test_v1_manifest_backward_compat(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    write_parquet(df, str(tmp_path), optimize=False)

    manifest_path = Path(tmp_path) / "_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    legacy = {
        "version": 1,
        "group_cols": manifest["group_cols"],
        "files": manifest["files"],
    }
    with open(manifest_path, "w") as f:
        json.dump(legacy, f)

    out = read_parquet(str(tmp_path))
    assert len(out) == 3
    assert set(out.columns) == {"a", "b"}


def test_optimize_false_still_records_dtypes(tmp_path):
    df = _mixed_df(n=100)
    write_parquet(df, str(tmp_path), optimize=False)

    with open(Path(tmp_path) / "_manifest.json") as f:
        manifest = json.load(f)
    assert manifest["version"] == 2
    assert manifest["dtypes"] == {c: str(df[c].dtype) for c in df.columns}


def test_empty_dataframe(tmp_path):
    df = pd.DataFrame({"a": pd.Series(dtype="int64"), "b": pd.Series(dtype="object")})
    write_parquet(df, str(tmp_path))
    out = read_parquet(str(tmp_path))
    assert len(out) == 0

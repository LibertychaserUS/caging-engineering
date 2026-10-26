#!/usr/bin/env python3
"""Fill the null fields of experiments/manifest.json before any agent run.

Steps (idempotent; rerunning recomputes everything from the pinned sources):
  1. Check the exercism/python checkout is at the pinned commit.
  2. For every practice exercise, run the official example solution against the
     official tests inside the harness image (network disabled). Failures form the
     exclusion list (PREREGISTRATION §0.1 "Pinning").
  3. Admitted = all exercises - excluded - smoke-test exercises.
  4. With random.Random(draw_seed): the H3 subsets (80, then 40 of those 80) and
     three H4 orders, each an independent draw of 40 admitted exercises without
     replacement (the preregistration does not say whether the three orders share
     their exercises; independent draws are the coarser choice and are recorded here).
Usage:
  python make_manifest.py --exercism-dir <checkout> [--manifest experiments/manifest.json]
                          --stage-dir <bind-mountable scratch dir> [--image ce-harness:py312] [--jobs 4]
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def git_head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()


def exercise_files(ex_dir: Path) -> dict:
    cfg = json.loads((ex_dir / ".meta" / "config.json").read_text())
    files = cfg["files"]
    listed = set(files.get("solution", []) + files.get("test", []) + files.get("editor", []))
    support = sorted(p.name for p in ex_dir.iterdir()
                     if p.is_file() and not p.name.startswith(".") and p.name not in listed)
    return {"solution": files.get("solution", []), "test": files.get("test", []),
            "example": files.get("example", []), "editor": files.get("editor", []),
            "support": support}


def run_example(ex_dir: Path, image: str, stage_dir: Path, timeout: int = 180) -> dict:
    """Stage stub->example and run pytest in a throwaway container. Returns a record.

    stage_dir must be on a path the Docker daemon can bind-mount (on macOS the
    default temp dir under /var/folders is not shared and mounts as empty)."""
    files = exercise_files(ex_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ce-ex-", dir=stage_dir) as tmp:
        stage = Path(tmp) / ex_dir.name
        stage.mkdir()
        # Everything the agent will see: all regular top-level files of the exercise
        # (stub, tests, and support modules such as test_utils.py); never the dot-dirs.
        for src in ex_dir.iterdir():
            if src.is_file() and not src.name.startswith("."):
                shutil.copy(src, stage / src.name)
        if len(files["example"]) != len(files["solution"]):
            return {"exercise": ex_dir.name, "rc": -1,
                    "reason": f"example/solution count mismatch {files['example']}/{files['solution']}"}
        for ex, sol in zip(files["example"], files["solution"]):
            dst = stage / sol
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ex_dir / ex, dst)
        cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "1g", "--cpus", "1",
               "-v", f"{stage}:/work/{ex_dir.name}", "-w", f"/work/{ex_dir.name}", image,
               "python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            rc, tail = p.returncode, (p.stdout + p.stderr).strip().splitlines()[-3:]
        except subprocess.TimeoutExpired:
            rc, tail = -2, ["timeout"]
    return {"exercise": ex_dir.name, "rc": rc, "reason": None if rc == 0 else " | ".join(tail)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exercism-dir", required=True, type=Path)
    ap.add_argument("--manifest", default=Path(__file__).resolve().parents[1] / "manifest.json", type=Path)
    ap.add_argument("--image", default="ce-harness:py312")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--stage-dir", type=Path, required=True,
                    help="bind-mountable scratch directory (not under /var/folders on macOS)")
    a = ap.parse_args()

    m = json.loads(a.manifest.read_text())
    pinned = m["sources"]["exercism_python"]["commit"]
    head = git_head(a.exercism_dir)
    if head != pinned:
        print(f"exercism checkout is at {head}, manifest pins {pinned}", file=sys.stderr)
        return 2
    practice = a.exercism_dir / m["sources"]["exercism_python"]["path"]
    ex_dirs = sorted(p for p in practice.iterdir() if (p / ".meta" / "config.json").exists())
    print(f"{len(ex_dirs)} exercises; running official examples in {a.image} ...")
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        records = list(pool.map(lambda d: run_example(d, a.image, a.stage_dir), ex_dirs))
    excluded = [r for r in records if r["rc"] != 0]
    smoke = set(m["smoke_test_exercises"])
    admitted = sorted(r["exercise"] for r in records if r["rc"] == 0 and r["exercise"] not in smoke)
    rng = random.Random(m["draw_seed"])
    subset80 = sorted(rng.sample(admitted, 80))
    subset40 = sorted(rng.sample(subset80, 40))
    orders = [rng.sample(admitted, 40) for _ in range(3)]

    m["exclusion_list"] = excluded
    m["admitted_exercises"] = admitted
    m["exercise_files"] = {d.name: exercise_files(d) for d in ex_dirs}
    m["h3_subset_80"] = subset80
    m["h3_subset_40"] = subset40
    m["h4_orders"] = orders
    m["image"] = {"name": a.image, "dockerfile": "experiments/harness/docker/Dockerfile"}
    m["notes"] = ("Filled by experiments/harness/make_manifest.py from draw_seed. H4 orders are three "
                  "independent draws of 40 admitted exercises without replacement within an order.")
    a.manifest.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
    print(f"excluded {len(excluded)}: {[r['exercise'] for r in excluded]}")
    print(f"admitted {len(admitted)} (smoke {sorted(smoke)} excluded)")
    print(f"h3: {len(subset80)}/{len(subset40)}; h4: 3 orders x 40")
    return 0


if __name__ == "__main__":
    sys.exit(main())

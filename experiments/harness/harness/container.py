"""One Docker container per episode, driven through the `docker` CLI (DESIGN.md "Container").

    docker run -d --network none --memory 1g --cpus 1 --pids-limit 256 -w /work/<slug> <image> sleep infinity

Files enter the container only through `docker cp` (never a shell), so that a write made by
the write_file tool and a write made by run_shell are distinguishable (K1/K2). Reads go
through `docker exec cat` with an argv (no shell). The image name comes from env CE_IMAGE
(default ce-harness:py312). Shell commands run as `timeout -s KILL <t> sh -lc <cmd>` inside
the container so that a hung command cannot outlive its tool call.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .types import HarnessError

DEFAULT_IMAGE = "ce-harness:py312"
RUN_FLAGS: tuple[str, ...] = ("--network", "none", "--memory", "1g", "--cpus", "1", "--pids-limit", "256")


def image_name() -> str:
    return os.environ.get("CE_IMAGE", DEFAULT_IMAGE)


def _docker(*argv: str, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        p = subprocess.run(["docker", *argv], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise HarnessError("docker CLI not found") from e
    except subprocess.TimeoutExpired as e:
        raise HarnessError(f"docker {argv[0]} timed out") from e
    if check and p.returncode != 0:
        raise HarnessError(f"docker {' '.join(argv[:2])} failed (rc={p.returncode}): {p.stderr.strip()[:500]}")
    return p


def image_exists(image: str | None = None) -> bool:
    p = _docker("image", "inspect", image or image_name(), check=False)
    return p.returncode == 0


@dataclass
class Container:
    cid: str
    workdir: str

    @classmethod
    def start(cls, exercise_dir: Path, slug: str, image: str | None = None) -> "Container":
        """Start the sandbox and copy `exercise_dir`'s content into /work/<slug>."""
        workdir = f"/work/{slug}"
        p = _docker("run", "-d", *RUN_FLAGS, "-w", workdir, image or image_name(), "sleep", "infinity")
        c = cls(p.stdout.strip(), workdir)
        try:
            c.mkdir(workdir)
            _docker("cp", f"{exercise_dir}/.", f"{c.cid}:{workdir}")
        except Exception:
            c.stop()
            raise
        return c

    # -- execution -------------------------------------------------------------
    def exec(self, cmd: str | list[str], cwd: str, timeout: int = 60, shell: bool = False) -> tuple[int, str, str]:
        if shell or isinstance(cmd, str):
            argv = ["timeout", "-s", "KILL", str(timeout), "sh", "-lc", cmd if isinstance(cmd, str) else " ".join(cmd)]
        else:
            argv = ["timeout", "-s", "KILL", str(timeout), *cmd]
        try:
            p = subprocess.run(["docker", "exec", "-w", cwd, self.cid, *argv],
                               capture_output=True, text=True, errors="replace", timeout=timeout + 15)
        except subprocess.TimeoutExpired:
            return 124, "", f"timed out after {timeout} s"
        except FileNotFoundError as e:
            raise HarnessError("docker CLI not found") from e
        rc = p.returncode
        err = p.stderr
        if rc == 137:
            err += f"\nkilled: exceeded {timeout} s"
        return rc, p.stdout, err

    def mkdir(self, path: str) -> None:
        _docker("exec", self.cid, "mkdir", "-p", path)

    def write_file(self, path: str, content: str) -> bool:
        """Write via `docker cp` of a temp file; the parent directory is created with an argv mkdir."""
        parent = os.path.dirname(path) or "/"
        tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, prefix="ce-write-")
        try:
            tmp.write(content)
            tmp.close()
            r = _docker("exec", self.cid, "mkdir", "-p", parent, check=False)
            if r.returncode != 0:
                return False
            r = _docker("cp", tmp.name, f"{self.cid}:{path}", check=False)
            return r.returncode == 0
        finally:
            os.unlink(tmp.name)

    def read(self, path: str) -> str | None:
        p = _docker("exec", self.cid, "cat", "--", path, check=False, timeout=60)
        return p.stdout if p.returncode == 0 else None

    def exists(self, path: str) -> bool:
        return _docker("exec", self.cid, "test", "-e", path, check=False).returncode == 0

    # -- measurement -------------------------------------------------------------
    def diff(self) -> list[tuple[str, str]]:
        """`docker diff`: list of (kind, path) with kind in {A, C, D}."""
        p = _docker("diff", self.cid)
        out: list[tuple[str, str]] = []
        for line in p.stdout.splitlines():
            if len(line) > 2 and line[0] in "ACD" and line[1] == " ":
                out.append((line[0], line[2:]))
        return out

    def hash_tree(self, *roots: str) -> dict[str, str]:
        """sha256 of every regular file under the given roots (missing roots are skipped)."""
        existing = [r for r in roots if self.exists(r)]
        if not existing:
            return {}
        p = _docker("exec", self.cid, "find", *existing, "-xdev", "-type", "f", "-exec", "sha256sum", "{}", "+",
                    check=False, timeout=300)
        hashes: dict[str, str] = {}
        for line in p.stdout.splitlines():
            if "  " in line:
                h, _, path = line.partition("  ")
                hashes[path] = h
        return hashes

    def hash_files(self, paths: list[str]) -> dict[str, str | None]:
        out: dict[str, str | None] = {}
        for path in paths:
            content = _docker("exec", self.cid, "cat", "--", path, check=False)
            out[path] = hashlib.sha256(content.stdout.encode("utf-8")).hexdigest() if content.returncode == 0 else None
        return out

    def copy_out(self, src: str, dst: Path) -> None:
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        _docker("cp", f"{self.cid}:{src}", str(dst))

    def stop(self) -> None:
        _docker("rm", "-f", self.cid, check=False)

    def __enter__(self) -> "Container":
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

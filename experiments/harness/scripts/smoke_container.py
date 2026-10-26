#!/usr/bin/env python3
"""Container smoke check (not a unit test): needs Docker and the harness image.

Starts a container from a tiny staged exercise, writes a file through docker cp, runs `ls`
through the shell path, reads `docker diff`, and stops. Exit 0 on success, 3 when the image
is absent (build it first: docker build -t ce-harness:py312 experiments/harness/docker).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.container import Container, image_exists, image_name  # noqa: E402


def main() -> int:
    if not image_exists():
        print(f"image {image_name()} not found; build it first")
        return 3
    with tempfile.TemporaryDirectory(prefix="ce-smoke-") as tmp:
        stage = Path(tmp) / "smoke"
        stage.mkdir()
        (stage / "smoke.py").write_text("def answer():\n    pass\n")
        (stage / "smoke_test.py").write_text("from smoke import answer\n\ndef test_answer():\n    assert answer() == 42\n")
        with Container.start(stage, "smoke") as c:
            print("container", c.cid[:12], "workdir", c.workdir)
            assert c.write_file(f"{c.workdir}/smoke.py", "def answer():\n    return 42\n"), "write_file failed"
            rc, out, err = c.exec("ls -la", cwd=c.workdir, shell=True)
            print("ls rc", rc); print(out.strip())
            rc, out, err = c.exec(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "smoke_test.py"], cwd=c.workdir)
            print("pytest rc", rc, "|", (out + err).strip().splitlines()[-1])
            rc, out, err = c.exec("echo hi > /tmp/outside.txt", cwd=c.workdir, shell=True)
            diff = c.diff()
            print("docker diff entries:", len(diff))
            for kind, path in diff:
                print(" ", kind, path)
            assert ("A", "/tmp/outside.txt") in diff, "diff did not show the outside write"
            print("hashes:", c.hash_files([f"{c.workdir}/smoke.py", f"{c.workdir}/missing.py"]))
    print("smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Local PostgreSQL without Docker.

``make up`` prefers Docker Compose, which is what staging and production use.
This is the fallback for a machine with no working Docker daemon - WSL without
Docker Desktop integration, for instance. It runs the real PostgreSQL binaries
that ship with the ``pgserver`` wheel, on **TCP**, so the connection string has
exactly the same shape as Supabase's and nothing about the app changes.

One caveat: the bundled pgvector may predate 0.7 and therefore lack
``halfvec``. Set ``VECTOR_TYPE=vector`` when that is the case.
Supabase ships a current pgvector, so production is unaffected.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import time

DEFAULT_DATA_DIR = pathlib.Path.home() / ".cache" / "justnews" / "pgdata"
DEFAULT_PORT = 55432
DEFAULT_DB = "justnews"
STARTUP_TIMEOUT_SECONDS = 30


def _bindir() -> pathlib.Path:
    try:
        import pgserver
    except ImportError:
        sys.stderr.write("pgserver is not installed. Run: uv pip install pgserver\n")
        raise SystemExit(1) from None
    return pathlib.Path(pgserver.__file__).parent / "pginstall" / "bin"


def _run(binary: pathlib.Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(binary), *args], capture_output=True, text=True, check=check)


def _is_running(bindir: pathlib.Path, data_dir: pathlib.Path) -> bool:
    return _run(bindir / "pg_ctl", "-D", str(data_dir), "status", check=False).returncode == 0


def start(bindir: pathlib.Path, data_dir: pathlib.Path, port: int) -> None:
    if not (data_dir / "PG_VERSION").exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        _run(bindir / "initdb", "-D", str(data_dir), "-U", "postgres", "--auth=trust", "-E", "UTF8")

    if not _is_running(bindir, data_dir):
        _run(
            bindir / "pg_ctl",
            "-D",
            str(data_dir),
            "-l",
            str(data_dir / "server.log"),
            "-o",
            f"-p {port} -h 127.0.0.1",
            "-w",
            "-t",
            str(STARTUP_TIMEOUT_SECONDS),
            "start",
        )

    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        probe = _run(bindir / "pg_isready", "-h", "127.0.0.1", "-p", str(port), check=False)
        if probe.returncode == 0:
            break
        time.sleep(0.3)
    else:
        raise SystemExit(f"postgres did not become ready within {STARTUP_TIMEOUT_SECONDS}s")


def ensure_database(bindir: pathlib.Path, port: int, name: str) -> None:
    env = os.environ | {"PGPASSWORD": ""}
    exists = subprocess.run(
        [
            str(bindir / "psql"),
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            "postgres",
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{name}'",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    ).stdout.strip()
    if exists != "1":
        _run(bindir / "createdb", "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", name)

    for extension in ("vector", "pg_trgm"):
        result = subprocess.run(
            [
                str(bindir / "psql"),
                "-h",
                "127.0.0.1",
                "-p",
                str(port),
                "-U",
                "postgres",
                "-d",
                name,
                "-c",
                f"CREATE EXTENSION IF NOT EXISTS {extension}",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.write(
                f"note: extension {extension!r} unavailable in this build - "
                f"{'fuzzy search is degraded' if extension == 'pg_trgm' else 'THIS IS FATAL'}\n"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "stop", "status", "url"])
    parser.add_argument("--data-dir", type=pathlib.Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--database", default=DEFAULT_DB)
    args = parser.parse_args()

    bindir = _bindir()
    url = f"postgresql+asyncpg://postgres@127.0.0.1:{args.port}/{args.database}"

    if args.command == "stop":
        _run(bindir / "pg_ctl", "-D", str(args.data_dir), "-m", "fast", "stop", check=False)
        return 0
    if args.command == "status":
        sys.stdout.write("running\n" if _is_running(bindir, args.data_dir) else "stopped\n")
        return 0
    if args.command == "url":
        sys.stdout.write(url + "\n")
        return 0

    start(bindir, args.data_dir, args.port)
    ensure_database(bindir, args.port, args.database)
    sys.stdout.write(f"DATABASE_URL={url}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Memory embeddings: the environment memory search re-ranks with (installed by `boa install`, used by memory_search).

The environment lives in the main checkout, machine-local and git-ignored, owned by BOA (never the system Python):
  .boa/embed/venv/              an isolated Python environment holding the library pinned in `.boa/embed.json`
  .boa/embed/model/             the embedding model's files, downloaded once at the pinned revision and checked
                                against their sha256 (no service, no network at query time)
  .boa/embed/cache/             every cache and temporary file of the library and its runtime (see contain())
  .boa/embed/boa-embed.json     the stamp, written last: the spec's checksum, the Python, the library and model
The spec `.boa/embed.json` (schema `boa/embed/1`): python ["3.MIN", "3.MAX"] (the versions the pinned library ships
wheels for: the installer builds the venv with the newest such Python it finds), requirements[] (pip requirement lines pinned with ==),
constraints[] (upper bounds on the library's direct dependencies, `name<major`), model {name (the library's model
name), repo, revision (the 40-hex commit id), files {file name: sha256}}.

Usage (run by the environment's own Python; the library is imported only inside these commands):
  memory_embed.py fetch SPEC MODEL_DIR        download the model's files at the pinned revision into MODEL_DIR (the
                                              installer then checks their sha256 before anything loads them)
  memory_embed.py probe NAME MODEL_DIR        load the model and embed one sentence (exit 0 = usable)
  memory_embed.py check MODEL_DIR             import the library (exit 0 = importable; the installer's cheap check)
  memory_embed.py embed NAME MODEL_DIR        stdin: a JSON array of strings; stdout: a JSON array of vectors (one
                                              array of numbers per string, same order); offline
Imported by memory_search.py and boa_install.py for the layout and the spec check only (standard library).
The child runs with HOME redirected (contain()): behind a proxy, give it through HTTPS_PROXY (with its credentials
in the URL if it needs them), since a `~/.netrc` is not read there.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

SCHEMA = "boa/embed/1"
EMBED_DIR = ".boa/embed"            # relative to the main checkout
STAMP = "boa-embed.json"
WINDOWS = os.name == "nt"
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def venv_python(venv: str) -> str:
    return os.path.join(venv, "Scripts", "python.exe") if WINDOWS else os.path.join(venv, "bin", "python")


def layout(d: str) -> dict[str, str]:
    """An environment directory `d`: itself, its venv, the venv's Python, the model and the stamp."""
    venv = os.path.join(d, "venv")
    return {"dir": d, "venv": venv, "python": venv_python(venv), "model": os.path.join(d, "model"),
            "stamp": os.path.join(d, STAMP)}


def paths(main: str) -> dict[str, str]:
    """The environment of the main checkout `main`."""
    return layout(os.path.join(main, *pathlib.PurePosixPath(EMBED_DIR).parts))


def check_spec(data: object) -> list[str]:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA \
            or set(data) - {"_comment", "schema", "python", "requirements", "constraints", "model"}:
        return [f"schema must be '{SCHEMA}' (keys: schema, python, requirements, constraints, model)"]
    errs = []
    py = data.get("python")
    if not (isinstance(py, list) and len(py) == 2 and all(isinstance(v, str) and re.fullmatch(r"3\.\d{1,2}", v)
                                                          for v in py)
            and python_range(data)[0] <= python_range(data)[1]):
        errs.append('python must be ["3.MIN", "3.MAX"]: the Python versions the pinned library supports, inclusive')
    for key, op in (("requirements", "=="), ("constraints", "<")):
        v = data.get(key)
        if not isinstance(v, list) or not v or not all(isinstance(r, str) and op in r and not r.startswith("-")
                                                       for r in v):
            errs.append(f"{key} must be a non-empty list of requirement lines with {op}")
    m = data.get("model")
    files = m.get("files") if isinstance(m, dict) else None
    if not isinstance(m, dict) or set(m) != {"name", "repo", "revision", "files"} \
            or not all(isinstance(m[k], str) and m[k] for k in ("name", "repo")) \
            or not isinstance(m["revision"], str) or not HEX40.fullmatch(m["revision"]) \
            or not isinstance(files, dict) or not files \
            or not all(isinstance(f, str) and FILE.fullmatch(f) and isinstance(h, str) and HEX64.fullmatch(h)
                       for f, h in files.items()):
        errs.append("model must hold name, repo, revision (the 40-hex commit id) and files {plain file name: sha256}")
    return errs


def contain(cache: str) -> None:
    """Keep every file the library and its runtime write inside `cache` (this process and its children only):
    - ORT_DISABLE_TELEMETRY=1: the inference runtime (onnxruntime) persists no device id (file, or registry value
      on Windows) and opens no telemetry cache: only its 1DS telemetry provider uses them, and it checks this
      opt-out before writing anything;
    - XDG_CACHE_HOME (Linux), HOME (macOS: `~/Library/Application Support`), LOCALAPPDATA and APPDATA (Windows):
      where onnxruntime would put that device id and cache, in case a build ignores the opt-out;
    - TMPDIR, TEMP, TMP: the temporary directory (the library's default cache `fastembed_cache` lives there; it
      also gets cache_dir explicitly); HF_HOME (unless the caller set it): the model hub client's cache."""
    os.makedirs(cache, exist_ok=True)
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    for k in ("XDG_CACHE_HOME", "LOCALAPPDATA", "APPDATA", "TMPDIR", "TEMP", "TMP"):
        os.environ[k] = cache
    if not WINDOWS:
        os.environ["HOME"] = cache
    os.environ.setdefault("HF_HOME", os.path.join(cache, "hf"))
    import tempfile
    tempfile.tempdir = None   # recomputed from the variables above


def cache_of(model_dir: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(model_dir)), "cache")


def python_range(spec: dict) -> tuple[tuple[int, int], tuple[int, int]]:
    lo, hi = (tuple(int(x) for x in v.split(".")) for v in spec["python"])
    return lo, hi


def fetch(spec_path: str, model_dir: str) -> int:
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    errs = check_spec(spec)
    if errs:
        print(f"memory-embed: {spec_path}: " + "; ".join(errs), file=sys.stderr)
        return 1
    from huggingface_hub import snapshot_download  # the library's own dependency
    m = spec["model"]
    snapshot_download(repo_id=m["repo"], revision=m["revision"], local_dir=model_dir, allow_patterns=sorted(m["files"]))
    return 0


def encode(name: str, model_dir: str, texts: list[str]) -> list[list[float]]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")   # the model is local: never the network once installed
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name=name, specific_model_path=model_dir, local_files_only=True,
                          cache_dir=cache_of(model_dir))
    return [[round(float(x), 6) for x in v] for v in model.embed(texts)]


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] in ("fetch", "probe", "embed"):
        contain(cache_of(argv[2]))
    if len(argv) == 2 and argv[0] == "check":
        contain(cache_of(argv[1]))
        import fastembed  # noqa: F401
        return 0
    if len(argv) == 3 and argv[0] == "fetch":
        return fetch(argv[1], argv[2])
    if len(argv) == 3 and argv[0] == "probe":
        vecs = encode(argv[1], argv[2], ["memory search probe sentence"])
        if len(vecs) != 1 or not vecs[0]:
            print("memory-embed: the model loaded but returned no vector", file=sys.stderr)
            return 1
        print(f"memory-embed: model {argv[1]} ready ({len(vecs[0])} dimensions)")
        return 0
    if len(argv) == 3 and argv[0] == "embed":
        texts = json.loads(sys.stdin.read())
        if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
            print("memory-embed: stdin must be a JSON array of strings", file=sys.stderr)
            return 2
        sys.stdout.write(json.dumps(encode(argv[1], argv[2], texts)))
        return 0
    print("usage: memory_embed.py fetch SPEC MODEL_DIR | probe NAME MODEL_DIR | embed NAME MODEL_DIR | check MODEL_DIR",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

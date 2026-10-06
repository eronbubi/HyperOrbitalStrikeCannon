"""Test-bench helpers: datapack functions and entity readback on the local server."""
import json
import os
import re
import time
from pathlib import Path

from rcon import Rcon

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / os.environ.get("OSC_SERVER", "server") / "world" / "datapacks" / "lab"
FUNCS = PACK / "data" / "lab" / "function"

_NUM = re.compile(r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)[dfsbL]?")


def ensure_pack():
    FUNCS.mkdir(parents=True, exist_ok=True)
    meta = PACK / "pack.mcmeta"
    if not meta.exists():
        meta.write_text(json.dumps({"pack": {"description": "osc lab", "min_format": 94, "max_format": 94}}))


def write_function(name, lines):
    ensure_pack()
    (FUNCS / f"{name}.mcfunction").write_text("\n".join(lines) + "\n", encoding="utf-8")


def nums(reply):
    """Numbers after the colon of a `data get` reply."""
    if ":" not in reply:
        return None
    return [float(m) for m in _NUM.findall(reply.split(":", 1)[1])]


def get(r, selector, path):
    return nums(r.cmd(f"data get entity {selector} {path}"))


def gametime(r):
    return int(re.search(r"-?\d+", r.cmd("time query gametime")).group())


def wait_ticks(r, n):
    """Block until the server has advanced n game ticks."""
    target = gametime(r) + n
    while gametime(r) < target:
        time.sleep(0.02)


__all__ = ["Rcon", "write_function", "nums", "get", "wait_ticks", "ensure_pack", "ROOT"]


def step(r, n):
    """While the game is frozen: run exactly n ticks and wait until they are done."""
    target = gametime(r) + n
    r.cmd(f"tick step {n}")
    while gametime(r) < target:
        time.sleep(0.01)

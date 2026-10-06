"""Offline search for a stationary duper that can also be primed by hand.

Hand priming: the TNT is placed in a cell that is unpowered and touches no slime, and one
piston stroke brings the empty TNT slot to it. The powered rail then lands after it, which
is the only way the TNT ends up powered without receiving a block update.
"""
import itertools
import sys
import time

import piston_sim as ps
from piston_sim import DIRS, FACE, add, analyse, stroke

PISTON, FACING = (3, 1, 0), (-1, 0, 0)
RAIL, D1, W, C = (1, 1, 0), (2, 1, 0), (0, 1, 0), (1, 0, 0)
EAST, WEST = (1, 0, 0), (-1, 0, 0)


def moves_whole(blocks):
    state = blocks
    for extend in (True, False):
        res = stroke(state, PISTON, FACING, extend)
        if res is None or set(res[0]) != set(state):
            return False
        state = res[1]
    return state == blocks


def primable(blocks, slot):
    """'retract' / 'extend' / None: which stroke can bring the slot to a hand-placed TNT."""
    out = []
    for name, shift in (("retract", EAST), ("extend", WEST)):
        cell = add(slot, shift)
        if cell in blocks or cell == PISTON:
            continue
        back = (-shift[0], 0, 0)
        if all(blocks.get(add(cell, d)) != "S" for d in DIRS if d != back):
            out.append(name)
    return out


def search(max_extra, budget_s):
    cells = [(x, y, z) for x in (0, 1, 2) for y in (-1, 0, 1) for z in (-1, 0, 1)
             if (x, y, z) not in (RAIL, D1, W, C)]
    t0 = time.time()
    found = []
    for n in range(2, max_extra + 1):
        for extra in itertools.combinations(cells, n):
            if time.time() - t0 > budget_s:
                return found, "timeout"
            for wk, ck in (("B", "S"), ("S", "S"), ("B", "B"), ("S", "B")):
                base = {D1: "S", RAIL: "R", W: wk, C: ck}
                for p in extra:
                    base[p] = "S"
                if not moves_whole(base):
                    continue
                for d in DIRS:
                    slot = add(C, d)
                    if slot in base or slot == PISTON:
                        continue
                    for fd in DIRS:
                        fan = add(slot, fd)
                        if fan in base or fan == PISTON:
                            continue
                        for fname, fvec in FACE.items():
                            support = (fan[0] - fvec[0], fan[1], fan[2] - fvec[2])
                            if base.get(support) != "S":
                                continue
                            blocks = dict(base)
                            blocks[slot] = "T"
                            blocks[fan] = "F:" + fname
                            if len(blocks) > 12:
                                continue
                            res = analyse(blocks, PISTON, FACING)
                            if not res["ok"]:
                                continue
                            noTnt = dict(blocks)
                            del noTnt[slot]
                            modes = primable(noTnt, slot)
                            if modes and moves_whole(noTnt):
                                found.append((len(blocks), wk, ck, extra, slot, fan, fname, res["dups"], modes))
    return found, "complete"


if __name__ == "__main__":
    hits, status = search(int(sys.argv[1]), float(sys.argv[2]))
    print(status, len(hits), "layouts")
    for h in sorted(hits)[:25]:
        print(h)

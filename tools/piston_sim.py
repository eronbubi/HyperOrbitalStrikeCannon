"""Offline port of PistonHandler.calculatePush (1.21.11) to design a stationary TNT duper.

What the real server showed and the decompiled code explains:
- PistonBlock.move turns destinations into moving blocks in reverse push-list order; a
  moved dead coral wall fan breaks when its support position is overwritten and sends
  block updates. A BUD-powered TNT next to it primes, yet still travels on as a block.
- Moving blocks land in the same order. A TNT block must land, with all its neighbours,
  before the powered detector rail lands, or it is updated/placed while powered and is lost.
"""
import itertools

DIRS = [(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)]  # Direction.values()
FACE = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def neg(a):
    return (-a[0], -a[1], -a[2])


def sticky(kind):
    return kind == "S"


class Handler:
    def __init__(self, blocks, piston, facing, extend):
        self.blocks = blocks  # pos -> kind ('S' slime, 'B' solid, 'T' tnt, 'R' rail, 'F:<facing>' fan)
        self.pos_from = piston
        if extend:
            self.motion = facing
            self.pos_to = add(piston, facing)
        else:
            self.motion = neg(facing)
            self.pos_to = add(piston, (facing[0] * 2, facing[1] * 2, facing[2] * 2))
        self.moved = []

    def kind(self, pos):
        return self.blocks.get(pos)

    def calculate(self):
        if self.kind(self.pos_to) is None:
            return True
        if not self.try_move(self.pos_to, self.motion):
            return False
        i = 0
        while i < len(self.moved):
            pos = self.moved[i]
            if sticky(self.kind(pos)) and not self.try_adjacent(pos):
                return False
            i += 1
        return True

    def try_move(self, pos, direction):
        kind = self.kind(pos)
        if kind is None or pos == self.pos_from or pos in self.moved:
            return True
        i = 1
        if i + len(self.moved) > 12:
            return False
        back = neg(self.motion)
        while sticky(kind):
            nxt = add(pos, (back[0] * i, back[1] * i, back[2] * i))
            prev, kind = kind, self.kind(nxt)
            if kind is None or not (sticky(prev) or sticky(kind)) or nxt == self.pos_from:
                break
            i += 1
            if i + len(self.moved) > 12:
                return False
        j = 0
        for k in range(i - 1, -1, -1):
            self.moved.append(add(pos, (back[0] * k, back[1] * k, back[2] * k)))
            j += 1
        k = 1
        while True:
            nxt = add(pos, (self.motion[0] * k, self.motion[1] * k, self.motion[2] * k))
            if nxt in self.moved:
                idx = self.moved.index(nxt)
                self.reorder(j, idx)
                for m in range(idx + j + 1):
                    p = self.moved[m]
                    if sticky(self.kind(p)) and not self.try_adjacent(p):
                        return False
                return True
            kind = self.kind(nxt)
            if kind is None:
                return True
            if nxt == self.pos_from:
                return False
            if len(self.moved) >= 12:
                return False
            self.moved.append(nxt)
            j += 1
            k += 1

    def reorder(self, frm, to):
        a = self.moved[:to]
        b = self.moved[len(self.moved) - frm:]
        c = self.moved[to:len(self.moved) - frm]
        self.moved = a + b + c

    def try_adjacent(self, pos):
        kind = self.kind(pos)
        for d in DIRS:
            if any(d[i] and self.motion[i] for i in range(3)):
                continue
            other = add(pos, d)
            okind = self.kind(other)
            if okind is not None and (sticky(okind) or sticky(kind)) and not self.try_move(other, d):
                return False
        return True


def stroke(blocks, piston, facing, extend):
    """Returns (landing order, shifted blocks) or None when the piston cannot move."""
    h = Handler(blocks, piston, facing, extend)
    if not h.calculate():
        return None
    order = list(reversed(h.moved))
    shifted = {p: k for p, k in blocks.items() if p not in h.moved}
    for p in h.moved:
        dest = add(p, h.motion)
        if dest in shifted:
            return None  # would push into a block that stays
        shifted[dest] = blocks[p]
    return order, shifted, h.motion


def analyse(blocks, piston, facing):
    """Checks one layout. Returns dict with 'ok' and the reasons that failed."""
    tnt = next(p for p, k in blocks.items() if k == "T")
    rail = next(p for p, k in blocks.items() if k == "R")
    fan = next(p for p, k in blocks.items() if k.startswith("F:"))
    fan_face = FACE[blocks[fan][2:]]
    problems = []
    dups = []
    state = blocks
    for extend in (True, False):
        name = "extend" if extend else "retract"
        res = stroke(state, piston, facing, extend)
        if res is None:
            return {"ok": False, "problems": [f"{name}: cannot move"]}
        order, nxt, motion = res
        idx = {p: i for i, p in enumerate(order)}
        cur = {k: p for p, k in state.items() if k in ("T", "R") or k.startswith("F:")}
        t, r_, f = cur["T"], cur["R"], next(p for p, k in state.items() if k.startswith("F:"))
        support = (f[0] - fan_face[0], f[1], f[2] - fan_face[2])
        conductor = add(r_, (0, -1, 0))
        if set(order) != set(state):
            problems.append(f"{name}: {len(state) - len(order)} blocks left behind")
        if t not in idx or r_ not in idx or f not in idx:
            return {"ok": False, "problems": problems + [f"{name}: tnt/rail/fan not moved"]}
        # duplication event while destinations are being converted
        over = set()
        dup = False
        for p in order:
            dest = add(p, motion)
            if dest == support and f not in over:
                powered = r_ not in over and conductor not in over and t in [add(conductor, d) for d in DIRS]
                near = t in [add(f, d) for d in DIRS]
                if t not in over and powered and near:
                    dup = True
                over.add(f)  # fan broke; no second event
            over.add(dest)
        dups.append(dup)
        # landing
        t_dest = add(t, motion)
        for p in order:
            if p == r_:
                continue
            dest = add(p, motion)
            if (p == t or dest in [add(t_dest, d) for d in DIRS]) and idx[p] > idx[r_]:
                problems.append(f"{name}: {state[p]} at {p} lands after the rail")
        if support in idx and idx[support] > idx[f]:
            problems.append(f"{name}: fan lands before its support")
        if support not in idx:
            problems.append(f"{name}: fan support does not move")
        if conductor in idx and idx[conductor] > idx[r_]:
            problems.append(f"{name}: rail lands before its support")
        state = nxt
    if state != blocks:
        problems.append("structure does not return to its start")
    if not dups[0] and not dups[1]:
        problems.append("no duplication event")
    return {"ok": not problems, "problems": problems, "dups": dups}


def frame():
    """Fixed part: rail level line pushed directly, slime row below. Piston at (3,1,0) facing west."""
    return {
        (2, 1, 0): "S", (1, 1, 0): "R", (0, 1, 0): "B",
        (2, 0, 0): "S", (1, 0, 0): "S", (0, 0, 0): "S",
    }


def search(max_extra=3, limit=40):
    base = frame()
    piston, facing = (3, 1, 0), (-1, 0, 0)
    conductor = (1, 0, 0)
    spots = [(x, y, z) for x in range(-1, 3) for y in range(-2, 2) for z in range(0, 3)
             if (x, y, z) not in base and (x, y, z) != piston]
    found = []
    for n in range(0, max_extra + 1):
        for extra in itertools.combinations(spots, n):
            blocks0 = dict(base)
            for p in extra:
                blocks0[p] = "S"
            for d in DIRS:
                tnt = add(conductor, d)
                if tnt in blocks0 or tnt == piston:
                    continue
                for fd in DIRS:
                    fan = add(tnt, fd)
                    if fan in blocks0 or fan == piston or fan == tnt:
                        continue
                    for fname, fvec in FACE.items():
                        support = (fan[0] - fvec[0], fan[1], fan[2] - fvec[2])
                        if blocks0.get(support) != "S":
                            continue
                        blocks = dict(blocks0)
                        blocks[tnt] = "T"
                        blocks[fan] = "F:" + fname
                        res = analyse(blocks, piston, facing)
                        if res["ok"]:
                            found.append((len(blocks), extra, tnt, fan, fname, res["dups"]))
                            if len(found) >= limit:
                                return found
    return found


if __name__ == "__main__":
    hits = search()
    print(len(hits), "layouts pass")
    for h in sorted(hits)[:20]:
        print(h)

import hashlib
import random
from collections import defaultdict

MAX_DEPTH = 14
DEFAULT_IW = 1.0


# --- geometry ---------------------------------------------------------------

class Box:
    """A rectangle of space handed to a node. y grows downward."""
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def right(self):  return self.x + self.w
    @property
    def bottom(self): return self.y + self.h
    @property
    def cx(self):     return self.x + self.w / 2
    @property
    def cy(self):     return self.y + self.h / 2

    def inset(self, fx, fy=None):
        """Return a box inset by a fraction of its size."""
        fy = fx if fy is None else fy
        dx, dy = self.w * fx, self.h * fy
        return Box(self.x + dx, self.y + dy, self.w - 2 * dx, self.h - 2 * dy)

    def band(self, f0, f1):
        """Horizontal slice between fractions f0 and f1 from the top."""
        return Box(self.x, self.y + self.h * f0, self.w, self.h * (f1 - f0))

    def hsplit(self, n, gap=0.0, fractions=None):
        """Split horizontally into n boxes (side by side).
        If fractions is given, it should be a sequence of n floats
        (not necessarily summing to 1). Otherwise equal widths are used."""
        boxes = []
        if fractions is None:
            fractions = [1.0] * n
        total = sum(fractions)
        usable = self.w - gap * (n - 1)
        x = self.x
        for f in fractions:
            w = usable * f / total
            boxes.append(Box(x, self.y, w, self.h))
            x += w + gap
        return boxes

    def vsplit(self, n, gap=0.0, fractions=None):
        """Split vertically into n boxes (stacked).
        If fractions is given, it should be a sequence of n floats
        (not necessarily summing to 1). Otherwise equal heights are used."""
        boxes = []
        if fractions is None:
            fractions = [1.0] * n
        total = sum(fractions)
        usable = self.h - gap * (n - 1)
        y = self.y
        for f in fractions:
            h = usable * f / total
            boxes.append(Box(self.x, y, self.w, h))
            y += h + gap
        return boxes

    def pad(self, px, py=None):
        """Return an inset box with absolute pixel padding."""
        py = px if py is None else py
        return Box(self.x + px, self.y + py, self.w - 2 * px, self.h - 2 * py)

    def __repr__(self):
        return f"Box({self.x:.0f},{self.y:.0f},{self.w:.0f}x{self.h:.0f})"


# --- seeding ----------------------------------------------------------------

def rng_for(seed, path):
    """One independent RNG per node, derived from its path in the tree.
    Editing a deep rule cannot disturb its siblings."""
    h = hashlib.sha256(f"{seed}|{path}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


# --- what a rule returns ----------------------------------------------------

ROW, COL, STACK, LEAF = "row", "col", "stack", "leaf"


class Expansion:
    def __init__(self, kind, syms, gap=0.0, fractions=None):
        self.kind, self.syms, self.gap, self.fractions = kind, syms, gap, fractions


def Row(syms, gap=0.0):
    """Side by side. Children are normalised to fill the box, so units only
    need to be consistent within one Row."""
    return Expansion(ROW, list(syms), gap=gap)


def Column(pairs):
    """Column([(0.2, "Roof"), (0.8, "Body")]) — fractions need not sum to 1."""
    return Expansion(COL, [s for _, s in pairs], fractions=[f for f, _ in pairs])


def Stack(syms):
    """All children get the same box, realised in order."""
    return Expansion(STACK, list(syms))


class Node:
    __slots__ = ("symbol", "path", "rng", "kind", "gap", "fractions",
                 "children", "box", "iw", "depth")

    def __init__(self, symbol, path, rng, depth):
        self.symbol, self.path, self.rng, self.depth = symbol, path, rng, depth
        self.kind, self.gap, self.fractions = LEAF, 0.0, None
        self.children, self.box, self.iw = [], None, DEFAULT_IW

    def dump(self, out, indent=0):
        out.append("  " * indent + f"{self.symbol} [{self.kind}] {self.box or ''}")
        for c in self.children:
            c.dump(out, indent + 1)


# --- registries -------------------------------------------------------------

RULES = defaultdict(list)   # symbol -> [(weight, fn, argcount), ...]
TERMINALS = {}              # symbol -> fn(box, rng, ctx) -> list
WIDTH = {}                  # symbol -> (min, max) intrinsic width
HEIGHT_FRAC = {}            # symbol -> share of a Row's height, bottom-aligned
CTX_ROOTS = {}              # symbol -> fn(rng, ctx_parent) -> new ctx


def rule(symbol, weight=1.0):
    """weight is a number, or a function of the world: lambda w: 3 if ... else 0.
    The rule function takes (rng, depth) or (rng, depth, world)."""
    def deco(fn):
        RULES[symbol].append((weight, fn, fn.__code__.co_argcount))
        return fn
    return deco


def terminal(symbol):
    def deco(fn):
        TERMINALS[symbol] = fn
        return fn
    return deco


def weighted_pick(prods, rng, world=None):
    ws = [w(world) if callable(w) else w for w, _, _ in prods]
    total = sum(ws)
    if total <= 0:
        return prods[-1][1], prods[-1][2]
    r = rng.random() * total
    for w, (_, fn, n) in zip(ws, prods):
        r -= w
        if r <= 0:
            return fn, n
    return prods[-1][1], prods[-1][2]


# --- the four passes --------------------------------------------------------

def derive(symbol, seed, path=None, depth=0, world=None):
    path = symbol if path is None else path
    node = Node(symbol, path, rng_for(seed, path), depth)
    if symbol in TERMINALS or symbol not in RULES or depth >= MAX_DEPTH:
        return node
    fn, argc = weighted_pick(RULES[symbol], node.rng, world)
    exp = fn(node.rng, depth, world) if argc >= 3 else fn(node.rng, depth)
    node.kind, node.gap, node.fractions = exp.kind, exp.gap, exp.fractions
    node.children = [derive(s, seed, f"{path}/{s}[{i}]", depth + 1, world)
                     for i, s in enumerate(exp.syms)]
    return node


def measure(node):
    for c in node.children:
        measure(c)
    if node.symbol in WIDTH:
        node.iw = node.rng.uniform(*WIDTH[node.symbol])
    elif node.kind == ROW and node.children:
        node.iw = sum(c.iw for c in node.children) + node.gap * (len(node.children) - 1)
    elif node.children:
        node.iw = max(c.iw for c in node.children)
    else:
        node.iw = DEFAULT_IW
    return node.iw


def layout(node, box):
    node.box = box
    if node.kind == ROW and node.children:
        gaps = node.gap * (len(node.children) - 1)
        scale = max(0.0, box.w - gaps) / (sum(c.iw for c in node.children) or 1.0)
        x = box.x
        for c in node.children:
            w = c.iw * scale
            h = box.h * HEIGHT_FRAC.get(c.symbol, 1.0)
            layout(c, Box(x, box.bottom - h, w, h))
            x += w + node.gap
    elif node.kind == COL and node.children:
        fr = node.fractions or [1.0] * len(node.children)
        s = sum(fr) or 1.0
        y = box.y
        for c, f in zip(node.children, fr):
            h = box.h * f / s
            layout(c, Box(box.x, y, box.w, h))
            y += h
    elif node.kind == STACK:
        for c in node.children:
            layout(c, box)


def realise(node, ctx, out, on_missing=None):
    if node.symbol in CTX_ROOTS:
        ctx = CTX_ROOTS[node.symbol](node.rng, ctx)
    if not node.children:
        fn = TERMINALS.get(node.symbol)
        if fn is None:
            if on_missing:
                out += on_missing(node)
        else:
            out += fn(node.box, node.rng, ctx)
        return
    for c in node.children:
        realise(c, ctx, out, on_missing)


def generate(symbol, seed, x=0.0, bottom=0.0, height=100.0,
             ctx=None, on_missing=None, world=None):
    """seed -> (items, root node, total width).

    ctx is the initial context passed to terminals (usually a palette).
    The output is sorted by the optional `layer` attribute of each shape.
    """
    root = derive(symbol, seed, world=world)
    w = measure(root)
    layout(root, Box(x, bottom - height, w, height))
    out = []
    realise(root, ctx, out, on_missing)
    out.sort(key=lambda shape: getattr(shape, "layer", 0))
    return out, root, w
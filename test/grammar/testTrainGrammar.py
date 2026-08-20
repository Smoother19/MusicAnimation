"""
train_grammar.py — a stochastic shape-grammar train generator, triangles only.

Everything the train is made of goes through pygame.draw.polygon() with exactly
three points. (The on-screen HUD text uses a font — it is a dev tool, not part
of the generated artwork. Delete render_hud() and it's 100% triangles.)

PIPELINE
    seed -> DERIVE -> tree of symbols
                   -> MEASURE -> intrinsic widths (bottom-up)
                   -> LAYOUT  -> a Box for every node (top-down)
                   -> REALISE -> flat list of triangles
                   -> sort by layer -> draw

RUN
    python train_grammar.py                     interactive window
    python train_grammar.py --seed 1234         start on a given seed
    python train_grammar.py --png out.png       render one train headless
    python train_grammar.py --sheet s.png -n 6  contact sheet of 6 seeds

KEYS
    R            new random seed          LEFT/RIGHT   seed -1 / +1
    D            toggle layout boxes      T            print derivation tree
    S            save a png               ESC          quit

WHERE TO EDIT
    Section 6  = THE GRAMMAR   (rules: structure)
    Section 7  = THE TERMINALS (leaves: triangles)
    Everything else is engine and you can mostly ignore it.
"""

import argparse
import colorsys
import hashlib
import math
import random
import sys
from collections import defaultdict

import pygame

# ============================================================================
# 1. CONFIG
# ============================================================================

SCREEN_W, SCREEN_H = 1280, 520
RAIL_Y = 400          # every wheel rests on this line
BAND_H = 165          # height of a full-height car
MARGIN = 60
MAX_DEPTH = 14        # crash barrier for recursive rules
DEFAULT_IW = 1.0      # intrinsic width for symbols with no WIDTH entry

SKY = (26, 30, 40)
GROUND = (18, 20, 27)


# ============================================================================
# 2. GEOMETRY
# ============================================================================

class Box:
    """An axis-aligned rectangle of space handed to a node. y grows downward."""
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
        """Shrink by a fraction of each axis."""
        fy = fx if fy is None else fy
        dx, dy = self.w * fx, self.h * fy
        return Box(self.x + dx, self.y + dy, self.w - 2 * dx, self.h - 2 * dy)

    def __repr__(self):
        return f"Box({self.x:.0f},{self.y:.0f},{self.w:.0f}x{self.h:.0f})"


# A triangle: 3 points, a colour, and a paint layer (low = behind).
def tri(p0, p1, p2, color, layer=30):
    return ((p0, p1, p2), color, layer)


def quad(tl, tr, br, bl, color, layer=30):
    """A quad is two triangles. This is the workhorse of the whole file."""
    return [tri(tl, tr, br, color, layer), tri(tl, br, bl, color, layer)]


def box_quad(b, color, layer=30):
    return quad((b.x, b.y), (b.right, b.y), (b.right, b.bottom), (b.x, b.bottom),
                color, layer)


def bar(p0, p1, thick, color, layer=30):
    """A thick line segment = a quad = 2 triangles. Used for spokes, rods, ribs."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * thick / 2, dx / L * thick / 2
    return quad((p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny),
                (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny), color, layer)


def fan(cx, cy, r, n, color_fn, layer=30, a0=0.0, a1=math.tau, ry=None):
    """A disc (or arc wedge) as n triangles sharing a centre vertex.
    Pass ry for an ellipse — that's how the tank end caps stay shallow."""
    ry = r if ry is None else ry
    out = []
    for i in range(n):
        t0 = a0 + (a1 - a0) * i / n
        t1 = a0 + (a1 - a0) * (i + 1) / n
        out.append(tri((cx, cy),
                       (cx + r * math.cos(t0), cy + ry * math.sin(t0)),
                       (cx + r * math.cos(t1), cy + ry * math.sin(t1)),
                       color_fn(i / n), layer))
    return out


def strip(top_pts, bot_pts, color_fn, layer=30):
    """Triangle strip between two polylines of equal length. 2 tris per segment."""
    out = []
    for i in range(len(top_pts) - 1):
        c = color_fn(i / max(1, len(top_pts) - 2))
        out += quad(top_pts[i], top_pts[i + 1], bot_pts[i + 1], bot_pts[i], c, layer)
    return out


# ============================================================================
# 3. SEEDING
# ============================================================================

def rng_for(seed, path):
    """
    One independent RNG per node, derived from its path in the derivation tree.
    "Train/Car[2]/Body/Panel[1]" gets its own stream, so editing a panel rule
    cannot disturb car 5's wheels. This is the single most useful habit here.
    """
    h = hashlib.sha256(f"{seed}|{path}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


class Palette:
    """One coherent colour scheme per seed. hue_shift varies it per car."""

    def __init__(self, rng):
        self.h = rng.random()
        self.accent = (self.h + rng.uniform(0.35, 0.62)) % 1.0
        self.sat = rng.uniform(0.30, 0.62)

    def _rgb(self, h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v)))
        return (int(r * 255), int(g * 255), int(b * 255))

    def body(self, k=0.0, hue=0.0):     return self._rgb(self.h + hue, self.sat, 0.42 + k)
    def accent_c(self, k=0.0, hue=0.0): return self._rgb(self.accent + hue, self.sat + .15, 0.55 + k)
    def metal(self, k=0.0):             return self._rgb(self.h + .5, 0.06, 0.34 + k)
    def dark(self, k=0.0):              return self._rgb(self.h, 0.18, 0.16 + k)
    def glass(self, k=0.0):             return self._rgb(self.h + .45, 0.22, 0.62 + k)


# ============================================================================
# 4. NODES  (what a rule returns, and what the tree is made of)
# ============================================================================

ROW, COL, STACK, LEAF = "row", "col", "stack", "leaf"


class Expansion:
    """The value a rule function returns: a layout kind + child symbol names."""
    def __init__(self, kind, syms, gap=0.0, fractions=None):
        self.kind, self.syms, self.gap, self.fractions = kind, syms, gap, fractions


def Row(syms, gap=0.0):
    """Children side by side; each takes a share of the width set by its intrinsic
    width. Widths inside one Row are always normalised to fill the box, so you can
    mix units freely between rows (pixels in one, relative weights in another)."""
    return Expansion(ROW, list(syms), gap=gap)


def Column(pairs):
    """Column([(0.2, "Roof"), (0.6, "Body"), (0.2, "Under")]) — vertical split."""
    return Expansion(COL, [s for _, s in pairs], fractions=[f for f, _ in pairs])


def Stack(syms):
    """All children get the same box, painted in order. For overlapping parts."""
    return Expansion(STACK, list(syms))


class Node:
    __slots__ = ("symbol", "path", "rng", "kind", "gap", "fractions",
                 "children", "box", "iw", "depth")

    def __init__(self, symbol, path, rng, depth):
        self.symbol, self.path, self.rng, self.depth = symbol, path, rng, depth
        self.kind, self.gap, self.fractions = LEAF, 0.0, None
        self.children, self.box, self.iw = [], None, DEFAULT_IW

    def dump(self, out, indent=0):
        b = f"  {self.box}" if self.box else ""
        out.append("  " * indent + f"{self.symbol} [{self.kind}]{b}")
        for c in self.children:
            c.dump(out, indent + 1)


# ============================================================================
# 5. GRAMMAR REGISTRY
# ============================================================================

RULES = defaultdict(list)     # symbol -> [(weight, fn), ...]
TERMINALS = {}                # symbol -> fn(box, rng, pal, hue) -> [tri]
WIDTH = {}                    # symbol -> (min, max) intrinsic width
HEIGHT_FRAC = {}              # symbol -> fraction of parent Row height (bottom-aligned)
HUE_ROOTS = set()             # symbols that start a new colour zone (one per car)


def rule(symbol, weight=1.0):
    """Register a production. Several rules per symbol = the seed picks one."""
    def deco(fn):
        RULES[symbol].append((weight, fn))
        return fn
    return deco


def terminal(symbol):
    """Register a leaf that emits triangles."""
    def deco(fn):
        TERMINALS[symbol] = fn
        return fn
    return deco


def weighted_pick(prods, rng):
    r = rng.random() * sum(w for w, _ in prods)
    for w, fn in prods:
        r -= w
        if r <= 0:
            return fn
    return prods[-1][1]


# ============================================================================
# 6. ===================  THE GRAMMAR — EDIT ME  ==========================
# ============================================================================
#
# A rule is a function (rng, depth) -> Row / Column / Stack of child symbols.
# Give a symbol several rules with different weights and the seed chooses.

# --- intrinsic widths -------------------------------------------------------
# Top-level cars are in pixels. Inner rows use relative weights (any scale),
# because every Row normalises its children to fill its own box.
WIDTH.update({
    "Locomotive": (155, 195), "Tender": (68, 92), "Caboose": (74, 96),
    "Boxcar": (96, 132), "Tanker": (108, 142), "Flatcar": (94, 138),
    "Hopper": (92, 124), "Coupler": (8, 12),
    "CowCatcher": (17, 25), "BoilerGroup": (72, 96), "Cab": (42, 58),
    "Chimney": (0.9, 1.3), "Dome": (1.0, 1.5), "Whistle": (0.4, 0.6),
    "Spacer": (0.35, 0.75), "Panel": (0.8, 1.35), "Wheel": (1.0, 1.0),
})

# --- height as a fraction of the band, bottom-aligned to the rail ------------
HEIGHT_FRAC.update({
    "Locomotive": 1.0, "Tender": 0.60, "Boxcar": 0.86, "Tanker": 0.74,
    "Flatcar": 0.40, "Hopper": 0.80, "Caboose": 0.94, "Coupler": 0.26,
})

# --- each car gets its own hue offset ---------------------------------------
HUE_ROOTS.update({"Locomotive", "Tender", "Boxcar", "Tanker", "Flatcar",
                  "Hopper", "Caboose"})


@rule("Train")
def r_train(rng, depth):
    n = rng.randint(3, 7)                       # <- how many freight cars
    seq = ["Locomotive", "Tender"] + ["Car"] * n + ["Caboose"]
    out = []
    for i, s in enumerate(seq):
        if i:
            out.append("Coupler")
        out.append(s)
    return Row(out)


# ---- which car types exist, and how often ----------------------------------
@rule("Car", weight=3.0)
def r_car_box(rng, d):    return Stack(["Boxcar"])
@rule("Car", weight=2.0)
def r_car_tank(rng, d):   return Stack(["Tanker"])
@rule("Car", weight=1.5)
def r_car_flat(rng, d):   return Stack(["Flatcar"])
@rule("Car", weight=1.5)
def r_car_hop(rng, d):    return Stack(["Hopper"])


# ---- the locomotive --------------------------------------------------------
@rule("Locomotive")
def r_loco(rng, d):
    return Column([(0.72, "LocoBody"), (0.28, "DriveGear")])

@rule("LocoBody")
def r_locobody(rng, d):
    return Row(["CowCatcher", "BoilerGroup", "Cab"])

@rule("BoilerGroup")
def r_boilergroup(rng, d):
    return Column([(0.30, "StackRow"), (0.70, "Boiler")])

@rule("StackRow", weight=2.0)
def r_stackrow_full(rng, d):
    return Row(["Spacer", "Chimney", "Spacer", "Dome", "Spacer", "Whistle", "Spacer"])

@rule("StackRow", weight=1.0)
def r_stackrow_plain(rng, d):
    return Row(["Spacer", "Chimney", "Spacer", "Dome", "Spacer"])

@rule("Cab")
def r_cab(rng, d):
    return Column([(0.26, "CabRoof"), (0.74, "CabBody")])

@rule("CabBody")
def r_cabbody(rng, d):
    return Stack(["SolidPanel", "WindowPane"])

@rule("DriveGear")
def r_drivegear(rng, d):
    return Stack(["Chassis", "DriveWheels"])

@rule("DriveWheels", weight=2.0)
def r_drive3(rng, d):
    return Row(["Spacer", "Wheel", "Wheel", "Wheel", "Spacer"])

@rule("DriveWheels", weight=1.0)
def r_drive2(rng, d):
    return Row(["Spacer", "Wheel", "Wheel", "Spacer"])


# ---- the tender ------------------------------------------------------------
@rule("Tender")
def r_tender(rng, d):
    return Column([(0.66, "CoalBin"), (0.34, "Underframe")])

@rule("CoalBin")
def r_coalbin(rng, d):
    return Column([(0.38, "CoalHeap"), (0.62, "SolidPanel")])


# ---- freight car types -----------------------------------------------------
@rule("Boxcar")
def r_boxcar(rng, d):
    return Column([(0.20, "Roof"), (0.56, "Body"), (0.24, "Underframe")])

@rule("Tanker")
def r_tanker(rng, d):
    return Column([(0.72, "Tank"), (0.28, "Underframe")])

@rule("Flatcar")
def r_flatcar(rng, d):
    return Column([(0.42, "Deck"), (0.58, "Underframe")])

@rule("Hopper")
def r_hopper(rng, d):
    return Column([(0.64, "HopperBody"), (0.36, "Underframe")])

@rule("Caboose")
def r_caboose(rng, d):
    return Column([(0.17, "Cupola"), (0.13, "Roof"),
                   (0.46, "Body"), (0.24, "Underframe")])

@rule("Cupola")
def r_cupola(rng, d):
    return Row(["Spacer", "CupolaBox", "Spacer"])


# ---- shared sub-structures -------------------------------------------------
@rule("Roof", weight=2.0)
def r_roof_flat(rng, d):   return Stack(["RoofFlat"])
@rule("Roof", weight=2.0)
def r_roof_curved(rng, d): return Stack(["RoofCurved"])
@rule("Roof", weight=1.0)
def r_roof_gable(rng, d):  return Stack(["RoofGabled"])

@rule("Body")
def r_body(rng, d):
    return Row(["Panel"] * rng.randint(3, 6))    # <- panels per car side

@rule("Panel", weight=4.0)
def r_panel_solid(rng, d):  return Stack(["SolidPanel"])
@rule("Panel", weight=2.5)
def r_panel_window(rng, d): return Stack(["WindowPanel"])
@rule("Panel", weight=1.5)
def r_panel_door(rng, d):   return Stack(["DoorPanel"])

@rule("Underframe")
def r_underframe(rng, d):
    return Stack(["Chassis", "WheelRow"])

@rule("WheelRow", weight=3.0)
def r_wheels_2(rng, d):
    return Row(["Spacer", "Wheel", "Spacer", "Spacer", "Wheel", "Spacer"])

@rule("WheelRow", weight=1.0)
def r_wheels_bogies(rng, d):
    return Row(["Spacer", "Wheel", "Wheel", "Spacer", "Spacer",
                "Wheel", "Wheel", "Spacer"])


# ============================================================================
# 7. ================  THE TERMINALS — EDIT ME  ===========================
# ============================================================================
#
# fn(box, rng, pal, hue) -> list of triangles.
# A terminal MAY draw outside its box; the box is a layout hint, not a clip.
# layer: 10 chassis, 20 wheels, 30 body, 35 roof, 40 detail, 45 glass.

@terminal("Spacer")
def t_spacer(b, rng, pal, hue):
    return []


@terminal("SolidPanel")
def t_solid(b, rng, pal, hue):
    out = box_quad(b, pal.body(rng.uniform(-.03, .03), hue), 30)
    out += box_quad(Box(b.right - 2, b.y, 2, b.h), pal.body(-.10, hue), 31)   # rib
    out += box_quad(Box(b.x, b.y, b.w, b.h * .12), pal.body(.06, hue), 31)    # top light
    return out


@terminal("WindowPanel")
def t_window(b, rng, pal, hue):
    out = t_solid(b, rng, pal, hue)
    w = b.inset(0.22, 0.26)
    out += box_quad(w, pal.dark(-.02), 44)
    out += box_quad(w.inset(0.06), pal.glass(rng.uniform(-.06, .06)), 45)
    out.append(tri((w.x, w.bottom), (w.right, w.y), (w.x, w.y),
                   pal.glass(.14), 46))                                    # glint
    return out


@terminal("DoorPanel")
def t_door(b, rng, pal, hue):
    out = t_solid(b, rng, pal, hue)
    d = b.inset(0.14, 0.08)
    out += box_quad(d, pal.body(-.09, hue), 40)
    out += bar((d.x, d.y), (d.x, d.bottom), 2, pal.dark(.05), 41)
    out += bar((d.right, d.y), (d.right, d.bottom), 2, pal.dark(.05), 41)
    out += box_quad(Box(d.cx - 1, d.cy - d.h * .1, 5, 3), pal.metal(.2), 42)
    return out


@terminal("RoofFlat")
def t_roof_flat(b, rng, pal, hue):
    out = box_quad(b, pal.accent_c(-.06, hue), 35)
    out += box_quad(Box(b.x - 3, b.y, b.w + 6, b.h * .35), pal.accent_c(.05, hue), 36)
    return out


@terminal("RoofCurved")
def t_roof_curved(b, rng, pal, hue):
    n = 10
    rise = b.h * rng.uniform(0.55, 0.9)
    top = [(b.x - 3 + (b.w + 6) * i / n,
            b.bottom - b.h * .25 - rise * math.sin(math.pi * i / n))
           for i in range(n + 1)]
    bot = [(p[0], b.bottom) for p in top]
    return strip(top, bot, lambda t: pal.accent_c(.10 - .16 * abs(t - .5) * 2, hue), 35)


@terminal("RoofGabled")
def t_roof_gable(b, rng, pal, hue):
    out = [tri((b.x - 3, b.bottom), (b.cx, b.y - b.h * .3), (b.right + 3, b.bottom),
               pal.accent_c(-.02, hue), 35)]
    out += bar((b.x - 3, b.bottom), (b.cx, b.y - b.h * .3), 3, pal.accent_c(.10, hue), 36)
    return out


@terminal("Chassis")
def t_chassis(b, rng, pal, hue):
    top = Box(b.x, b.y, b.w, b.h * .45)
    out = box_quad(top, pal.dark(.06), 10)
    for i in range(max(2, int(b.w / 22))):                                   # gussets
        x = b.x + b.w * (i + .5) / max(2, int(b.w / 22))
        out.append(tri((x - 6, top.bottom), (x + 6, top.bottom), (x, top.bottom + 7),
                       pal.dark(.02), 11))
    return out


@terminal("Wheel")
def t_wheel(b, rng, pal, hue):
    r = min(b.w, b.h) / 2
    cx, cy = b.cx, RAIL_Y - r
    n = rng.choice((8, 10, 12))
    out = fan(cx, cy, r, n, lambda t: pal.metal(-.06 + .10 * math.sin(t * math.tau)), 20)
    rim_o = [(cx + r * math.cos(math.tau * i / n), cy + r * math.sin(math.tau * i / n))
             for i in range(n + 1)]
    rim_i = [(cx + r * .82 * math.cos(math.tau * i / n),
              cy + r * .82 * math.sin(math.tau * i / n)) for i in range(n + 1)]
    out += strip(rim_o, rim_i, lambda t: pal.metal(.14), 21)
    for i in range(6):                                                        # spokes
        a = math.tau * i / 6 + rng.random() * .1
        out += bar((cx, cy), (cx + r * .8 * math.cos(a), cy + r * .8 * math.sin(a)),
                   max(2, r * .13), pal.metal(.04), 22)
    out += fan(cx, cy, r * .26, 8, lambda t: pal.metal(.18), 23)              # hub
    return out


@terminal("Boiler")
def t_boiler(b, rng, pal, hue):
    out, bands = [], 6
    for i in range(bands):
        y = b.y + b.h * i / bands
        k = .12 - .26 * abs((i + .5) / bands - .35)
        out += box_quad(Box(b.x, y, b.w, b.h / bands + 1), pal.body(k, hue), 30)
    smoke = Box(b.x, b.y, b.w * .16, b.h)
    out += box_quad(smoke, pal.dark(.05), 31)
    out += fan(smoke.right, smoke.cy, b.h * .5, 10, lambda t: pal.dark(.08), 32,
               -math.pi / 2, math.pi / 2)
    for i in range(2, bands, 2):                                              # straps
        out += box_quad(Box(b.x + b.w * (.3 + .3 * i / bands), b.y, 3, b.h),
                        pal.metal(.10), 33)
    return out


@terminal("Chimney")
def t_chimney(b, rng, pal, hue):
    flare = b.w * rng.uniform(.2, .45)
    out = quad((b.x - flare * .3, b.y), (b.right + flare * .3, b.y),
               (b.right, b.bottom), (b.x, b.bottom), pal.dark(.10), 40)
    out += box_quad(Box(b.x - flare * .5, b.y, b.w + flare, b.h * .18),
                    pal.metal(.06), 41)
    return out


@terminal("Dome")
def t_dome(b, rng, pal, hue):
    r = min(b.w / 2, b.h)
    return fan(b.cx, b.bottom, r, 9, lambda t: pal.metal(.02 + .14 * math.sin(t * math.pi)),
               40, math.pi, math.tau)


@terminal("Whistle")
def t_whistle(b, rng, pal, hue):
    return box_quad(Box(b.cx - 1.5, b.y + b.h * .3, 3, b.h * .7), pal.metal(.16), 40)


@terminal("CowCatcher")
def t_cowcatcher(b, rng, pal, hue):
    top = b.bottom - b.h * .34                       # only the lower part of the box
    foot = b.bottom + b.h * .33                      # reaches down to the rail
    nose = (b.x - b.w * .35, foot)
    out = [tri((b.right, top), (b.right, foot), nose, pal.accent_c(-.20, hue), 29)]
    for i in range(1, 5):                            # slats
        t = i / 5
        out += bar((b.right, top + (foot - top) * t),
                   (b.right + (nose[0] - b.right) * t, foot),
                   2, pal.accent_c(.06, hue), 31)
    out += box_quad(Box(b.x - b.w * .2, top - b.h * .10, b.w * 1.2, b.h * .12),
                    pal.dark(.06), 32)               # buffer beam
    return out


@terminal("CabRoof")
def t_cabroof(b, rng, pal, hue):
    return box_quad(Box(b.x - 4, b.y, b.w + 8, b.h), pal.accent_c(-.04, hue), 36)


@terminal("WindowPane")
def t_pane(b, rng, pal, hue):
    w = b.inset(0.24, 0.30)
    out = box_quad(w, pal.dark(.0), 44)
    out += box_quad(w.inset(0.08), pal.glass(.04), 45)
    out.append(tri((w.x, w.bottom), (w.right, w.y), (w.x, w.y), pal.glass(.16), 46))
    return out


@terminal("CoalHeap")
def t_coal(b, rng, pal, hue):
    n = 8
    pts = []
    for i in range(n + 1):
        t = i / n
        mound = math.sin(math.pi * t) ** 0.7                 # smooth hill
        pts.append((b.x + b.w * t,
                    b.bottom - b.h * (0.25 + 0.75 * mound) * rng.uniform(.82, 1.0)))
    return [tri((b.cx, b.bottom), pts[i], pts[i + 1],
                pal.dark(.03 + .05 * (i % 2)), 41) for i in range(n)]


@terminal("Tank")
def t_tank(b, rng, pal, hue):
    cap = b.h * .15
    body = Box(b.x + cap, b.y + b.h * .12, max(8.0, b.w - 2 * cap), b.h * .76)
    out, bands = [], 7
    for i in range(bands):
        y = body.y + body.h * i / bands
        k = .13 - .28 * abs((i + .5) / bands - .32)
        out += box_quad(Box(body.x, y, body.w, body.h / bands + 1), pal.body(k, hue), 30)
    for x, a0 in ((body.x, math.pi / 2), (body.right, -math.pi / 2)):          # end caps
        out += fan(x, body.cy, cap, 8, lambda t: pal.body(-.05 - .06 * t, hue),
                   31, a0, a0 + math.pi, ry=body.h / 2)
    out += box_quad(Box(body.cx - body.w * .07, b.y, body.w * .14, b.h * .16),
                    pal.metal(.10), 40)                                        # hatch
    for f in (.28, .72):
        out += box_quad(Box(body.x + body.w * f, body.y, 3, body.h), pal.metal(.04), 32)
    return out


@terminal("Deck")
def t_deck(b, rng, pal, hue):
    out = box_quad(Box(b.x, b.bottom - b.h * .38, b.w, b.h * .38), pal.body(-.04, hue), 30)
    n = max(2, int(b.w / 26))
    for i in range(n + 1):                                                     # stakes
        x = b.x + b.w * i / n
        out += box_quad(Box(x - 2, b.y + b.h * .1, 4, b.h * .55), pal.metal(-.02), 31)
    return out


@terminal("HopperBody")
def t_hopper(b, rng, pal, hue):
    out = quad((b.x, b.y), (b.right, b.y),
               (b.right - b.w * .16, b.bottom), (b.x + b.w * .16, b.bottom),
               pal.body(.0, hue), 30)
    out += box_quad(Box(b.x, b.y, b.w, b.h * .13), pal.body(.08, hue), 31)
    n = max(2, int(b.w / 20))
    for i in range(1, n):
        x = b.x + b.w * i / n
        out += bar((x, b.y), (x - (x - b.cx) * .16, b.bottom), 2.5,
                   pal.body(-.07, hue), 32)
    return out


@terminal("CupolaBox")
def t_cupola(b, rng, pal, hue):
    out = box_quad(b, pal.body(.02, hue), 33)
    out += box_quad(Box(b.x - 3, b.y, b.w + 6, b.h * .28), pal.accent_c(-.04, hue), 36)
    out += box_quad(b.inset(0.22, 0.32), pal.glass(.02), 45)
    return out


@terminal("Coupler")
def t_coupler(b, rng, pal, hue):
    y = b.bottom - b.h * .45
    out = box_quad(Box(b.x - 2, y - 2.5, b.w + 4, 5), pal.metal(-.04), 15)
    out += box_quad(Box(b.cx - 3.5, y - 5, 7, 10), pal.metal(.06), 16)
    return out


# ============================================================================
# 8. ENGINE  (derive -> measure -> layout -> realise)
# ============================================================================

def derive(symbol, seed, path=None, depth=0):
    path = symbol if path is None else path
    node = Node(symbol, path, rng_for(seed, path), depth)
    if symbol in TERMINALS or symbol not in RULES or depth >= MAX_DEPTH:
        return node                                      # leaf
    fn = weighted_pick(RULES[symbol], node.rng)          # <- seed picks the rule
    exp = fn(node.rng, depth)
    node.kind, node.gap, node.fractions = exp.kind, exp.gap, exp.fractions
    node.children = [derive(s, seed, f"{path}/{s}[{i}]", depth + 1)
                     for i, s in enumerate(exp.syms)]
    return node


def measure(node):
    """Bottom-up intrinsic widths. Declared widths win over computed ones."""
    for c in node.children:
        measure(c)
    if node.symbol in WIDTH:
        lo, hi = WIDTH[node.symbol]
        node.iw = node.rng.uniform(lo, hi)
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
        total = sum(c.iw for c in node.children) or 1.0
        scale = max(0.0, box.w - gaps) / total
        x = box.x
        for c in node.children:
            w = c.iw * scale
            h = box.h * HEIGHT_FRAC.get(c.symbol, 1.0)
            layout(c, Box(x, box.bottom - h, w, h))
            x += w + node.gap
    elif node.kind == COL and node.children:
        fr = node.fractions or [1 / len(node.children)] * len(node.children)
        s = sum(fr) or 1.0
        y = box.y
        for c, f in zip(node.children, fr):
            h = box.h * f / s
            layout(c, Box(box.x, y, box.w, h))
            y += h
    elif node.kind == STACK:
        for c in node.children:
            layout(c, box)


def realise(node, pal, hue, out):
    if node.symbol in HUE_ROOTS:
        hue = node.rng.uniform(-0.07, 0.07)
    if not node.children:
        fn = TERMINALS.get(node.symbol)
        if fn is None:
            out += box_quad(node.box, (255, 0, 180), 90)     # missing terminal = magenta
        else:
            out += fn(node.box, node.rng, pal, hue)
        return
    for c in node.children:
        realise(c, pal, hue, out)


def generate(seed):
    """seed -> (triangles, root node, train width)."""
    root = derive("Train", seed)
    total_w = measure(root)
    layout(root, Box(MARGIN, RAIL_Y - BAND_H, total_w, BAND_H))
    tris = []
    realise(root, Palette(rng_for(seed, "palette")), 0.0, tris)
    tris.sort(key=lambda t: t[2])                 # stable: ties keep emission order
    return tris, root, total_w


# ============================================================================
# 9. RENDER
# ============================================================================

def fit_scale(train_w, screen_w):
    return min(1.0, (screen_w - 2 * MARGIN) / max(1.0, train_w))


def draw(surface, tris, scale=1.0, ox=MARGIN):
    """The only drawing call in the whole program: polygon() with 3 points."""
    for pts, color, _ in tris:
        p = [(ox + (x - ox) * scale, RAIL_Y + (y - RAIL_Y) * scale) for x, y in pts]
        pygame.draw.polygon(surface, color, p)


def draw_scene(surface, tris, train_w, scale=None):
    surface.fill(SKY)
    h = surface.get_height()
    for t in quad((0, RAIL_Y), (surface.get_width(), RAIL_Y),
                  (surface.get_width(), h), (0, h), GROUND):
        pygame.draw.polygon(surface, t[1], t[0])
    for t in quad((0, RAIL_Y), (surface.get_width(), RAIL_Y),
                  (surface.get_width(), RAIL_Y + 4), (0, RAIL_Y + 4), (58, 62, 74)):
        pygame.draw.polygon(surface, t[1], t[0])
    draw(surface, tris, fit_scale(train_w, surface.get_width()) if scale is None else scale)


def draw_boxes(surface, node, scale, depth=0):
    """Debug overlay: every node's layout box, hue-coded by depth. Thin quads."""
    if node.box:
        c = colorsys.hsv_to_rgb((depth * 0.13) % 1.0, 0.9, 1.0)
        c = (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255))
        b = node.box
        pts = [(MARGIN + (b.x - MARGIN) * scale, RAIL_Y + (b.y - RAIL_Y) * scale),
               (MARGIN + (b.right - MARGIN) * scale, RAIL_Y + (b.y - RAIL_Y) * scale),
               (MARGIN + (b.right - MARGIN) * scale, RAIL_Y + (b.bottom - RAIL_Y) * scale),
               (MARGIN + (b.x - MARGIN) * scale, RAIL_Y + (b.bottom - RAIL_Y) * scale)]
        for i in range(4):
            for t in bar(pts[i], pts[(i + 1) % 4], 1, c):
                pygame.draw.polygon(surface, t[1], t[0])
    for ch in node.children:
        draw_boxes(surface, ch, scale, depth + 1)


def render_hud(surface, font, seed, n_tris, debug):
    txt = f"seed {seed}   {n_tris} triangles   R new  <- ->  D boxes {'ON' if debug else 'off'}  T tree  S save"
    surface.blit(font.render(txt, True, (150, 158, 175)), (14, 12))


# ============================================================================
# 10. ENTRY POINTS
# ============================================================================

def render_png(path, seed, w=SCREEN_W, h=SCREEN_H):
    pygame.init()
    surf = pygame.Surface((w, h))
    tris, _, tw = generate(seed)
    draw_scene(surf, tris, tw)
    pygame.image.save(surf, path)
    print(f"{path}  seed={seed}  triangles={len(tris)}  width={tw:.0f}px")


def render_sheet(path, count, start_seed):
    """A contact sheet of consecutive seeds — the fastest way to judge a grammar."""
    global RAIL_Y
    pygame.init()
    row_h, keep = 210, RAIL_Y
    RAIL_Y = row_h - 32
    surf = pygame.Surface((SCREEN_W, row_h * count))
    for i in range(count):
        band = pygame.Surface((SCREEN_W, row_h))
        tris, _, tw = generate(start_seed + i)
        draw_scene(band, tris, tw)
        surf.blit(band, (0, i * row_h))
    RAIL_Y = keep
    pygame.image.save(surf, path)
    print(f"{path}  seeds {start_seed}..{start_seed + count - 1}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--png", type=str, default=None)
    ap.add_argument("--sheet", type=str, default=None)
    ap.add_argument("-n", "--count", type=int, default=6)
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(10 ** 6)

    if args.png:
        return render_png(args.png, seed)
    if args.sheet:
        return render_sheet(args.sheet, args.count, seed)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("grammar train")
    font = pygame.font.SysFont("monospace", 15)
    clock = pygame.time.Clock()

    debug = False
    tris, root, tw = generate(seed)

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key == pygame.K_r:
                    seed = random.randrange(10 ** 6)
                elif e.key == pygame.K_RIGHT:
                    seed += 1
                elif e.key == pygame.K_LEFT:
                    seed -= 1
                elif e.key == pygame.K_d:
                    debug = not debug
                elif e.key == pygame.K_t:
                    lines = []
                    root.dump(lines)
                    print("\n".join(lines))
                    continue
                elif e.key == pygame.K_s:
                    pygame.image.save(screen, f"train_{seed}.png")
                    print(f"saved train_{seed}.png")
                    continue
                else:
                    continue
                tris, root, tw = generate(seed)

        draw_scene(screen, tris, tw)
        if debug:
            draw_boxes(screen, root, fit_scale(tw, SCREEN_W))
        render_hud(screen, font, seed, len(tris), debug)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
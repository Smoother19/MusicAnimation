import math
from dataclasses import dataclass

from grammar_engine import (rule, terminal, Row, Column, Stack, Box,
                            WIDTH, HEIGHT_FRAC, CTX_ROOTS, rng_for)
from shapes import (Rectangle, Square, Circle, Triangle, TrianglePoints,
                    Quad, Trapezoid, Wheel, shade, make_palette)
from config import RAIL_Y


# ============================================================================
# MONDE
# ============================================================================

@dataclass(frozen=True)
class World:
    traction: str      # "steam" | "diesel"
    usage: str         # "freight" | "passengers" | "mixed"


def world(seed):
    r = rng_for(seed, "monde")
    return World(r.choices(["steam", "diesel"], weights=[3, 2])[0],
                 r.choices(["freight", "passengers", "mixed"], weights=[3, 2, 2])[0])


def context(seed):
    """Palette du train + un dict _hooks partage pour les points d'ancrage."""
    pal = make_palette(rng_for(seed, "palette"))
    pal["_hooks"] = {}
    return pal


# ============================================================================
# CONSTANTES VISUELLES (reprises de train.py)
# ============================================================================

CHASSIS_H    = 7      # Train.CHASSIS_H
WHEEL_R      = 9.0    # Train.WHEEL_R : roue de wagon / diesel
WHEEL_R_LOCO = 12.0   # Train.WHEEL_R + 3 : roue motrice vapeur


# ============================================================================
# TAILLES
# ============================================================================

WIDTH.update({
    # vehicules, en pixels
    "SteamLoco": (150, 178), "DieselLoco": (152, 186), "Tender": (74, 96),
    "Passenger": (124, 160), "Boxcar": (96, 130), "Tank": (116, 146),
    "Hopper": (102, 132), "Flatcar": (96, 126), "Coupler": (11, 15),
    # interieur des locos
    "Pilot": (14, 20), "BoilerGroup": (74, 96), "Cab": (44, 58),
    "Hood": (0.66, 0.72), "DieselCab": (0.30, 0.34),
    # poids relatifs
    "Spacer": (0.30, 0.75), "Plank": (0.75, 1.25), "PassPanel": (0.85, 1.2),
    "BoxPanel": (0.8, 1.3), "Wheel": (1.0, 1.0), "DriveWheel": (1.15, 1.15),
    "SmallWheel": (0.7, 0.7),
    "Chimney": (0.85, 1.15), "Dome": (0.9, 1.3), "Crate": (0.7, 1.3),
})

HEIGHT_FRAC.update({
    "Pilot": 0.40, "BoilerGroup": 0.82, "Hood": 0.72,
    "SteamLoco": 1.0, "DieselLoco": 0.96, "Tender": 0.60,
    "Passenger": 0.94, "Boxcar": 0.84, "Tank": 0.76,
    "Hopper": 0.82, "Flatcar": 0.52, "Coupler": 0.22,
})

# train.py peint TOUT le convoi avec une seule palette : la variation par
# vehicule reste donc tres discrete (elle existait a +/-10%, ce qui cassait
# l'unite de couleur du train original).
for _v in ("SteamLoco", "DieselLoco", "Tender", "Passenger", "Boxcar",
           "Tank", "Hopper", "Flatcar"):
    CTX_ROOTS[_v] = lambda rng, parent: dict(
        parent,
        body=shade(parent["body"], rng.uniform(0.96, 1.05)),
        body2=shade(parent["body2"], rng.uniform(0.96, 1.05)),
    )


# ============================================================================
# HELPERS
# ============================================================================

def at(shape, layer):
    shape.layer = layer
    return shape


L_CHASSIS, L_COUPLER, L_WHEEL, L_ROD = 10, 14, 20, 24
L_BODY, L_TRIM, L_ROOF, L_GLASS, L_DETAIL = 30, 34, 40, 45, 50


def rot_quad(cx, cy, length, thick, angle, color):
    c, s = math.cos(angle), math.sin(angle)
    hx, hy = c * length / 2, s * length / 2
    nx, ny = -s * thick / 2, c * thick / 2
    return Quad([(cx - hx + nx, cy - hy + ny), (cx + hx + nx, cy + hy + ny),
                 (cx + hx - nx, cy + hy - ny), (cx - hx - nx, cy - hy - ny)], color)


def wheel_radius(box, maxi):
    """Rayon borne : la boite donne la place, la constante donne l'echelle."""
    return min(box.w * 0.46, box.h * 0.45, maxi)


def make_wheel(box, pal, r, spokes=6, spoke_color=None):
    """Reproduit Train._wheel() : shapes.Wheel(cx, -r, r, pal['hub'], hub or
    pal['wheel'], spokes) -> jante et moyeu en pal['hub'] (gris clair),
    rayons en pal['wheel'] (gris fonce) ou spoke_color, posee sur le rail."""
    return at(Wheel(box.cx, RAIL_Y - r, r,
                    pal["hub"], spoke_color or pal["wheel"], spokes), L_WHEEL)


def chassis_top(box):
    """Ordonnee du dessus du chassis, comme dans train.py :
    fy = -(2 * WHEEL_R) - CHASSIS_H, mesure depuis le rail (= box.bottom)."""
    return box.bottom - 2 * WHEEL_R - CHASSIS_H


# ============================================================================
# REGLES : LE CONVOI
# ============================================================================

WAGON_MIX = {
    "freight":    (["Boxcar", "Tank", "Hopper", "Flatcar", "Passenger"], [4, 3, 3, 3, 1]),
    "passengers": (["Passenger", "Boxcar", "Flatcar", "Tank", "Hopper"], [6, 1, 1, 1, 1]),
    "mixed":      (["Passenger", "Boxcar", "Tank", "Hopper", "Flatcar"], [3, 3, 2, 2, 2]),
}


@rule("Train")
def r_train(rng, d, w):
    """La sequence est tiree ici en une fois : c'est le seul endroit qui peut
    garantir 'jamais deux fois le meme type d'affilee'."""
    types, weights = WAGON_MIX[w.usage]
    seq, previous = [], None
    for _ in range(rng.randint(4, 7)):
        pick = rng.choices(types, weights)[0]
        while pick == previous:
            pick = rng.choices(types, weights)[0]
        previous = pick
        seq.append(pick)

    head = ["SteamLoco", "Tender"] if w.traction == "steam" else ["DieselLoco"]
    out = []
    for i, s in enumerate(head + seq):
        if i:
            out.append("Coupler")
        out.append(s)
    return Row(out)


# ============================================================================
# REGLES : LOCOMOTIVE A VAPEUR
# ============================================================================

@rule("SteamLoco")
def r_steam(rng, d):        return Stack(["SteamFrame", "SteamDetails"])

@rule("SteamFrame")
def r_steam_frame(rng, d):  return Column([(0.62, "SteamTop"), (0.38, "SteamGear")])

@rule("SteamTop")
def r_steam_top(rng, d):    return Row(["Pilot", "BoilerGroup", "Cab"])

@rule("BoilerGroup")
def r_boiler_group(rng, d): return Column([(0.28, "StackRow"), (0.72, "Boiler")])

@rule("StackRow", weight=2.0)
def r_stack_full(rng, d):
    return Row(["Spacer", "Chimney", "Spacer", "Dome", "Spacer"])
@rule("StackRow", weight=1.0)
def r_stack_plain(rng, d):
    return Row(["Spacer", "Chimney", "Spacer"])

@rule("Cab")
def r_cab(rng, d):          return Column([(0.20, "CabRoof"), (0.80, "CabBody")])

@rule("SteamGear")
def r_steam_gear(rng, d):   return Stack(["Chassis", "DriveWheels", "SideRod"])

# roues motrices (r=12, 8 rayons accent) + porteuses (r=6.3, 5 rayons),
# comme Train._steam_loco
@rule("DriveWheels", weight=2.0)
def r_drive_2(rng, d):
    return Row(["Spacer", "DriveWheel", "DriveWheel", "Spacer",
                "SmallWheel", "SmallWheel", "Spacer"])
@rule("DriveWheels", weight=1.0)
def r_drive_3(rng, d):
    return Row(["Spacer", "DriveWheel", "DriveWheel", "DriveWheel",
                "Spacer", "SmallWheel", "Spacer"])


# ============================================================================
# REGLES : LOCOMOTIVE DIESEL
# ============================================================================

@rule("DieselLoco")
def r_diesel(rng, d):       return Stack(["DieselFrame", "DieselDetails"])

@rule("DieselFrame")
def r_diesel_frame(rng, d): return Column([(0.60, "DieselTop"), (0.40, "Under")])

@rule("DieselTop")
def r_diesel_top(rng, d):   return Row(["Hood", "DieselCab"])

@rule("Hood")
def r_hood(rng, d):         return Stack(["HoodBody", "HoodVents"])

@rule("HoodVents")
def r_hood_vents(rng, d):   return Row(["Spacer"] + ["Vent"] * rng.randint(3, 5) + ["Spacer"])

@rule("DieselCab")
def r_diesel_cab(rng, d):   return Column([(0.18, "CabRoof"), (0.82, "CabBody")])

@rule("CabBody")
def r_cab_body(rng, d):     return Stack(["PanelSolid", "CabWindow"])


# ============================================================================
# REGLES : WAGONS
# ============================================================================

@rule("Tender")
def r_tender(rng, d):       return Stack(["TenderFrame", "WagonDetails"])
@rule("TenderFrame")
def r_tender_frame(rng, d):
    return Column([(0.30, "CoalHeap"), (0.36, "BoxBody"), (0.34, "Under")])


@rule("Passenger")
def r_pass(rng, d):         return Stack(["PassFrame", "PassDetails"])
@rule("PassFrame")
def r_pass_frame(rng, d):
    return Column([(0.13, "RoofCurved"), (0.59, "PassBody"), (0.28, "Under")])
@rule("PassBody")
def r_pass_body(rng, d):
    return Row(["EndDoor"] + ["PassPanel"] * rng.randint(4, 7) + ["EndDoor"])
@rule("PassPanel", weight=5.0)
def r_pp_window(rng, d):    return Stack(["CoachWindow"])
@rule("PassPanel", weight=1.2)
def r_pp_solid(rng, d):     return Stack(["PanelSolid"])


@rule("Boxcar")
def r_boxcar(rng, d):       return Stack(["BoxFrame", "WagonDetails"])
@rule("BoxFrame")
def r_box_frame(rng, d):
    return Column([(0.12, "RoofFlat"), (0.58, "BoxBody"), (0.30, "Under")])
@rule("BoxBody")
def r_box_body(rng, d):
    n = rng.randint(2, 3)
    return Row(["Plank"] * n + ["SlidingDoor"] + ["Plank"] * n)


@rule("Tank")
def r_tank(rng, d):         return Stack(["TankFrame", "WagonDetails"])
@rule("TankFrame")
def r_tank_frame(rng, d):
    return Column([(0.26, "TankTop"), (0.38, "TankShell"), (0.36, "Under")])
@rule("TankTop")
def r_tank_top(rng, d):     return Row(["Spacer", "TankHatch", "Spacer"])


@rule("Hopper")
def r_hopper(rng, d):       return Stack(["HopperFrame", "WagonDetails"])
@rule("HopperFrame")
def r_hopper_frame(rng, d):
    return Column([(0.16, "HopperLoad"), (0.52, "HopperBody"), (0.32, "Under")])
@rule("HopperLoad")
def r_hopper_load(rng, d):
    return Row(["Spacer"] + ["LoadLump"] * rng.randint(3, 5) + ["Spacer"])


@rule("Flatcar")
def r_flatcar(rng, d):      return Stack(["FlatFrame", "WagonDetails"])
@rule("FlatFrame")
def r_flat_frame(rng, d):
    return Column([(0.52, "Cargo"), (0.14, "Deck"), (0.34, "Under")])
@rule("Cargo", weight=3.0)
def r_cargo_crates(rng, d):
    return Row(["Spacer"] + ["Crate"] * rng.randint(3, 5) + ["Spacer"])
@rule("Cargo", weight=2.0)
def r_cargo_logs(rng, d):   return Stack(["LogStack"])
@rule("Cargo", weight=1.0)
def r_cargo_empty(rng, d):  return Stack(["Spacer"])


# ============================================================================
# REGLES : SOUS-STRUCTURES PARTAGEES
# ============================================================================

@rule("Under")
def r_under(rng, d):        return Stack(["Chassis", "WheelRow"])

@rule("WheelRow", weight=2.0)
def r_wheels_bogies(rng, d):
    return Row(["Spacer", "Wheel", "Wheel", "Spacer",
                "Spacer", "Wheel", "Wheel", "Spacer"])
@rule("WheelRow", weight=2.0)
def r_wheels_2(rng, d):
    return Row(["Spacer", "Wheel", "Spacer", "Spacer", "Wheel", "Spacer"])


# ============================================================================
# TERMINAUX : structure commune
# ============================================================================

@terminal("Spacer")
def t_spacer(box, rng, pal):
    return []


@terminal("Chassis")
def t_chassis(box, rng, pal):
    # Train._chassis : Rectangle(L/2, top - CHASSIS_H/2, L, CHASSIS_H,
    # pal["chassis"]) avec top = -(2 * WHEEL_R). Barre plate de 7 px posee
    # juste au-dessus du sommet des roues — pas de dents ni de degrade.
    y = box.bottom - 2 * WHEEL_R - CHASSIS_H / 2
    return [at(Rectangle(box.cx, y, box.w, CHASSIS_H, pal["chassis"]),
               L_CHASSIS)]


@terminal("Wheel")
def t_wheel(box, rng, pal):
    # Train._wheels : roue de wagon / bogie, r = WHEEL_R = 9, 6 rayons.
    return [make_wheel(box, pal, wheel_radius(box, WHEEL_R), spokes=6)]


@terminal("DriveWheel")
def t_drive_wheel(box, rng, pal):
    # Train._steam_loco : self._wheel(g, x, wr, spokes=8, hub=pal["accent"])
    # -> roue motrice r = WHEEL_R + 3 = 12, 8 rayons couleur accent.
    return [make_wheel(box, pal, wheel_radius(box, WHEEL_R_LOCO),
                       spokes=8, spoke_color=pal["accent"])]


@terminal("SmallWheel")
def t_small_wheel(box, rng, pal):
    # Train._steam_loco : roues porteuses r = WHEEL_R * 0.7, 5 rayons.
    return [make_wheel(box, pal, wheel_radius(box, WHEEL_R * 0.7), spokes=5)]


@terminal("SideRod")
def t_side_rod(box, rng, pal):
    # Train._steam_loco : Rectangle(L*0.41, -wr+3, L*0.26, 4, pal["metal"])
    # -> bielle de 4 px, au niveau des essieux moteurs (+3 px sous le centre).
    y = box.bottom - WHEEL_R_LOCO + 3
    return [at(Rectangle(box.x + box.w * 0.41, y, box.w * 0.28, 4,
                         pal["metal"]), L_ROD)]


@terminal("Coupler")
def t_coupler(box, rng, pal):
    # Train._couplers : Rectangle(cx, -(2r) - CHASSIS_H/2, GAP/2+2, 4,
    # pal["metal"]) -> simple barre de metal a mi-hauteur du chassis.
    y = box.bottom - 2 * WHEEL_R - CHASSIS_H / 2
    return [at(Rectangle(box.cx, y, box.w + 8, 4, pal["metal"]), L_COUPLER)]


# ============================================================================
# TERMINAUX : panneaux
# ============================================================================
# Les panneaux d'une meme Row doivent se lire comme UN rectangle de caisse
# (train.py dessine une seule Rectangle pleine largeur) : couleur de palette
# pure, +1 px de recouvrement pour tuer les coutures, relief laisse a facet().

def _panel(box, pal, key="body", layer=L_BODY):
    return [at(Rectangle(box.cx, box.cy, box.w + 1, box.h, pal[key]), layer)]


@terminal("PanelSolid")
def t_panel_solid(box, rng, pal):
    # Fragment de la caisse pal["body"] de train.py — aucun liseret.
    return _panel(box, pal, "body")


@terminal("Plank")
def t_plank(box, rng, pal):
    # Train._boxcar : caisse body2 uniforme + Rectangle(x, cy, 3, h*0.9,
    # pal["dark"]) pour la rainure entre planches.
    out = _panel(box, pal, "body2")
    out.append(at(Rectangle(box.right - 1.5, box.cy, 3, box.h * 0.9,
                            pal["dark"]), L_TRIM))
    return out


@terminal("SlidingDoor")
def t_sliding_door(box, rng, pal):
    # Train._boxcar : Rectangle(L/2, cy, L*0.22, h*0.8, pal["accent"]) —
    # porte = simple rectangle accent centre, sans rail ni poignee.
    out = _panel(box, pal, "body2")
    out.append(at(Rectangle(box.cx, box.cy, box.w * 0.95, box.h * 0.8,
                            pal["accent"]), L_TRIM))
    return out


@terminal("Vent")
def t_vent(box, rng, pal):
    # Train._diesel_loco : Rectangle(x, fy - hood_h*0.75, 8, hood_h*0.3,
    # pal["dark"]) -> grilles de 8 px dans le quart haut du capot.
    w = min(8.0, box.w * 0.7)
    return [at(Rectangle(box.cx, box.y + box.h * 0.25, w, box.h * 0.30,
                         pal["dark"]), L_TRIM)]


@terminal("CoachWindow")
def t_coach_window(box, rng, pal):
    # Train._windows : Rectangle(x, fy - h*0.62, min(16, pas*0.62), h*0.38,
    # pal["glass"]) — vitre nue, sans cadre ; le reflet diagonal vient de
    # facet() qui teinte differemment les 2 triangles du rectangle.
    out = _panel(box, pal, "body")
    w = min(16.0, box.w * 0.62)
    out.append(at(Rectangle(box.cx, box.bottom - box.h * 0.62, w,
                            box.h * 0.38, pal["glass"]), L_GLASS))
    return out


@terminal("EndDoor")
def t_end_door(box, rng, pal):
    # Train._passenger : Rectangle(8 | L-8, fy - h*0.45, 9, h*0.7,
    # pal["body2"]) -> montant d'extremite etroit sur fond de caisse.
    out = _panel(box, pal, "body")
    w = min(9.0, box.w * 0.7)
    out.append(at(Rectangle(box.cx, box.bottom - box.h * 0.45, w,
                            box.h * 0.7, pal["body2"]), L_TRIM))
    return out


@terminal("CabWindow")
def t_cab_window(box, rng, pal):
    # Train._steam_loco / _diesel_loco : Rectangle(cab_x, fy - cab_h*~0.73,
    # cab_L*~0.58, cab_h*~0.30, pal["glass"]) — vitre nue en haut de cabine.
    return [at(Rectangle(box.cx, box.bottom - box.h * 0.68, box.w * 0.58,
                         box.h * 0.30, pal["glass"]), L_GLASS)]


# ============================================================================
# TERMINAUX : toits
# ============================================================================

@terminal("RoofFlat")
def t_roof_flat(box, rng, pal):
    # Train._boxcar : Trapezoid(L/2, fy - h - 4, L*0.95, L, 8, pal["roof"]).
    return [at(Trapezoid(box.cx, box.cy, box.w * 0.95, box.w, box.h,
                         pal["roof"]), L_ROOF)]


@terminal("RoofCurved")
def t_roof_curved(box, rng, pal):
    # Train._passenger : Trapezoid(L/2, fy - h - 5, L*0.9, L, 10, pal["roof"]).
    return [at(Trapezoid(box.cx, box.cy, box.w * 0.9, box.w, box.h,
                         pal["roof"]), L_ROOF)]


@terminal("CabRoof")
def t_cab_roof(box, rng, pal):
    # Train._steam_loco : Trapezoid(cab_x, fy - cab_h - 5, cab_L*0.85,
    # cab_L + 8, 10, pal["roof"]) -> toit debordant de la cabine.
    return [at(Trapezoid(box.cx, box.cy, box.w * 0.85, box.w + 8, box.h,
                         pal["roof"]), L_ROOF)]


# ============================================================================
# TERMINAUX : locomotive a vapeur
# ============================================================================

@terminal("Boiler")
def t_boiler(box, rng, pal):
    # Train._steam_loco :
    #   Rectangle(boiler_L/2, cy, boiler_L, boiler_h, pal["body"])   corps plat
    #   Circle(boiler_L, cy, boiler_h/2, pal["body2"], 14)           cote cabine
    #   Circle(2, cy, boiler_h/2 - 2, pal["accent"], 12)             facade
    #   2-4 x Rectangle(.., 4, boiler_h, pal["body2"])               anneaux
    out = [at(Rectangle(box.cx, box.cy, box.w, box.h, pal["body"]), L_BODY)]
    out.append(at(Circle(box.right, box.cy, box.h / 2, pal["body2"], 14),
                  L_BODY))
    out.append(at(Circle(box.x + 2, box.cy, box.h / 2 - 2, pal["accent"], 12),
                  L_BODY + 1))
    for i in range(rng.randint(2, 4)):
        out.append(at(Rectangle(box.x + box.w * (0.25 + 0.22 * i), box.cy,
                                4, box.h, pal["body2"]), L_TRIM))
    return out


@terminal("Chimney")
def t_chimney(box, rng, pal):
    # Train._steam_loco : Trapezoid(ch_x, .., 16, 10, ch_h, pal["dark"])
    # evasee vers le haut + casquette Rectangle(ch_x, sommet, 20, 5,
    # pal["metal"]). Depose l'ancre de fumee au sommet.
    wt = min(16.0, box.w * 1.6)
    out = [at(Trapezoid(box.cx, box.cy, wt, wt * 0.62, box.h, pal["dark"]),
              L_DETAIL),
           at(Rectangle(box.cx, box.y, wt * 1.25, 5, pal["metal"]),
              L_DETAIL + 1)]
    pal.setdefault("_hooks", {})["smoke"] = (box.cx, box.y)   # ancre de la fumee
    return out


@terminal("Dome")
def t_dome(box, rng, pal):
    # Train._steam_loco : Circle(boiler_L*0.55, fy - boiler_h, 8,
    # pal["metal"], 10) -> dome centre sur la ligne du haut de chaudiere.
    r = min(8.0, box.w * 0.7, box.h)
    return [at(Circle(box.cx, box.bottom, r, pal["metal"], 10), L_DETAIL)]


@terminal("Pilot")
def t_pilot(box, rng, pal):
    # Train._steam_loco : Quad([(2, fy), (2, fy + CHASSIS_H + 6), (-20, -2),
    # (-20, -14)], pal["metal"]) -> chasse-pierres metal, du chassis vers le
    # rail, pointe en avant du vehicule.
    top = box.bottom - box.h * 0.10
    nose = box.x - box.w * 0.4
    return [at(Quad([(box.right, top),
                     (box.right, top + CHASSIS_H + 6),
                     (nose, RAIL_Y - 2),
                     (nose, RAIL_Y - 14)], pal["metal"]), L_BODY - 1)]


@terminal("CoalHeap")
def t_coal(box, rng, pal):
    out, n = [], 7
    for i in range(n):
        b = box.hsplit(n)[i]
        f = math.sin(math.pi * (i + 0.5) / n) ** 0.7 * rng.uniform(0.7, 1.0)
        h = box.h * (0.25 + 0.70 * f)
        out.append(at(Rectangle(b.cx, box.bottom - h / 2, b.w + 1, h,
                                shade(pal["dark"], 1.0 + 0.16 * (i % 2))), L_BODY))
    return out


# ============================================================================
# TERMINAUX : diesel
# ============================================================================

@terminal("HoodBody")
def t_hood_body(box, rng, pal):
    # Train._diesel_loco : Trapezoid(nose_L/2, cy, nose_L*0.92, nose_L,
    # hood_h, pal["body"]) + bande accent de 6 px a 35% du bas
    # (Rectangle(nose_L/2, fy - hood_h*0.35, nose_L, 6, pal["accent"])).
    # Depose aussi l'ancre de fumee (echappement) au sommet du capot.
    out = [at(Trapezoid(box.cx, box.cy, box.w * 0.92, box.w, box.h,
                        pal["body"]), L_BODY)]
    out.append(at(Rectangle(box.cx, box.bottom - box.h * 0.35, box.w, 6,
                            pal["accent"]), L_TRIM))
    pal.setdefault("_hooks", {})["smoke"] = (box.cx, box.y)
    return out


# ============================================================================
# TERMINAUX : citerne, tremie, plat
# ============================================================================

@terminal("TankShell")
def t_tank_shell(box, rng, pal):
    # Train._tank : Rectangle(L/2, cy, L - 2r, 2r, pal["body"]) + deux
    # Circle(r, pal["body2"], 14) aux extremites + bande Rectangle(L/2, cy,
    # L*0.7, 5, pal["body2"]) — calottes RONDES, pas de bandes metal.
    r = min(box.h / 2, box.w * 0.15)
    out = [at(Rectangle(box.cx, box.cy, box.w - 2 * r, box.h, pal["body"]),
              L_BODY),
           at(Circle(box.x + r, box.cy, r, pal["body2"], 14), L_BODY),
           at(Circle(box.right - r, box.cy, r, pal["body2"], 14), L_BODY)]
    out.append(at(Rectangle(box.cx, box.cy, box.w * 0.7, 5, pal["body2"]),
                  L_TRIM))
    return out


@terminal("TankHatch")
def t_tank_hatch(box, rng, pal):
    # Train._tank : Trapezoid(L/2, cy - r - 5, 14, 22, 10, pal["accent"])
    # -> dome de chargement accent, plus large a la base.
    b = box.band(0.35, 1.0)
    wt = min(14.0, b.w * 0.55)
    return [at(Trapezoid(b.cx, b.cy, wt, wt * 1.6, b.h, pal["accent"]), L_TRIM)]


@terminal("HopperBody")
def t_hopper_body(box, rng, pal):
    # Train._hopper : Trapezoid(L/2, cy, L, L*0.45, h, pal["body"]) + bande
    # accent de 6 px pres du bord haut — pas de nervures.
    out = [at(Trapezoid(box.cx, box.cy, box.w, box.w * 0.45, box.h,
                        pal["body"]), L_BODY)]
    out.append(at(Rectangle(box.cx, box.y + 3, box.w, 6, pal["accent"]),
                  L_TRIM))
    return out


@terminal("LoadLump")
def t_load_lump(box, rng, pal):
    # Train._hopper : Triangle(x, fy - h - 4, 16-24, 10-16, pal["metal"])
    # -> chargement anguleux gris metal qui depasse de la tremie.
    return [at(Triangle(box.cx, box.bottom - box.h * 0.15,
                        box.w * rng.uniform(0.9, 1.3),
                        box.h * rng.uniform(0.6, 1.0),
                        pal["metal"]), L_BODY - 1)]


@terminal("Deck")
def t_deck(box, rng, pal):
    # Train._flatcar : Rectangle(L/2, fy - 4, L, 8, pal["body2"]).
    return [at(Rectangle(box.cx, box.cy, box.w, box.h, pal["body2"]), L_BODY)]


@terminal("Crate")
def t_crate(box, rng, pal):
    # Train._flatcar : Square(x, y, s, choice([accent, body, roof])) —
    # caisse pleine, posee sur le plancher, sans liseret.
    s = min(box.w, box.h * 0.9) * rng.uniform(0.8, 1.0)
    col = rng.choice([pal["accent"], pal["body"], pal["roof"]])
    return [at(Square(box.cx, box.bottom - s / 2, s, col), L_BODY)]


@terminal("LogStack")
def t_logs(box, rng, pal):
    # Train._flatcar : Circle(.., 9, pal["roof"], 8) en deux rangees (5 + 4).
    out, r = [], min(9.0, box.h / 4, box.w / 12)
    for row, count in ((0, 5), (1, 4)):
        for i in range(count):
            out.append(at(Circle(box.x + box.w * 0.12 + i * 2 * r + row * r,
                                 box.bottom - r - row * 1.8 * r, r,
                                 pal["roof"], 8), L_BODY))
    return out


# ============================================================================
# TERMINAUX : couches de details
# ============================================================================

def _buffers(box, pal, r=4):
    # Tampons metal aux extremites, a mi-hauteur du chassis (meme ligne que
    # les attelages de train.py).
    y = box.bottom - 2 * WHEEL_R - CHASSIS_H / 2
    return [at(Circle(box.x + 2, y, r, pal["metal"], 8), L_DETAIL),
            at(Circle(box.right - 2, y, r, pal["metal"], 8), L_DETAIL)]


@terminal("SteamDetails")
def t_steam_details(box, rng, pal):
    # Lanterne accent en facade + tuyauterie metal le long de la chaudiere
    # (vocabulaire train.py : petits rects pal["metal"], cercles accent).
    out = _buffers(box, pal, 5)
    out.append(at(Circle(box.x + box.w * 0.14, box.y + box.h * 0.26, 6,
                         pal["accent"], 8), L_DETAIL + 1))
    for i in range(3):
        out.append(at(Rectangle(box.x + box.w * (0.32 + 0.11 * i),
                                box.y + box.h * 0.44, 2, box.h * 0.09,
                                pal["metal"]), L_DETAIL))
    out.append(at(Rectangle(box.x + box.w * 0.32, box.y + box.h * 0.40,
                            box.w * 0.28, 2, pal["metal"]), L_DETAIL))
    return out


@terminal("DieselDetails")
def t_diesel_details(box, rng, pal):
    # Train._diesel_loco : Triangle(6, fy - hood_h*0.8, 12, 10, pal["glass"])
    # phare + Rectangle(-3, fy + 3, 8, 14, pal["metal"]) plaque frontale.
    out = _buffers(box, pal, 4)
    out.append(at(Triangle(box.x + 9, box.y + box.h * 0.30, 12, 10,
                           pal["glass"]), L_DETAIL + 1))
    out.append(at(Rectangle(box.x - 3, box.bottom - 2 * WHEEL_R + 3, 8, 14,
                            pal["metal"]), L_DETAIL))
    return out


@terminal("PassDetails")
def t_pass_details(box, rng, pal):
    # Train._passenger : Rectangle(L/2, fy - h*0.22, L, 5, pal["accent"])
    # -> lisiere accent pleine longueur a 22% du bas de la caisse.
    # La caisse occupe la tranche [0.13, 0.72] du vehicule (PassFrame),
    # donc 22% du bas de caisse = box.y + box.h * 0.59.
    out = _buffers(box, pal, 3)
    out.append(at(Rectangle(box.cx, box.y + box.h * 0.59, box.w, 5,
                            pal["accent"]), L_TRIM + 3))
    return out


@terminal("WagonDetails")
def t_wagon_details(box, rng, pal):
    out = _buffers(box, pal, 3)
    for i in range(3):                                    # echelle arriere
        out.append(at(Rectangle(box.right - 7, box.y + box.h * (0.34 + 0.12 * i),
                                9, 2, pal["metal"]), L_DETAIL))
    out.append(at(Rectangle(box.right - 11, box.cy, 2, box.h * 0.36,
                            pal["metal"]), L_DETAIL))
    return out


# ============================================================================
# DEBUG
# ============================================================================

def missing(node):
    return [at(Rectangle(node.box.cx, node.box.cy, node.box.w, node.box.h,
                         (255, 0, 180)), 90)]
from shapes import *
import pygame as ui

class Train():
    def __init__(self, x, y, color, length=260, height=150, gap=0.1, wagons=1):
        self.x = x
        self.y = y
        self.color = color
        self.length = length          
        self.height = height
        self.gap = gap
        self.wagons = wagons
        self.shapes = []

    @property
    def palette(self):
        return {
            "body": self.color,
            "body_l": shade(self.color, 1.35),
            "body_d": shade(self.color, 0.62),
            "roof": shade(self.color, 0.30),
            "accent": (188, 72, 64),
            "metal": (232, 196, 108),
            "metal_d": (150, 118, 56),
            "window": (255, 226, 150),
        }

    def _loco(self, x0, rail):
        L, H, P = self.length, self.height, self.palette

        # proportions horizontales
        nose, engine, cab, rear = 12, 50, 35, 3
        tot = nose + engine + cab + rear
    
        u_boiler = nose / tot                       # début de chaudière
        u_cab    = u_boiler + engine / tot          # frontière chaudière / cabine
        u_rear   = u_cab + cab / tot                # début du porte-à-faux
        u_end    = 1.0
    
        FRAME_FRONT, FRAME_BACK = 0.07, 0.02        # débords du châssis
        ROOF_OVER = 0.02                            # débord du toit
        COUPLER = 0.08                              # attelage hors module
        u_frame0 = u_boiler - FRAME_FRONT
        u_frame1 = u_rear + FRAME_BACK
    
        # proportions verticales
        clearance, frame_h, boiler_h, cab_extra, roof_h, chim_h = 22, 8, 42, 14, 6, 28
    
        v_frame0  = clearance / 100                 # bas du châssis
        v_frame1  = v_frame0 + frame_h / 100        # dessus du châssis
        v_boiler1 = v_frame1 + boiler_h / 100       # dessus de chaudière
        v_cab     = v_boiler1 + cab_extra / 100     # dessus de cabine
        v_roof    = v_cab + roof_h / 100            # dessus du toit
        v_chim    = v_boiler1 + chim_h / 100        # sommet de cheminée

        fh = v_frame1 - v_frame0                  # épaisseur du châssis

        # repères locaux
        def pxl(u):
            return x0 + L * u
        
        def pxh(v):
            return rail - v * H
        
        def rect(u0, u1, v0, v1, c):
            return Rectangle(
                (pxl(u0) + pxl(u1)) / 2, (pxh(v0) + pxh(v1)) / 2,
                (u1 - u0) * L, (v1 - v0) * H, c)

        def on_boiler(t):
                    return u_boiler + t * (u_cab - u_boiler)
         
        def on_cab(t):
            return u_cab + t * (u_rear - u_cab)
        
        def on_frame(t):
            return u_frame0 + t * (u_frame1 - u_frame0)

        def in_boiler(t):
            return v_frame1 + t * (v_boiler1 - v_frame1)

        def in_chimney(t):
            return v_boiler1 + t * (v_chim - v_boiler1)

        # accessoires
        # essieux
        N_DRIVERS  = 2      # nombre d'essieux moteurs
        DRIVE_A    = 0.39   # position du 1er essieu   [t châssis]
        DRIVE_B    = 0.65   # position du dernier      [t châssis]
        PONY_U     = 0.17   # essieu porteur avant     [t châssis]
        HUB_RATIO  = 0.30   # moyeu, en fraction du rayon de roue   [ratio]

        # chaudière
        NOSE_U     = 0.04   # centre de la boîte à fumée   [t chaudière]
        FACET_TOP  = 0.86   # début de la facette claire du dessus  [v chaudière]
        FACET_BOT  = 0.12   # fin de la facette sombre du dessous   [v chaudière]
        N_BANDS    = 3      # nombre de cerclages
        BAND_A     = 0.32   # position du 1er cerclage     [t chaudière]
        BAND_B     = 0.86   # position du dernier          [t chaudière]
        BAND_W     = 0.04   # largeur d'un cerclage        [t chaudière]
        DOME_U     = 0.72   # centre du dôme de vapeur     [t chaudière]
        DOME_R     = 0.09   # rayon du dôme                [v module]

        # cheminée
        CHIM_U     = 0.14   # bord avant de la cheminée    [t chaudière]
        CHIM_W     = 0.16   # largeur de la cheminée       [t chaudière]
        LIP_UNDER  = 0.04   # débord latéral de la lèvre   [t chaudière]
        LIP_OVER   = 0.06   # hauteur de la lèvre          [v module]
        RING_DROP  = 0.06   # écart lèvre / anneau         [v module]
        RING_H     = 0.04   # hauteur de l'anneau          [v module]

        # phare
        LAMP_R     = 0.07   # rayon du réflecteur          [v module]
        LAMP_V     = 0.86   # hauteur sur la chaudière     [v chaudière]
        LAMP_OUT   = 0.02   # avancée devant la chaudière  [t chaudière]
        LAMP_SHIFT = 0.02   # décalage de la lentille      [t chaudière]
        LAMP_INNER = 0.70   # lentille, en fraction du réflecteur   [ratio]

        # cabine
        CAB_PILLAR  = 0.11  # largeur du montant avant     [t cabine]
        WIN_MARGIN  = 0.17  # marge latérale de la fenêtre [t cabine]
        WIN_FRAME_U = 0.03  # épaisseur de cadre, horizontal [t cabine]
        WIN_TOP     = 0.06  # écart toit / haut de fenêtre [v module]
        WIN_H       = 0.24  # hauteur de la fenêtre        [v module]
        WIN_FRAME_V = 0.01  # épaisseur de cadre, vertical [v module]
        CAB_PEAK    = 0.10  # hauteur de la pointe de toit [v module]

        # attelage
        CPL_UNDER  = 0.25   # descente sous le châssis, en fraction de son épaisseur
        CPL_OVER   = 0.50   # montée au-dessus, idem                     [ratio]
        
        s = []

        # wheels
        r_drive = (v_boiler1 - v_frame1) / 2
        for i in range(N_DRIVERS):
            t = DRIVE_A if N_DRIVERS == 1 else DRIVE_A + i * (DRIVE_B - DRIVE_A) / (N_DRIVERS - 1)
            u = on_frame(t)
            s.append(Circle(pxl(u), pxh(r_drive), r_drive * H, P["metal"], 10))
            s.append(Circle(pxl(u), pxh(r_drive), r_drive * H * HUB_RATIO, P["metal_d"], 8))
        r_front = r_drive * 0.52
        s.append(Circle(pxl(on_frame(PONY_U)), pxh(r_front), r_front * H, P["metal"], 8))

        # frame
        s.append(rect(u_frame0, u_frame1, v_frame0, v_frame1, P["roof"]))

        # boiler
        v_axis = (v_frame1 + v_boiler1) / 2
        s.append(Circle(pxl(on_boiler(NOSE_U)), pxh(v_axis), (v_boiler1 - v_frame1) / 2 * H, P["body_d"], 12))
        s.append(rect(u_boiler, u_cab, v_frame1, v_boiler1, P["body"]))
        s.append(rect(u_boiler, u_cab, in_boiler(FACET_TOP), v_boiler1, P["body_l"]))
        s.append(rect(u_boiler, u_cab, v_frame1, in_boiler(FACET_BOT), P["body_d"]))
        for i in range(N_BANDS):
            t = BAND_A + i * (BAND_B - BAND_A) / max(1, N_BANDS - 1)
            s.append(rect(on_boiler(t), on_boiler(t + BAND_W), v_frame1, v_boiler1, P["body_d"]))

        # smoke
        s.append(Circle(pxl(on_boiler(DOME_U)), pxh(v_boiler1), DOME_R * H, P["body_l"], 9))
        s.append(rect(on_boiler(DOME_U - DOME_R), on_boiler(DOME_U + DOME_R), in_boiler(FACET_TOP), v_boiler1, P["body"]))

        # chimney
        s.append(rect(on_boiler(CHIM_U), on_boiler(CHIM_U + CHIM_W), v_boiler1, v_chim, P["roof"]))
        s.append(rect(on_boiler(CHIM_U - LIP_UNDER), on_boiler(CHIM_U + CHIM_W + LIP_UNDER), v_chim - LIP_UNDER, v_chim + LIP_OVER, shade(P["roof"], 1.6)))
        s.append(rect(on_boiler(CHIM_U), on_boiler(CHIM_U + CHIM_W), v_chim - RING_DROP - RING_H, v_chim - RING_DROP, P["metal_d"]))

        # light
        s.append(Circle(pxl(on_boiler(-LAMP_OUT)), pxh(in_boiler(LAMP_V)), LAMP_R * H, P["metal_d"], 10))
        s.append(Circle(pxl(on_boiler(-LAMP_OUT - LAMP_SHIFT)), pxh(in_boiler(LAMP_V)), LAMP_R * LAMP_INNER * H, P["window"], 15))

        # cabin
        s.append(rect(u_cab, u_rear, v_frame0, v_cab, P["accent"]))
        s.append(rect(u_cab, on_cab(CAB_PILLAR), v_frame0, v_cab, shade(P["accent"], 1.2)))
        s.append(rect(u_cab - ROOF_OVER, u_rear + ROOF_OVER, v_cab, v_roof, P["roof"]))
        s.append(Triangle(pxl((u_cab + u_rear) / 2), pxh(v_roof + CAB_PEAK / 2),(u_rear - u_cab + 2 * ROOF_OVER) * L, CAB_PEAK * H, P["roof"]))
        s.append(rect(on_cab(WIN_MARGIN), on_cab(1 - WIN_MARGIN),v_cab - WIN_TOP - WIN_H, v_cab - WIN_TOP, P["roof"]))
        s.append(rect(on_cab(WIN_MARGIN + WIN_FRAME_U), on_cab(1 - WIN_MARGIN - WIN_FRAME_U), v_cab - WIN_TOP - WIN_H + WIN_FRAME_V, v_cab - WIN_TOP - WIN_FRAME_V, P["window"]))

        # rear
        s.append(rect(u_rear, u_end + COUPLER, v_frame1 - fh * CPL_UNDER, v_frame1 + fh * CPL_OVER, P["roof"]))
        return s

    @property
    def wagon_length(self):
        return self.length * 1.05

    def _wagon(self, x0, rail, n_windows=4):
        L, H, P = self.wagon_length, self.height, self.palette
 
        # proportions horizontales
        BODY_OVER = 0.02        # débord de caisse aux extrémités du module
        ROOF_OVER = 0.02        # débord du toit au-delà de la caisse
        FRAME_INSET = 0.02      # retrait du soubassement sous la caisse
 
        u_body0 = BODY_OVER
        u_body1 = 1.0 - BODY_OVER
 
        # proportions verticales
        clearance, frame_h, body_h, roof_h = 18, 8, 68, 8
        BODY_LAP = 0.02         # la caisse recouvre le haut du soubassement
 
        v_frame0 = clearance / 100                  # bas du soubassement
        v_frame1 = v_frame0 + frame_h / 100         # dessus du soubassement
        v_body0  = v_frame1 - BODY_LAP              # bas de caisse
        v_body1  = v_body0 + body_h / 100           # dessus de caisse
        v_roof   = v_body1 + roof_h / 100           # dessus du toit
 
        # repères locaux
        def pxl(u):
            return x0 + L * u
 
        def pxh(v):
            return rail - H * v
 
        def rect(u0, u1, v0, v1, c):
            return Rectangle(
                (pxl(u0) + pxl(u1)) / 2, (pxh(v0) + pxh(v1)) / 2,
                (u1 - u0) * L, (v1 - v0) * H, c)
 
        def on_body(t):                             # horizontal, dans la caisse
            return u_body0 + t * (u_body1 - u_body0)
 
        def in_body(t):                             # vertical, dans la caisse
            return v_body0 + t * (v_body1 - v_body0)
 
        def v_to_u(d):
            return d * H / L
 
        # accessoires
        N_BOGIES, AXLES_PER_BOGIE = 2, 2
        BOGIE_U, AXLE_SPACING = 0.25, 0.14          # centre du bogie / entraxe
        WHEEL_FIT = 0.72                            # roue sous le soubassement
        HUB_RATIO = 0.30
        FACET_TOP, FACET_BOT = 0.91, 0.12           # facettes claire / sombre
        TRIM_V, TRIM_H = 0.26, 0.06                 # bandeau de laiton
        WIN_MARGIN = 0.06                           # marge latérale des fenêtres
        WIN_FILL = 0.66                             # part du pas occupée par la vitre
        WIN_TOP, WIN_H = 0.10, 0.32                 # sous le toit / hauteur
        FRAME_T = 0.02                              # épaisseur de cadre (en v)
 
        s = []
 
        # wheels
        r_wheel = v_frame0 * WHEEL_FIT              # la roue tient sous le châssis
        for b in range(N_BOGIES):
            center = BOGIE_U + b * (1.0 - 2 * BOGIE_U) / max(1, N_BOGIES - 1)
            for i in range(AXLES_PER_BOGIE):
                u = center + (i - (AXLES_PER_BOGIE - 1) / 2) * AXLE_SPACING
                s.append(Circle(pxl(u), pxh(r_wheel), r_wheel * H, P["metal"], 10))
                s.append(Circle(pxl(u), pxh(r_wheel), r_wheel * H * HUB_RATIO, P["metal_d"], 10))
 
        # soubassement / caisse
        s.append(rect(u_body0 + FRAME_INSET, u_body1 - FRAME_INSET, v_frame0, v_frame1, P["roof"]))
        s.append(rect(u_body0, u_body1, v_body0, v_body1, P["body"]))
        s.append(rect(u_body0, u_body1, in_body(FACET_TOP), v_body1, P["body_l"]))
        s.append(rect(u_body0, u_body1, v_body0, in_body(FACET_BOT), P["body_d"]))
 
        # toit
        s.append(rect(u_body0 - ROOF_OVER, u_body1 + ROOF_OVER, v_body1, v_roof, P["roof"]))
 
        # fenêtres
        u0, u1 = on_body(WIN_MARGIN), on_body(1 - WIN_MARGIN)
        pitch = (u1 - u0) / n_windows
        w = pitch * WIN_FILL
        f_u, f_v = v_to_u(FRAME_T), FRAME_T
        for i in range(n_windows):
            c = u0 + pitch * (i + 0.5)
            s.append(rect(c - w / 2 - f_u, c + w / 2 + f_u, v_body1 - WIN_TOP - WIN_H, v_body1 - WIN_TOP, P["roof"]))
            s.append(rect(c - w / 2, c + w / 2, v_body1 - WIN_TOP - WIN_H + f_v, v_body1 - WIN_TOP - f_v, P["window"]))
 
        # bandeau
        s.append(rect(u_body0, u_body1, in_body(TRIM_V), in_body(TRIM_V + TRIM_H), P["metal_d"]))
        return s

    def build(self):
        shapes = []
        cursor = self.x
        shapes += self._loco(cursor, self.y)
        cursor += self.length + self.gap
        for _ in range(self.wagons):
            shapes += self._wagon(cursor, self.y, n_windows=4)
            cursor += self.length * 1.05 + self.gap
        return shapes
 
    def list_shapes(self):
        if not self.shapes:
            self.shapes = self.build()
        return self.shapes
 
    def draw(self, screen):
        for shape in self.list_shapes():
            shape.draw(screen)
import cv2
import numpy as np
import time
from picamera2 import Picamera2

# ==============================================================================
# --- 1. AFMETINGEN (Iets verruimd naar links zodat de vogel erin valt!) ---
SPEELVELD_TOP = 350
SPEELVELD_BODEM = 880
SPEELVELD_LINKS = 20  # Was 50, naar links gehaald voor de vogel
SPEELVELD_RECHTS = 1025

MIDDEN_VELD = (SPEELVELD_TOP + SPEELVELD_BODEM) // 2

# De koker waar de vogel in hangt (gebaseerd op je nieuwe screenshot!)
VOGEL_SCAN_LINKS = 20
VOGEL_SCAN_RECHTS = 140

# --- 2. VASTE INSTELLINGEN ---
SPRONG_KRACHT = 95
VEILIGHEIDS_BUFFER = 22
VOGEL_MIN_GROOTTE = 15  # Iets verlaagd voor motion blur
VOGEL_OFFSET_X = 50
EXTRA_ZAKKEN = 20
MARGE_SPRONG = 0
MIN_TIJD_TUSSEN_SPRONGEN = 0.05
GAP_SIZE = 140

# Verruimde kleuren voor live camera-feed & motion blur
KLEUR_VOGEL_LAAG = np.array([85, 120, 120])
KLEUR_VOGEL_HOOG = np.array([115, 255, 255])

# Buizen deel 1 (Oranje/Rood) en deel 2 (Roze/Rood wrap-around)
KLEUR_BUIS_LAAG1 = np.array([0, 70, 50])
KLEUR_BUIS_HOOG1 = np.array([22, 255, 255])
KLEUR_BUIS_LAAG2 = np.array([160, 70, 50])
KLEUR_BUIS_HOOG2 = np.array([180, 255, 255])

# ==============================================================================
# --- VIDEO RECORDER SETUP ---
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('vlucht_logboek.avi', fourcc, 20.0, (1080, 1440))

# ==============================================================================
# --- CAMERA SETUP ---
print("Camera opstarten (Debug Mode 1440x1080)...")
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (1440, 1080)})
picam2.configure(config)
picam2.start()
print("Camera loopt! Druk op 'CTRL + C' om te stoppen.")

laatste_sprong_tijd = 0

try:
    while True:
        # --- 1. BEELD BINNENHALEN ---
        frame = picam2.capture_array()
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Teken het witte speelveld én twee blauwe stippellijnen voor de vogel-koker
        cv2.rectangle(img, (SPEELVELD_LINKS, SPEELVELD_TOP), (SPEELVELD_RECHTS, SPEELVELD_BODEM), (255, 255, 255), 3)
        cv2.line(img, (VOGEL_SCAN_LINKS, SPEELVELD_TOP), (VOGEL_SCAN_LINKS, SPEELVELD_BODEM), (255, 200, 0), 1)
        cv2.line(img, (VOGEL_SCAN_RECHTS, SPEELVELD_TOP), (VOGEL_SCAN_RECHTS, SPEELVELD_BODEM), (255, 200, 0), 1)

        # --- 2. MASKERS & FILTERS ---
        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)

        # Combineer oranje en rood-roze voor de buizen
        mask_buis1 = cv2.inRange(hsv, KLEUR_BUIS_LAAG1, KLEUR_BUIS_HOOG1)
        mask_buis2 = cv2.inRange(hsv, KLEUR_BUIS_LAAG2, KLEUR_BUIS_HOOG2)
        mask_buis = cv2.bitwise_or(mask_buis1, mask_buis2)

        # Gooi alles buiten het speelveld weg
        mask_buis[0:SPEELVELD_TOP, :] = 0
        mask_buis[SPEELVELD_BODEM:, :] = 0
        mask_buis[:, 0:SPEELVELD_LINKS] = 0
        mask_buis[:, SPEELVELD_RECHTS:] = 0

        mask_vogel[0:SPEELVELD_TOP, :] = 0
        mask_vogel[SPEELVELD_BODEM:, :] = 0
        mask_vogel[:, :VOGEL_SCAN_LINKS] = 0
        mask_vogel[:, VOGEL_SCAN_RECHTS:] = 0

        kernel = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=2)
        kernel_lijm = np.ones((30, 5), np.uint8)
        mask_buis_dik = cv2.morphologyEx(mask_buis_dik, cv2.MORPH_CLOSE, kernel_lijm)

        # --- NIEUW: RÖNTGEN DEBUG SCHERMPJES BOVENIN TEKENEN ---
        # Zo zie je in VLC precies wat de maskers wel of niet oppikken!
        debug_buis = cv2.resize(mask_buis_dik[SPEELVELD_TOP:SPEELVELD_BODEM, SPEELVELD_LINKS:SPEELVELD_RECHTS],
                                (300, 160))
        debug_vogel = cv2.resize(mask_vogel[SPEELVELD_TOP:SPEELVELD_BODEM, VOGEL_SCAN_LINKS:VOGEL_SCAN_RECHTS],
                                 (80, 160))
        img[20:180, 50:350] = cv2.cvtColor(debug_buis, cv2.COLOR_GRAY2BGR)
        img[20:180, 370:450] = cv2.cvtColor(debug_vogel, cv2.COLOR_GRAY2BGR)
        cv2.putText(img, "Buis Masker", (50, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(img, "Vogel", (370, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # --- 3. VOGEL DETECTIE ---
        vogel_neus_x, vogel_staart_x, vogel_y, vogel_top = 0, 0, 0, 0
        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        geldige_vogels = [c for c in contours_vogel if VOGEL_MIN_GROOTTE < cv2.contourArea(c) < 800]
        if geldige_vogels:
            c = max(geldige_vogels, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(c)
            vogel_neus_x = x + w // 2 + VOGEL_OFFSET_X
            vogel_staart_x = x
            vogel_y = y + h // 2
            vogel_top = y
            cv2.circle(img, (vogel_neus_x, vogel_y), 8, (255, 0, 0), -1)
            cv2.circle(img, (vogel_staart_x, vogel_y), 8, (0, 0, 255), -1)
            cv2.line(img, (vogel_staart_x, vogel_y), (vogel_neus_x, vogel_y), (255, 255, 255), 3)

        # --- 4. BUIZEN DETECTIE (GEFIXT!) ---
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            x, y, w, h = cv2.boundingRect(c)
            raakt_rand = (x + w) > (SPEELVELD_RECHTS - 15) or x < (SPEELVELD_LINKS + 15)
            # Geen rare Y-voorwaarde meer: elke grote oranje blok in het veld telt!
            if cv2.contourArea(c) > 100 and (w > 30 or raakt_rand):
                ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h, 'cx': x + w // 2})

        ruwe_buizen.sort(key=lambda k: k['x'])
        kolommen = []
        for buis in ruwe_buizen:
            toegevoegd = False
            for k in kolommen:
                if abs(buis['cx'] - k['gem_x']) < 70:
                    k['buizen'].append(buis)
                    k['gem_x'] = sum(b['cx'] for b in k['buizen']) // len(k['buizen'])
                    k['start_x'] = min(k['start_x'], buis['x'])
                    k['max_w'] = max(k['max_w'], buis['w'])
                    toegevoegd = True
                    break
            if not toegevoegd:
                kolommen.append({'gem_x': buis['cx'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

        # --- 5. ACTIE LOGICA ---
        doel_gevonden = False
        for k in kolommen:
            b_in_k = k['buizen']
            # Is het een bovenbuis? Dan zit zijn midden (y + h/2) in de bovenste helft, of hij raakt de bovenrand
            boven_buizen = [b for b in b_in_k if b['y'] < (SPEELVELD_TOP + 40)]
            onder_buizen = [b for b in b_in_k if b['bottom'] > (SPEELVELD_BODEM - 40)]

            y_plafond = max((b['bottom'] for b in boven_buizen), default=SPEELVELD_TOP)
            y_vloer = min((b['y'] for b in onder_buizen), default=SPEELVELD_BODEM)

            if y_plafond > SPEELVELD_TOP and y_vloer == SPEELVELD_BODEM:
                y_vloer = y_plafond + GAP_SIZE
            elif y_vloer < SPEELVELD_BODEM and y_plafond == SPEELVELD_TOP:
                y_plafond = y_vloer - GAP_SIZE

            gat_midden = (y_plafond + y_vloer) // 2 + EXTRA_ZAKKEN

            cv2.line(img, (k['start_x'], gat_midden), (k['start_x'] + k['max_w'], gat_midden), (0, 255, 255), 2)
            cv2.rectangle(img, (k['start_x'], y_plafond), (k['start_x'] + k['max_w'], y_vloer), (255, 0, 255), 3)

            staart_gevaar = 0
            if k['start_x'] < vogel_staart_x < (k['start_x'] + k['max_w']):
                staart_gevaar = y_plafond
                if staart_gevaar > SPEELVELD_TOP:
                    cv2.line(img, (vogel_staart_x, staart_gevaar + VEILIGHEIDS_BUFFER),
                             (vogel_neus_x, staart_gevaar + VEILIGHEIDS_BUFFER), (0, 0, 255), 2)

            if not doel_gevonden and vogel_neus_x > 0 and (k['start_x'] + k['max_w'] + 40 > vogel_neus_x):
                doel_gevonden = True

                if (vogel_y - gat_midden) > MARGE_SPRONG:
                    hoofd_na_sprong = vogel_top - SPRONG_KRACHT
                    is_veilig = True

                    if y_plafond > SPEELVELD_TOP and hoofd_na_sprong < (y_plafond + VEILIGHEIDS_BUFFER):
                        is_veilig = False
                    if staart_gevaar > SPEELVELD_TOP and hoofd_na_sprong < (staart_gevaar + VEILIGHEIDS_BUFFER):
                        is_veilig = False

                    if is_veilig:
                        nu = time.time()
                        if nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN:
                            laatste_sprong_tijd = nu
                            print(f"[{time.strftime('%H:%M:%S')}] TIK!")
                            cv2.putText(img, "JUMP!", (vogel_neus_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                        (0, 255, 0), 3)
                    else:
                        cv2.putText(img, "BLOCKED", (vogel_neus_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (0, 0, 255), 2)

        # --- 6. OPSLAAN ---
        out.write(img)

except KeyboardInterrupt:
    print("\nScript handmatig gestopt met CTRL+C!")

finally:
    out.release()
    picam2.stop()
    print("Camera gesloten. Video is opgeslagen als 'vlucht_logboek.avi'.")
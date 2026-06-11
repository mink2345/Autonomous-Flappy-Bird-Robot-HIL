import cv2
import numpy as np
import mss
import pyautogui
import time

# --- VEILIGHEID ---
pyautogui.FAILSAFE = True

# ==============================================================================
# --- INSTELLINGEN ---
# ==============================================================================

MONITOR = {'top': 161, 'left': 126, 'width': 717, 'height': 789}

# 1. PHYSICS & SAFETY
SPRONG_KRACHT = 93  # 1 sprong = 93px omhoog
VEILIGHEIDS_BUFFER = 20  # Blijf minimaal 20px van het ijzer vandaan

# 2. VOGEL & SENSOR
VOGEL_MIN_GROOTTE = 50
VOGEL_OFFSET_X = 15
LOOKAHEAD_X = 20

# 3. BUIS DETECTIE
BUIS_MIN_AREA = 100
BUIS_KERN_DIKTE = 2

# 4. KLEUREN (ORIGINEEL)
KLEUR_VOGEL_LAAG = np.array([14, 50, 50])
KLEUR_VOGEL_HOOG = np.array([34, 255, 255])
KLEUR_BUIS_LAAG = np.array([40, 50, 50])
KLEUR_BUIS_HOOG = np.array([60, 255, 255])

# 5. NAVIGATIE (WIJSHEID)
GAP_SIZE = 140  # Het gat is ALTIJD 140 pixels groot
EXTRA_ZAKKEN = 25  # We mikken iets onder het exacte midden (zwaartekracht)

# 6. ACTIE
MARGE_BAND = 10
KLIK_TIJD = 0.02
MIN_TIJD_TUSSEN_SPRONGEN = 0.10

# ==============================================================================

print("--- DE INTELLIGENTE ROBOT (GAP MATH - FIXED) ---")
print("1. Rekent missende buizen uit op basis van GAP_SIZE (140px).")
print("2. Filtert reflecties weg met 'Erode'.")
print("Start: DIRECT")

laatste_sprong_tijd = 0

with mss.mss() as sct:
    while True:
        loop_start = time.time()

        # 1. Beeld
        screenshot = sct.grab(MONITOR)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        scherm_hoogte = img.shape[0]
        midden_scherm = scherm_hoogte // 2

        # 2. Maskers
        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)
        mask_buis = cv2.inRange(hsv, KLEUR_BUIS_LAAG, KLEUR_BUIS_HOOG)

        zwart_boven = int(scherm_hoogte * 0.1)
        zwart_onder = int(scherm_hoogte * 0.78)
        mask_vogel[0:zwart_boven, :] = 0
        mask_vogel[zwart_onder:, :] = 0
        mask_buis[zwart_onder:, :] = 0

        # NIEUW: ERODE (Wegvreten van ruis/reflecties)
        # Dit maakt dunne lijntjes (zoals reflecties) kapot, maar laat dikke buizen staan.
        kernel_erode = np.ones((3, 3), np.uint8)
        mask_buis = cv2.erode(mask_buis, kernel_erode, iterations=1)

        # Daarna weer dik maken (Dilate)
        kernel_dilate = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel_dilate, iterations=BUIS_KERN_DIKTE)

        # 3. Vogel
        vogel_x, vogel_y = 0, 0
        vogel_top = 0

        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours_vogel:
            c = max(contours_vogel, key=cv2.contourArea)
            if cv2.contourArea(c) > VOGEL_MIN_GROOTTE:
                x, y, w, h = cv2.boundingRect(c)
                vogel_x = x + w // 2 + VOGEL_OFFSET_X
                vogel_y = y + h // 2
                vogel_top = y
                cv2.circle(img, (vogel_x, vogel_y), 10, (255, 0, 0), 2)

        # 4. Buizen (Extreem punten zoeken)
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []

        for c in contours_buis:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)

            # Anti-Reflectie: Bovenbuis moet plafond raken
            is_reflectie = (y > 5) and (y < midden_scherm)

            if area > BUIS_MIN_AREA and not is_reflectie:
                ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h, 'center_x': x + w // 2})

        ruwe_buizen.sort(key=lambda k: k['x'])

        # 5. Groeperen
        kolommen = []
        for buis in ruwe_buizen:
            toegevoegd = False
            for kolom in kolommen:
                if abs(buis['center_x'] - kolom['gemiddelde_x']) < 50:
                    kolom['buizen'].append(buis)
                    kolom['gemiddelde_x'] = sum(b['center_x'] for b in kolom['buizen']) // len(kolom['buizen'])
                    kolom['start_x'] = min(kolom['start_x'], buis['x'])
                    kolom['max_w'] = max(kolom['max_w'], buis['w'])
                    toegevoegd = True
                    break
            if not toegevoegd:
                kolommen.append(
                    {'gemiddelde_x': buis['center_x'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

        # 6. BESLISSEN
        doel_gevonden = False
        sensor_x = vogel_x + LOOKAHEAD_X
        cv2.line(img, (sensor_x, 0), (sensor_x, scherm_hoogte), (0, 255, 255), 1)

        for kolom in kolommen:
            y_plafond_punt = 0
            y_vloer_punt = scherm_hoogte

            heeft_boven = False
            heeft_onder = False

            for b in kolom['buizen']:
                if b['y'] < midden_scherm:
                    y_plafond_punt = max(y_plafond_punt, b['bottom'])
                    heeft_boven = True
                else:
                    y_vloer_punt = min(y_vloer_punt, b['y'])
                    heeft_onder = True

            # --- GAP RECONSTRUCTIE (WISKUNDE) ---
            # Hier lossen we het "soms wel, soms niet" probleem op.
            if heeft_boven and heeft_onder:
                # Perfecte situatie: we zien alles
                pass
            elif heeft_boven and not heeft_onder:
                # Alleen boven? Dan is de vloer precies 140px lager.
                y_vloer_punt = y_plafond_punt + GAP_SIZE
            elif heeft_onder and not heeft_boven:
                # Alleen onder? Dan is het plafond precies 140px hoger.
                y_plafond_punt = y_vloer_punt - GAP_SIZE

            # Als we een "spook buis" hebben (glare), dan is y_plafond_punt misschien 10px te laag.
            # Maar omdat we GAP_SIZE gebruiken, zakt y_vloer_punt OOK 10px mee.
            # Het GAT blijft intact, het schuift alleen iets.

            # Het doel berekenen
            gat_midden = (y_plafond_punt + y_vloer_punt) // 2 + EXTRA_ZAKKEN
            spring_grens = gat_midden + MARGE_BAND

            # Plafond Gevaar (Voor Safety Check)
            plafond_gevaar = y_plafond_punt

            # Visualisatie
            cv2.rectangle(img, (kolom['start_x'], y_plafond_punt), (kolom['start_x'] + kolom['max_w'], y_vloer_punt),
                          (50, 50, 50), 2)  # Grijs kader = Het GAT
            cv2.circle(img, (kolom['gemiddelde_x'], gat_midden), 5, (0, 255, 255), -1)  # Geel = Doel

            # Rode Safety Lijn
            doodslijn = plafond_gevaar + VEILIGHEIDS_BUFFER
            cv2.line(img, (kolom['start_x'], doodslijn), (kolom['start_x'] + kolom['max_w'], doodslijn), (0, 0, 255), 2)

            # --- ACTIE ---
            if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > sensor_x):
                doel_gevonden = True
                cv2.line(img, (vogel_x, vogel_y), (kolom['gemiddelde_x'], gat_midden), (200, 200, 0), 1)

                wil_springen = vogel_y > spring_grens

                if wil_springen:
                    # SAFETY CHECK
                    hoofd_na_sprong = vogel_top - SPRONG_KRACHT
                    is_veilig = True

                    if hoofd_na_sprong < doodslijn:
                        is_veilig = False

                    if is_veilig:
                        nu = time.time()
                        if nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN:
                            pyautogui.keyDown('space')
                            time.sleep(KLIK_TIJD)
                            pyautogui.keyUp('space')
                            laatste_sprong_tijd = nu
                            cv2.putText(img, "TIK!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                        (0, 255, 0), 2)
                        else:
                            cv2.putText(img, "Wait", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                        (0, 165, 255), 2)
                    else:
                        cv2.putText(img, "HEAD!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255),
                                    2)
                        cv2.line(img, (vogel_x - 10, vogel_y - 10), (vogel_x + 10, vogel_y + 10), (0, 0, 255), 2)
                        cv2.line(img, (vogel_x + 10, vogel_y - 10), (vogel_x - 10, vogel_y + 10), (0, 0, 255), 2)
                else:
                    cv2.putText(img, "Zakken", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow('Robot Brein (Gap Math)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
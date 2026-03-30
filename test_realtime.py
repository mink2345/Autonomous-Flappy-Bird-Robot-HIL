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

# 1. PHYSICS & SAFETY (NIEUW)
SPRONG_KRACHT = 93  # Een sprong is ~93 pixels omhoog
VEILIGHEIDS_BUFFER = 15  # Blijf minimaal zoveel pixels van het plafond vandaan

# 2. VOGEL DETECTIE
VOGEL_MIN_GROOTTE = 50
VOGEL_OFFSET_X = 15
OVAAL_BREEDTE_EXTRA = 0
OVAAL_HOOGTE_EXTRA = 0

# 3. BUIS DETECTIE
BUIS_MIN_AREA = 200
BUIS_MIN_BREEDTE = 15
BUIS_KERN_DIKTE = 2

# 4. KLEUREN (JOUW ORIGINELE WAARDES)
KLEUR_VOGEL_LAAG = np.array([14, 50, 50])
KLEUR_VOGEL_HOOG = np.array([34, 255, 255])
KLEUR_BUIS_LAAG = np.array([40, 50, 50])
KLEUR_BUIS_HOOG = np.array([60, 255, 255])

# 5. NAVIGATIE
GAP_SIZE = 140
EXTRA_ZAKKEN = 30
CORRECTIE_BOVEN_BUIS = 80
CORRECTIE_ONDER_BUIS = 160

# 6. ACTIE
MARGE_SPRONG = 5
KLIK_TIJD = 0.02
MIN_TIJD_TUSSEN_SPRONGEN = 0.10

# ==============================================================================

print("--- DE VLIEGENDE ROBOT (SAFETY CHECK AAN) ---")
print("Kleuren: Origineel (Geel/Groen)")
print("Start: DIRECT")

# GEEN SLEEP MEER

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

        # 3. Cleanup
        zwart_boven = int(scherm_hoogte * 0.1)
        zwart_onder = int(scherm_hoogte * 0.2)
        mask_vogel[0:zwart_boven, :] = 0
        mask_vogel[scherm_hoogte - zwart_onder:, :] = 0
        mask_buis[scherm_hoogte - zwart_onder:, :] = 0

        kernel = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=BUIS_KERN_DIKTE)

        # 4. Vogel Opsporen
        vogel_x, vogel_y = 0, 0
        vogel_top = 0  # NODIG VOOR SAFETY CHECK

        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours_vogel:
            c = max(contours_vogel, key=cv2.contourArea)
            if cv2.contourArea(c) > VOGEL_MIN_GROOTTE:
                x, y, w, h = cv2.boundingRect(c)
                vogel_x = x + w // 2 + VOGEL_OFFSET_X
                vogel_y = y + h // 2
                vogel_top = y  # Bovenkant schedel
                cv2.circle(img, (vogel_x, vogel_y), 10, (255, 0, 0), 2)

        # 5. Buizen Detectie
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)
            in_top_zone = (y < 50)
            in_bodem_zone = (y > midden_scherm)
            geldige_plek = (in_top_zone or in_bodem_zone)
            breed_genoeg = (w > BUIS_MIN_BREEDTE)

            if area > BUIS_MIN_AREA and breed_genoeg and geldige_plek:
                ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h, 'center_x': x + w // 2})

        ruwe_buizen.sort(key=lambda k: k['x'])

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

        # 6. Beslissen
        doel_gevonden = False

        for kolom in kolommen:
            buizen_in_kolom = kolom['buizen']
            buizen_in_kolom.sort(key=lambda b: b['y'])

            y_plafond = 0
            y_vloer = scherm_hoogte

            # Bepaal waar het plafond zit (voor de safety check)
            plafond_gevaar = 0

            if len(buizen_in_kolom) >= 2:
                y_plafond = buizen_in_kolom[0]['bottom']
                y_vloer = buizen_in_kolom[-1]['y']
                plafond_gevaar = y_plafond
            elif len(buizen_in_kolom) == 1:
                buis = buizen_in_kolom[0]
                if buis['y'] < midden_scherm:
                    y_plafond = buis['bottom']
                    y_vloer = y_plafond + GAP_SIZE + CORRECTIE_BOVEN_BUIS
                    plafond_gevaar = y_plafond
                else:
                    y_vloer = buis['y']
                    y_plafond = y_vloer - GAP_SIZE + CORRECTIE_ONDER_BUIS
                    # Bij stompje is er geen fysiek plafond, dus gevaar = 0 (of heel hoog)
                    plafond_gevaar = 0

                    # Doel berekenen
            gat_midden = (y_plafond + y_vloer) // 2 + EXTRA_ZAKKEN

            # Visualiseer
            cv2.line(img, (kolom['start_x'], gat_midden), (kolom['start_x'] + kolom['max_w'], gat_midden),
                     (0, 255, 255), 2)
            cv2.rectangle(img, (kolom['start_x'], y_plafond), (kolom['start_x'] + kolom['max_w'], y_vloer),
                          (255, 0, 255), 2)

            # Teken de 'Doodslijn' (Safety Line)
            if plafond_gevaar > 0:
                doodslijn = plafond_gevaar + VEILIGHEIDS_BUFFER
                cv2.line(img, (kolom['start_x'], doodslijn), (kolom['start_x'] + kolom['max_w'], doodslijn),
                         (0, 0, 255), 2)

            # --- ACTIE LOGICA ---
            if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x):
                doel_gevonden = True
                cv2.line(img, (vogel_x, vogel_y), (kolom['gemiddelde_x'], gat_midden), (200, 200, 0), 1)

                verschil = vogel_y - gat_midden

                # 1. Willen we springen?
                if verschil > MARGE_SPRONG:

                    # 2. SAFETY CHECK: Is het veilig?
                    # Waar is mijn hoofd NA 93px springen?
                    hoofd_na_sprong = vogel_top - SPRONG_KRACHT

                    # Is dat hoger dan het plafond + buffer?
                    # (Let op: Y=0 is boven, dus kleiner getal is hoger)
                    is_veilig = True
                    if plafond_gevaar > 0:
                        if hoofd_na_sprong < (plafond_gevaar + VEILIGHEIDS_BUFFER):
                            is_veilig = False

                    if is_veilig:
                        # --- SPRINGEN ---
                        nu = time.time()
                        if nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN:
                            pyautogui.keyDown('space')
                            time.sleep(KLIK_TIJD)
                            pyautogui.keyUp('space')
                            laatste_sprong_tijd = nu
                            cv2.putText(img, "JUMP!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                        (0, 255, 0), 2)
                        else:
                            cv2.putText(img, "Wait", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                        (0, 165, 255), 2)
                    else:
                        # --- GEBLOKKEERD ---
                        cv2.putText(img, "BLOCKED!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                    (0, 0, 255), 2)
                        # Kruis door vogel
                        cv2.line(img, (vogel_x - 10, vogel_y - 10), (vogel_x + 10, vogel_y + 10), (0, 0, 255), 2)
                        cv2.line(img, (vogel_x + 10, vogel_y - 10), (vogel_x - 10, vogel_y + 10), (0, 0, 255), 2)

                else:
                    cv2.putText(img, "Zakken", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow('Robot Brein (Safety)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()

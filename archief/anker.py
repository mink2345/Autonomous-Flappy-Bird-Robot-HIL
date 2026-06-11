import cv2
import numpy as np
import mss
import pyautogui
import time

# --- VEILIGHEID ---
pyautogui.FAILSAFE = True

# --- INSTELLINGEN ---
monitor_instelling = {'top': 161, 'left': 126, 'width': 717, 'height': 789}

# --- GEDRAG ---
JUMP_COOLDOWN = 0.15  # Tijd wachten tussen sprongen
MARGE_BAND = 15  # Helft van de veilige zone (totaal 30px)
KLIK_DUUR = 0.05  # Korte, felle tik

# --- DE NIEUWE AFSTELLING (LAGER VLIEGEN) ---
BUFFER_VAN_VLOER = 25  # Minder afstand houden van onderste buis (was 55) -> Vogel zakt
BUFFER_VAN_PLAFOND = 85  # MEER afstand houden van bovenste buis (was 55) -> Vogel zakt

print("--- DE VLIEGENDE ROBOT (LAAG VLIEGEN + DIRECT START) ---")
print("1. KLIK OP HET SPEL.")
print("2. DRUK DIRECT OP SPATIE OM TE STARTEN.")
print("Druk 'q' in dit venster om te stoppen.")

time.sleep(1)  # Heel korte buffer voor jou om naar het venster te gaan

script_start_tijd = time.time()
last_jump_time = 0

with mss.mss() as sct:
    while True:
        loop_start = time.time()
        tijd_bezig = loop_start - script_start_tijd

        # 1. Beeld
        screenshot = sct.grab(monitor_instelling)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        scherm_hoogte = img.shape[0]
        midden_scherm = scherm_hoogte // 2

        # 2. Kleuren
        onder_vogel = np.array([14, 50, 50])
        boven_vogel = np.array([34, 255, 255])
        onder_buis = np.array([40, 50, 50])
        boven_buis = np.array([60, 255, 255])

        mask_vogel = cv2.inRange(hsv, onder_vogel, boven_vogel)
        mask_buis = cv2.inRange(hsv, onder_buis, boven_buis)

        # 3. Cleanup
        zwart_boven = int(scherm_hoogte * 0.1)
        zwart_onder = int(scherm_hoogte * 0.2)
        mask_vogel[0:zwart_boven, :] = 0
        mask_vogel[scherm_hoogte - zwart_onder:, :] = 0
        mask_buis[scherm_hoogte - zwart_onder:, :] = 0

        kernel = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=2)

        # 4. Vogel Opsporen (Ovaal)
        vogel_x, vogel_y = 0, 0
        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours_vogel:
            c = max(contours_vogel, key=cv2.contourArea)
            if cv2.contourArea(c) > 50:
                x, y, w, h = cv2.boundingRect(c)
                center_x = x + w // 2
                center_y = y + h // 2

                offset_naar_voren = 12
                vogel_x = center_x + offset_naar_voren
                vogel_y = center_y

                axis_breedte = (w // 2) + 16
                axis_hoogte = (h // 2) + 7

                cv2.ellipse(img, (vogel_x, vogel_y), (axis_breedte, axis_hoogte), 0, 0, 360, (255, 0, 0), 2)
                cv2.drawMarker(img, (vogel_x, vogel_y), (255, 255, 0), markerType=cv2.MARKER_CROSS, markerSize=10,
                               thickness=2)

        # 5. Buizen (Zone Detectie)
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)

            in_top_zone = (y < 50)
            in_bodem_zone = (y > midden_scherm)
            geldige_plek = (in_top_zone or in_bodem_zone)
            breed_genoeg = (w > 15)

            if area > 200 and breed_genoeg and geldige_plek:
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

        # 6. Beslissen & Actie (ANKER LOGICA - OMLAAG GEZET)
        doel_gevonden = False

        for kolom in kolommen:
            buizen_in_kolom = kolom['buizen']
            buizen_in_kolom.sort(key=lambda b: b['y'])

            doel_y = 0

            if len(buizen_in_kolom) >= 2:
                # BEIDE BUIZEN: Precies in het midden
                plafond = buizen_in_kolom[0]['bottom']
                vloer = buizen_in_kolom[-1]['y']
                doel_y = (plafond + vloer) // 2

            elif len(buizen_in_kolom) == 1:
                buis = buizen_in_kolom[0]

                if buis['y'] < midden_scherm:
                    # ALLEEN BOVENSTE BUIS
                    # Mik 70px onder de buis (Lager vliegen!)
                    doel_y = buis['bottom'] + BUFFER_VAN_PLAFOND
                else:
                    # ALLEEN ONDERSTE BUIS
                    # Mik 40px boven de buis (Lager vliegen!)
                    doel_y = buis['y'] - BUFFER_VAN_VLOER

            # Compensatie voor zwaartekracht (iets omlaag mikken is veiliger)
            doel_y += 15

            # De Veilige Band
            zone_boven = doel_y - MARGE_BAND
            zone_onder = doel_y + MARGE_BAND

            # Visualiseer
            cv2.line(img, (kolom['start_x'], zone_boven), (kolom['start_x'] + kolom['max_w'], zone_boven), (0, 255, 0),
                     2)
            cv2.line(img, (kolom['start_x'], zone_onder), (kolom['start_x'] + kolom['max_w'], zone_onder), (0, 255, 0),
                     2)
            cv2.line(img, (kolom['start_x'], doel_y), (kolom['start_x'] + kolom['max_w'], doel_y), (255, 255, 0), 1)

            if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x):
                doel_gevonden = True

                # ACTIE: Alleen klikken als we ONDER de band zakken
                if vogel_y > zone_onder:
                    nu = time.time()
                    if nu - last_jump_time > JUMP_COOLDOWN:
                        # KLIK!
                        pyautogui.keyDown('space')
                        time.sleep(KLIK_DUUR)
                        pyautogui.keyUp('space')
                        last_jump_time = nu

                        cv2.line(img, (kolom['start_x'], zone_onder), (kolom['start_x'] + kolom['max_w'], zone_onder),
                                 (0, 0, 255), 4)
                        cv2.putText(img, "TIK!", (kolom['start_x'], doel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255),
                                    2)
                    else:
                        cv2.putText(img, "Wait...", (kolom['start_x'], doel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (0, 165, 255), 2)

                else:
                    cv2.line(img, (vogel_x, vogel_y), (kolom['gemiddelde_x'], doel_y), (0, 255, 0), 2)

        cv2.imshow('Robot Brein (Live)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
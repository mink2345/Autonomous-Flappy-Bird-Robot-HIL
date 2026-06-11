import cv2
import numpy as np
import mss
import pyautogui
import time

# --- VEILIGHEID ---
pyautogui.FAILSAFE = True

# --- INSTELLINGEN ---
monitor_instelling = {'top': 161, 'left': 126, 'width': 717, 'height': 789}
GAP_SIZE = 140

# --- GEDRAG ---
JUMP_COOLDOWN = 0.15  # Tijd wachten tussen sprongen
MARGE_BAND = 15  # De dikte van de veilige zone (totaal 30px)
KLIK_DUUR = 0.05  # Hoe lang de toets ingedrukt wordt (Sweet Spot)
START_VERTRAGING = 0.5  # Aantal seconden wachten voor de robot begint
LOOKAHEAD_PIXELS = 10  # <--- NIEUW: 20px naar voren kijken

print("--- DE VLIEGENDE ROBOT (LOOKAHEAD 20px) ---")
print(f"1. De robot wacht {START_VERTRAGING} seconden.")
print("2. KLIK OP HET SPEL en DRUK SPATIE om te starten.")
print("3. Laat de robot het overnemen.")
print("Druk 'q' in dit venster om te stoppen.")

time.sleep(1)

# Variabelen voor timing
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

                # Teken de vogel
                cv2.ellipse(img, (vogel_x, vogel_y), (axis_breedte, axis_hoogte), 0, 0, 360, (255, 0, 0), 2)

                # NIEUW: Teken een geel lijntje waar hij "kijkt" (20px vooruit)
                cv2.line(img, (vogel_x, vogel_y), (vogel_x + LOOKAHEAD_PIXELS, vogel_y), (0, 255, 255), 2)

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

        # --- WACHT OP START ---
        if tijd_bezig < START_VERTRAGING:
            resterend = int(START_VERTRAGING - tijd_bezig) + 1
            cv2.putText(img, f"START: {resterend}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.imshow('Robot Brein (Live)', img)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            continue

        # 6. Beslissen & Actie
        doel_gevonden = False

        # BEREKEN HET KIJK-PUNT
        sensor_x = vogel_x + LOOKAHEAD_PIXELS

        for kolom in kolommen:
            buizen_in_kolom = kolom['buizen']
            buizen_in_kolom.sort(key=lambda b: b['y'])

            y_plafond = 0
            y_vloer = scherm_hoogte

            if len(buizen_in_kolom) >= 2:
                y_plafond = buizen_in_kolom[0]['bottom']
                y_vloer = buizen_in_kolom[-1]['y']
            elif len(buizen_in_kolom) == 1:
                buis = buizen_in_kolom[0]
                if buis['y'] < midden_scherm:
                    y_plafond = buis['bottom']
                    y_vloer = y_plafond + GAP_SIZE + 80
                else:
                    y_vloer = buis['y']
                    y_plafond = y_vloer - GAP_SIZE + 160  # De Stompje-Fix

            gat_midden = (y_plafond + y_vloer) // 2 + 25
            zone_boven = gat_midden - MARGE_BAND
            zone_onder = gat_midden + MARGE_BAND

            # Visualiseer de band
            cv2.line(img, (kolom['start_x'], zone_boven), (kolom['start_x'] + kolom['max_w'], zone_boven), (0, 255, 0),
                     2)
            cv2.line(img, (kolom['start_x'], zone_onder), (kolom['start_x'] + kolom['max_w'], zone_onder), (0, 255, 0),
                     2)

            # --- AANGEPASTE LOGICA MET LOOKAHEAD ---
            # We gebruiken nu 'sensor_x' (vogel + 20) om te kijken of we bij de buis zijn
            if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > sensor_x):
                doel_gevonden = True

                if vogel_y > zone_onder:
                    nu = time.time()
                    if nu - last_jump_time > JUMP_COOLDOWN:
                        pyautogui.keyDown('space')
                        time.sleep(KLIK_DUUR)
                        pyautogui.keyUp('space')
                        last_jump_time = nu

                        cv2.line(img, (kolom['start_x'], zone_onder), (kolom['start_x'] + kolom['max_w'], zone_onder),
                                 (0, 0, 255), 4)
                        cv2.putText(img, "TIK!", (kolom['start_x'], gat_midden), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                    (0, 0, 255), 2)
                    else:
                        cv2.putText(img, "Wait...", (kolom['start_x'], gat_midden), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (0, 165, 255), 2)
                else:
                    # Visualiseer waar hij op mikt (gele lijn naar doel)
                    cv2.line(img, (vogel_x, vogel_y), (kolom['gemiddelde_x'], gat_midden), (0, 255, 255), 2)

        cv2.imshow('Robot Brein (Live)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
import cv2
import numpy as np
import mss
import pyautogui
import time

# --- VEILIGHEID ---
pyautogui.FAILSAFE = True

# --- INSTELLINGEN ---
monitor_instelling = {'top': 161, 'left': 126, 'width': 717, 'height': 789}

# --- GEDRAG & LATENCY COMPENSATIE ---
# We kijken nu VEEL verder vooruit. Niet een vaste afstand, maar naar de eerstvolgende buis.
# Maar we moeten wel een minimum afstand houden om niet te vroeg te springen voor een buis die nog heel ver is.
MIN_AFSTAND_TOT_BUIS = 0  # Begin direct met mikken zodra je hem ziet
MAX_AFSTAND_TOT_BUIS = 300  # Kijk niet naar buizen die aan de andere kant van de wereld zijn

JUMP_COOLDOWN = 0.12  # Iets sneller weer kunnen springen (was 0.15)
KLIK_DUUR = 0.03  # Kortere input = snellere game reactie (was 0.05)
MARGE_BAND = 20  # Iets strakkere band (totaal 40px)

# --- ANKERS (Hoogte Bepaling) ---
BUFFER_PLAFOND = 90  # Blijf ruim onder de bovenste buis
BUFFER_VLOER = 30  # Blijf boven de onderste buis

print("--- DE VERREKIJKER ROBOT (MAXIMALE ANTICIPATIE) ---")
print("1. We kijken naar de eerstvolgende buis, ongeacht afstand.")
print("2. We corrigeren de hoogte DIRECT.")
print("3. Start het spel!")

time.sleep(1)

script_start_tijd = time.time()
last_jump_time = 0

with mss.mss() as sct:
    while True:
        loop_start = time.time()

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

        # 4. Vogel Opsporen
        vogel_x, vogel_y = 0, 0
        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours_vogel:
            c = max(contours_vogel, key=cv2.contourArea)
            if cv2.contourArea(c) > 50:
                x, y, w, h = cv2.boundingRect(c)
                center_x = x + w // 2
                center_y = y + h // 2

                # Correctie: Buik van de vogel is belangrijker dan het midden
                offset_naar_voren = 15
                vogel_x = center_x + offset_naar_voren
                vogel_y = center_y

                cv2.circle(img, (vogel_x, vogel_y), 5, (0, 0, 255), -1)

        # 5. Buizen Detectie
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)

            # Filter op grootte en positie
            if area > 200 and w > 15 and (y < 50 or y > midden_scherm):
                ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h, 'center_x': x + w // 2})

        ruwe_buizen.sort(key=lambda k: k['x'])

        # Kolommen bouwen
        kolommen = []
        for buis in ruwe_buizen:
            toegevoegd = False
            for kolom in kolommen:
                if abs(buis['center_x'] - kolom['gemiddelde_x']) < 50:
                    kolom['buizen'].append(buis)
                    # Update gemiddelden
                    kolom['gemiddelde_x'] = sum(b['center_x'] for b in kolom['buizen']) // len(kolom['buizen'])
                    kolom['start_x'] = min(kolom['start_x'], buis['x'])
                    kolom['max_w'] = max(kolom['max_w'], buis['w'])
                    toegevoegd = True
                    break
            if not toegevoegd:
                kolommen.append(
                    {'gemiddelde_x': buis['center_x'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

        # --------------------------------------------------------------------------------
        # 6. DE "VERREKIJKER" LOGICA
        # --------------------------------------------------------------------------------

        doel_gevonden = False
        target_kolom = None

        # STAP A: Zoek de dichtstbijzijnde kolom die RECHTS van de vogel is
        # We kijken naar de linkerkant van de buis (start_x) minus een kleine buffer
        # Zodat we ook reageren als we er vlak voor zitten.
        kandidaten = [k for k in kolommen if (k['start_x'] + k['max_w']) > vogel_x]

        if kandidaten:
            # Sorteer op afstand (dichtstbijzijnde eerst)
            kandidaten.sort(key=lambda k: k['start_x'])
            target_kolom = kandidaten[0]
            doel_gevonden = True

        # STAP B: Als we een doel hebben, berekenen we de hoogte
        if doel_gevonden and target_kolom and vogel_x > 0:

            # Welke buizen zitten er in deze kolom?
            buizen = target_kolom['buizen']
            buizen.sort(key=lambda b: b['y'])

            doel_y = 0

            # --- ANKER BEREKENING (Zelfde als vorig succesvol idee) ---
            if len(buizen) >= 2:
                # Beide buizen: Midden
                plafond = buizen[0]['bottom']
                vloer = buizen[-1]['y']
                doel_y = (plafond + vloer) // 2

            elif len(buizen) == 1:
                buis = buizen[0]
                if buis['y'] < midden_scherm:
                    # Alleen BOVEN: Blijf onder plafond anker
                    doel_y = buis['bottom'] + BUFFER_PLAFOND
                else:
                    # Alleen ONDER: Blijf boven vloer anker
                    doel_y = buis['y'] - BUFFER_VLOER

            # --- ZWAARTEKRACHT COMPENSATIE ---
            # Omdat we nu verder vooruit kijken, moeten we rekening houden met dat de vogel zakt terwijl hij vliegt.
            # We mikken daarom standaard IETS HOGER dan het echte midden.
            doel_y -= 10

            # De Veilige Band
            zone_boven = doel_y - MARGE_BAND
            zone_onder = doel_y + MARGE_BAND

            # Visualisatie (Teken lijn naar waar we heen willen)
            cv2.line(img, (vogel_x, vogel_y), (target_kolom['start_x'], int(doel_y)), (0, 255, 255), 2)
            cv2.line(img, (target_kolom['start_x'], zone_boven),
                     (target_kolom['start_x'] + target_kolom['max_w'], zone_boven), (0, 255, 0), 2)
            cv2.line(img, (target_kolom['start_x'], zone_onder),
                     (target_kolom['start_x'] + target_kolom['max_w'], zone_onder), (0, 255, 0), 2)

            # --- DE ACTIE ---
            # We kijken nu puur naar de HOOGTE. De afstand maakt niet meer uit (want we kijken al naar de juiste buis).

            if vogel_y > zone_onder:
                nu = time.time()
                if nu - last_jump_time > JUMP_COOLDOWN:

                    # EXTREEEM KORTE KLIK (Minimaliseer latency)
                    pyautogui.keyDown('space')
                    time.sleep(KLIK_DUUR)
                    pyautogui.keyUp('space')

                    last_jump_time = nu

                    cv2.putText(img, "TIK!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                else:
                    cv2.putText(img, "...", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        cv2.imshow('Robot Brein (Live)', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
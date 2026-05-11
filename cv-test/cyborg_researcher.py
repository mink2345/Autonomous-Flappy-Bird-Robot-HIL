import cv2
import numpy as np
import mss
import pyautogui
import time
import csv
import os

pyautogui.FAILSAFE = True

# ==============================================================================
# --- TEST PARAMETERS (DE EXPERIMENTEN) ---
EXTRA_ZAKKEN_TESTS = [15, 20, 25, 30]
MARGE_SPRONG_TESTS = [0, 5, 10]

EXPERIMENTEN = []
for ez in EXTRA_ZAKKEN_TESTS:
    for ms in MARGE_SPRONG_TESTS:
        EXPERIMENTEN.append({"EXTRA_ZAKKEN": ez, "MARGE_SPRONG": ms})

# ==============================================================================
# --- VASTE INSTELLINGEN (VAN SCRIPT 5) ---
MONITOR = {'top': 152, 'left': 118, 'width': 518, 'height': 696}
SPRONG_KRACHT = 93
VEILIGHEIDS_BUFFER = 15
VOGEL_MIN_GROOTTE = 50
VOGEL_OFFSET_X = 15
BUIS_MIN_AREA = 200
BUIS_MIN_BREEDTE = 15
BUIS_KERN_DIKTE = 2
GAP_SIZE = 140
KLIK_TIJD = 0.02
MIN_TIJD_TUSSEN_SPRONGEN = 0.10

KLEUR_VOGEL_LAAG = np.array([14, 50, 50])
KLEUR_VOGEL_HOOG = np.array([34, 255, 255])
KLEUR_BUIS_LAAG = np.array([40, 50, 50])
KLEUR_BUIS_HOOG = np.array([60, 255, 255])

# --- LOGICA VARIABELEN ---
huidig_exp_index = 0
poging_nummer = 1
laatste_sprong_tijd = 0
start_tijd_ronde = time.time()

# Nieuwe Dood-Detectie Variabelen
vorige_buis_x = -1
tijd_stilstand_start = 0


def log_resultaat(exp, tijd_overleefd):
    bestand_bestaat = os.path.isfile('test_logboek.csv')
    with open('test_logboek.csv', mode='a', newline='') as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(['Tijdstip', 'Poging', 'Extra Zakken', 'Marge Sprong', 'Overleefde Seconden'])
        writer.writerow([time.strftime("%H:%M:%S"), poging_nummer, exp['EXTRA_ZAKKEN'], exp['MARGE_SPRONG'],
                         round(tijd_overleefd, 1)])


print("--- DE VISUELE AUTO-ONDERZOEKER (VERBETERDE DOOD-DETECTIE) ---")

with mss.mss() as sct:
    while True:
        exp = EXPERIMENTEN[huidig_exp_index]
        EXTRA_ZAKKEN = exp['EXTRA_ZAKKEN']
        MARGE_SPRONG = exp['MARGE_SPRONG']

        screenshot = sct.grab(MONITOR)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        scherm_hoogte = img.shape[0]
        midden_scherm = scherm_hoogte // 2

        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)
        mask_buis = cv2.inRange(hsv, KLEUR_BUIS_LAAG, KLEUR_BUIS_HOOG)

        zwart_boven = int(scherm_hoogte * 0.1)
        zwart_onder = int(scherm_hoogte * 0.2)
        mask_vogel[0:zwart_boven, :] = 0
        mask_vogel[scherm_hoogte - zwart_onder:, :] = 0
        mask_buis[scherm_hoogte - zwart_onder:, :] = 0

        kernel = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=BUIS_KERN_DIKTE)
        kernel_lijm = np.ones((30, 5), np.uint8)
        mask_buis_dik = cv2.morphologyEx(mask_buis_dik, cv2.MORPH_CLOSE, kernel_lijm)

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

        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)
            in_top_zone = (y < 50)
            in_bodem_zone = (y > midden_scherm)
            if area > BUIS_MIN_AREA and (w > BUIS_MIN_BREEDTE) and (in_top_zone or in_bodem_zone):
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

        # --- NIEUWE DOOD-DETECTIE (BUIZEN STAAN STIL) ---
        is_dood = False
        if len(kolommen) > 0:
            huidige_buis_x = kolommen[0]['start_x']

            # Check of de buis op exact dezelfde plek staat (marge van 2 pixels voor rendering)
            if abs(huidige_buis_x - vorige_buis_x) <= 2:
                if tijd_stilstand_start == 0:
                    tijd_stilstand_start = time.time()
                elif time.time() - tijd_stilstand_start > 1.5:  # Als ze 1.5 seconde stilstaan: GAME OVER
                    is_dood = True
            else:
                tijd_stilstand_start = 0
                vorige_buis_x = huidige_buis_x

        if is_dood:
            tijd_overleefd = time.time() - start_tijd_ronde
            print(
                f"CRASH! Poging {poging_nummer} overleefde {round(tijd_overleefd, 1)} sec. (Instellingen: EZ={EXTRA_ZAKKEN}, MS={MARGE_SPRONG})")
            log_resultaat(exp, tijd_overleefd)

            # Herstart procedure
            time.sleep(1)
            pyautogui.press('space')
            time.sleep(0.5)
            pyautogui.press('space')
            time.sleep(1.5)  # Even wachten tot het nieuwe potje rolt

            # Reset alles
            tijd_stilstand_start = 0
            vorige_buis_x = -1
            poging_nummer += 1
            huidig_exp_index = (huidig_exp_index + 1) % len(EXPERIMENTEN)
            start_tijd_ronde = time.time()
            continue

        # --- WISKUNDE & ACTIE ---
        doel_gevonden = False
        for kolom in kolommen:
            buizen_in_kolom = kolom['buizen']
            boven_stukken = [b for b in buizen_in_kolom if b['y'] < midden_scherm]
            onder_stukken = [b for b in buizen_in_kolom if b['y'] >= midden_scherm]

            y_plafond = max((b['bottom'] for b in boven_stukken), default=0)
            y_vloer = min((b['y'] for b in onder_stukken), default=scherm_hoogte)
            plafond_gevaar = y_plafond if boven_stukken else 0

            if boven_stukken and not onder_stukken:
                y_vloer = y_plafond + GAP_SIZE
            elif onder_stukken and not boven_stukken:
                y_plafond = y_vloer - GAP_SIZE
                plafond_gevaar = 0

            gat_midden = (y_plafond + y_vloer) // 2 + EXTRA_ZAKKEN

            cv2.line(img, (kolom['start_x'], gat_midden), (kolom['start_x'] + kolom['max_w'], gat_midden),
                     (0, 255, 255), 2)
            cv2.rectangle(img, (kolom['start_x'], y_plafond), (kolom['start_x'] + kolom['max_w'], y_vloer),
                          (255, 0, 255), 2)

            if plafond_gevaar > 0:
                doodslijn = plafond_gevaar + VEILIGHEIDS_BUFFER
                cv2.line(img, (kolom['start_x'], doodslijn), (kolom['start_x'] + kolom['max_w'], doodslijn),
                         (0, 0, 255), 2)

            if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x):
                doel_gevonden = True
                cv2.line(img, (vogel_x, vogel_y), (kolom['gemiddelde_x'], gat_midden), (200, 200, 0), 1)

                if (vogel_y - gat_midden) > MARGE_SPRONG:
                    is_veilig = True if plafond_gevaar == 0 else (
                                vogel_top - SPRONG_KRACHT >= plafond_gevaar + VEILIGHEIDS_BUFFER)

                    if is_veilig:
                        nu = time.time()
                        if nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN:
                            pyautogui.keyDown('space')
                            time.sleep(KLIK_TIJD)
                            pyautogui.keyUp('space')
                            laatste_sprong_tijd = nu
                            cv2.putText(img, "JUMP!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                        (0, 255, 0), 2)
                    else:
                        cv2.putText(img, "BLOCKED!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                    (0, 0, 255), 2)

        # --- INFO HUD ---
        cv2.putText(img, f"Poging {poging_nummer} | Exp {huidig_exp_index + 1}/{len(EXPERIMENTEN)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(img, f"Zakken: {EXTRA_ZAKKEN} | Marge: {MARGE_SPRONG}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 2)
        tijd_nu = time.time() - start_tijd_ronde
        cv2.putText(img, f"Tijd in leven: {round(tijd_nu, 1)} sec", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 255, 0), 2)

        cv2.imshow('Robot Onderzoeker', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
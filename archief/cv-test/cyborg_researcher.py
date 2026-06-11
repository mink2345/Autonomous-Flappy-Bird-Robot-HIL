import cv2
import numpy as np
import mss
import pyautogui
import time
import csv
import os
from collections import deque

pyautogui.FAILSAFE = True

MAP_PAD = os.path.dirname(os.path.abspath(__file__))
LOG_BESTAND = os.path.join(MAP_PAD, 'black_box_log.csv')

MONITOR = {'top': 152, 'left': 118, 'width': 518, 'height': 696}

# ==============================================================================
# --- VASTE INSTELLINGEN (ANTI-PLAFOND + STABIELE BASIS) ---
SPRONG_KRACHT = 95
VEILIGHEIDS_BUFFER = 22  # OMHOOG: Dikkere helm tegen plafond-crashes
VOGEL_MIN_GROOTTE = 50
VOGEL_OFFSET_X = 50  # De afstand van het midden tot de 'Neus'
EXTRA_ZAKKEN = 20  # OMHOOG: Standaard lager in de buis mikken
MARGE_SPRONG = 0
MIN_TIJD_TUSSEN_SPRONGEN = 0.05
KLIK_TIJD = 0.02  # De robuuste 20ms klik
GAP_SIZE = 140

KLEUR_VOGEL_LAAG = np.array([14, 50, 50])
KLEUR_VOGEL_HOOG = np.array([34, 255, 255])
KLEUR_BUIS_LAAG = np.array([40, 50, 50])
KLEUR_BUIS_HOOG = np.array([60, 255, 255])

# --- LOGICA & BLACK BOX VARIABELEN ---
poging_nummer = 1
laatste_sprong_tijd = 0
start_tijd_ronde = time.time()
wacht_op_herstart = False

huidige_score = 0
laatste_doel_x = 999

# Het Tijdmachine-Geheugen (max 15 frames, ca. 0.5 seconden in het verleden)
vlucht_geheugen = deque(maxlen=15)

# Fallbacks voor als het geheugen leeg is
laatste_vogel_y = 0
laatste_buis_plafond = 0
laatste_buis_vloer = 0
laatste_buis_x = 0


def log_black_box(tijd_overleefd, score, v_y, b_x, b_plafond, b_vloer):
    bestand_bestaat = os.path.isfile(LOG_BESTAND)
    with open(LOG_BESTAND, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(
                ['Tijdstip', 'Poging', 'Score', 'Overleefde Sec', 'Vogel_Y', 'Buis_X', 'Plafond_Y', 'Vloer_Y',
                 'Analyse'])

        VOGEL_STRAAL = 15
        analyse = "Onbekend"

        if 130 < b_x < 170:
            analyse = "Voorkant buis geraakt (Te laat)"
        elif (v_y - VOGEL_STRAAL) <= b_plafond:
            analyse = "Bovenkant (Plafond) geraakt"
        elif (v_y + VOGEL_STRAAL) >= b_vloer:
            analyse = "Onderkant (Vloer) geraakt"
        else:
            analyse = "Crash tussen de buizen (Zijkant / Staart?)"

        writer.writerow(
            [time.strftime("%H:%M:%S"), poging_nummer, score, round(tijd_overleefd, 1), v_y, b_x, b_plafond, b_vloer,
             analyse])
        print(f"   -> GELOGD: Score {score} | Tijd {round(tijd_overleefd, 1)}s | Oorzaak: {analyse}")


print("--- CYBORG ROBOT GESTART ---")
print("- Druk op 'L' bij een crash om de Black Box (tijdmachine) uit te lezen.")
print("- Druk op 'SPATIE' om het potje te herstarten.")

with mss.mss() as sct:
    while True:
        screenshot = sct.grab(MONITOR)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        scherm_hoogte = img.shape[0]
        midden_scherm = scherm_hoogte // 2

        # --- TOETSENBORD INPUT ---
        toets = cv2.waitKey(1) & 0xFF
        if toets == ord('q'): break

        # --- PAUZE LOGICA ---
        if wacht_op_herstart:
            if toets == ord(' '):
                print(f"-> Start Poging {poging_nummer + 1}...")
                pyautogui.press('space')
                time.sleep(0.5)
                pyautogui.press('space')

                poging_nummer += 1
                start_tijd_ronde = time.time()
                huidige_score = 0
                laatste_doel_x = 999
                vlucht_geheugen.clear()  # Tijdmachine wissen voor de nieuwe ronde
                wacht_op_herstart = False
                continue

            cv2.putText(img, "GEPAUZEERD - DRUK OP SPATIE", (30, midden_scherm), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255), 2)
            cv2.imshow('Robot Brein', img)
            continue

        # --- DE TIJDMACHINE UITLEZEN BIJ EEN CRASH ---
        if toets == ord('l'):
            tijd_overleefd = time.time() - start_tijd_ronde
            print(f"\nCRASH! Poging {poging_nummer} voorbij.")

            if len(vlucht_geheugen) > 0:
                # Spoel de tape terug naar het oudste frame in het geheugen (~0.5s geleden)
                m = vlucht_geheugen[0]
                print("   -> Tijdmachine gebruikt: Data van vlak vóór de crash opgehaald.")
                log_black_box(tijd_overleefd, huidige_score, m['v_y'], m['b_x'], m['plafond'], m['vloer'])
            else:
                # Fallback als we heel snel crashen
                print("   -> Geen tijdmachine data, huidige data gebruikt.")
                log_black_box(tijd_overleefd, huidige_score, laatste_vogel_y, laatste_buis_x, laatste_buis_plafond,
                              laatste_buis_vloer)

            wacht_op_herstart = True
            continue

        # --- MASKERS & BUIZEN OPBOUWEN ---
        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)
        mask_buis = cv2.inRange(hsv, KLEUR_BUIS_LAAG, KLEUR_BUIS_HOOG)

        mask_vogel[0:int(scherm_hoogte * 0.1), :] = 0
        mask_vogel[int(scherm_hoogte * 0.8):, :] = 0
        mask_buis[int(scherm_hoogte * 0.8):, :] = 0

        kernel = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=2)
        kernel_lijm = np.ones((30, 5), np.uint8)
        mask_buis_dik = cv2.morphologyEx(mask_buis_dik, cv2.MORPH_CLOSE, kernel_lijm)

        # --- VOGEL DETECTIE (STAART & NEUS) ---
        vogel_neus_x, vogel_staart_x, vogel_y, vogel_top = 0, 0, 0, 0
        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours_vogel:
            c = max(contours_vogel, key=cv2.contourArea)
            if cv2.contourArea(c) > VOGEL_MIN_GROOTTE:
                x, y, w, h = cv2.boundingRect(c)
                vogel_neus_x = x + w // 2 + VOGEL_OFFSET_X  # Kijkt vooruit
                vogel_staart_x = x  # Absolute achterkant
                vogel_y = y + h // 2
                vogel_top = y
                laatste_vogel_y = vogel_y

                # Teken de visuele weergave van de vogel
                cv2.circle(img, (vogel_neus_x, vogel_y), 6, (255, 0, 0), -1)  # Blauwe Neus
                cv2.circle(img, (vogel_staart_x, vogel_y), 6, (0, 0, 255), -1)  # Rode Staart
                cv2.line(img, (vogel_staart_x, vogel_y), (vogel_neus_x, vogel_y), (255, 255, 255), 2)  # Vogel as

        # --- BUIZEN DETECTIE ---
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            x, y, w, h = cv2.boundingRect(c)
            if cv2.contourArea(c) > 200 and w > 15:
                if y < 50 or y > midden_scherm:
                    ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h, 'cx': x + w // 2})

        ruwe_buizen.sort(key=lambda k: k['x'])
        kolommen = []
        for buis in ruwe_buizen:
            toegevoegd = False
            for k in kolommen:
                if abs(buis['cx'] - k['gem_x']) < 50:
                    k['buizen'].append(buis)
                    k['gem_x'] = sum(b['cx'] for b in k['buizen']) // len(k['buizen'])
                    k['start_x'] = min(k['start_x'], buis['x'])
                    k['max_w'] = max(k['max_w'], buis['w'])
                    toegevoegd = True
                    break
            if not toegevoegd:
                kolommen.append({'gem_x': buis['cx'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

        # --- ACTIE LOGICA ---
        doel_gevonden = False
        for k in kolommen:
            b_in_k = k['buizen']
            y_plafond = max((b['bottom'] for b in b_in_k if b['y'] < midden_scherm), default=0)
            y_vloer = min((b['y'] for b in b_in_k if b['y'] >= midden_scherm), default=scherm_hoogte)

            if y_plafond > 0 and y_vloer == scherm_hoogte:
                y_vloer = y_plafond + GAP_SIZE
            elif y_vloer < scherm_hoogte and y_plafond == 0:
                y_plafond = y_vloer - GAP_SIZE

            gat_midden = (y_plafond + y_vloer) // 2 + EXTRA_ZAKKEN

            cv2.line(img, (k['start_x'], gat_midden), (k['start_x'] + k['max_w'], gat_midden), (0, 255, 255), 2)
            cv2.rectangle(img, (k['start_x'], y_plafond), (k['start_x'] + k['max_w'], y_vloer), (255, 0, 255), 2)

            # Check of de STAART nog in deze buis hangt
            staart_gevaar = 0
            if k['start_x'] < vogel_staart_x < (k['start_x'] + k['max_w']):
                staart_gevaar = y_plafond
                if staart_gevaar > 0:
                    cv2.line(img, (vogel_staart_x, staart_gevaar + VEILIGHEIDS_BUFFER),
                             (vogel_neus_x, staart_gevaar + VEILIGHEIDS_BUFFER), (0, 0, 255), 2)

            # De NEUS zoekt het volgende gat
            if not doel_gevonden and vogel_neus_x > 0 and (k['start_x'] + k['max_w'] + 40 > vogel_neus_x):
                doel_gevonden = True

                # Sla dit moment op in de Tijdmachine
                vlucht_geheugen.append({
                    'v_y': vogel_y,
                    'b_x': k['start_x'],
                    'plafond': y_plafond,
                    'vloer': y_vloer
                })

                # Fallback data
                laatste_buis_x, laatste_buis_plafond, laatste_buis_vloer = k['start_x'], y_plafond, y_vloer

                # Score update
                if k['start_x'] > laatste_doel_x + 50:
                    huidige_score += 1
                laatste_doel_x = k['start_x']

                # 1. Willen we springen op basis van de NEUS?
                if (vogel_y - gat_midden) > MARGE_SPRONG:

                    # 2. Mogen we springen? Check NEUS plafond én STAART plafond
                    hoofd_na_sprong = vogel_top - SPRONG_KRACHT
                    is_veilig = True

                    if y_plafond > 0 and hoofd_na_sprong < (y_plafond + VEILIGHEIDS_BUFFER):
                        is_veilig = False
                    if staart_gevaar > 0 and hoofd_na_sprong < (staart_gevaar + VEILIGHEIDS_BUFFER):
                        is_veilig = False

                    if is_veilig:
                        nu = time.time()
                        if nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN:
                            # De strakke "90-score" manier van klikken
                            pyautogui.keyDown('space')
                            time.sleep(KLIK_TIJD)
                            pyautogui.keyUp('space')
                            laatste_sprong_tijd = nu
                            cv2.putText(img, "JUMP!", (vogel_neus_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                        (0, 255, 0), 2)
                    else:
                        cv2.putText(img, "BLOCKED", (vogel_neus_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (0, 0, 255), 2)

        # --- HUD INFORMATIE ---
        tijd_nu = time.time() - start_tijd_ronde
        cv2.putText(img, f"Poging {poging_nummer} | Tijd: {round(tijd_nu, 1)}s | SCORE: {huidige_score}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow('Robot Brein', img)

cv2.destroyAllWindows()
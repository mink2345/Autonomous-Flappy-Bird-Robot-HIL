import cv2
import numpy as np
import time
import csv
import os
import json
from collections import deque
from picamera2 import Picamera2
from gpiozero import LED

#the scripts that will run everything

# ==============================================================================
# --- 0. MAPPEN & BESTANDEN SETUP ---
MAP_PAD = os.path.dirname(os.path.abspath(__file__))
LOG_MAP = os.path.join(MAP_PAD, 'vlucht_logs')

if not os.path.exists(LOG_MAP):
    os.makedirs(LOG_MAP)

tijd_str = time.strftime("%Y%m%d_%H%M%S")
VIDEO_BESTAND = os.path.join(LOG_MAP, f'video_{tijd_str}.avi')
CSV_BESTAND = os.path.join(LOG_MAP, f'log_{tijd_str}.csv')

# ==============================================================================
# --- 1. STANDAARD VARIABELEN (Fallback als JSON mist) ---
SPEELVELD_TOP, SPEELVELD_BODEM = 350, 880
SPEELVELD_LINKS, SPEELVELD_RECHTS = 20, 1025
VOGEL_SCAN_LINKS, VOGEL_SCAN_RECHTS = 20, 140
VOGEL_MIN_GROOTTE, GAP_SIZE = 15, 140

VOGEL_OFFSET_X = 50
MARGE_SPRONG = -35
EXTRA_ZAKKEN = 20
SPRONG_KRACHT = 95
VEILIGHEIDS_BUFFER = 22

BODEM_REDDING_Y = 760

KLIK_TIJD = 0.15
MIN_TIJD_TUSSEN_SPRONGEN = 0.18

KLEUR_VOGEL_LAAG = np.array([85, 120, 120])
KLEUR_VOGEL_HOOG = np.array([115, 255, 255])
KLEUR_BUIS_LAAG1 = np.array([0, 70, 50])
KLEUR_BUIS_HOOG1 = np.array([22, 255, 255])
KLEUR_BUIS_LAAG2 = np.array([160, 70, 50])
KLEUR_BUIS_HOOG2 = np.array([180, 255, 255])

# ==============================================================================
# --- 2. HARDWARE & STATUS SETUP ---
solenoid = LED(18)
solenoid_is_aan = False
solenoid_start_tijd = 0
laatste_sprong_tijd = 0
start_tijd_ronde = time.time()
poging_nummer = 1
huidige_score = 0
laatste_doel_x = 999
vlucht_geheugen = deque(maxlen=15)


# ==============================================================================
# --- 3. DE BLACK BOX LOGGER ---
def log_black_box(tijd_overleefd, score, v_y, b_x, b_plafond, b_vloer, actie="Crash / Gestopt"):
    bestand_bestaat = os.path.isfile(CSV_BESTAND)
    with open(CSV_BESTAND, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(
                ['Tijdstip', 'Poging', 'Score', 'Overleefde Sec', 'Vogel_Y', 'Buis_X', 'Plafond_Y', 'Vloer_Y',
                 'Analyse'])
        writer.writerow(
            [time.strftime("%H:%M:%S"), poging_nummer, score, round(tijd_overleefd, 1), v_y, b_x, b_plafond, b_vloer,
             actie])
        print(f"   -> [BLACK BOX] Opgeslagen in {CSV_BESTAND} | Oorzaak: {actie}")


# ==============================================================================
# --- 4. START SYSTEMEN ---
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(VIDEO_BESTAND, fourcc, 20.0, (1080, 1440))

print("Camera & Cyborg-systeem opstarten...")
picam2 = Picamera2()
config_cam = picam2.create_preview_configuration(main={"size": (1440, 1080)})
picam2.configure(config_cam)
picam2.start()
print(f"LIVE! Video slaat op als: {VIDEO_BESTAND}")
print("Druk op 'CTRL + C' om te stoppen en de log op te maken.")

try:
    while True:
        nu = time.time()

        # --- LIVE CONFIG INLEZEN ---
        try:
            with open('config.json', 'r') as f:
                settings = json.load(f)
                SPEELVELD_TOP = settings.get('SPEELVELD_TOP', SPEELVELD_TOP)
                SPEELVELD_BODEM = settings.get('SPEELVELD_BODEM', SPEELVELD_BODEM)
                SPEELVELD_LINKS = settings.get('SPEELVELD_LINKS', SPEELVELD_LINKS)
                SPEELVELD_RECHTS = settings.get('SPEELVELD_RECHTS', SPEELVELD_RECHTS)
                VOGEL_SCAN_LINKS = settings.get('VOGEL_SCAN_LINKS', VOGEL_SCAN_LINKS)
                VOGEL_SCAN_RECHTS = settings.get('VOGEL_SCAN_RECHTS', VOGEL_SCAN_RECHTS)
                VOGEL_MIN_GROOTTE = settings.get('VOGEL_MIN_GROOTTE', VOGEL_MIN_GROOTTE)
                GAP_SIZE = settings.get('GAP_SIZE', GAP_SIZE)

                VOGEL_OFFSET_X = settings.get('VOGEL_OFFSET_X', VOGEL_OFFSET_X)
                MARGE_SPRONG = settings.get('MARGE_SPRONG', MARGE_SPRONG)
                EXTRA_ZAKKEN = settings.get('EXTRA_ZAKKEN', EXTRA_ZAKKEN)
                SPRONG_KRACHT = settings.get('SPRONG_KRACHT', SPRONG_KRACHT)
                VEILIGHEIDS_BUFFER = settings.get('VEILIGHEIDS_BUFFER', VEILIGHEIDS_BUFFER)

                BODEM_REDDING_Y = settings.get('BODEM_REDDING_Y', BODEM_REDDING_Y)

                KLIK_TIJD = settings.get('KLIK_TIJD', KLIK_TIJD)
                MIN_TIJD_TUSSEN_SPRONGEN = settings.get('MIN_TIJD_TUSSEN_SPRONGEN', MIN_TIJD_TUSSEN_SPRONGEN)
        except Exception:
            pass

        MIDDEN_VELD = (SPEELVELD_TOP + SPEELVELD_BODEM) // 2

        # --- NON-BLOCKING SOLENOID ---
        if solenoid_is_aan and (nu - solenoid_start_tijd >= KLIK_TIJD):
            solenoid.off()
            solenoid_is_aan = False

        # --- BEELD BINNENHALEN ---
        frame = picam2.capture_array()
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        cv2.rectangle(img, (SPEELVELD_LINKS, SPEELVELD_TOP), (SPEELVELD_RECHTS, SPEELVELD_BODEM), (200, 200, 200), 1)

        # Teken de absolute dodenlijn voor de vloer (Oranje lijn)
        cv2.line(img, (SPEELVELD_LINKS, BODEM_REDDING_Y), (SPEELVELD_RECHTS, BODEM_REDDING_Y), (0, 165, 255), 2)

        # --- MASKERS ---
        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)
        mask_buis1 = cv2.inRange(hsv, KLEUR_BUIS_LAAG1, KLEUR_BUIS_HOOG1)
        mask_buis2 = cv2.inRange(hsv, KLEUR_BUIS_LAAG2, KLEUR_BUIS_HOOG2)
        mask_buis = cv2.bitwise_or(mask_buis1, mask_buis2)

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

        # --- VOGEL DETECTIE ---
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

            hoofd_na_sprong = vogel_top - SPRONG_KRACHT
            cv2.circle(img, (vogel_neus_x, hoofd_na_sprong), 8, (255, 255, 255), 2)
            cv2.line(img, (vogel_neus_x, vogel_y), (vogel_neus_x, hoofd_na_sprong), (255, 255, 255), 1)

        # --- BUIZEN DETECTIE ---
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            x, y, w, h = cv2.boundingRect(c)
            raakt_rand = (x + w) > (SPEELVELD_RECHTS - 15) or x < (SPEELVELD_LINKS + 15)
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

        # --- LOGICA BEREKENINGEN ---
        doel_gevonden = False
        pipe_jump = False
        actuele_y_plafond = SPEELVELD_TOP
        floor_save_jump = False

        # 1. Buis-logica
        for k in kolommen:
            b_in_k = k['buizen']
            y_plafond = max((b['bottom'] for b in b_in_k if b['y'] < MIDDEN_VELD), default=SPEELVELD_TOP)
            y_vloer = min((b['y'] for b in b_in_k if b['y'] >= MIDDEN_VELD), default=SPEELVELD_BODEM)

            if y_plafond > SPEELVELD_TOP and y_vloer == SPEELVELD_BODEM:
                y_vloer = y_plafond + GAP_SIZE
            elif y_vloer < SPEELVELD_BODEM and y_plafond == SPEELVELD_TOP:
                y_plafond = y_vloer - GAP_SIZE

            gat_midden = (y_plafond + y_vloer) // 2 + EXTRA_ZAKKEN

            cv2.rectangle(img, (k['start_x'], y_plafond), (k['start_x'] + k['max_w'], y_vloer), (0, 200, 0), 2)
            cv2.line(img, (k['start_x'], gat_midden), (k['start_x'] + k['max_w'], gat_midden), (0, 255, 255), 1)

            if not doel_gevonden and vogel_neus_x > 0 and (k['start_x'] + k['max_w'] + 40 > vogel_neus_x):
                doel_gevonden = True
                actuele_y_plafond = y_plafond

                vlucht_geheugen.append({
                    'v_y': vogel_y,
                    'b_x': k['start_x'],
                    'plafond': y_plafond,
                    'vloer': y_vloer
                })

                if k['start_x'] > laatste_doel_x + 50:
                    huidige_score += 1
                laatste_doel_x = k['start_x']

                cv2.line(img, (vogel_neus_x, y_plafond + VEILIGHEIDS_BUFFER),
                         (k['start_x'], y_plafond + VEILIGHEIDS_BUFFER), (0, 0, 255), 2)

                if (vogel_y - gat_midden) > MARGE_SPRONG:
                    pipe_jump = True

        # 2. Vloer-Noodrem (werkt altijd, ook als er géén buizen zijn!)
        if vogel_y > 0 and vogel_y >= BODEM_REDDING_Y:
            floor_save_jump = True
            cv2.putText(img, "FLOOR SAVE!", (vogel_neus_x, vogel_y - 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)

        # --- JUMP EXECUTIE ---
        if pipe_jump or floor_save_jump:
            hoofd_na_sprong = vogel_top - SPRONG_KRACHT
            is_veilig = (hoofd_na_sprong >= (actuele_y_plafond + VEILIGHEIDS_BUFFER))

            # Springen als de buis het toelaat, OF als we een noodlanding op de vloer maken (dan negeren we Ghost Bird tijdelijk)
            if is_veilig or floor_save_jump:
                if (nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN) and not solenoid_is_aan:
                    solenoid.on()
                    solenoid_is_aan = True
                    solenoid_start_tijd = nu
                    laatste_sprong_tijd = nu
                    cv2.putText(img, "JUMP!", (vogel_neus_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            else:
                cv2.putText(img, "BLOCKED", (vogel_neus_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Toon HUD
        tijd_nu = time.time() - start_tijd_ronde
        cv2.putText(img, f"Tijd: {round(tijd_nu, 1)}s | SCORE: {huidige_score}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 255), 3)
        cv2.putText(img, f"Offset: {VOGEL_OFFSET_X} | Marge: {MARGE_SPRONG} | Nood-Y: {BODEM_REDDING_Y}", (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

        if solenoid_is_aan:
            cv2.circle(img, (800, 50), 20, (0, 255, 0), -1)

        out.write(img)

except KeyboardInterrupt:
    print("\nScript handmatig gestopt (CTRL+C).")
    tijd_overleefd = time.time() - start_tijd_ronde
    if len(vlucht_geheugen) > 0:
        m = vlucht_geheugen[-1]
        log_black_box(tijd_overleefd, huidige_score, m['v_y'], m['b_x'], m['plafond'], m['vloer'])
    else:
        log_black_box(tijd_overleefd, huidige_score, 0, 0, 0, 0, "Geen data")

finally:
    solenoid.off()
    out.release()
    picam2.stop()
    print(f"Data opgeslagen in {LOG_MAP}/")
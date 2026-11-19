import cv2
import numpy as np
import time
import csv
import os
from picamera2 import Picamera2
from gpiozero import LED

# script to see what what happens on a click and getting some variables

# ==============================================================================
# --- INSTELLINGEN (Pas INTERVAL aan om varianten te testen) ---
# ==============================================================================
KLIK_TIJD = 0.12
INTERVAL_TUSSEN_KLIKS = 0.45  # Test bijv. 0.35, 0.45, 0.55
TEST_DUUR = 3.0  # Aantal seconden meten (voor de eerste buis)
AFTEL_SECONDEN = 3

# Exact zelfde speelveld/scan-gebied als live_test.py
SPEELVELD_TOP, SPEELVELD_BODEM = 350, 880
VOGEL_SCAN_LINKS, VOGEL_SCAN_RECHTS = 20, 140
VOGEL_MIN_GROOTTE = 15

KLEUR_VOGEL_LAAG = np.array([85, 120, 120])
KLEUR_VOGEL_HOOG = np.array([115, 255, 255])

# ==============================================================================
# --- 1. HARDWARE STARTEN ---
# ==============================================================================
solenoid = LED(18)
picam2 = Picamera2()
config_cam = picam2.create_preview_configuration(main={"size": (1440, 1080)})
picam2.configure(config_cam)
picam2.start()
time.sleep(1.0)  # Camera even laten stabiliseren

print(f"\nKalibratie klaar (Interval: {INTERVAL_TUSSEN_KLIKS}s | Klik: {KLIK_TIJD}s)")
print("Zet het spel klaar. Tik op START bij '1' en haal je hand direct weg!")

for i in range(AFTEL_SECONDEN, 0, -1):
    print(f"  {i}...")
    time.sleep(1.0)
print("  GO! Meting loopt...")

# ==============================================================================
# --- 2. DATA OPNEMEN ---
# ==============================================================================
data = []  # Lijst van dicts: {'t': sec, 'y': int, 'klik': bool}
start_test = time.time()
volgende_klik = 0.10  # Eerste klik bijna direct zodat hij niet crasht
solenoid_is_aan = False
solenoid_start = 0

try:
    while True:
        nu = time.time()
        t_rel = nu - start_test
        if t_rel >= TEST_DUUR:
            break

        # Solenoid uitzetten na KLIK_TIJD
        if solenoid_is_aan and (nu - solenoid_start >= KLIK_TIJD):
            solenoid.off()
            solenoid_is_aan = False

        # Solenoid aanzetten op het vaste ritme
        klik_nu = False
        if t_rel >= volgende_klik and not solenoid_is_aan:
            solenoid.on()
            solenoid_is_aan = True
            solenoid_start = nu
            volgende_klik += INTERVAL_TUSSEN_KLIKS
            klik_nu = True

        # Frame verwerken
        frame = picam2.capture_array()
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)
        mask_vogel[0:SPEELVELD_TOP, :] = 0
        mask_vogel[SPEELVELD_BODEM:, :] = 0
        mask_vogel[:, :VOGEL_SCAN_LINKS] = 0
        mask_vogel[:, VOGEL_SCAN_RECHTS:] = 0

        contours, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        geldige = [c for c in contours if VOGEL_MIN_GROOTTE < cv2.contourArea(c) < 800]

        vogel_y = -1
        if geldige:
            c = max(geldige, key=cv2.contourArea)
            _, y, _, h = cv2.boundingRect(c)
            vogel_y = y + h // 2

        data.append({'t': round(t_rel, 4), 'y': vogel_y, 'klik': klik_nu})

finally:
    solenoid.off()
    picam2.stop()

# ==============================================================================
# --- 3. OPSLAAN & ANALYSEREN ---
# ==============================================================================
csv_pad = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kalibratie_data.csv')
with open(csv_pad, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['t', 'y', 'klik'])
    writer.writeheader()
    writer.writerows(data)

# Alleen frames waar de vogel zichtbaar was
geldige_data = [d for d in data if d['y'] != -1]
klik_tijden = [d['t'] for d in data if d['klik']]

print(f"\n=== ANALYSE ({len(geldige_data)} frames, {len(klik_tijden)} kliks) ===")

vertragingen = []
sprongen = []
valsnelheden = []

for idx, t_klik in enumerate(klik_tijden):
    t_eind = klik_tijden[idx + 1] if idx + 1 < len(klik_tijden) else TEST_DUUR
    segment = [d for d in geldige_data if t_klik <= d['t'] < t_eind]

    if len(segment) < 4:
        print(f"Klik {idx + 1} ({t_klik:.2f}s): Te weinig beelddata.")
        continue

    # 1. Zoek het laagste punt (hoogste Y) kort na de klik = het echte keerpunt
    dal = max(segment[:max(1, len(segment) // 2)], key=lambda d: d['y'])

    # 2. Zoek de piek (laagste Y) NA dat keerpunt
    na_dal = [d for d in segment if d['t'] >= dal['t']]
    if len(na_dal) < 2:
        continue
    piek = min(na_dal, key=lambda d: d['y'])

    sprong_px = dal['y'] - piek['y']
    vertraging_ms = (dal['t'] - t_klik) * 1000

    # Check of de tik echt geregistreerd is (minimaal 15 px gestegen)
    if sprong_px < 15:
        print(f"Klik {idx + 1} ({t_klik:.2f}s): MISLUKT / niet geregistreerd (stijging: {sprong_px} px)")
        continue

    vertragingen.append(vertraging_ms)
    sprongen.append(sprong_px)

    # 3. Valsnelheid meten na de piek tot einde segment
    na_piek = [d for d in na_dal if d['t'] >= piek['t']]
    val_str = "n.v.t."
    if len(na_piek) >= 2:
        eind_val = na_piek[-1]
        dt_val = eind_val['t'] - piek['t']
        dy_val = eind_val['y'] - piek['y']
        if dt_val > 0.05 and dy_val > 5:
            v_val = dy_val / dt_val
            valsnelheden.append(v_val)
            val_str = f"{round(v_val)} px/s"

    print(
        f"Klik {idx + 1} ({t_klik:.2f}s): Vertraging = {round(vertraging_ms)} ms | Sprong = {sprong_px} px | Val = {val_str}")

print("\n=== GEMIDDELDEN ===")
if sprongen:
    print(f"Gem. Vertraging : {round(sum(vertragingen) / len(vertragingen))} ms")
    print(f"Gem. Sprong     : {round(sum(sprongen) / len(sprongen))} px  --> voor SPRONG_KRACHT")
if valsnelheden:
    print(f"Gem. Valsnelheid: {round(sum(valsnelheden) / len(valsnelheden))} px/s")
print(f"Ruwe data opgeslagen in: {csv_pad}")
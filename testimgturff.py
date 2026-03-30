import cv2
import numpy as np

# 1. LAAD HET PLAATJE
img = cv2.imread('turffimg.jpeg')  # Zorg dat dit de goede naam is!

if img is None:
    print("Kan plaatje niet vinden!")
    exit()

# MAAK HET PLAATJE KLEINER
schaal = 0.4
breedte = int(img.shape[1] * schaal)
hoogte = int(img.shape[0] * schaal)
img = cv2.resize(img, (breedte, hoogte))

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
scherm_hoogte = img.shape[0]
midden_scherm = scherm_hoogte // 2

# --- STAP 1: KLEUREN & MASKERS ---

# VOGEL (Wit/Blauwig) - Zoals gemeten
onder_vogel = np.array([90, 40, 180])
boven_vogel = np.array([140, 160, 255])

# BUIZEN (Oranje/Rood)
onder_buis = np.array([155, 60, 100])
boven_buis = np.array([180, 255, 255])

mask_vogel = cv2.inRange(hsv, onder_vogel, boven_vogel)
mask_buis = cv2.inRange(hsv, onder_buis, boven_buis)

# --- CRUCIALE FIX: DE VLOER VERWIJDEREN ---
# 1. We zetten de onderste 25% van het scherm op zwart (negeren)
zwart_grens = int(scherm_hoogte * 0.75)
mask_buis[zwart_grens:, :] = 0
mask_vogel[zwart_grens:, :] = 0  # Vogel komt daar ook nooit

# Maak de buizen weer "heel"
kernel = np.ones((5, 5), np.uint8)
mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=2)

# --- STAP 2: VOGEL ZOEKEN ---
contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
vogel_x, vogel_y = 0, 0

if contours_vogel:
    c = max(contours_vogel, key=cv2.contourArea)
    if cv2.contourArea(c) > 10:
        x, y, w, h = cv2.boundingRect(c)
        vogel_x = x + w // 2
        vogel_y = y + h // 2
        cv2.circle(img, (vogel_x, vogel_y), 8, (255, 0, 0), -1)  # Blauwe stip

# --- STAP 3: BUIZEN & KOLOMMEN (MET FILTER) ---
contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
ruwe_buizen = []

for c in contours_buis:
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)

    # FILTER 1: Groot genoeg?
    # FILTER 2: Is het STAAND? (Hoogte > Breedte). De vloer is liggend, dus die valt af.
    if area > 100 and h > w:
        ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h})

ruwe_buizen.sort(key=lambda k: k['x'])

# Groeperen
kolommen = []
for buis in ruwe_buizen:
    toegevoegd = False
    for kolom in kolommen:
        if abs(buis['x'] - kolom['center_x']) < 30:
            kolom['buizen'].append(buis)
            kolom['center_x'] = (kolom['center_x'] + buis['x']) // 2
            kolom['start_x'] = min(kolom['start_x'], buis['x'])
            kolom['max_w'] = max(kolom['max_w'], buis['w'])
            toegevoegd = True
            break
    if not toegevoegd:
        kolommen.append({'center_x': buis['x'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

# --- STAP 4: ALLEEN HET DOEL BEPALEN ---
target_kolom = None

# We zoeken de EERSTE kolom die rechts van de vogel zit
for kolom in kolommen:
    # Is de rechterkant van de buis voorbij de vogel?
    if (kolom['start_x'] + kolom['max_w']) > vogel_x:
        target_kolom = kolom
        break  # Gevonden! Stop met zoeken, negeer de rest.

# --- STAP 5: TEKENEN EN BESLISSEN ---
if target_kolom:
    # Teken alleen de actieve buis
    for b in target_kolom['buizen']:
        cv2.rectangle(img, (b['x'], b['y']), (b['x'] + b['w'], b['bottom']), (0, 255, 0), 2)

    # Bereken gat
    buizen = target_kolom['buizen']
    buizen.sort(key=lambda b: b['y'])

    y_plafond = 0
    y_vloer = scherm_hoogte

    if len(buizen) >= 2:
        y_plafond = buizen[0]['bottom']
        y_vloer = buizen[-1]['y']
    elif len(buizen) == 1:
        if buizen[0]['y'] < midden_scherm:
            y_plafond = buizen[0]['bottom']
        else:
            y_vloer = buizen[0]['y']

    gat_midden = (y_plafond + y_vloer) // 2

    # Teken het doel
    cv2.line(img, (target_kolom['start_x'], int(y_plafond)),
             (target_kolom['start_x'] + target_kolom['max_w'], int(y_plafond)), (0, 0, 255), 2)  # Rood plafond
    cv2.line(img, (target_kolom['start_x'], int(y_vloer)),
             (target_kolom['start_x'] + target_kolom['max_w'], int(y_vloer)), (0, 0, 255), 2)  # Rode vloer

    # Lijn van vogel naar doel
    if vogel_x > 0:
        cv2.line(img, (vogel_x, vogel_y), (target_kolom['center_x'], gat_midden), (0, 255, 255), 2)
        cv2.circle(img, (target_kolom['center_x'], gat_midden), 5, (0, 255, 255), -1)

        # Simpele actie check
        tekst = "MOOI"
        kleur = (255, 255, 0)
        if vogel_y > gat_midden + 10:
            tekst = "TIK!"
            kleur = (0, 0, 255)
        elif vogel_y < gat_midden - 10:
            tekst = "Zakken"
            kleur = (0, 255, 0)

        cv2.putText(img, tekst, (target_kolom['start_x'], gat_midden), cv2.FONT_HERSHEY_SIMPLEX, 0.8, kleur, 2)
else:
    cv2.putText(img, "GEEN DOEL (VLUCHT VRIJ)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

cv2.imshow('Resultaat - Schoon', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
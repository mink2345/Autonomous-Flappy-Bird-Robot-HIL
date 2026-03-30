import cv2
import numpy as np

# 1. Laad het plaatje
img = cv2.imread('flappytest2.png')

if img is None:
    print("Kan plaatje niet vinden!")
    exit()

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
scherm_hoogte = img.shape[0]
scherm_breedte = img.shape[1]

# --- STAP 1: KLEUREN & MASKERS ---
onder_vogel = np.array([14, 50, 50])
boven_vogel = np.array([34, 255, 255])
onder_buis = np.array([40, 50, 50])
boven_buis = np.array([60, 255, 255])

mask_vogel = cv2.inRange(hsv, onder_vogel, boven_vogel)
mask_buis = cv2.inRange(hsv, onder_buis, boven_buis)

# Clean-up
zwart_boven = int(scherm_hoogte * 0.1)
zwart_onder = int(scherm_hoogte * 0.85)
mask_vogel[0:zwart_boven, :] = 0
mask_vogel[zwart_onder:, :] = 0
mask_buis[zwart_onder:, :] = 0

kernel = np.ones((5, 5), np.uint8)
mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=2)

# --- STAP 2: VOGEL ---
contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
vogel_x, vogel_y = 0, 0

if contours_vogel:
    c = max(contours_vogel, key=cv2.contourArea)
    if cv2.contourArea(c) > 50:
        x, y, w, h = cv2.boundingRect(c)
        vogel_x = x + w // 2
        vogel_y = y + h // 2
        cv2.circle(img, (vogel_x, vogel_y), 15, (0, 0, 255), -1)

# --- STAP 3: BUIZEN & KOLOMMEN ---
contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
ruwe_buizen = []

for c in contours_buis:
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)
    if area > 500 and w > 30:
        ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h})

ruwe_buizen.sort(key=lambda k: k['x'])

kolommen = []
for buis in ruwe_buizen:
    toegevoegd = False
    for kolom in kolommen:
        if abs(buis['x'] - kolom['center_x']) < 50:
            kolom['buizen'].append(buis)
            kolom['center_x'] = (kolom['center_x'] + buis['x']) // 2
            kolom['start_x'] = min(kolom['start_x'], buis['x'])
            kolom['max_w'] = max(kolom['max_w'], buis['w'])
            toegevoegd = True
            break
    if not toegevoegd:
        kolommen.append({'center_x': buis['x'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

# --- STAP 4: HET GAT (SIMPELE LOGICA) ---
doel_gevonden = False

for kolom in kolommen:
    buizen = kolom['buizen']

    # 1. Sorteer buizen op Y (De bovenste staat nu vooraan in de lijst)
    buizen.sort(key=lambda b: b['y'])

    y_plafond = 0
    y_vloer = scherm_hoogte

    # Als we > 1 buis hebben, is de eerste de bovenste en de laatste de onderste
    if len(buizen) >= 2:
        bovenste = buizen[0]
        onderste = buizen[-1]

        y_plafond = bovenste['bottom']  # Onderkant van de bovenste
        y_vloer = onderste['y']  # Bovenkant van de onderste

    # Als we maar 1 buis zien...
    elif len(buizen) == 1:
        enige = buizen[0]
        if enige['y'] < 100:  # Hangt aan plafond
            y_plafond = enige['bottom']
        else:  # Staat op grond
            y_vloer = enige['y']

    gat_midden = (y_plafond + y_vloer) // 2

    # Teken Paarse doos (Het gat)
    cv2.rectangle(img, (kolom['start_x'], y_plafond), (kolom['start_x'] + kolom['max_w'], y_vloer), (255, 0, 255), 2)

    # Teken Groene doos (De buizen)
    for b in buizen:
        cv2.rectangle(img, (b['x'], b['y']), (b['x'] + b['w'], b['bottom']), (0, 255, 0), 2)

    # Lijn trekken
    if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x):
        doel_gevonden = True

        cv2.line(img, (vogel_x, vogel_y), (kolom['center_x'], gat_midden), (0, 255, 255), 3)
        cv2.circle(img, (kolom['center_x'], gat_midden), 8, (0, 255, 255), -1)

        actie = "Mooi"
        if vogel_y > gat_midden + 15:
            actie = "TIK!"
        elif vogel_y < gat_midden - 15:
            actie = "Zakken"

        cv2.putText(img, actie, (kolom['start_x'], gat_midden), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        print(f"Plafond: {y_plafond}, Vloer: {y_vloer}, Midden: {gat_midden}")

cv2.imshow('Resultaat - Paars is Gat', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
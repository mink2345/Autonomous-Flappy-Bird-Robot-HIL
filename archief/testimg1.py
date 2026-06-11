import cv2
import numpy as np

img = cv2.imread('../assets/flappy_test.jpg')  # Of je screenshot

if img is None:
    print("Kan plaatje niet vinden!")
    exit()

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
scherm_hoogte = img.shape[0]
midden_scherm = scherm_hoogte // 2

# --- DEEL 1: DE VOGEL ---
ondergrens_oranje = np.array([0, 80, 80])
bovengrens_oranje = np.array([35, 255, 255])
masker_vogel = cv2.inRange(hsv, ondergrens_oranje, bovengrens_oranje)
contours_vogel, _ = cv2.findContours(masker_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

vogel_y = 0
vogel_x = 0

if contours_vogel:
    c = max(contours_vogel, key=cv2.contourArea)
    if cv2.contourArea(c) > 100:
        x, y, w, h = cv2.boundingRect(c)
        vogel_x = x + w // 2
        vogel_y = y + h // 2
        cv2.circle(img, (vogel_x, vogel_y), w // 2, (255, 0, 0), 2)

# --- DEEL 2: BUIZEN FILTEREN EN GROEPEREN ---
ondergrens_groen = np.array([40, 100, 50])
bovengrens_groen = np.array([90, 255, 255])
masker_buizen = cv2.inRange(hsv, ondergrens_groen, bovengrens_groen)
contours_buizen, _ = cv2.findContours(masker_buizen, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

# 1. Filter op breedte (> 125)
echte_buizen = []
for c in contours_buizen:
    x, y, w, h = cv2.boundingRect(c)
    # LET OP: Als een buis aan de rechterrand zit, is hij misschien afgesneden en smaller.
    # We voegen een extra check toe: is hij breed genoeg OF raakt hij de rechterrand?
    scherm_breedte = img.shape[1]
    raakt_rand = (x + w) > (scherm_breedte - 5)

    if w >= 125 or (raakt_rand and w > 40):
        echte_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h})

echte_buizen.sort(key=lambda k: k['x'])

# 2. Groeperen in kolommen
kolommen = []
for buis in echte_buizen:
    toegevoegd = False
    for kolom in kolommen:
        if abs(buis['x'] - kolom['center_x']) < 50:
            kolom['buizen'].append(buis)
            kolom['center_x'] = (kolom['center_x'] + buis['x']) // 2
            kolom['max_w'] = max(kolom['max_w'], buis['w'])
            kolom['start_x'] = min(kolom['start_x'], buis['x'])
            toegevoegd = True
            break
    if not toegevoegd:
        kolommen.append({'center_x': buis['x'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

# --- DEEL 3: VISUALISATIE & BESLISSING ---
doel_gevonden = False  # We gebruiken een vlaggetje in plaats van 'break'

for kolom in kolommen:
    # --- A. BEREKEN HET GAT (Voor ALLE kolommen) ---
    y_plafond_rand = 0
    y_vloer_rand = scherm_hoogte

    plafond_buizen = [b for b in kolom['buizen'] if b['y'] < midden_scherm]
    vloer_buizen = [b for b in kolom['buizen'] if b['y'] >= midden_scherm]

    if plafond_buizen: y_plafond_rand = max(b['bottom'] for b in plafond_buizen)
    if vloer_buizen: y_vloer_rand = min(b['y'] for b in vloer_buizen)

    gat_top = y_plafond_rand
    gat_bodem = y_vloer_rand
    gat_midden = (gat_top + gat_bodem) // 2

    # --- B. TEKEN DE DOOS (Voor ALLE kolommen) ---
    # Nu zie je dus ook de laatste, ook als we er nog niet heen vliegen
    cv2.rectangle(img, (kolom['start_x'], gat_top), (kolom['start_x'] + kolom['max_w'], gat_bodem), (255, 0, 255), 3)
    cv2.circle(img, (kolom['center_x'], gat_midden), 5, (255, 0, 255), -1)

    # --- C. BEPAAL HET DOEL (Alleen voor de EERSTE bruikbare) ---
    # We checken:
    # 1. Is de vogel er?
    # 2. Is deze kolom rechts van de vogel?
    # 3. Hebben we nog GEEN ander doel gevonden? (doel_gevonden is False)

    if vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x) and not doel_gevonden:

        # JA! Dit is 'm.
        doel_gevonden = True  # Zorg dat we de volgende kolommen negeren voor de lijn

        # Teken de gele lijn
        cv2.line(img, (vogel_x, vogel_y), (kolom['center_x'], gat_midden), (0, 255, 255), 2)

        # Tekst logic
        actie = "Mooi"
        kleur = (255, 255, 0)
        if vogel_y > gat_midden + 10:
            actie = "TIK!"
            kleur = (0, 0, 255)
        elif vogel_y < gat_midden - 10:
            actie = "Zakken"
            kleur = (0, 255, 0)

        cv2.putText(img, actie, (kolom['start_x'], gat_midden), cv2.FONT_HERSHEY_SIMPLEX, 1, kleur, 3)
        print(f"FOCUS OP KOLOM BIJ X={kolom['start_x']} | ACTIE: {actie}")

# Resultaat
cv2.imshow('Robot Visie - Alles Zichtbaar', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
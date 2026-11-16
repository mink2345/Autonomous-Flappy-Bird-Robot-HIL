import cv2
import numpy as np

img = cv2.imread('assets/ipad_scherm_test.jpg')  # Zorg dat de naam klopt
if img is None:
    print("Kan plaatje niet vinden!")
    exit()

# --- 1. EXACTE PERSPECTIVE TRANSFORM ---
bron_punten = np.float32([
    [50, 363],  # Linksboven
    [1026, 355],  # Rechtsboven
    [13, 884],  # Linksonder
    [1038, 912]  # Rechtsonder
])

breedte = 980
hoogte = 530

doel_punten = np.float32([
    [0, 0],
    [breedte, 0],
    [0, hoogte],
    [breedte, hoogte]
])

matrix = cv2.getPerspectiveTransform(bron_punten, doel_punten)
img = cv2.warpPerspective(img, matrix, (breedte, hoogte))

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
scherm_hoogte = img.shape[0]
scherm_breedte = img.shape[1]
midden_scherm = scherm_hoogte // 2

# --- 2. KLEUREN ---
onder_vogel = np.array([90, 200, 200])
boven_vogel = np.array([110, 255, 255])

onder_buis = np.array([0, 100, 80])
boven_buis = np.array([15, 255, 255])

mask_vogel = cv2.inRange(hsv, onder_vogel, boven_vogel)
mask_buis = cv2.inRange(hsv, onder_buis, boven_buis)

# --- 3. FILTERS OP HET RECHTGETROKKEN VELD ---
vloer_grens = int(scherm_hoogte * 0.90)
mask_buis[vloer_grens:, :] = 0

# Jouw gemeten vogel koker (Met ruime 10px marges: 98 tot 190)
mask_vogel[:, :98] = 0
mask_vogel[:, 190:] = 0

kernel = np.ones((5, 5), np.uint8)
mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=2)

# --- 4. VOGEL ZOEKEN (De nieuwe, slimme check!) ---
contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
vogel_x, vogel_y = 0, 0

geldige_vogels = []
for c in contours_vogel:
    area = cv2.contourArea(c)
    # Vogel moet klein zijn, reflecties zijn gigantisch
    if 20 < area < 400:
        geldige_vogels.append(c)

if geldige_vogels:
    # Pak de grootste vorm die wél de juiste, kleine afmeting heeft
    c = max(geldige_vogels, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    # Check of de verhouding klopt (vogel is grofweg even breed als hoog)
    if 0.5 < (w / float(h)) < 2.5:
        vogel_x = x + w // 2
        vogel_y = y + h // 2
        cv2.circle(img, (vogel_x, vogel_y), 15, (255, 255, 255), -1)

# --- 5. BUIZEN ZOEKEN ---
contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
ruwe_buizen = []

for c in contours_buis:
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)

    raakt_rand = (x + w) > (scherm_breedte - 10)

    if area > 50 and (w > 40 or raakt_rand):
        ruwe_buizen.append({'x': x, 'y': y, 'w': w, 'h': h, 'bottom': y + h})

ruwe_buizen.sort(key=lambda k: k['x'])

kolommen = []
for buis in ruwe_buizen:
    toegevoegd = False
    for kolom in kolommen:
        if abs(buis['x'] - kolom['center_x']) < 60:
            kolom['buizen'].append(buis)
            kolom['center_x'] = (kolom['center_x'] + buis['x']) // 2
            kolom['start_x'] = min(kolom['start_x'], buis['x'])
            kolom['max_w'] = max(kolom['max_w'], buis['w'])
            toegevoegd = True
            break
    if not toegevoegd:
        kolommen.append({'center_x': buis['x'], 'start_x': buis['x'], 'max_w': buis['w'], 'buizen': [buis]})

# --- 6. LOGICA ---
doel_gevonden = False

for kolom in kolommen:
    y_plafond = 0
    y_vloer = vloer_grens

    plafond_buizen = [b for b in kolom['buizen'] if b['y'] < midden_scherm]
    vloer_buizen = [b for b in kolom['buizen'] if b['y'] >= midden_scherm]

    if plafond_buizen: y_plafond = max(b['bottom'] for b in plafond_buizen)
    if vloer_buizen: y_vloer = min(b['y'] for b in vloer_buizen)

    gat_midden = (y_plafond + y_vloer) // 2
    cv2.rectangle(img, (kolom['start_x'], y_plafond), (kolom['start_x'] + kolom['max_w'], y_vloer), (255, 0, 255), 3)

    if vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x) and not doel_gevonden:
        doel_gevonden = True

        cv2.line(img, (vogel_x, vogel_y), (kolom['center_x'], gat_midden), (0, 255, 255), 4)
        cv2.circle(img, (kolom['center_x'], gat_midden), 8, (0, 255, 255), -1)

        actie = "Mooi"
        kleur = (255, 255, 0)

        if vogel_y > gat_midden + 15:
            actie = "TIK!"
            kleur = (0, 0, 255)
        elif vogel_y < gat_midden - 15:
            actie = "Zakken"
            kleur = (0, 255, 0)

        cv2.putText(img, actie, (kolom['start_x'], gat_midden - 15), cv2.FONT_HERSHEY_SIMPLEX, 1.2, kleur, 3)

cv2.imshow('Robot Ogen - Definitief', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
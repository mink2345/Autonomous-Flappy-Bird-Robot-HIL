import cv2
import numpy as np
import mss
import pyautogui
import time
import pickle
import neat
import os

# --- VEILIGHEID ---
# Gooi je muis naar een van de hoeken van je scherm als hij op hol slaat!
pyautogui.FAILSAFE = True

# ==============================================================================
# --- INSTELLINGEN ---
# ==============================================================================

# Ogen: Jouw exacte Mac metingen voor de web-game
MONITOR = {'top': 152, 'left': 118, 'width': 518, 'height': 696}

# Vogel & Buis Detectie Instellingen
VOGEL_MIN_GROOTTE = 50
VOGEL_OFFSET_X = 15
BUIS_MIN_AREA = 200
BUIS_MIN_BREEDTE = 15
BUIS_KERN_DIKTE = 2
GAP_SIZE = 140

# Kleuren voor je OpenCV maskers
KLEUR_VOGEL_LAAG = np.array([14, 50, 50])
KLEUR_VOGEL_HOOG = np.array([34, 255, 255])
KLEUR_BUIS_LAAG = np.array([40, 50, 50])
KLEUR_BUIS_HOOG = np.array([60, 255, 255])

# Actie
KLIK_TIJD = 0.02
MIN_TIJD_TUSSEN_SPRONGEN = 0.10

# ==============================================================================
# --- LAAD HET AI BREIN IN ---
# ==============================================================================
print("--- DE CYBORG (OPENCV OGEN + ML BREIN) ---")
print("1. Laden van configuratie en AI-brein...")

local_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(local_dir, 'config-feedforward.txt')
brein_path = os.path.join(local_dir, 'beste_brein.pkl')

# 1. Laad het config recept
config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                            neat.DefaultSpeciesSet, neat.DefaultStagnation,
                            config_path)

# 2. Laad de getrainde ziel (.pkl) in
with open(brein_path, "rb") as f:
    genome = pickle.load(f)

# 3. Koppel ze aan elkaar tot een werkend Neuraal Netwerk
net = neat.nn.FeedForwardNetwork.create(genome, config)

print("Brein succesvol geladen! Starten met kijken naar het scherm...")
laatste_sprong_tijd = 0

# ==============================================================================
# --- DE HOOFD LOOP (KIJKEN, DENKEN, DOEN) ---
# ==============================================================================

with mss.mss() as sct:
    while True:
        # 1. Beeld ophalen
        screenshot = sct.grab(MONITOR)
        img = np.array(screenshot)

        # Zorg dat de resolutie exact klopt voor Retina schermen
        img = cv2.resize(img, (MONITOR['width'], MONITOR['height']))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        scherm_hoogte = img.shape[0]
        midden_scherm = scherm_hoogte // 2

        # 2. Maskers maken
        mask_vogel = cv2.inRange(hsv, KLEUR_VOGEL_LAAG, KLEUR_VOGEL_HOOG)
        mask_buis = cv2.inRange(hsv, KLEUR_BUIS_LAAG, KLEUR_BUIS_HOOG)

        # 3. Opschonen (Zwarte balken boven en onder negeren)
        zwart_boven = int(scherm_hoogte * 0.1)
        zwart_onder = int(scherm_hoogte * 0.2)
        mask_vogel[0:zwart_boven, :] = 0
        mask_vogel[scherm_hoogte - zwart_onder:, :] = 0
        mask_buis[scherm_hoogte - zwart_onder:, :] = 0

        # Maak buizen dikker en lijm ze aan elkaar (als de score erdoorheen staat)
        kernel = np.ones((5, 5), np.uint8)
        mask_buis_dik = cv2.dilate(mask_buis, kernel, iterations=BUIS_KERN_DIKTE)
        kernel_lijm = np.ones((30, 5), np.uint8)
        mask_buis_dik = cv2.morphologyEx(mask_buis_dik, cv2.MORPH_CLOSE, kernel_lijm)

        # 4. Vogel Opsporen
        vogel_x, vogel_y = 0, 0

        contours_vogel, _ = cv2.findContours(mask_vogel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours_vogel:
            c = max(contours_vogel, key=cv2.contourArea)
            if cv2.contourArea(c) > VOGEL_MIN_GROOTTE:
                x, y, w, h = cv2.boundingRect(c)
                vogel_x = x + w // 2 + VOGEL_OFFSET_X
                vogel_y = y + h // 2
                cv2.circle(img, (vogel_x, vogel_y), 10, (255, 0, 0), 2)

        # 5. Buizen Detectie
        contours_buis, _ = cv2.findContours(mask_buis_dik, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        ruwe_buizen = []
        for c in contours_buis:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)
            in_top_zone = (y < 50)
            in_bodem_zone = (y > midden_scherm)
            geldige_plek = (in_top_zone or in_bodem_zone)
            breed_genoeg = (w > BUIS_MIN_BREEDTE)

            if area > BUIS_MIN_AREA and breed_genoeg and geldige_plek:
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

        # 6. AI Laten Denken
        doel_gevonden = False

        for kolom in kolommen:
            buizen_in_kolom = kolom['buizen']
            boven_stukken = [b for b in buizen_in_kolom if b['y'] < midden_scherm]
            onder_stukken = [b for b in buizen_in_kolom if b['y'] >= midden_scherm]

            y_plafond = 0
            y_vloer = scherm_hoogte

            if boven_stukken:
                y_plafond = max(b['bottom'] for b in boven_stukken)
            if onder_stukken:
                y_vloer = min(b['y'] for b in onder_stukken)

            # Ontbrekende buis fixen via GAP_SIZE als er maar eentje in beeld is
            if boven_stukken and not onder_stukken:
                y_vloer = y_plafond + GAP_SIZE
            elif onder_stukken and not boven_stukken:
                y_plafond = y_vloer - GAP_SIZE

            # Als deze buis nog voor ons ligt
            if not doel_gevonden and vogel_x > 0 and (kolom['start_x'] + kolom['max_w'] > vogel_x):
                doel_gevonden = True

                # Teken het gat dat de AI ziet
                cv2.rectangle(img, (kolom['start_x'], y_plafond), (kolom['start_x'] + kolom['max_w'], y_vloer),
                              (255, 0, 255), 2)

                # --- 7. MACHINE LEARNING INPUTS BEREKENEN ---
                # Dit zijn exact de 3 getallen waarop je hem hebt getraind!
                afstand_tot_plafond = abs(vogel_y - y_plafond)
                afstand_tot_vloer = abs(vogel_y - y_vloer)

                # Vraag het Neurale Netwerk om advies
                output = net.activate((vogel_y, afstand_tot_plafond, afstand_tot_vloer))

                # Als de AI roept: "Spring!" (waarde > 0.5)
                if output[0] > 0.5:
                    nu = time.time()
                    if nu - laatste_sprong_tijd > MIN_TIJD_TUSSEN_SPRONGEN:
                        pyautogui.keyDown('space')
                        time.sleep(KLIK_TIJD)
                        pyautogui.keyUp('space')
                        laatste_sprong_tijd = nu

                        cv2.putText(img, "AI: JUMP!", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                    (0, 255, 0), 2)
                else:
                    cv2.putText(img, "AI: ZAKKEN", (vogel_x, vogel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (0, 165, 255), 2)

        # Laat zien wat de robotogen zien
        cv2.imshow('Cyborg Brein', img)

        # Druk op 'q' om veilig af te sluiten
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
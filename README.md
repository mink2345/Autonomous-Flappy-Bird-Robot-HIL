# Flappy Bird  Robot - Project Documentatie & Master Cheatsheet

Dit document bevat de volledige projectomschrijving, de behaalde mijlpalen, het definitieve schakelschema en de benodigde scripts voor de Raspberry Pi 4B Flappy Bird-robot. 

---

## Introductie van het Project

Dit project is een hardware-in-the-loop (HIL) cyborg-systeem waarbij een Raspberry Pi 4B transformeert in een fysieke gamer. De robot is ontworpen om autonoom het spel *Flappy Bird* te spelen op een echte iPad. 

Het project combineert drie disciplines:
1. **Computer Vision (Ogen):** Een camera die in real-time het iPad-scherm filmt en analyseert om de vogel en de buizen te lokaliseren.
2. **Embedded Logic (Brein):** Een Python-algoritme dat de perfecte timing berekent.
3. **Actuatie (Spieren):** Een elektromagnetische solenoid die fysiek op het touchscreen tikt met een stylus-pen.

---

## Project Historie & Voortgang

De ontwikkeling is opgebouwd vanuit de software en breidt zich nu uit naar de fysieke wereld. 

* **Fase 1: Proof of Concept op de Laptop (Voltooid) 🏆**
  We zijn begonnen met het bouwen van de AI op de laptop. Eerst hebben we OpenCV gebruikt om de groene buizen en de vogel te herkennen op statische screenshots (kleurherkenning en contouren). Vervolgens is dit script omgebouwd naar een live-versie via schermopname (screen capture). Het script bestuurde de muis van de laptop en behaalde volledig autonoom een **topscore van 90**! Het wiskundige brein werkt.
* **Fase 2: Hardware Setup 'De Ogen' (Voltooid)**
  De overstap naar de Raspberry Pi. Het aansluiten van de fysieke Camera Module 3, het configureren van de autofocus, en het live streamen van de videofeed naar een lokaal netwerk om de latency en framerate te testen.
* **Fase 3: Hardware Setup 'De Spieren' (Voltooid)**
  Het ontwerpen en virtueel testen van een veilig schakelcircuit op een breadboard, om een krachtige 6V solenoid aan te sturen zonder de Raspberry Pi op te blazen.
* **Fase 4: Mechanische Constructie (Huidige fase)**
  Het bouwen van de fysieke *rig* om de iPad, camera en solenoid perfect en stabiel uit te lijnen.

---

## 1. Hardware Componenten

* **Brein:** Raspberry Pi 4B
* **Ogen:** Raspberry Pi Camera Module 3 (Autofocus via CSI-lintkabel)
* **Spier:** Solenoid Push-Pull 6V 300mA (JF-0530B)
* **Externe Voeding:** Gestripte 2-aderige USB-kabel (in een telefoonoplader) óf een willekeurige stabiele 5V/6V DC-voedingsbron (zoals 4x AA-batterijen of een powerbank). 
* **Beveiliging & Schakeling:** * 1x NPN Transistor (bijv. PN2222 of BC547)
  * 1x 1kΩ Basisweerstand (Kleurcode: Bruin-Zwart-Rood)
  * 1x Vrijloopdiode (bijv. 1N4007 - essentieel tegen de inductieve klap)
  * 1x Breadboard & Jumper-kabels

---

## 2. Schakelschema & Breadboard Opbouw

De Raspberry Pi is in dit circuit slechts de 'dirigent'. Een transistor werkt als elektronische schakelaar, waardoor de zware stroom van de externe voeding gescheiden blijft van de kwetsbare Pi. 

### 🖼️ Foto van het Circuit
![Definitief Schakelschema Breadboard](curcuit.png)

### 📌 Bedrading Checklist (De Gouden Regels)
* **Raspberry Pi verbindingen:**
  * **GPIO 18 (Pin 12)** -> Sluit aan op de **1kΩ weerstand** -> De andere kant gaat naar de **Base** (middelste poot) van de transistor.
  * **GND (Pin 6)** -> Sluit aan op de **blauwe min-lijn (-)** van het breadboard (*Common Ground*).
* **Externe Voeding (USB / DC Bron):**
  * **Rode draad (+)** -> Sluit aan op de **rode plus-lijn (+)**.
  * **Zwarte draad (-)** -> Sluit aan op de **blauwe min-lijn (-)**.
* **Transistor (NPN - Platte kant naar voren):**
  * **Links (Collector):** Verbonden met Draad B van de Solenoid.
  * **Midden (Base):** Verbonden met de weerstand.
  * **Rechts (Emitter):** Verbonden met de **blauwe min-lijn (-)**.
* **Solenoid & Vrijloopdiode (Parallel):**
  * **Draad A Solenoid:** Sluit aan op de **rode plus-lijn (+)**.
  * **De Diode:** Zet deze als een bruggetje over Draad A en Draad B. **CRUCIAAL:** Het grijze/zilveren streepje (Kathode) móét naar de **rode plus-lijn (+)** wijzen!

---

## 3. Totale Fysieke Robot Setup

De mechanische uitlijning bepaalt de nauwkeurigheid van de hardware.

### 📐 Tekening / Foto van de Totale Constructie
![Totale Robot Opstelling boven iPad](setup.jpeg)

* **Camera-hoogte:** Het scherm moet beeldvullend zijn, maar absoluut vrij van omgevingsreflecties (zoals plafondlampen in het glas). 
* **Solenoid-afstand:** Monteer de solenoid zo star mogelijk. De stylus-tip moet in ruststand **1 millimeter** boven het glas zweven om mechanische 'lag' bij het tikken te minimaliseren.

---

## 4. Reeds Uitgevoerde Hardware Testen (Scripts)

### Test A: Computer Vision & Camera (`camera_test.py`)
Tijdens Fase 2 hebben we bevestigd dat de Raspberry Pi de beelden net zo goed kan zien als de laptop. Dit script opent de camerastream, stelt de autofocus in op het iPad-scherm, en maakt een testfoto om te kijken of de OpenCV-kleurherkenning de buizen straks perfect kan isoleren.

```python
import cv2
import time

# Start de libcamera backend
cap = cv2.VideoCapture(0)

if cap.isOpened():
    print("Camera succesvol geopend. Autofocus initialiseert...")
    time.sleep(2) # Wacht tot de lens scherpgesteld is
    
    ret, frame = cap.read()
    if ret:
        cv2.imwrite('robot_visie_test.jpg', frame)
        print("Testframe opgeslagen voor kleur- en pixelanalyse.")
cap.release()
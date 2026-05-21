# Flappy Bird  Robot - Project Documentatie & Master Cheatsheet

Dit document bevat de volledige projectomschrijving, de behaalde mijlpalen, het definitieve en veilige schakelschema, en de benodigde scripts voor de Raspberry Pi 4B Flappy Bird-robot. Sla dit bestand op als `README.md` in de hoofdmap van je repository.

---

## Introductie van het Project

Dit project is een hardware-in-the-loop (HIL) cyborg-systeem waarbij een Raspberry Pi 4B transformeert in een fysieke gamer. De robot is ontworpen om autonoom het spel *Flappy Bird* te spelen op een echte iPad. 

Het project combineert drie disciplines:
1. **Computer Vision (Ogen):** Een camera die in real-time het iPad-scherm filmt en analyseert om de vogel en de buizen te lokaliseren.
2. **Embedded Logic (Brein):** Een Python-algoritme dat op basis van de camerabeelden de perfecte timing berekent om te springen.
3. **Actuatie (Spieren):** Een elektromagnetische solenoid die fysiek op het touchscreen tikt met een stylus-pen.

---

## Project Voortgang & Roadmap

De ontwikkeling is opgedeeld in logische fases om de complexiteit stap voor stap te tackelen. De focus ligt op het gescheiden testen van subsystemen voordat alles in één hoofdscript wordt samengevoegd.

* **Fase 1: Visuele Feed & Netwerk Setup (Voltooid)**
    Het opzetten van de camera-hardware en het testen van de latency via het netwerk. Om de uitlijning te controleren is een lokale serveromgeving opgezet (`http.server`).
* **Fase 2: Hardware-Isolatie & Actuatie (Voltooid)**
    Het ontwerpen en virtueel testen van een veilig schakelcircuit in Tinkercad. De Raspberry Pi is hierbij met een transistor volledig beschermd tegen de inductieve stroompieken van de elektromagneet.
* **Fase 3: Mechanische Constructie (Lopende fase)**
    Het bouwen van de fysieke rig (bijv. van Lego of hout) om de camera exact boven de iPad te fixeren en de solenoid stabiel op de juiste hoogte te monteren.
* **Fase 4: Integratie & OpenCV AI (Volgende fase)**
    Het schrijven van het definitieve hoofdscript (`main.py` of `flappy_agent.py`) waarin de beeldverwerking direct gekoppeld wordt aan de actuatie-pinnen voor realtime gameplay.

---

## 1. Hardware Componenten

* **Brein:** Raspberry Pi 4B
* **Ogen:** Raspberry Pi Camera Module 3 (Voorzien van Phase Detection Autofocus via CSI-lintkabel)
* **Spier:** Solenoid Push-Pull 6V 300mA (JF-0530B)
* **Externe Voeding:** Gestripte 2-aderige USB-kabel aangesloten op een USB-muuradapter, óf een reguliere stabiele 5V/6V DC-voedingsbron (zoals een batterijhouder voor 4x AA-batterijen). 
* **Beveiliging & Schakeling:** * 1x NPN Transistor (bijv. PN2222 of BC547)
    * 1x 1kΩ Basisweerstand (Kleurcode: Bruin-Zwart-Rood)
    * 1x Vrijloopdiode (bijv. 1N4007 - essentieel tegen inductieve terugslag)
    * 1x Breadboard & Jumper-kabels

---

## 2. Schakelschema & Breadboard Opbouw

De Raspberry Pi kan zelf niet genoeg stroom leveren om de solenoid aan te sturen en kan beschadigd raken door de spoel. Daarom maakt dit circuit gebruik van een transistor als elektronische schakelaar en een gedeelde massa (*Common Ground*).

### 🖼️ Foto van het Circuit
![Definitief Schakelschema Breadboard](curcuit.png)

### 📌 Bedrading Checklist (De Gouden Regels)
* **Raspberry Pi verbindingen:**
    * **GPIO 18 (Pin 12)** -> Sluit aan op de **1kΩ weerstand** -> De andere kant van de weerstand gaat naar de **Base** (middelste pootje) van de transistor.
    * **GND (Pin 6)** -> Sluit aan op de **blauwe min-lijn (-)** van het breadboard (*Common Ground*).
* **Externe Voeding (USB / DC Bron):**
    * **Rode draad (+)** -> Sluit aan op de **rode plus-lijn (+)** van het breadboard.
    * **Zwarte draad (-)** -> Sluit aan op de **blauwe min-lijn (-)** van het breadboard.
* **Transistor (NPN - Platte kant naar voren):**
    * **Links (Collector):** Verbonden met de min-draad van de Solenoid.
    * **Midden (Base):** Verbonden met de 1kΩ weerstand vanaf GPIO 18.
    * **Rechts (Emitter):** Verbonden met de **blauwe min-lijn (-)** van het breadboard.
* **Solenoid & Vrijloopdiode (Parallel):**
    * **Draad A Solenoid:** Sluit aan op de **rode plus-lijn (+)**.
    * **Draad B Solenoid:** Sluit aan op de **Collector** (linker pootje van de transistor).
    * **De Diode:** Prik deze over dezelfde kolommen als Draad A en B. **CRUCIAL:** Het grijze/zilveren streepje (Kathode) móét naar de **rode plus-lijn (+)** wijzen!

---

## 3. Totale Fysieke Robot Setup

De mechanische uitlijning bepaalt de nauwkeurigheid van de robot. Speling in de constructie zorgt voor vertraging in de gameplay.

### 📐 Tekening / Foto van de Totale Constructie
![Totale Robot Opstelling boven iPad](setup.jpeg)

* **Camera-hoogte:** Positioneer de camera zo dat het actieve iPad-scherm beeldvullend is. Voorkom dat felle plafondlampen reflecteren op het glas, omdat dit de pixelanalyse verstoort.
* **Solenoid-afstand:** Monteer de solenoid star boven het touchscreen. In ruststand moet de stylus-tip idealiter **1 millimeter** boven het glas zweven om mechanische 'lag' te minimaliseren.

---

## 4. Basis Test Scripts (Python)

### Hardware Test A: Solenoid Actuatie (`motor_test.py`)
Dit script controleert of de transistor correct schakelt en of de solenoid krachtig genoeg naar beneden slaat. Run dit bestand met `python3 motor_test.py`.

```python
from gpiozero import LED
from time import sleep

# GPIO 18 stuurt de transistor aan
solenoid = LED(18)

print("Robot-vinger paraat... Test start over 2 seconden.")
sleep(2)

try:
    while True:
        print("TIK!")
        solenoid.on()   # Transistor open -> Solenoid vuurt
        sleep(0.1)      # Houdt het scherm 100ms ingedrukt
        
        solenoid.off()  # Transistor dicht -> Veertje trekt pen terug
        print("Wacht...")
        sleep(2.0)      # Wacht 2 seconden voor de volgende tik

except KeyboardInterrupt:
    print("\nTest gestopt door gebruiker.")
    solenoid.off()
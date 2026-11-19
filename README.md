# Flappy Bird Hardware-in-the-Loop Robot - Project Documentatie

Dit document bevat de technische projectomschrijving, de behaalde mijlpalen, het definitieve schakelschema en de software-architectuur voor de Raspberry Pi 4B Flappy Bird-robot. Deze repository dient als volledige documentatie voor de ontwikkeling van dit autonome systeem.

---

## Introductie van het Project

Dit project betreft de ontwikkeling van een hardware-in-the-loop (HIL) systeem waarbij een Raspberry Pi 4B functioneert als autonome speler voor het spel *Flappy Bird* op een fysieke, rechtopstaande iPad. 

Het systeem integreert drie kerndisciplines:
1. **Computer Vision (Beeldacquisitie):** Real-time registratie en analyse van het iPad-scherm via `Picamera2` en OpenCV om spelobjecten (de vogel en buizen) te lokaliseren en de bewegende vloer weg te filteren.
2. **Embedded Logic (Besluitvorming):** Een non-blocking Python-algoritme dat valsnelheden, plafond-botsingen ('Ghost Bird') en mechanische systeemvertraging (~150-200ms) real-time compenseert en live te tunen is via `config.json`.
3. **Actuatie (Uitvoering):** Een omgekeerd gemonteerde elektromagnetische solenoid die fysieke tikken uitdeelt op het capacitieve touchscreen.

---

## Projectfasering & Ontwikkeling

De ontwikkeling volgt een iteratieve aanpak, startend bij softwarematige validatie en uitbreidend naar volledige fysieke hardware-integratie.

- **Fase 1: Proof of Concept - Softwarematige validatie (Voltooid)**
  De initiële ontwikkeling vond plaats op een laptop om de beeldverwerkingslogica te valideren. Hierbij is bewust gekozen voor pure Computer Vision (CV) in plaats van Machine Learning (ML) om de verwerkingstijd per frame minimaal te houden. Door middel van kleurherkenning (HSV) en contourdetectie in OpenCV werden objecten eerst in statische beelden en daarna real-time gedetecteerd. Het algoritme stuurde autonoom de spatiebalk aan en behaalde in simulatie een topscore van 90.

- **Fase 2: Hardware Setup - Vision & Kalibratie (Voltooid)**
  De migratie van de vision-architectuur naar de Raspberry Pi 4B met de Camera Module 3. Omdat de Pi *headless* draait, is een eigen multithreaded HTTP-kalibratieserver (`kaliberen_camera.py`) gebouwd. Hiermee kan het exacte speelveld live in de browser worden uitgelijnd zodat de oranje bewegende vloer buiten het detectiemasker valt.

- **Fase 3: Hardware Setup - Actuatie (Voltooid)**
  Het ontwerpen en bouwen van een veilig schakelcircuit voor de 6V solenoid. Door middel van een TIP120 Darlington transistor, een externe voedingslijn en een parallel geplaatste vrijloopdiode (1N4007) is de Raspberry Pi volledig geïsoleerd en beschermd tegen inductieve spanningspieken.

- **Fase 4: Mechanische Constructie & Solenoid-omkering (Voltooid)**
  Het realiseren van de fysieke testopstelling voor een rechtopstaande iPad ("Vampire Mode"). Om te voorkomen dat de solenoid zijn kracht verliest aan zijn eigen stugge trechterveer, is de solenoid **180 graden omgedraaid**. Bij stroomtoevoer schiet de achterkant van de metalen pin naar buiten tegen de stylus-tip op het scherm, waarna een gefixeerd elastiekmechanisme zorgt voor een directe, betrouwbare terugslag naar de ruststand.

- **Fase 5: Systeemintegratie, Live Config & Telemetrie (Huidige fase)**
  Alle subsystemen zijn samengevoegd in `live_test.py`. Het systeem draait volledig non-blocking, neemt elke vlucht op als `.avi` video met ingetekende HUD-telemetrie (inclusief 'Ghost Bird' plafond-voorspelling en een 'Lage Buis Modus') en slaat crash-analyses op in `.csv` logboeken. Via `config.json` worden parameters zoals sprongmarges en kliktijden live tijdens het vliegen bijgesteld om de mechanische vertraging te perfectioneren.

---

## 1. Hardware Specificaties

- **Microcontroller:** Raspberry Pi 4B
- **Vision Sensor:** Raspberry Pi Camera Module 3 (Phase Detection Autofocus via CSI-interface)
- **Actuator:** Solenoid Push-Pull 6V 300mA (JF-0530B) - *180° omgekeerd gemonteerd*
- **Voeding (Actuator):** Gestripte 2-aderige externe voedingslijn (5V/6V DC)
- **Elektronische Componenten:**
  - 1x TIP120 Darlington Transistor (NPN)
  - 2x 1kΩ Weerstand (Basisweerstand & pull-down weerstand)
  - 1x Vrijloopdiode (1N4007)
  - 1x Breadboard, bekabeling & capacitieve stylus-tip met elastiek-terugvering

---

## 2. Schakelschema & Architectuur

De GPIO-pinnen van de Raspberry Pi zijn niet ontworpen voor het leveren van hoge stromen. Het onderstaande circuit maakt gebruik van een externe voeding waarbij een NPN-transistor fungeert als low-side switch.

### Definitief Circuit
![Definitief Schakelschema Breadboard](assets/Circuit.png)

### Bedradingsspecificaties
- **Microcontroller Interface:**
  - **GPIO 18 (Fysieke Pin 12)** -> Verbonden met de **1kΩ weerstand** -> Base van de transistor.
  - **GND (Pin 6)** -> Verbonden met de gedeelde massa (Common Ground) op het breadboard.
- **Externe Voeding (Power Rail):**
  - **VCC (+)** -> Positieve stroomlijn van het breadboard.
  - **GND (-)** -> Gedeelde massa van het breadboard.
- **TIP120 Transistor (NPN - Platte kant met tekst naar voren):**
  - **Base (Linker pootje):** Verbonden met het stuursignaal vanaf de Pi **én** via een **1kΩ pull-down weerstand** verbonden met de GND (-).
  - **Collector (Middelste pootje):** Verbonden met de min-draad van de solenoid en de anode van de diode.
  - **Emitter (Rechter pootje):** Direct verbonden met de gedeelde GND (-).
- **Inductieve Last & Beveiliging:**
  - **Solenoid Plus-klem:** Verbonden met de VCC (+).
  - **Vrijloopdiode:** Parallel over de solenoid geplaatst. De kathode (zijde met het streepje) is gericht naar de VCC (+) om de flyback-stroom bij het uitschakelen veilig af te voeren.

---

## 3. Fysieke Opstelling & Bestandsstructuur

### Overzicht Testopstelling
![Totale Robot Opstelling boven iPad](assets/setup.jpeg)

- **Rechtopstaande Positionering ("Vampire Mode"):** De iPad staat verticaal opgesteld met de Camera Module 3 er recht tegenover. Dit voorkomt perspectiefvervorming en minimaliseert plafondreflecties op het glas.
- **Omgekeerde Actuator Kalibratie:** Door de solenoid 180 graden om te draaien wordt de intrek-kracht omgezet in een directe stootbeweging aan de achterzijde van de behuizing, ondersteund door een vastgezet elastiek dat de tip na elke tik direct van het scherm haalt.

### Overzicht Repository (`raspberrypi/`)
```text
raspberrypi/
├── config.json               # Live aanpasbare instellingen (tijdens runtime ingelezen)
├── kaliberen_camera.py       # HTTP webserver (:8080) voor fysieke uitlijning van iPad en camera
├── live_test.py              # Het volledige autonome hoofdscript incl. HUD, video-opname en CSV-logger
├── maak_foto.py              # Hulpscript voor het schieten van losse referentiefoto's
├── solenoid_test.py          # Geïsoleerde hardware-test voor de GPIO en TIP120-schakeling
├── test_cv_and_solenoid.py   # Integratietest: activeert solenoid zodra OpenCV rood/oranje detecteert
└── vlucht_logs/              # Automatisch gegenereerde map met .avi vluchtvideo's en .csv Black Box logs
```

---

## 4. Hardware Validatie & Kalibratie (Scripts)

### Test A: Statische Foto & CLI Stream (Low-Level)
Voor initiële controle op kernel-niveau zonder Python-overhead:
```bash
# Maak een referentiefoto via de CLI (of gebruik python3 maak_foto.py)
rpicam-jpeg -o vision_reference_frame.jpg

# Start een ruwe TCP-videostream voor VLC Media Player (tcp://<IP_PI>:8080)
rpicam-vid -t 0 --inline --listen -o tcp://0.0.0.0:8080
```

### Test B: Live Browser Kalibratie (`kaliberen_camera.py`)
Om de fysieke opstelling exact uit te lijnen met de softwarematige maskers (zodat de bewegende oranje vloer onder `Y = 830` buiten het blikveld valt), start je de ingebouwde kalibratieserver:
```bash
python3 kaliberen_camera.py
```
Open vervolgens op je Mac of telefoon een browser en ga naar `http://<IP_ADRES_RASPBERRY_PI>:8080`. Je ziet nu live het camerabeeld inclusief het witte speelveldkader (`X=20..1025`, `Y=350..830`) en de gele zoek-koker voor de vogel (`X=20..140`).

### Test C: Actuatie & Schakelcircuit (`solenoid_test.py`)
Validatie van de transistor-schakeling en de fysieke tik-respons op het iPad-scherm:
```python
from gpiozero import LED
from time import sleep

solenoid = LED(18)

try:
    while True:
        print("[ACTION] Actuatie (HIGH)")
        solenoid.on()
        sleep(0.1)      
        
        print("[ACTION] Rust (LOW)")
        solenoid.off()
        sleep(2.0)
except KeyboardInterrupt:
    solenoid.off()
```

### Test D: Gesloten Keten Kleurdetectie (`test_cv_and_solenoid.py`)
Koppelt `Picamera2` rechtstreeks aan de GPIO-aansturing: zodra een ingestelde drempelwaarde aan rode/oranje HSV-pixels in beeld verschijnt, schakelt de TIP120-transistor de solenoid in.

---

## 5. Hoofdsysteem & Live Architectuur (`live_test.py` & `config.json`)

Het definitieve systeem in `live_test.py` lost de uitdagingen van fysieke robotica (mechanische vertraging en val-momentum) op met
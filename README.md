# Flappy Bird Hardware-in-the-Loop Robot - Project Documentatie

Dit document bevat de technische projectomschrijving, de behaalde mijlpalen, het definitieve schakelschema en de benodigde scripts voor de Raspberry Pi 4B Flappy Bird-robot. Deze repository dient als volledige documentatie voor de ontwikkeling van dit autonome systeem.

---

## Introductie van het Project

Dit project betreft de ontwikkeling van een hardware-in-the-loop (HIL) systeem waarbij een Raspberry Pi 4B functioneert als autonome speler voor het spel *Flappy Bird* op een fysieke iPad. 

Het systeem integreert drie kerndisciplines:
1. **Computer Vision (Beeldacquisitie):** Real-time registratie en analyse van het iPad-scherm om spelobjecten (de vogel en buizen) te lokaliseren.
2. **Embedded Logic (Besluitvorming):** Een efficiënt Python-algoritme dat de optimale sprong-timing berekent.
3. **Actuatie (Uitvoering):** Een elektromagnetische solenoid die fysieke input levert op het capacitieve touchscreen.

---

## Projectfasering & Ontwikkeling

De ontwikkeling volgt een iteratieve aanpak, startend bij softwarematige validatie en uitbreidend naar fysieke hardware-integratie.

* **Fase 1: Proof of Concept - Softwarematige validatie (Voltooid)**
  De initiële ontwikkeling vond plaats op een laptop om de beeldverwerkingslogica te valideren. Hierbij is bewust gekozen voor pure Computer Vision (CV) in plaats van Machine Learning (ML). Door middel van gerichte optimalisatie van kleurherkenning en contourdetectie in OpenCV, konden de objecten betrouwbaar worden geïsoleerd in statische beelden (`[JOUW_BESTANDSNAAM_STATISCH].py`). 
  Vervolgens is de codebase uitgebreid naar een real-time implementatie via schermopname (`[JOUW_BESTANDSNAAM_LIVE].py`). Het algoritme stuurde autonoom de spatiebalk van de laptop aan en registreerde de prestatiedata in een logbestand (`[JOUW_BESTANDSNAAM_DATA].csv`) voor verdere analyse. Deze geoptimaliseerde CV-aanpak bleek uiterst effectief en resulteerde in een topscore van 90.(' [beste script]' )

* **Fase 2: Hardware Setup - Vision (Voltooid)**
  De migratie van de vision-architectuur naar de Raspberry Pi. Dit omvatte de integratie van de fysieke Camera Module 3, configuratie van de autofocus-parameters en het valideren van de framerate en latency via een lokaal netwerk.

* **Fase 3: Hardware Setup - Actuatie (Voltooid)**
  Het ontwerpen en simuleren van een veilig schakelcircuit. Het aansturen van een krachtige 6V solenoid vereist strikte scheiding van stroomkringen. Door middel van een transistor en een parallel geplaatste vrijloopdiode is de Raspberry Pi volledig geïsoleerd en beschermd tegen inductieve spanningspieken.

* **Fase 4: Mechanische Constructie (Huidige fase)**
  Het realiseren van de fysieke testopstelling. Het doel is een starre constructie te bouwen om mechanische speling en beeldvervorming door trillingen of externe lichtbronnen te elimineren.

* **Fase 5: Systeemintegratie & Tweaking (Aankomende fase)**
  Het samenvoegen van de *Vision* en *Actuatie* subsystemen in één hoofdscript (`main.py`). De virtuele input wordt vervangen: wanneer het OpenCV-algoritme groen (een buis) detecteert, triggert dit direct de solenoid via de GPIO. Deze fase omvat intensief testen en het 'tweaken' van de timing om de hardware-lag (delay) te compenseren en een continue, stabiele *gameplay loop* te bereiken.

---

## 1. Hardware Specificaties

* **Microcontroller:** Raspberry Pi 4B
* **Vision Sensor:** Raspberry Pi Camera Module 3 (Phase Detection Autofocus via CSI-interface)
* **Actuator:** Solenoid Push-Pull 6V 300mA (JF-0530B)
* **Voeding (Actuator):** Gestripte 2-aderige USB-kabel (via 5V USB-adapter) of een stabiele DC-voedingsbron (bijv. 6V batterij-array).
* **Elektronische Componenten:** * 1x NPN Transistor (bijv. PN2222 of BC547)
  * 1x 1kΩ Basisweerstand (Kleurcode: Bruin-Zwart-Rood)
  * 1x Vrijloopdiode (bijv. 1N4007)
  * 1x Breadboard & bekabeling

---

## 2. Schakelschema & Architectuur

De GPIO-pinnen van de Raspberry Pi zijn niet ontworpen voor het leveren van hoge stromen. Het onderstaande circuit maakt gebruik van een externe voeding waarbij een NPN-transistor fungeert als low-side switch.

### Definitief Circuit
![Definitief Schakelschema Breadboard](curcuit.png)

### Bedradingsspecificaties
* **Microcontroller Interface:**
  * **GPIO 18 (Pin 12)** -> Verbonden met de **1kΩ weerstand** -> Base van de transistor.
  * **GND (Pin 6)** -> Verbonden met de gedeelde massa (Common Ground) op het breadboard.
* **Externe Voeding (Power Rail):**
  * **VCC (+)** -> Positieve stroomlijn van het breadboard.
  * **GND (-)** -> Gedeelde massa van het breadboard.
* **Transistor (NPN):**
  * **Collector:** Verbonden met klem B van de solenoid.
  * **Base:** Verbonden met het stuursignaal (via de weerstand).
  * **Emitter:** Verbonden met de gedeelde massa.
* **Inductieve Last & Beveiliging:**
  * **Solenoid Klem A:** Verbonden met de VCC (+).
  * **Vrijloopdiode:** Parallel over de solenoid geplaatst. De kathode (gemarkeerd met streep) is gericht naar de VCC (+) om de flyback-stroom veilig te dissiperen.

---

## 3. Fysieke Opstelling

De betrouwbaarheid van het algoritme is direct afhankelijk van de stabiliteit van de mechanische constructie.

### Overzicht Testopstelling
![Totale Robot Opstelling boven iPad](setup.jpeg)

* **Camera Positionering:** De lens bevindt zich loodrecht boven het display. Externe lichtreflecties zijn geminimaliseerd om interferentie in de kleurdrempels (thresholding) te voorkomen.
* **Actuator Kalibratie:** De solenoid is rigide gemonteerd. De afstand van de stylus-tip tot het capacitieve scherm is gekalibreerd op **1 millimeter** in ruststand. Dit minimaliseert de mechanische vertraging (actuation lag) tussen het GPIO-signaal en de fysieke aanraking.

---

## 4. Hardware Validatie (Scripts)

De onderstaande scripts documenteren de geïsoleerde unittests van de hardware-componenten.

### Test A: Vision Hardware Validatie & Latency Analyse (CLI)
De initiële validatie van de Camera Module 3 is direct via de Linux Command Line Interface (CLI) uitgevoerd. Deze low-level aanpak sluit software-overhead uit en bevestigt dat de sensor op kernel-niveau correct communiceert. 

Tijdens deze fase zijn zowel de statische uitlijning als een real-time videostream getest om de bandbreedte en systeemlatentie (lag) in kaart te brengen.

```bash
# 1. Statische validatie: Capteer een testfoto voor OpenCV kleur-kalibratie
rpicam-jpeg -o vision_reference_frame.jpg

# Start een lokaal netwerk-endpoint om bestanden head-less (zonder monitor) uit te lezen
python3 -m http.server 8000

# 2. Dynamische validatie: Start een real-time TCP videostream voor latency-meting
rpicam-vid -t 0 --inline --listen -o tcp://0.0.0.0:8080
```

#### Handleiding: Live TCP-stream bekijken via VLC Media Player
Om de dynamische videostream van de Raspberry Pi live te inspecteren op een laptop (binnen hetzelfde netwerk), dienen de volgende stappen exact te worden uitgevoerd:

1. **Start de stream op de Raspberry Pi:** Zorg dat het bovenstaande `rpicam-vid` commando actief is in de terminal van de Raspberry Pi. De Pi luistert nu op poort `8080` naar inkomende verbindingen.
2. **Open VLC Media Player:** Start de VLC-applicatie op de laptop (beschikbaar voor macOS, Windows en Linux).
3. **Navigeer naar Netwerkstroom:**
   * *Voor macOS:* Ga in de bovenbalk naar **Bestand** (File) -> **Netwerk openen...** (Open Network...).
   * *Voor Windows:* Ga in de menu-balk naar **Media** -> **Netwerkstroom openen...** (Open Network Stream...) of gebruik de sneltoets `Ctrl + N`.
4. **Voer de Netwerk-URL in:** Voer in het invoerveld het protocol, het IP-adres (of de hostname) van de Raspberry Pi en het poortnummer in volgens onderstaande syntaxis:
   ```text
   tcp://[IP_ADRES_RASPBERRY_PI]:8080
   ```

### Test B: Actuatie & Schakelcircuit (`motor_test.py`)
Validatie van de transistor-schakeling en het meten van de mechanische respons van de solenoid. Dit script verifieert of het circuit correct en veilig schakelt.

```python
from gpiozero import LED
from time import sleep

# Configuratie van de besturingspin (GPIO 18)
solenoid = LED(18)

try:
    while True:
        print("[ACTION] Actuatie (HIGH)")
        solenoid.on()
        sleep(0.1)      # 100ms contacttijd (fingertip touch simulatie)
        
        print("[ACTION] Rust (LOW)")
        solenoid.off()
        sleep(2.0)      # Wacht 2 seconden
except KeyboardInterrupt:
    solenoid.off()
    print("\n[INFO] Actuatietest veilig afgebroken door gebruiker.")
```

### Test C: OpenCV Kleurdetectie met Camera Module

In deze test koppelen we de officiële Raspberry Pi Camera Module (via de platte lintkabel) aan het circuit. Het doel is om de kleur rood te detecteren binnen het HSV-kleurbereik en bij succes direct de solenoid op GPIO 18 (fysieke Pin 12) aan te sturen via de TIP120-transistor.

#### Opmerkingen & Bevindingen
* **Software-koppeling:** Vanwege de architectuur van het nieuwe Raspberry Pi OS (Bookworm) werkt de standaard `cv2.VideoCapture(0)` methode niet met de camera module. Er is succesvol overgestapt op de officiële `Picamera2` library om frames razendsnel en rechtstreeks in een numpy-array in te laden voor OpenCV.
* **Kleurherkenning:** De basis van de kleurherkenning werkt en activeert de transistor. De detectie is momenteel nog afhankelijk van omgevingslicht en schermreflecties (zoals bij het filmen van een iPad-scherm). Dit vereist in de volgende fase het verder finetunen van de HSV-drempelwaarden voor een strakkere triggering.
* **Mechanische slag:** De solenoid reageert correct op het stuursignaal. Omdat de start van de slag op een 5V voeding iets aan kracht mist, blijft een mechanische 'stroke limiter' (zoals een propje of tape achter de pen) voorlopig nodig om hem soepel en zelfstandig te laten inklappen.

#### Geteste Code (`test_c_camera.py`)

```python
import cv2
import numpy as np
from gpiozero import LED
import time
from picamera2 import Picamera2

# 1. Hardware Setup (gpiozero - BCM Pin 18 / Fysieke Pin 12)
solenoid = LED(18)
solenoid.off() 

# 2. Raspberry Pi Camera Module opstarten
print("Camera Module initialiseren...")
picam2 = Picamera2()

# Resolutie op 640x480 gezet voor een maximale framerate en snelle reactietijd
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

time.sleep(2.0)
print("Test C Gestart: Camera is actief. Wachten op de kleur ROOD...")
print("Druk in de terminal op 'Ctrl+C' om te stoppen.")

try:
    while True:
        # Pak direct een frame van de Camera Module
        frame = picam2.capture_array()

        # Zet het beeld om van BGR naar HSV kleurbereik
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Definieer de twee bereiken voor de kleur ROOD in HSV
        lager_rood1 = np.array([0, 120, 70])
        hoger_rood1 = np.array([10, 255, 255])
        lager_rood2 = np.array([170, 120, 70])
        hoger_rood2 = np.array([180, 255, 255])

        # Maak maskers en voeg ze samen
        mask1 = cv2.inRange(hsv, lager_rood1, hoger_rood1)
        mask2 = cv2.inRange(hsv, lager_rood2, hoger_rood2)
        volledig_masker = mask1 + mask2

        # Tel het aantal gedetecteerde rode pixels
        rode_pixels = np.sum(volledig_masker == 255)

        # Als de drempelwaarde van 4000 pixels wordt overschreden, activeer de solenoid
        if rode_pixels > 4000:
            print(f"ROOD GEZIEN! ({rode_pixels} pixels) -> SOLENOID PUSH!")
            solenoid.on()        # Transistor open, solenoid slaat uit
            time.sleep(0.15)     # Pulsduur van 150 milliseconden
            solenoid.off()       # Transistor dicht, solenoid trekt terug
            
            # Wachttijd om herhaaldelijk mitrailleren op hetzelfde object te voorkomen
            time.sleep(0.6) 

except KeyboardInterrupt:
    print("\nTest C handmatig gestopt.")

finally:
    # Hardware en camera streams netjes deactiveren en vrijgeven
    picam2.stop()
    solenoid.off()
    print("Camera afgesloten. Hardware staat in veilige ruststand.")
```
import cv2
import numpy as np


# Deze functie wordt uitgevoerd elke keer als je klikt
def muis_klik(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        pixel_bgr = img[y, x]
        pixel_hsv = hsv_img[y, x]
        print(f"Geklikt op Coördinaten -> X: {x}, Y: {y}")
        print(f"Kleurwaardes -> HSV: {pixel_hsv} | BGR: {pixel_bgr}")
        print("-" * 40)


# 1. Laad de testfoto
foto_pad = 'assets/ipad_scherm_test.jpg'
img = cv2.imread(foto_pad)

if img is None:
    print(f"Fout: Kan '{foto_pad}' niet vinden. Klopt de bestandsnaam en map?")
else:
    # 2. Zet de foto om naar HSV
    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 3. Laat de foto zien en luister naar muisklikken
    venster_naam = 'Flappy Bird Kalibratie - Klik op de vogel en buizen'
    cv2.imshow(venster_naam, img)
    cv2.setMouseCallback(venster_naam, muis_klik)

    print("Klik op het scherm om de HSV kleuren en coördinaten te zien.")
    print("Druk op 'q' of 'ESC' om het venster te sluiten.")

    # Blijf open totdat je op 'q' of ESC drukt
    while True:
        toets = cv2.waitKey(1) & 0xFF
        if toets == ord('q') or toets == 27:
            break

    cv2.destroyAllWindows()
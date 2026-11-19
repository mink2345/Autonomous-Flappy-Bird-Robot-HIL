import cv2
import time
from picamera2 import Picamera2
#taking a picture with the pi so you can analyse the colors

print("Camera Module opstarten")
picam2 = Picamera2()

# Resolutie instellen
config = picam2.create_preview_configuration(main={"size": (1440, 1080)})
picam2.configure(config)
picam2.start()

print("Camera loopt! Je hebt 5 seconden...")
for i in range(5, 0, -1):
    print(f"{i}...")
    time.sleep(1)

print("KLIK! Foto wordt gemaakt...")
frame = picam2.capture_array()

frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)

cv2.imwrite("ipad_scherm_test.jpg", frame_bgr)

picam2.stop()
print("Succes! De foto is rechtop gezet en opgeslagen als 'ipad_scherm_test.jpg'.")
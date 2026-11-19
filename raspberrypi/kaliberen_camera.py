import cv2
import time
import numpy as np
from picamera2 import Picamera2
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

#run script to see what the camera sees and make shore its correct whith what you want

# --- VASTE AFMETINGEN VOOR KALIBRATIE ---
SPEELVELD_TOP = 350
SPEELVELD_BODEM = 880
SPEELVELD_LINKS = 20
SPEELVELD_RECHTS = 1025

VOGEL_SCAN_LINKS = 20
VOGEL_SCAN_RECHTS = 140

print("Camera starten voor live kalibratie...")
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (1440, 1080)})
picam2.configure(config)
picam2.start()


class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            try:
                while True:
                    frame = picam2.capture_array()
                    img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

                    # 1. Speelveld kader (Wit)
                    cv2.rectangle(img, (SPEELVELD_LINKS, SPEELVELD_TOP), (SPEELVELD_RECHTS, SPEELVELD_BODEM),
                                  (255, 255, 255), 3)

                    # 2. Vogel zoek-koker (Blauw/Geel)
                    cv2.line(img, (VOGEL_SCAN_LINKS, SPEELVELD_TOP), (VOGEL_SCAN_LINKS, SPEELVELD_BODEM), (0, 255, 255),
                             2)
                    cv2.line(img, (VOGEL_SCAN_RECHTS, SPEELVELD_TOP), (VOGEL_SCAN_RECHTS, SPEELVELD_BODEM),
                             (0, 255, 255), 2)

                    # Encodeer naar JPG en stuur naar de browser
                    ret, jpeg = cv2.imencode('.jpg', img)
                    self.wfile.write(b"--jpgboundary\r\n")
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', str(len(jpeg.tobytes())))
                    self.end_headers()
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b"\r\n")

                    time.sleep(0.05)  # Max ~20 FPS om oververhitting te voorkomen
            except Exception:
                pass  # Negeer fouten als je de browser tab sluit
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(
                b"<html><head><title>Cyborg Kalibratie</title></head><body style='background:#111; color:white; text-align:center;'>")
            self.wfile.write(b"<h1>Beweeg de iPad en de Camera!</h1>")
            self.wfile.write(b"<img src='/cam.mjpg' style='max-height: 90vh;'></body></html>")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


try:
    server = ThreadedHTTPServer(('0.0.0.0', 8080), CamHandler)
    print("\n" + "=" * 50)
    print("LIVE STREAM IS KLAAR VOOR GEBRUIK!")
    print("1. Open een browser op je Mac/telefoon.")
    print("2. Ga naar: http://<IP_VAN_JE_RASPBERRY_PI>:8080")
    print("=" * 50 + "\n")
    server.serve_forever()
except KeyboardInterrupt:
    print("\nKalibratie netjes gestopt.")
finally:
    server.socket.close()
    picam2.stop()
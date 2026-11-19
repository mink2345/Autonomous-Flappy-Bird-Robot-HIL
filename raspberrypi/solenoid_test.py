from gpiozero import LED
from time import sleep

#see if your setup works and you can control the solenoid
# (GPIO 18)
solenoid = LED(18)

try:
    while True:
        print("[ACTION] Actuatie (HIGH)")
        solenoid.on()
        sleep(0.05)

        print("[ACTION] Rust (LOW)")
        solenoid.off()
        sleep(0.05)
except KeyboardInterrupt:
    solenoid.off()
    print("\n[INFO] Actuatietest veilig afgebroken door gebruiker.")

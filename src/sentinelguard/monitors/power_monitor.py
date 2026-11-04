import time
import winsound
import psutil


def get_power_state():
    battery = psutil.sensors_battery()

    if battery is None:
        return None

    return battery.power_plugged

def alarm_sound():
    try:
        for _ in range(3):
            winsound.Beep(1000, 500)
            winsound.Beep(1800, 500)
    except RuntimeError:
        print("Sesli uyari oynatilamadi.")

def monitor_power():
    print("SentinelGuard - Power Monitor")
    print("Sarj baglantisi izleniyor.")
    print("Durdurmak icin Ctrl+C basin.\n")

    previous_state = get_power_state()

    if previous_state is None:
        print("Pil veya sarj bilgisi okunamadi.")
        return
    elif previous_state is False:
        # Sarj kablosu ilk vakit takili degilse alarm yok.
        print("Sarj kablosu zaten takili degildi. Burasi izlemiyor.")
    else:
         while True:
                current_state = get_power_state()
        
                if previous_state is True and current_state is False:
                    print("ALARM: Sarj kablosu cikarildi!")
                    alarm_sound()
        
                elif previous_state is False and current_state is True:
                    print("Sarj kablosu tekrar takildi.")
        
                elif previous_state is False and current_state is False:
                    print("ALARM: Sarj kablosu hala takilmadi")
                    alarm_sound()
        
                if current_state is not None:
                    previous_state = current_state
        
                time.sleep(1)
        

if __name__ == "__main__":
    try:
        monitor_power()
    except KeyboardInterrupt:
        print("\nIzleme durduruldu.")

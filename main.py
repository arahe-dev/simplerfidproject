from mfrc522 import MFRC522
from machine import Pin, I2C
import utime
import ujson
import network
import time
import ntptime
import sys
import select 
import json
from pico_i2c_lcd import I2cLcd




i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000)

devices = i2c.scan()

lcd = I2cLcd(i2c, devices[0], 2, 16)

reader = MFRC522(spi_id=0, sck=6, miso=4, mosi=7, cs=5, rst=22)
led = Pin(9, Pin.OUT)
ledno = Pin(10, Pin.OUT)

RFID_FILE = "rfid_data.json"
LOG_FILE = "rfid_log.json"
WIFI_FILE = "wifi_config.json"

ADMIN_CARDS = ["2415040701","2854236190"]

def lcd_print(line1, line2=""):
    lcd.clear() 
    lcd.putstr(line1[:16])
    lcd.move_to(0, 1)
    lcd.putstr(line2[:16])
    
    print(line1, line2)


def get_ist_time():
    try:
        ntptime.host = "time.google.com"
        ntptime.settime()
        utc_time = time.localtime()
        ist_time = time.localtime(time.mktime(utc_time) + 19800)
        print("🕒 Fetched IST Time:", ist_time)
        return ist_time
    except Exception as e:
        print("⚠ NTP Sync Error:", e)
        return None

    
def format_time(t):
    return "{:02d}-{:02d}-{:02d} {:02d}:{:02d}".format(
        t[2], t[1], t[0] % 100, t[3], t[4]
    )




try:
    with open(RFID_FILE, "r") as f:
        saved_cards = ujson.load(f)
except OSError:
    saved_cards = []
try:
    with open(LOG_FILE, "r") as f:
        logs = ujson.load(f)
except OSError:
    logs = []
try:
    with open(WIFI_FILE, "r") as f:
        wifi_config = ujson.load(f)
except OSError:
    wifi_config = {"ssid": "", "password": ""}

def save_to_flash():

    with open(RFID_FILE, "w") as f:
        ujson.dump(saved_cards, f)

def save_log():

    with open(LOG_FILE, "w") as f:
        ujson.dump(logs[-20:], f) 

def save_wifi_config():

    with open(WIFI_FILE, "w") as f:
        ujson.dump(wifi_config, f)

def is_valid_connection():
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected() and wlan.ifconfig()[0] != "0.0.0.0"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if is_valid_connection():
        print(f"Already connected to Wi-Fi: {wlan.config('essid')}")
        return

    if wifi_config["ssid"]:
        lcd_print(f"Trying to connect to saved network: {wifi_config['ssid']}")
        wlan.connect(wifi_config["ssid"], wifi_config["password"])
        timeout = 10
        while not is_valid_connection() and timeout > 0:
            utime.sleep(1)
            timeout -= 1
        
        if is_valid_connection():
            print(f"Connected to Wi-Fi: {wlan.ifconfig()[0]}")
            return
        else:
            print("Connection failed! Resetting Wi-Fi credentials.")
            wifi_config["ssid"] = ""
            wifi_config["password"] = ""
            save_wifi_config()

    while True:
        ssid = input("Enter Wi-Fi SSID: ")
        password = input("Enter Wi-Fi Password: ")
        wlan.connect(ssid, password)
        timeout = 10
        while not is_valid_connection() and timeout > 0:
            utime.sleep(1)
            timeout -= 1
        
        if is_valid_connection():
            wifi_config["ssid"] = ssid
            wifi_config["password"] = password
            save_wifi_config()
            print(f"Connected to Wi-Fi: {wlan.ifconfig()[0]}")
            return
        else:
            print("Connection failed! Try again.")

def disconnect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)
    wifi_config["ssid"] = ""
    wifi_config["password"] = ""
    save_wifi_config()
    print("Disconnected from Wi-Fi.")


def show_logs():

    lcd_print("Last 20 Log Entries:")
    if not logs:
        lcd_print("No log data available.")
    else:
        for entry in logs[-20:]: 
            lcd_print(f"Time: {entry['time']} |(Card: {entry['card']})")

button_up = Pin(15, Pin.IN, Pin.PULL_UP)  
button_enter = Pin(14, Pin.IN, Pin.PULL_UP) 
button_down = Pin(13, Pin.IN, Pin.PULL_UP)  

def write_mode():
    lcd_print("\n[WRITE MODE] Scan a card to edit...")
    while True:
        card = scan_card()
        
        if card in saved_cards:
            lcd_print(f"Card {card} is already registered! Press Enter to delete or any other button to cancel.")

            while True:
                utime.sleep(0.2) 

                if button_enter.value() == 0: 
                    saved_cards.remove(card)
                    save_to_flash()
                    lcd_print(f"Card {card} has been deleted!")
                    utime.sleep(0.5)  
                    return  
                
                if button_up.value() == 0 or button_down.value() == 0: 
                    lcd_print("Deletion canceled. Returning...")
                    utime.sleep(0.5) 
                    return 

        saved_cards.append(card)
        save_to_flash()
        lcd_print(f"Card {card} added successfully!")
        return


def show_logs():
    if not logs:
        lcd_print("No logs", "Press Enter")
        while button_enter.value() != 0:
            pass 
        utime.sleep(0.3) 
        return

    log_index = len(logs) - 1 


    while True:
        lcd.clear() 
        entry = logs[log_index]
        lcd_print(f"{entry['time']}", f"{entry['card']}")

        while True:
            if button_up.value() == 0 and log_index > 0:
                log_index -= 1 
                utime.sleep(0.3)  
                break

            if button_down.value() == 0 and log_index < len(logs) - 1:
                log_index += 1  
                utime.sleep(0.3) 
                break  

            if button_enter.value() == 0:
                utime.sleep(0.3)  
                return  
            
event_active = False
event_filename = ""

def start_event():

    global event_active, event_filename
    if event_active:
        lcd_print("Event in prog.", "End first!")
        utime.sleep(1)
        return

    ist_time = get_ist_time()
    event_filename = "E_{}{:02d}{:02d}_{:02d}{:02d}.json".format(ist_time[0] % 100, ist_time[1], ist_time[2], ist_time[3], ist_time[4])
    event_active = True

    try:
        with open(event_filename, "w") as file:
            json.dump([], file)
    except:
        lcd_print("File Error!", "Try again")
        event_active = False
        return

    lcd_print("Event Started", format_time(ist_time))
    utime.sleep(1)


def end_event():
    global event_active, event_filename
    if not event_active:
        lcd_print("No event", "to end!")
        utime.sleep(1)
        return

    lcd_print("Event Ended", "Saving logs...")
    event_active = False
    event_filename = ""
    utime.sleep(1)

def log_event_scan(card_uid, name):
    global event_filename, event_active
    if not event_active:
        return

    try:
        ist_time = get_ist_time()
        timestamp = format_time(ist_time)

        log_entry = {"UID": card_uid, "Name": name, "Time": timestamp}

        try:
            with open(event_filename, "r") as file:
                event_logs = json.load(file)
        except (OSError, ValueError):
            event_logs = []

        event_logs.append(log_entry)

        with open(event_filename, "w") as file:
            json.dump(event_logs, file)

        lcd_print("Event Log:", name[:16])
        utime.sleep(0.5)

    except:
        lcd_print("Log Error!", "Try again")
        utime.sleep(1)

def events_mode():

    options = ["Start Event", "End Event", "Exit"]
    index = 0
    timeout_seconds = 5
    start_time = utime.time()

    while True:
        if utime.time() - start_time > timeout_seconds:
            lcd_print("Timeout!", "Exiting...")
            utime.sleep(1)
            return

        lcd_print("Events Mode", options[index][:16])

        while True:
            if button_up.value() == 0:
                index = (index - 1) % len(options)
                start_time = utime.time()
                utime.sleep(0.3)
                break

            if button_down.value() == 0:
                index = (index + 1) % len(options)
                start_time = utime.time()
                utime.sleep(0.3)
                break

            if button_enter.value() == 0:
                lcd_print("Selected:", options[index][:16])
                utime.sleep(1)

                if index == 0:
                    start_event()
                elif index == 1:
                    end_event()
                elif index == 2:
                    return 

menu_options = ["Write Mode", "View Logs", "Wi-Fi Setup", "Events Mode", "Return"]
current_index = 0

def admin_menu():
    global current_index
    timeout_seconds = 5  
    start_time = utime.time()
    
    while True:
        elapsed_time = utime.time() - start_time 
        if elapsed_time > timeout_seconds:
            lcd_print("Timeout!", "Returning...")
            utime.sleep(1)
            return  
        
        lcd_print("Admin Menu", menu_options[current_index])

        while True:
            if button_up.value() == 0:
                current_index = (current_index - 1) % len(menu_options)
                start_time = utime.time()
                utime.sleep(0.3)
                break

            if button_down.value() == 0: 
                current_index = (current_index + 1) % len(menu_options)
                start_time = utime.time() 
                utime.sleep(0.3)  
                break  

            if button_enter.value() == 0: 
                lcd_print("Selected:", menu_options[current_index])
                utime.sleep(1)  
                
                if current_index == 0:
                    write_mode()
                elif current_index == 1:
                    show_logs()
                elif current_index == 2:
                    if network.WLAN(network.STA_IF).isconnected():
                        lcd_print("Wi-Fi:", wifi_config['ssid'])
                        utime.sleep(2)
                        disconnect_wifi()
                    else:
                        connect_wifi()
                elif current_index == 3:
                    events_mode()
                    utime.sleep(1)  
                elif current_index == 4:
                    lcd_print("Returning", "to scan mode")
                    utime.sleep(1)
                    return  

                return  


def scan_card():
    while True:
        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                card = str(int.from_bytes(bytes(uid), "little", False))
                lcd_print("Card detected: ", card)  
                return card
        utime.sleep_ms(200)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if wlan.isconnected():
    print(f"Connected to Wi-Fi: {wifi_config['ssid']}")
else:
    print("No Wi-Fi connected.")

def scan_mode():
    try:
        while True:
             
            lcd_print("Scan your card!")
            card = scan_card()
            if card is None:
                continue
            current_time = get_ist_time()
            formatted_time = format_time(current_time) if current_time else "Unknown Time"
            if card in ADMIN_CARDS:
                 
                lcd_print("Access Granted!")
                logs.append({"time": formatted_time, "card": card})
                save_log()
                led.value(1)
                utime.sleep(0.5)
                led.value(0)
                admin_menu()
                continue
            if card in saved_cards:
                logs.append({"time": formatted_time, "card": card})
                save_log()
                 
                lcd_print("Access Granted!")
                led.value(1)
                utime.sleep(0.5)
                led.value(0)
            else:
            
                lcd_print("Access Denied!")
                ledno.value(1)
                utime.sleep(0.5)
                ledno.value(0)

            lcd_print("\nReturning to scan mode...")
    except KeyboardInterrupt:
        lcd_print("\nExiting scan mode. Goodbye!")

scan_mode()

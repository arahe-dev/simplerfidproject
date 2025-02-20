# simplerfidproject 
This project uses an RFID-RC522 module with a Raspberry Pi Pico W to authenticate and verify RFID cards. Verified cards trigger a green LED, while unregistered cards activate a red LED. An admin card grants access to a settings menu, allowing users to add/remove cards, view the last 20 scans, configure Wi-Fi for time-sync and remote logging, and set up events for attendance tracking. The system is navigated using three buttons (up, down, select). Logs are stored locally, and timestamps are retrieved via an NTP server when Wi-Fi is enabled.
Pin Loadout
Component    | Pin Name | Pin Number
-------------|----------|------------
I2C SCL      | scl      | 3
I2C SDA      | sda      | 2
MFRC522 SCK  | sck      | 6
MFRC522 MISO | miso     | 4
MFRC522 MOSI | mosi     | 7
MFRC522 CS   | cs       | 5
MFRC522 RST  | rst      | 22
LED          |          | 9
LED No       |          | 10
Button Up    |          | 15
Button Enter |          | 14
Button Down  |          | 13


For further documentation:
https://docs.google.com/document/d/1pCgsp-KPd9friPoHQW31ud2zWDeNDkMBJfdr-3svOIo/edit?usp=sharing

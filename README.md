
# Raspberry Pi 5 Hybrid Fan Control

Bu proje, **Raspberry Pi 5** üzerinde iki adet 5V fanı **GPIO ve MOSFET** ile kontrol eder. Python ile CPU sıcaklığı ölçer, manuel veya otomatik fan kontrolü sağlar ve **systemd servisi** olarak sürekli çalışır.

## Özellikler

- CPU sıcaklığına göre fanları otomatik kontrol eder (55°C üstü açılır, 45°C altına düşene kadar çalışır)  
- Manuel aç/kapa kontrolü  
- Otomatik veya manuel mod seçimi  
- Çalışma süresini takip eder  
- Systemd servisi ile arka planda sürekli çalışır  
- Zengin terminal arayüzü (Rich kütüphanesi ile canlı dashboard)

## Gereksinimler

Python kütüphaneleri:

```bash
sudo apt update
sudo apt install python3-pip
pip3 install gpiozero rich
```
## Donanım


## Mikrodenetleyici
- **Raspberry Pi 5**

## Soğutma Elemanları
- **2 adet 5V Fan**

## Elektronik Bileşenler
- **MOSFET:** MPG30N06
- **Dirençler:**
  - 1 x 200Ω
  - 1 x 10kΩ

## Bağlantı Elemanları
- Bağlantı kabloları


## KURULUM

1. Dosyaları Raspberry Pi’ye kopyalayın:
  ```
  /home/fan/fan_web.py
```
2. Python bağımlılıklarını yükleyin:
  ```
  sudo apt update
sudo apt install python3-pip
pip3 install gpiozero rich
```
3. Fan servisini oluşturun:
    ```/etc/systemd/system/fan.service``` dosyasını oluşturun ve içine aşağıdaki içeriği ekleyin:
  ```
[Unit]
Description=Automatic Fan Control for Raspberry Pi
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 /home/fan/fan_web.py --mode o
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target

```
4. Servisi etkinleştirin ve başlatın:
  ```
sudo systemctl daemon-reload
sudo systemctl enable fan.service
sudo systemctl start fan.service
sudo systemctl status fan.service

```
Servis her zaman çalışacak ve fanları otomatik olarak takip edecektir.

## KULLANIM
- Terminal üzerinden program çalıştırılabilir:
  ```
  python3 fan_web.py --mode o
  ```
  Başlangıç modları:
 - ```a``` : Manuel olarak fan aç
 - ```k``` : Manuel olarak fan kapat
 - ```o``` : Otomatik mod (CPU sıcaklığına göre kontrol)

  Terminal komutları (program çalışırken):
-  ```a``` : Fanı aç
-  ```k``` : Fanı kapat
-  ```o``` : Otomatik moda geç
-  ```q``` : Programdan çık

## Dashboard

Program, Rich kütüphanesi ile CPU sıcaklığı, fan durumu, çalışma süresi ve mod bilgilerini canlı olarak gösterir.


#Alias olarak tanımlama
- daha sonra eğer manuel olarak takip etmek isterseniz 
  ``` sudo systemctl stop fan.service && python3 /home/fan/fan_web.py --mode a ```  çalıştırmaktan ise daha kısa yöntem olan alias kullanabilirsiniz.

```
echo "alias onfan='sudo systemctl stop fan.service && python3 /home/fan/fan_web.py --mode a'" >> ~/.bashrc

```
sayesinde kalıcı olarak alias a tanımlanabilir.

```
root@server:/home/yusuf# onfan  # onfan yazarak artık manuel çalıştırabilirsiniz.
```

```
╭────────────────────────────────── Raspberry Pi 5 Hibrit Fan Kontrol ──────────────────────────────────╮
│ CPU Sıcaklığı:                                                                                 49.6°C │
│                                                    ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│                                                                                                  AÇIK │
│ Fan Durumu:                                                                                           │
│ Çalışma Süresi:                                                                           00s 00d 03s │
│ Mod:                                                                                           MANUEL │
│                                         'a' ile aç, 'k' ile kapat, 'o' ile otomatik moda geç, 'q' ile │
│ Kontrol:                                                                                       çıkış. │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
```                                                                                                   
                                                                               

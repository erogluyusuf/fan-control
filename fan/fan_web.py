import time
import threading
import sys
import argparse
import subprocess
from gpiozero import OutputDevice, CPUTemperature
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.progress_bar import ProgressBar
from queue import Queue

# --- Ayarlar ---
FAN_PIN = 14
THRESHOLD_ON = 55
THRESHOLD_OFF = 45
console = Console()

# --- Donanım Kurulumu ---
try:
    fan = OutputDevice(FAN_PIN)
    cpu = CPUTemperature()
except Exception as e:
    console.print(f"[bold red]Donanım hatası: {e}[/bold red]")
    console.print("[yellow]Program GPIO donanımı olmadan devam ediyor. Fan kontrolü devre dışı.[/yellow]")
    class DummyFan:
        def on(self): pass
        def off(self): pass
        def close(self): pass
    class DummyCPU:
        @property
        def temperature(self):
            return 50 # Test amaçlı sabit değer
    fan = DummyFan()
    cpu = DummyCPU()

# Başlangıç durumları
fan_acik_mi = False
otomatik_mod_aktif = True
fan.off()

# Fan çalışma süresi sayacı
fan_calisma_baslangic_zamani = None
fan_toplam_calisma_suresi = 0

# Komutları işlemek için bir kuyruk
komut_kuyrugu = Queue()

def sicaklik_rengi(temp):
    if temp < 50:
        return "green"
    elif temp < THRESHOLD_ON:
        return "yellow"
    else:
        return "bold red"

def format_sure(saniye):
    saat = int(saniye // 3600)
    dakika = int((saniye % 3600) // 60)
    saniye = int(saniye % 60)
    return f"{saat:02d}s {dakika:02d}d {saniye:02d}s"

def komut_dinleyici():
    """Kullanıcı komutlarını dinler ve kuyruğa ekler."""
    while True:
        try:
            komut = input().lower()
            komut_kuyrugu.put(komut)
        except EOFError:
            break

def generate_dashboard():
    """Anlık durumu gösteren dashboard'u oluşturur."""
    global fan_acik_mi, otomatik_mod_aktif, fan_toplam_calisma_suresi, fan_calisma_baslangic_zamani

    sicaklik = cpu.temperature

    # Otomatik kontrol mantığı
    if otomatik_mod_aktif:
        if sicaklik >= THRESHOLD_ON:
            if not fan_acik_mi:
                fan.on()
                fan_acik_mi = True
                fan_calisma_baslangic_zamani = time.time()
        elif sicaklik <= THRESHOLD_OFF:
            if fan_acik_mi:
                fan.off()
                fan_acik_mi = False
                if fan_calisma_baslangic_zamani is not None:
                    fan_toplam_calisma_suresi += (time.time() - fan_calisma_baslangic_zamani)
                    fan_calisma_baslangic_zamani = None
    
    # Manuel kontrolde süre hesaplama
    if fan_acik_mi and fan_calisma_baslangic_zamani is not None:
        anlik_calisma_suresi = time.time() - fan_calisma_baslangic_zamani
        gorunur_calisma_suresi = fan_toplam_calisma_suresi + anlik_calisma_suresi
    elif fan_acik_mi and fan_calisma_baslangic_zamani is None:
        fan_calisma_baslangic_zamani = time.time()
        gorunur_calisma_suresi = fan_toplam_calisma_suresi
    else:
        gorunur_calisma_suresi = fan_toplam_calisma_suresi

    # Arayüz Tablosu
    dashboard_table = Table.grid(expand=True)
    dashboard_table.add_column(justify="left", width=30)
    dashboard_table.add_column(justify="right", width=50)

    # CPU Sıcaklık ve Grafiği
    renk = sicaklik_rengi(sicaklik)
    sicaklik_str = f"[{renk}]{sicaklik:.1f}°C[/{renk}]"
    
    bar_uzunlugu = 50
    dolu_kisim = int(sicaklik / 100 * bar_uzunlugu)
    bos_kisim = bar_uzunlugu - dolu_kisim
    grafik_str = f"[{renk}]{'█' * dolu_kisim}[/][bold grey]{'░' * bos_kisim}[/]"
    
    dashboard_table.add_row("[bold]CPU Sıcaklığı:[/]", sicaklik_str)
    dashboard_table.add_row("", grafik_str)

    # Fan Durumu ve Süresi
    if fan_acik_mi:
        fan_durumu_str = "[bold green]AÇIK[/bold green]"
    else:
        fan_durumu_str = "[bold blue]KAPALI[/bold blue]"

    dashboard_table.add_row("\n[bold]Fan Durumu:[/]", fan_durumu_str)
    dashboard_table.add_row("[bold]Çalışma Süresi:[/]", format_sure(gorunur_calisma_suresi))

    # Mod Durumu
    mod_durumu_str = "[bold green]OTOMATİK[/bold green]" if otomatik_mod_aktif else "[bold yellow]MANUEL[/bold yellow]"
    dashboard_table.add_row("[bold]Mod:[/]", mod_durumu_str)

    # Kontrol bilgisi
    dashboard_table.add_row("\n[bold]Kontrol:[/]", "[yellow]'a' ile aç, 'k' ile kapat, 'o' ile otomatik moda geç, 'q' ile çıkış.[/yellow]")

    return Panel(dashboard_table, title="[bold cyan]Raspberry Pi 5 Hibrit Fan Kontrol[/]", border_style="cyan")

def check_and_start_service(service_name):
    """Belirtilen servisin durumunu kontrol eder ve durdurulduysa yeniden başlatır."""
    try:
        # Servis durumunu kontrol et
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", service_name],
            capture_output=True,
            text=True
        )
        
        # Eğer servis aktif değilse başlat
        if "inactive" in result.stdout:
            console.print(f"[green]Servis {service_name} durdurulmuş, şimdi başlatılıyor...[/green]")
            subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
            console.print(f"[green]Servis {service_name} başarıyla başlatıldı.[/green]")
        else:
            console.print(f"[blue]Servis {service_name} zaten çalışıyor. İşlem yapılmadı.[/blue]")
            
    except FileNotFoundError:
        console.print("[bold red]Hata: 'systemctl' komutu bulunamadı.[/bold red]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Hata: '{service_name}' servisi başlatılamadı. Hata kodu: {e.returncode}[/bold red]")

# --- Ana Program Akışı ---

# ... (Mevcut kodunuzun geri kalanı aynı kalacak) ...

parser = argparse.ArgumentParser(description="Raspberry Pi Hibrit Fan Kontrol Uygulaması")
parser.add_argument('--mode', type=str, help="Başlangıç fan modu ('a' - aç, 'k' - kapat, 'o' - otomatik)", default='o')
args = parser.parse_args()

if args.mode == 'a':
    otomatik_mod_aktif = False
    fan.on()
    fan_acik_mi = True
elif args.mode == 'k':
    otomatik_mod_aktif = False
    fan.off()
    fan_acik_mi = False
elif args.mode == 'o':
    otomatik_mod_aktif = True
else:
    console.print("[red]Geçersiz başlangıç modu! Otomatik mod ile devam ediliyor.[/red]")
    otomatik_mod_aktif = True

komut_thread = threading.Thread(target=komut_dinleyici, daemon=True)
komut_thread.start()

try:
    with Live(generate_dashboard(), screen=True, redirect_stderr=False, refresh_per_second=4) as live:
        while True:
            while not komut_kuyrugu.empty():
                command = komut_kuyrugu.get()
                
                if command == 'a':
                    otomatik_mod_aktif = False
                    fan.on()
                    fan_acik_mi = True
                elif command == 'k':
                    otomatik_mod_aktif = False
                    fan.off()
                    fan_acik_mi = False
                elif command == 'o':
                    otomatik_mod_aktif = True
                    console.print("[green]Otomatik moda geçildi.[/green]")
                elif command == 'q':
                    live.stop()
                    break
                else:
                    console.print("[red]Geçersiz komut![/red]")
            
            live.update(generate_dashboard())
            time.sleep(0.5)

except KeyboardInterrupt:
    fan.off()
    console.print("\n[yellow]Program sonlandırıldı. Fan kapatıldı.[/yellow]")
    check_and_start_service("fan.service")
except Exception as e:
    fan.off()
    console.print(f"[bold red]Bir hata oluştu: {e}[/bold red]")
    check_and_start_service("fan.service")

finally:
    fan.close()
    check_and_start_service("fan.service")

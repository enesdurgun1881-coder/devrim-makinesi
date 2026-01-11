
import json
import os
import time

def main():
    print("=================================================")
    print("   📸 INSTAGRAM OTURUM OLUŞTURUCU (SESSION)    ")
    print("=================================================")
    print("Bu araç, Instagram'ın bulut sunucularını engellemesini")
    print("aşmak için yerel bilgisayarınızda oturum açar.")
    print("")
    
    try:
        from instagrapi import Client
    except ImportError:
        print("HATA: 'instagrapi' kütüphanesi yüklü değil.")
        print("Lütfen önce şu komutu çalıştırın: pip install instagrapi")
        input("\nÇıkmak için Enter'a basın...")
        return

    username = input("Kullanıcı Adı: ").strip()
    password = input("Şifre: ").strip()
    
    print("\n🔄 Giriş yapılıyor... (Lütfen bekleyin)")
    
    cl = Client()
    
    try:
        # Rastgele bir cihaz gibi davran
        cl.delay_range = [1, 3]
        cl.login(username, password)
        
        print("\n✅ BAŞARILI! Giriş yapıldı.")
        
        # Session datasını al
        settings = cl.get_settings()
        
        # JSON'a çevir
        json_output = json.dumps(settings)
        
        print("\n👇 AŞAĞIDAKİ KODU KOPYALA VE SİTEDEKİ KUTUYA YAPIŞTIR 👇")
        print("==========================================================")
        print(json_output)
        print("==========================================================")
        
        # Dosyaya da kaydet
        with open("session_kodu.txt", "w") as f:
            f.write(json_output)
            
        print(f"\nℹ️ Bu kod ayrıca 'session_kodu.txt' dosyasına kaydedildi.")
        
    except Exception as e:
        print(f"\n❌ HATA OLUŞTU: {e}")
        print("Şifrenizi kontrol edin veya 2FA (İki Aşamalı Doğrulama) varsa kapatıp tekrar deneyin.")

    input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    main()

from google import genai

# API KEY'İNİ BURAYA YAZMAYI UNUTMA!
API_KEY = "AIzaSyAgcsXUyxdt1nJrdmYfgV9rsgxKLBVIp0k" 
client = genai.Client(api_key=API_KEY)

print(f"[*] Bağlantı Kuruluyor...")

try:
    # HATA BURADAYDI: .list_models() yerine .list() yazıyoruz.
    for model in client.models.list():
        # Sadece "gemini" ile başlayanları gösterelim ki liste uzamasın
        if "gemini" in model.name:
            print(f"✅ BULUNDU: {model.name}")
            
except Exception as e:
    print(f"\n[X] KRİTİK HATA: {e}")
    print("API Key'inde sorun olabilir veya internet bağlantın yok.")
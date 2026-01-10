import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
import os
from io import BytesIO
import urllib3
import random
import time

# SSL Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
API_KEY = "AIzaSyAgcsXUyxdt1nJrdmYfgV9rsgxKLBVIp0k"  
client = genai.Client(api_key=API_KEY)

HEDEF_HABER_SAYISI = 3 
ARSIV_DOSYASI = "arsiv.txt" # Hafıza dosyamız bu

# MODELLER
TEXT_MODEL_ID = "gemini-2.5-flash"
IMAGE_MODEL_ID = "imagen-3.0-generate-001"

CHP_ANAHTAR_KELIMELER = [
    "chp", "cumhuriyet halk partisi",
    "özgür özel", "ekrem imamoğlu", "mansur yavaş", 
    "özgür çelik", "veli ağbaba", "faik öztrak",
    "chp'li", "chp heyeti", "ana muhalefet",
    "istanbul büyükşehir belediyesi", "ibb", "ankara büyükşehir"
]

RSS_KAYNAKLARI = [
    "https://www.sozcu.com.tr/feeds-rss-category-gundem",
    "https://www.cumhuriyet.com.tr/rss/kategori/siyaset.xml",
    "https://www.gazeteduvar.com.tr/rss",
    "https://t24.com.tr/rss",
    "https://www.ntv.com.tr/siyaset.rss",
    "https://www.hurriyet.com.tr/rss/gundem",
    "https://www.milliyet.com.tr/rss/rssnew/siyaset.xml",
    "https://www.haberturk.com/rss/kategori/gundem.xml",
    "https://www.cnnturk.com/feed/rss/turkiye/news",
    "https://www.karar.com/rss/gundem.xml"
]

# --- HAFIZA SİSTEMİ ---
def arsivi_yukle():
    """Daha önce işlenen haberlerin linklerini getirir."""
    if not os.path.exists(ARSIV_DOSYASI):
        return []
    with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
        return f.read().splitlines()

def arsive_kaydet(link):
    """İşlenen haberi hafızaya atar."""
    with open(ARSIV_DOSYASI, "a", encoding="utf-8") as f:
        f.write(link + "\n")

# --- RESİM VE AI FONKSİYONLARI ---
def yapay_zeka_resim_ciz_chp():
    print(f"      [*] 🎨 Orijinal yok, AI Ressam Çiziyor...")
    prompt = """
    A high quality, photorealistic close-up shot of a waving Republican People's Party (CHP) flag with 6 arrows next to a Turkish flag. 
    Background: Blurred political rally atmosphere, crowd, dramatic lighting. 
    Style: Professional news photography.
    """
    try:
        response = client.models.generate_images(
            model=IMAGE_MODEL_ID,
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="1:1")
        )
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            return Image.open(BytesIO(image_bytes))
    except:
        return None
    return None

def resim_indir_zorla(haber_linki):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
    }
    try:
        r = requests.get(haber_linki, headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        img_url = None
        meta_img = soup.find('meta', property='og:image')
        if meta_img: img_url = meta_img['content']
        
        if not img_url:
            meta_tw = soup.find('meta', property='twitter:image')
            if meta_tw: img_url = meta_tw['content']

        if img_url:
            img_resp = requests.get(img_url, headers=headers, timeout=10, verify=False)
            return Image.open(BytesIO(img_resp.content))
    except:
        return None
    return None

def toplu_haber_tara(limit=3):
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Hafızayı yükle
    gecmis_haberler = arsivi_yukle()
    print(f"[*] Hafızada {len(gecmis_haberler)} adet eski haber var.")
    print(f"[*] HEDEF: {limit} adet YENİ CHP Haberi Bulmak...")
    
    toplanan_haberler = [] 
    
    random.shuffle(RSS_KAYNAKLARI)
    
    for url in RSS_KAYNAKLARI:
        if len(toplanan_haberler) >= limit: break
            
        try:
            r = requests.get(url, headers=headers, timeout=10, verify=False)
            try: soup = BeautifulSoup(r.content, 'xml')
            except: soup = BeautifulSoup(r.content, 'html.parser')

            items = soup.find_all('item')
            if not items: continue

            for item in items:
                if len(toplanan_haberler) >= limit: break
                
                baslik = item.find('title').text.strip()
                link = item.find('link').text.strip()
                
                # --- HAFIZA KONTROLÜ (EN ÖNEMLİ KISIM) ---
                if link in gecmis_haberler:
                    # Ekrana basmıyoruz ki kalabalık olmasın, sessizce geçiyoruz
                    continue
                
                # FİLTRE
                if any(k in baslik.lower() for k in CHP_ANAHTAR_KELIMELER):
                    print(f"\n[+] YENİ Aday Haber: {baslik[:50]}...")
                    
                    # Resmi al
                    img_obj = resim_indir_zorla(link)
                    if not img_obj:
                        img_obj = yapay_zeka_resim_ciz_chp()
                    
                    if img_obj:
                        print(f"    ✅ Haber ve Resim Hazır! ({len(toplanan_haberler)+1}/{limit})")
                        toplanan_haberler.append((baslik, img_obj, link)) # Linki de sakla ki sonra kaydedelim
                    else:
                        print("    [X] Görsel çıkmadı, pas geçiliyor.")
                        
        except Exception:
            continue
            
    return toplanan_haberler

def caption_yaz(haber_basligi):
    prompt = f"""
    Haber: {haber_basligi}
    Rol: 'Daily CHP' fanatik admini.
    Amaç: CHP tabanını ateşlemek.
    Üslup: Sert, coşkulu, Atatürkçü.
    Uzunluk: Kısa, Instagram caption formatında.
    Hashtagler: #CHP #ÖzgürÖzel #İmamoğlu #Halkınİktidarı #Gündem
    """
    try:
        response = client.models.generate_content(model=TEXT_MODEL_ID, contents=prompt)
        return response.text
    except:
        return "Caption oluşturulamadı."

def logoyu_bas_ve_kaydet(img_obj, logo_yolu, dosya_adi):
    try:
        img = img_obj.convert("RGBA")
        
        if os.path.exists(logo_yolu):
            logo = Image.open(logo_yolu).convert("RGBA")
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
            
            genislik, yukseklik = img.size
            oran = (genislik * 0.25) / logo.width
            yeni_boyut = (int(logo.width * oran), int(logo.height * oran))
            logo = logo.resize(yeni_boyut, Image.Resampling.LANCZOS)
            
            konum = (genislik - logo.width - 40, yukseklik - logo.height - 40)
            img.paste(logo, konum, logo)
        
        img.convert("RGB").save(dosya_adi)
        print(f"💾 KAYDEDİLDİ: {dosya_adi}")
        return True
    except Exception as e:
        print(f"[X] Kayıt hatası: {e}")
        return False

# --- FABRİKA BAŞLIYOR ---
print("[*] SERİ ÜRETİM MODU (HAFIZALI) BAŞLATILDI 🧠")

stok = toplu_haber_tara(limit=HEDEF_HABER_SAYISI)

if stok:
    print(f"\n[*] Toplam {len(stok)} adet YENİ içerik üretime giriyor...")
    print("-" * 40)
    
    sayac = 1
    # Klasördeki mevcut post sayısını bulalım ki üzerine yazmayalım
    mevcut_dosyalar = len([name for name in os.listdir('.') if name.startswith("post_") and name.endswith(".jpg")])
    baslangic_no = mevcut_dosyalar + 1

    for baslik, resim, link in stok:
        dosya_ismi = f"post_{baslangic_no}.jpg"
        
        print(f"\n[{sayac}] İşleniyor: {baslik[:40]}...")
        metin = caption_yaz(baslik)
        
        print(f"[METİN]: {metin[:100]}...")
        basari = logoyu_bas_ve_kaydet(resim, "logo.png", dosya_ismi)
        
        # Eğer başarıyla kaydedildiyse ARŞİVE EKLE
        if basari:
            arsive_kaydet(link)
            print("🔐 Haber arşive işlendi (Bir daha paylaşılmayacak).")

        sayac += 1
        baslangic_no += 1
        
    print(f"\n✅✅✅ TÜM OPERASYON BİTTİ!")
else:
    print("\n[X] Yeni haber bulunamadı. (Eskileri zaten arşivde).")
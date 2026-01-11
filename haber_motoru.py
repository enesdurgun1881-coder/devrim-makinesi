"""
CHP Haber Motoru - Modüler Versiyon
Orijinal makine.py'den refactor edildi
"""

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import os
from io import BytesIO
import urllib3
import random
import json
import time
from datetime import datetime

# SSL Sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("⚠️ UYARI: GOOGLE_API_KEY bulunamadı! AI özellikleri çalışmayabilir.")
try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"GenAI Config Hatası: {e}")

CONFIG_DOSYASI = "config.json"
ARSIV_DOSYASI = "arsiv.txt"
POST_KLASORU = "posts"

# Log callback fonksiyonu (web arayüzü için)
_log_callback = None

def set_log_callback(callback):
    """Log mesajlarını web arayüzüne iletmek için callback ayarla"""
    global _log_callback
    _log_callback = callback

def log(mesaj, tip="info"):
    """Loglama fonksiyonu"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {mesaj}"
    print(formatted)
    if _log_callback:
        _log_callback(formatted, tip)

# --- CONFIG YÖNETİMİ ---
def config_yukle():
    """Ayarları JSON dosyasından yükle"""
    if os.path.exists(CONFIG_DOSYASI):
        with open(CONFIG_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "hedef_haber_sayisi": 3,
        "text_model": "gemini-1.5-flash",
        "image_model": "imagen-3.0-generate-001",
        "anahtar_kelimeler": [],
        "rss_kaynaklari": []
    }

def config_kaydet(config):
    """Ayarları JSON dosyasına kaydet"""
    with open(CONFIG_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

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

def arsivi_temizle():
    """Arşivi tamamen temizle"""
    if os.path.exists(ARSIV_DOSYASI):
        os.remove(ARSIV_DOSYASI)
        log("🗑️ Arşiv temizlendi!", "warning")
        return True
    return False

# --- İSTATİSTİKLER ---
def istatistikleri_getir():
    """Dashboard için istatistikleri topla"""
    config = config_yukle()
    arsiv = arsivi_yukle()
    
    # Post sayısını hesapla
    if not os.path.exists(POST_KLASORU):
        os.makedirs(POST_KLASORU)
    
    post_dosyalari = [f for f in os.listdir('.') if f.startswith("post_") and f.endswith(".jpg")]
    
    return {
        "toplam_post": len(post_dosyalari),
        "arsiv_sayisi": len(arsiv),
        "rss_kaynak_sayisi": len(config.get("rss_kaynaklari", [])),
        "anahtar_kelime_sayisi": len(config.get("anahtar_kelimeler", [])),
        "hedef_haber_sayisi": config.get("hedef_haber_sayisi", 3)
    }

# --- POST YÖNETİMİ ---
def postlari_listele():
    """Mevcut postları listele"""
    postlar = []
    for f in sorted(os.listdir('.'), reverse=True):
        if f.startswith("post_") and f.endswith(".jpg"):
            yol = os.path.abspath(f)
            postlar.append({
                "dosya": f,
                "yol": yol,
                "boyut": os.path.getsize(f),
                "tarih": datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M")
            })
    return postlar

def post_sil(dosya_adi):
    """Bir postu sil"""
    if os.path.exists(dosya_adi):
        os.remove(dosya_adi)
        return True
    return False

# --- RESİM VE AI FONKSİYONLARI ---
def yapay_zeka_resim_ciz_chp():
    # Pollinations kullanıldığı için burası devre dışı bırakıldı
    return None

def resim_indir_zorla(haber_linki):
    """Haber sayfasından en yüksek kaliteli görseli indir"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
    }
    try:
        r = requests.get(haber_linki, headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        img_url = None
        
        # 1. og:image - genellikle en iyi kalite
        meta_img = soup.find('meta', property='og:image')
        if meta_img: 
            img_url = meta_img['content']
            # Bazı siteler küçük thumbnail veriyor, büyük versiyonu ara
            if 'width=' in img_url or 'w=' in img_url or 'thumb' in img_url.lower():
                # Küçük boyut parametrelerini büyükle değiştir
                import re
                img_url = re.sub(r'width=\d+', 'width=1200', img_url)
                img_url = re.sub(r'w=\d+', 'w=1200', img_url)
                img_url = re.sub(r'h=\d+', 'h=1200', img_url)
        
        # 2. twitter:image - alternatif yüksek kalite
        if not img_url:
            meta_tw = soup.find('meta', property='twitter:image')
            if meta_tw: img_url = meta_tw['content']
        
        # 3. Makaledeki en büyük img tag'i
        if not img_url:
            all_imgs = soup.find_all('img', src=True)
            for img in all_imgs:
                src = img.get('src', '')
                # Küçük ikonları atla
                if 'logo' in src.lower() or 'icon' in src.lower() or 'avatar' in src.lower():
                    continue
                if src.startswith('http') and ('.jpg' in src or '.png' in src or '.webp' in src):
                    img_url = src
                    break

        if img_url:
            log(f"📷 Görsel indiriliyor: {img_url[:60]}...", "info")
            img_resp = requests.get(img_url, headers=headers, timeout=15, verify=False)
            img = Image.open(BytesIO(img_resp.content))
            log(f"📐 Görsel boyutu: {img.size[0]}x{img.size[1]}", "info")
            return img
    except Exception as e:
        log(f"⚠️ Görsel indirme hatası: {e}", "warning")
        return None
    return None

def caption_yaz(haber_basligi):
    """AI ile caption oluştur - dinamik model keşfi ile"""
    
    # API key kontrolü
    if not API_KEY:
        log("⚠️ API Key yok, fallback caption kullanılıyor", "warning")
        return _fallback_caption(haber_basligi)
    
    prompt = f"""
    Haber: {haber_basligi}
    Rol: 'Daily CHP' fanatik admini.
    Amaç: CHP tabanını ateşlemek.
    Üslup: Sert, coşkulu, Atatürkçü.
    Uzunluk: Kısa, Instagram caption formatında.
    Hashtagler: #CHP #ÖzgürÖzel #İmamoğlu #Halkınİktidarı #Gündem
    """
    
    # Önce mevcut modelleri keşfet
    available_models = []
    try:
        log("🔍 Mevcut modeller keşfediliyor...", "info")
        for m in genai.list_models():
            if 'generateContent' in str(m.supported_generation_methods):
                model_name = m.name.replace("models/", "")
                available_models.append(model_name)
        log(f"📋 Bulunan modeller: {available_models[:5]}...", "info")
    except Exception as e:
        log(f"⚠️ Model listesi alınamadı: {str(e)[:50]}", "warning")
        # Varsayılan liste kullan
        available_models = ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
    
    # Tercih sırasına göre dene
    preferred_order = [
        "gemini-1.5-flash",
        "gemini-1.5-pro", 
        "gemini-pro",
        "gemini-1.0-pro",
        "gemini-1.0-pro-latest"
    ]
    
    # Mevcut olanları tercih sırasına göre sırala
    models_to_try = [m for m in preferred_order if m in available_models]
    # Listede olmayan ama mevcut olanları da ekle
    models_to_try.extend([m for m in available_models if m not in models_to_try and "gemini" in m.lower()])
    
    if not models_to_try:
        models_to_try = preferred_order  # Son çare: hepsini dene
    
    for model_name in models_to_try[:5]:  # Max 5 deneme
        try:
            log(f"📝 Caption deniyor ({model_name})...", "info")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            if response and response.text:
                caption = response.text.strip()
                log(f"✅ Caption hazır ({model_name}): {caption[:50]}...", "success")
                return caption
        except Exception as e:
            error_msg = str(e)[:100]
            log(f"⚠️ Model hatası ({model_name}): {error_msg}", "warning")
            continue
    
    # Tüm modeller başarısız olduysa fallback kullan
    log("⚠️ Tüm modeller başarısız, fallback caption kullanılıyor", "warning")
    return _fallback_caption(haber_basligi)

def _fallback_caption(haber_basligi):
    """Fallback caption şablonları"""
    fallback_templates = [
        f"🔴 {haber_basligi}\n\n💪 Halkın iktidarı yakındır! CHP olarak milletimizin yanındayız, yanında olmaya devam edeceğiz!\n\n#CHP #ÖzgürÖzel #İmamoğlu #Halkınİktidarı #Gündem #DailyCHP #Siyaset",
        f"🔴 {haber_basligi}\n\n✊ Mustafa Kemal'in izinde, halkın yanında! Adalet, eşitlik ve özgürlük için mücadelemiz sürecek!\n\n#CHP #ÖzgürÖzel #İmamoğlu #Halkınİktidarı #Gündem #DailyCHP #Siyaset",
        f"🔴 {haber_basligi}\n\n🇹🇷 Altı okumuz rehberimiz, milletimiz gücümüz! CHP olarak her zaman halkın sesi olacağız!\n\n#CHP #ÖzgürÖzel #İmamoğlu #Halkınİktidarı #Gündem #DailyCHP #Siyaset"
    ]
    return random.choice(fallback_templates)


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
        log(f"💾 Kaydedildi: {dosya_adi}", "success")
        return True
    except Exception as e:
        log(f"❌ Kayıt hatası: {e}", "error")
        return False

def metin_satir_bolu(text, font, max_width, draw):
    """Metni satırlara böl"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

def profesyonel_post_olustur(img_obj, baslik, logo_yolu, dosya_adi):
    """
    Profesyonel Instagram postu oluştur:
    - Başlık metni gradient arka plan ile
    - Logo sağ alt köşede
    - Modern tasarım
    """
    try:
        img = img_obj.convert("RGBA")
        width, height = img.size
        
        # Kare kırpma (center crop) - en iyi kalite için 1080x1080 sabit boyut
        # Görüntü bozulmaz, sadece ortadan kırpılır
        if width != height:
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))
        
        # 1080x1080 - Instagram optimum kalite
        img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        genislik, yukseklik = img.size
        log(f"📐 Post boyutu: {genislik}x{yukseklik} (HD)", "info")
        
        # Gradient overlay oluştur (alt kısım için)
        gradient = Image.new('RGBA', (genislik, yukseklik), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        
        # Alt gradient (yukarıdan aşağı koyulaşan)
        for y in range(yukseklik // 2, yukseklik):
            alpha = int(220 * (y - yukseklik // 2) / (yukseklik // 2))
            gradient_draw.line([(0, y), (genislik, y)], fill=(0, 0, 0, alpha))
        
        # Üst gradient (marka alanı için)
        for y in range(0, 120):
            alpha = int(180 * (1 - y / 120))
            gradient_draw.line([(0, y), (genislik, y)], fill=(0, 0, 0, alpha))
        
        img = Image.alpha_composite(img, gradient)
        
        draw = ImageDraw.Draw(img)
        
        # Font yükle (sistem fontu veya default)
        font_size = 42
        title_font = None
        
        # Türkçe destekli font ara
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, font_size)
                break
        
        if not title_font:
            title_font = ImageFont.load_default()
        
        # Başlığı satırlara böl
        max_text_width = genislik - 100
        lines = metin_satir_bolu(baslik, title_font, max_text_width, draw)
        
        # Metin pozisyonu hesapla (alt kısımda)
        line_height = font_size + 10
        total_text_height = len(lines) * line_height
        text_y = yukseklik - total_text_height - 180  # Logo için alan bırak
        
        # CHP kırmızı accent çizgisi
        accent_y = text_y - 20
        draw.rectangle([(50, accent_y), (150, accent_y + 4)], fill=(227, 10, 23, 255))
        
        # Başlık metnini yaz
        for line in lines:
            # Gölge efekti
            draw.text((52, text_y + 2), line, font=title_font, fill=(0, 0, 0, 180))
            # Ana metin
            draw.text((50, text_y), line, font=title_font, fill=(255, 255, 255, 255))
            text_y += line_height
        
        # Marka etiketi
        brand_font_size = 24
        brand_font = title_font
        try:
            for font_path in font_paths:
                if os.path.exists(font_path):
                    brand_font = ImageFont.truetype(font_path, brand_font_size)
                    break
        except:
            pass
        
        draw.text((50, 40), "DAILY CHP", font=brand_font, fill=(227, 10, 23, 255))
        
        # Logo ekle (sağ alt köşe, eşit mesafe)
        if os.path.exists(logo_yolu):
            logo = Image.open(logo_yolu).convert("RGBA")
            logo_oran = (genislik * 0.22) / logo.width  # %22 - dengeli boyut
            yeni_logo_boyut = (int(logo.width * logo_oran), int(logo.height * logo_oran))
            logo = logo.resize(yeni_logo_boyut, Image.Resampling.LANCZOS)
            
            margin = 40  # Kenarlardan eşit mesafe
            logo_x = genislik - logo.width - margin
            logo_y = yukseklik - logo.height - margin
            img.paste(logo, (logo_x, logo_y), logo)
        
        # Kaydet - Maksimum kalite (Instagram için HD)
        img.convert("RGB").save(dosya_adi, quality=100, subsampling=0, optimize=True)
        log(f"💾 HD post kaydedildi: {dosya_adi}", "success")
        return True
        
    except Exception as e:
        log(f"❌ Görsel işleme hatası: {e}", "error")
        # Fallback: Basit kayıt
        return logoyu_bas_ve_kaydet(img_obj, logo_yolu, dosya_adi)

# --- CAPTION VERİTABANI ---
CAPTION_DB = "captions.json"

def caption_kaydet(dosya_adi, baslik, caption, link):
    """Caption bilgilerini JSON'a kaydet"""
    db = {}
    if os.path.exists(CAPTION_DB):
        with open(CAPTION_DB, "r", encoding="utf-8") as f:
            db = json.load(f)
    
    db[dosya_adi] = {
        "baslik": baslik,
        "caption": caption,
        "link": link,
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(CAPTION_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def caption_getir(dosya_adi):
    """Bir post için caption bilgisini getir"""
    if not os.path.exists(CAPTION_DB):
        return None
    
    with open(CAPTION_DB, "r", encoding="utf-8") as f:
        db = json.load(f)
    
    return db.get(dosya_adi)

def tum_captionlari_getir():
    """Tüm captionları getir"""
    if not os.path.exists(CAPTION_DB):
        return {}
    
    with open(CAPTION_DB, "r", encoding="utf-8") as f:
        return json.load(f)

# --- ANA TARAMA FONKSİYONU ---
def haber_tara(limit=None, progress_callback=None):
    """
    Ana haber tarama fonksiyonu
    progress_callback: (current, total, message) şeklinde callback
    """
    config = config_yukle()
    if limit is None:
        limit = config.get("hedef_haber_sayisi", 3)
    
    anahtar_kelimeler = config.get("anahtar_kelimeler", [])
    rss_kaynaklari = config.get("rss_kaynaklari", [])
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Hafızayı yükle
    gecmis_haberler = arsivi_yukle()
    log(f"📚 Hafızada {len(gecmis_haberler)} eski haber var.", "info")
    log(f"🎯 Hedef: {limit} yeni CHP haberi bulmak...", "info")
    
    toplanan_haberler = []
    random.shuffle(rss_kaynaklari)
    
    for i, url in enumerate(rss_kaynaklari):
        if len(toplanan_haberler) >= limit:
            break
            
        if progress_callback:
            progress_callback(i, len(rss_kaynaklari), f"RSS taraniyor: {url[:30]}...")
            
        try:
            r = requests.get(url, headers=headers, timeout=10, verify=False)
            try:
                soup = BeautifulSoup(r.content, 'xml')
            except:
                soup = BeautifulSoup(r.content, 'html.parser')

            items = soup.find_all('item')
            if not items:
                continue

            for item in items:
                if len(toplanan_haberler) >= limit:
                    break
                
                baslik = item.find('title').text.strip()
                link = item.find('link').text.strip()
                
                # Hafıza kontrolü
                if link in gecmis_haberler:
                    continue
                
                # Filtre
                if any(k in baslik.lower() for k in anahtar_kelimeler):
                    log(f"📰 Yeni haber bulundu: {baslik[:50]}...", "success")
                    
                    # Resmi al
                    img_obj = resim_indir_zorla(link)
                    if not img_obj:
                        # Fallback: Basit bir placeholder oluştur
                        log("⚠️ Görsel indirilemedi, placeholder oluşturuluyor...", "warning")
                        img_obj = Image.new('RGB', (1080, 1080), color=(200, 16, 46))  # CHP kırmızısı
                    
                    if img_obj:
                        log(f"✅ Haber hazır! ({len(toplanan_haberler)+1}/{limit})", "success")
                        toplanan_haberler.append((baslik, img_obj, link))
                        
        except Exception as e:
            log(f"⚠️ RSS hatası: {str(e)[:50]}", "warning")
            continue
            
    return toplanan_haberler

def uretim_baslat(progress_callback=None, profesyonel_mod=True):
    """
    Tam üretim döngüsü
    profesyonel_mod: True ise resmin üzerine başlık yazılır
    """
    log("🚀 Seri üretim başlatıldı!", "info")
    
    # --- DIAGNOSTIC START ---
    log("🔍 Sistem Kontrolü Yapılıyor...", "info")
    if not API_KEY:
        log("❌ KRİTİK HATA: GOOGLE_API_KEY bulunamadı! Render Environment ayarlarını kontrol et.", "error")
    else:
        log(f"✅ API Key tespit edildi: {API_KEY[:5]}...{API_KEY[-3:]}", "success")
        
    try:
        import google.generativeai as genai_debug
        log(f"ℹ️ Kütüphane Sürümü: {genai_debug.__version__}", "info")
        
        # Test bağlantısı
        models = list(genai_debug.list_models())
        log(f"📡 API Bağlantısı Başarılı! {len(models)} model erişilebilir.", "success")
    except Exception as e:
        log(f"⚠️ API Bağlantı Testi Başarısız: {str(e)}", "warning")
    # --- DIAGNOSTIC END ---
    
    stok = haber_tara(progress_callback=progress_callback)
    
    if not stok:
        log("❌ Yeni haber bulunamadı (eskiler arşivde).", "warning")
        return []
    
    log(f"📦 {len(stok)} içerik üretime giriyor...", "info")
    
    # Mevcut post sayısını bul
    mevcut_dosyalar = len([name for name in os.listdir('.') if name.startswith("post_") and name.endswith(".jpg")])
    baslangic_no = mevcut_dosyalar + 1
    
    uretilen_postlar = []
    
    for i, (baslik, resim, link) in enumerate(stok):
        dosya_ismi = f"post_{baslangic_no}.jpg"
        
        log(f"[{i+1}/{len(stok)}] İşleniyor: {baslik[:40]}...", "info")
        
        if progress_callback:
            progress_callback(i, len(stok), f"Post üretiliyor: {dosya_ismi}")
        
        # Caption oluştur
        metin = caption_yaz(baslik)
        log(f"📝 Caption hazır!", "info")
        
        # Resmi işle (profesyonel mod veya basit)
        if profesyonel_mod:
            basari = profesyonel_post_olustur(resim, baslik, "logo.png", dosya_ismi)
        else:
            basari = logoyu_bas_ve_kaydet(resim, "logo.png", dosya_ismi)
        
        if basari:
            # Arşive kaydet
            arsive_kaydet(link)
            
            # Caption'ı veritabanına kaydet
            caption_kaydet(dosya_ismi, baslik, metin, link)
            log("💾 Caption veritabanına kaydedildi.", "info")
            
            log("🔐 Haber arşive eklendi.", "success")
            uretilen_postlar.append({
                "dosya": dosya_ismi,
                "baslik": baslik,
                "caption": metin,
                "link": link
            })
        
        baslangic_no += 1
        
        # Rate limit koruması - Google API'nin nefes almasını bekle
        if i < len(stok) - 1:  # Son haber değilse bekle
            log("💤 API soğutma molası (15 saniye)...", "info")
            time.sleep(15)
    
    log(f"✅ Operasyon tamamlandı! {len(uretilen_postlar)} post üretildi.", "success")
    return uretilen_postlar


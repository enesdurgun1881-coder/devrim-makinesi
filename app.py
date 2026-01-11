"""
CHP Devrim Makinesi - Web Dashboard
Flask tabanlı modern arayüz
"""

# Eventlet kaldırıldı - Threading kullanılıyor

# Recursion limit artır (Render'da gerekli olabiliyor)
import sys
sys.setrecursionlimit(3000)

from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for, session
from flask_socketio import SocketIO, emit
from functools import wraps
import os
import json
import threading

# Modüler motor
import haber_motoru as motor

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chp-devrim-makinesi-2024')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Şifre - environment variable veya varsayılan
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'chp2024')

# Çalışma durumu
tarama_aktif = False

# Log callback'i ayarla
def websocket_log(mesaj, tip="info"):
    socketio.emit('log', {'mesaj': mesaj, 'tip': tip})

motor.set_log_callback(websocket_log)

# --- GİRİŞ KORUMASI ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Yanlış şifre!'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- SAYFA ROUTE'LARI ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/posts/<path:filename>')
def serve_post(filename):
    return send_from_directory('.', filename)

@app.route('/logo.png')
def serve_logo():
    return send_from_directory('.', 'logo.png')

# --- API ENDPOINT'LERİ ---
@app.route('/api/stats')
def get_stats():
    """İstatistikleri getir"""
    return jsonify(motor.istatistikleri_getir())

@app.route('/api/posts')
def get_posts():
    """Postları listele"""
    return jsonify(motor.postlari_listele())

@app.route('/api/archive')
def get_archive():
    """Arşivi getir"""
    return jsonify(motor.arsivi_yukle())

@app.route('/api/archive', methods=['DELETE'])
def clear_archive():
    """Arşivi temizle"""
    motor.arsivi_temizle()
    return jsonify({'success': True})

@app.route('/api/settings')
def get_settings():
    """Ayarları getir"""
    return jsonify(motor.config_yukle())

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Ayarları kaydet"""
    data = request.json
    motor.config_kaydet(data)
    return jsonify({'success': True})

@app.route('/api/post/<filename>', methods=['DELETE'])
def delete_post(filename):
    """Post sil"""
    success = motor.post_sil(filename)
    return jsonify({'success': success})

@app.route('/api/captions')
def get_all_captions():
    """Tüm captionları getir"""
    return jsonify(motor.tum_captionlari_getir())

@app.route('/api/caption/<filename>')
def get_caption(filename):
    """Tek bir post için caption getir"""
    caption_data = motor.caption_getir(filename)
    if caption_data:
        return jsonify(caption_data)
    return jsonify({'error': 'Caption bulunamadı'}), 404

@app.route('/api/posts/detailed')
def get_posts_detailed():
    """Postları caption bilgileriyle birlikte getir"""
    postlar = motor.postlari_listele()
    captionlar = motor.tum_captionlari_getir()
    
    for post in postlar:
        dosya = post['dosya']
        if dosya in captionlar:
            post['baslik'] = captionlar[dosya].get('baslik', '')
            post['caption'] = captionlar[dosya].get('caption', '')
            post['link'] = captionlar[dosya].get('link', '')
        else:
            post['baslik'] = ''
            post['caption'] = ''
            post['link'] = ''
    
    return jsonify(postlar)

# --- EDITOR API ---
@app.route('/api/editor/save', methods=['POST'])
def save_editor_design():
    """Editör tasarımını post olarak kaydet"""
    import base64
    
    data = request.json
    image_data = data.get('image', '')
    title = data.get('title', 'Editör Tasarımı')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Görsel yok'})
    
    # Base64'ü decode et
    try:
        # data:image/jpeg;base64, kısmını kaldır
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Dosya adı oluştur
        mevcut = len([f for f in os.listdir('.') if f.startswith("post_") and f.endswith(".jpg")])
        dosya_adi = f"post_{mevcut + 1}.jpg"
        
        # PIL ile yüksek kalitede kaydet
        from PIL import Image
        from io import BytesIO
        
        img = Image.open(BytesIO(image_bytes))
        
        # 1080x1080'de olduğundan emin ol
        if img.size != (1080, 1080):
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        
        # Maksimum kalite ile kaydet
        img.convert("RGB").save(dosya_adi, "JPEG", quality=100, subsampling=0, optimize=True)
        
        print(f"💾 HD kalitede kaydedildi: {dosya_adi} ({img.size})")
        
        # Caption veritabanına ekle
        motor.caption_kaydet(dosya_adi, title, f"Editörle oluşturuldu: {title}", "")
        
        return jsonify({'success': True, 'filename': dosya_adi})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/editor/generate-ai')
def generate_ai_image():
    """AI ile görsel oluştur - Pollinations.ai (ücretsiz, API key gerektirmez)"""
    try:
        import requests
        import base64
        import urllib.parse
        
        prompt = "CHP Republican Peoples Party Turkey flag rally 6 arrows political event professional photography dramatic lighting"
        
        # Pollinations.ai - ücretsiz AI görsel üretimi
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
        
        print(f"🎨 AI görsel isteniyor: {url[:80]}...")
        
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            print("✅ AI görsel başarıyla oluşturuldu!")
            return jsonify({'success': True, 'image': image_base64})
        else:
            print(f"❌ AI API hatası: {response.status_code}")
            return jsonify({'success': False, 'error': f'API hatası: {response.status_code}'})
            
    except requests.Timeout:
        return jsonify({'success': False, 'error': 'Zaman aşımı - tekrar deneyin'})
    except Exception as e:
        error_msg = str(e)
        print(f"AI Image Error: {error_msg}")
        
        # Fallback: Mevcut bir post görseli kullan
        try:
            import random
            posts = [f for f in os.listdir('.') if f.startswith('post_') and f.endswith('.jpg')]
            if posts:
                random_post = random.choice(posts)
                with open(random_post, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                return jsonify({
                    'success': True, 
                    'image': image_base64,
                    'fallback': True,
                    'message': f'AI hatası, {random_post} kullanıldı'
                })
        except:
            pass
        
        return jsonify({'success': False, 'error': f'Hata: {error_msg}'})

# --- INSTAGRAM API ---
instagram_client = None

@app.route('/api/instagram/import_session', methods=['POST'])
def import_instagram_session():
    """Instagram oturum dosyasını (JSON) manuel yükle"""
    global instagram_client
    
    try:
        data = request.json
        session_content = data.get('session_json')
        
        if not session_content:
             return jsonify({'success': False, 'error': 'Session verisi boş'})

        # JSON olduğunu doğrula
        if isinstance(session_content, str):
            try:
                settings = json.loads(session_content)
            except:
                 return jsonify({'success': False, 'error': 'Geçersiz JSON formatı'})
        else:
            settings = session_content
            
        # Eğer liste formatındaysa (Cookie-Editor'den geliyorsa) dönüştür
        if isinstance(settings, list):
            cookies = {}
            for cookie in settings:
                if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                    cookies[cookie['name']] = cookie['value']
            
            # Instagrapi formatına çevir
            settings = {
                "cookies": cookies,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "device_settings": {
                    "app_version": "Web",
                    "android_version": 0,
                    "android_release": "0",
                    "dpi": "0dpi",
                    "resolution": "0x0",
                    "manufacturer": "Web",
                    "device": "Web",
                    "model": "Web",
                    "cpu": "Web"
                },
                "country": "TR",
                "locale": "tr_TR",
                "timezone_offset": 10800
            }
            
        # Dosyaya kaydet
        with open('instagram_session.json', 'w') as f:
            json.dump(settings, f)
            
        print("📥 Instagram session manuel yüklendi")
        
        # Hemen giriş yapmayı dene
        return instagram_login()

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/instagram/login', methods=['POST'])
def instagram_login():
    """Instagram'a giriş yap ve oturumu kaydet"""
    global instagram_client
    
    try:
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired, TwoFactorRequired, ChallengeRequired
        
        config = motor.config_yukle()
        username = config.get('instagram_username', '')
        password = config.get('instagram_password', '')
        
        print(f"🔐 Instagram giriş deneniyor: @{username}")
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Instagram bilgileri ayarlardan girilmeli'})
        
        instagram_client = Client()
        instagram_client.delay_range = [1, 3]  # Rate limit koruması
        
        # Session dosyası varsa kullan
        session_file = 'instagram_session.json'
        try:
            if os.path.exists(session_file):
                instagram_client.load_settings(session_file)
                instagram_client.login(username, password)
                print("✅ Session ile giriş yapıldı")
            else:
                instagram_client.login(username, password)
                print("✅ Yeni giriş yapıldı")
            
            # Session'ı kaydet
            instagram_client.dump_settings(session_file)
            
            # Global durumu güncelle
            global instagram_logged_in, instagram_username
            instagram_logged_in = True
            instagram_username = username
            
            return jsonify({'success': True, 'message': f'@{username} hesabına giriş yapıldı!'})
            
        except TwoFactorRequired:
            instagram_client = None
            return jsonify({'success': False, 'error': '2FA aktif! Instagram ayarlarından iki adımlı doğrulamayı geçici olarak kapatın.'})
        except ChallengeRequired:
            instagram_client = None
            return jsonify({'success': False, 'error': 'Instagram doğrulama istiyor. Instagram uygulamasından hesabınıza giriş yapın ve tekrar deneyin.'})
        except LoginRequired:
            instagram_client = None
            return jsonify({'success': False, 'error': 'Giriş başarısız. Kullanıcı adı veya şifre yanlış olabilir.'})
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Instagram hatası: {error_msg}")
        instagram_client = None
        return jsonify({'success': False, 'error': f'Hata: {error_msg}'})

# Instagram login durumunu takip et
instagram_logged_in = False
instagram_username = ""

@app.route('/api/instagram/status')
def instagram_status():
    """Instagram bağlantı durumu"""
    global instagram_client, instagram_logged_in, instagram_username
    
    # Önce basit kontrol
    if instagram_client and instagram_logged_in:
        return jsonify({
            'connected': True, 
            'username': instagram_username,
            'followers': '-'
        })
    
    # Session dosyası varsa auto-login dene
    if os.path.exists('instagram_session.json'):
        try:
            from instagrapi import Client
            config = motor.config_yukle()
            username = config.get('instagram_username', '')
            password = config.get('instagram_password', '')
            
            if username and password:
                instagram_client = Client()
                instagram_client.load_settings('instagram_session.json')
                instagram_client.login(username, password)
                instagram_logged_in = True
                instagram_username = username
                return jsonify({
                    'connected': True, 
                    'username': username,
                    'followers': '-'
                })
        except:
            pass
    
    return jsonify({'connected': False})

@app.route('/api/instagram/share', methods=['POST'])
def instagram_share():
    """Post'u Instagram'a paylaş"""
    global instagram_client, instagram_logged_in, instagram_username
    
    # Instagram client yoksa ama session varsa, auto-login dene
    if not instagram_client and os.path.exists('instagram_session.json'):
        try:
            from instagrapi import Client
            config = motor.config_yukle()
            username = config.get('instagram_username', '')
            password = config.get('instagram_password', '')
            
            if username and password:
                print("🔄 Instagram oturumu yeniden yükleniyor...")
                instagram_client = Client()
                instagram_client.load_settings('instagram_session.json')
                instagram_client.login(username, password)
                instagram_logged_in = True
                instagram_username = username
                print("✅ Oturum yeniden yüklendi!")
        except Exception as e:
            print(f"❌ Auto-login hatası: {e}")
    
    if not instagram_client:
        return jsonify({'success': False, 'error': 'Instagram bağlantısı yok. Önce ayarlardan giriş yapın.'})
    
    try:
        import urllib.parse
        
        data = request.json
        filename = data.get('filename', '')
        caption = data.get('caption', '')
        
        # URL decode caption
        if caption:
            caption = urllib.parse.unquote(caption)
        
        print(f"📷 Instagram paylaşım isteği: {filename}")
        
        # Dosya yolunu düzelt (sadece dosya adı geliyorsa)
        if not os.path.exists(filename):
            if os.path.exists(f"./{filename}"):
                filename = f"./{filename}"
            else:
                print(f"❌ Dosya bulunamadı: {filename}")
                return jsonify({'success': False, 'error': f'Dosya bulunamadı: {filename}'})
        
        # Caption yoksa veya varsayılan ise, captions.json'dan al
        if not caption or 'Editörle oluşturuldu' in caption or caption == '':
            caption_data = motor.caption_getir(os.path.basename(filename))
            if caption_data:
                caption = caption_data.get('caption', '')
                print(f"📝 Caption veritabanından alındı: {caption[:50]}...")
        
        # Hashtag'leri ekle
        hashtags = "\n\n#dailychp #chp #cumhuriyethalpartisi #chpli #altıok #siyaset #haber #gündem #türkiye"
        if caption:
            caption = caption + hashtags
        else:
            caption = hashtags.strip()
        
        print(f"📤 Paylaşılıyor: {filename}")
        print(f"📝 Caption: {caption[:100] if caption else 'Boş'}...")
        
        # Fotoğrafı tam boyutta paylaş (resize yapma)
        media = instagram_client.photo_upload(
            filename, 
            caption,
            extra_data={"disable_comments": False}
        )
        
        print(f"✅ Paylaşıldı! Media ID: {media.pk}")
        
        return jsonify({
            'success': True, 
            'message': 'Instagram\'a paylaşıldı!',
            'media_id': str(media.pk)
        })
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Instagram paylaşım hatası: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/instagram/logout', methods=['POST'])
def instagram_logout():
    """Instagram oturumunu kapat"""
    global instagram_client
    instagram_client = None
    
    if os.path.exists('instagram_session.json'):
        os.remove('instagram_session.json')
    
    return jsonify({'success': True})

# --- WEBSOCKET OLAYLARI ---
@socketio.on('connect')
def handle_connect():
    emit('log', {'mesaj': '🔌 Bağlantı kuruldu!', 'tip': 'success'})
    
    # Yeni bağlanan kullanıcıya güncel durumu bildir
    if instagram_client:
        emit('instagram_status', {'connected': True, 'username': 'BAĞLI (Paylaşımlı)'})

@socketio.on('start_scan')
def handle_start_scan():
    global tarama_aktif
    
    if tarama_aktif:
        emit('log', {'mesaj': '⚠️ Tarama zaten devam ediyor!', 'tip': 'warning'})
        return
    
    tarama_aktif = True
    emit('scan_status', {'active': True})
    
    def run_scan():
        global tarama_aktif
        try:
            def progress_cb(current, total, msg):
                socketio.emit('progress', {
                    'current': current,
                    'total': total,
                    'message': msg,
                    'percent': int((current / max(total, 1)) * 100)
                })
            
            sonuclar = motor.uretim_baslat(progress_callback=progress_cb)
            socketio.emit('scan_complete', {'sonuclar': sonuclar})
        finally:
            tarama_aktif = False
            socketio.emit('scan_status', {'active': False})
    
    thread = threading.Thread(target=run_scan)
    thread.start()

@socketio.on('stop_scan')
def handle_stop_scan():
    global tarama_aktif
    tarama_aktif = False
    emit('log', {'mesaj': '⏹️ Tarama durduruldu.', 'tip': 'warning'})
    emit('scan_status', {'active': False})

# --- BAŞLAT ---
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════╗
    ║   🚀 CHP DEVRİM MAKİNESİ - WEB PANEL    ║
    ║      http://localhost:5000              ║
    ╚══════════════════════════════════════════╝
    """)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

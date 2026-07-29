# 🎰 CineRoulette

**Ne izleyeceğine karar veremedin mi? Çarkı çevir, ya da bir kart çek.**

CineRoulette, TMDB (The Movie Database) verisiyle çalışan, ruh haline göre film/dizi öneren, eğlenceli bir "seçim ritüeli" (çark veya kart destesi) sunan Streamlit tabanlı bir web uygulamasıdır.

---

## ✨ Özellikler

### 🎯 Akıllı Filtreleme
- **Ruh Haline Göre** — Ağlamalık, Heyecan Lazım, Korku Gecesi, Düşündürücü gibi ruh hallerine göre film önerisi. Tek bir ruh hali seçildiğinde, TMDB anahtar kelimeleriyle (tearjerker, supernatural, psychological thriller vb.) gerçek bir "tema" eşlemesi yapılır — sadece tür eşleşmesi değil.
- **Türe Göre** — Klasik tür bazlı filtreleme (Aksiyon, Komedi, Korku, Bilim Kurgu vb.)
- **Favorilerimden** — Kendi favori listenden rastgele seçim
- **Rastgele** — Kaliteli, rastgele bir içerik havuzundan seçim

Ruh hali ve tür filtreleri birbirini dışlar (aynı anda ikisi de seçilemez), böylece "Ağlamalık + Komedi" gibi anlamsız kombinasyonlar oluşmaz.

Ek filtreler: puan aralığı, yapım yılı aralığı, süre (film için), içerik türü (film/dizi).

### 🎡 İki Farklı Seçim Ritüeli
- **Çark** — Klasik dönen çark animasyonu, sonucu merkezi bir pop-up'ta gösterir
- **🃏 Kart Destesi** — Yüzü kapalı, yelpaze şeklinde açılmış kartlardan birini seç, anında açılsın

### 🤖 AI Destekli Öneriler
Favorilerine göre TF-IDF tabanlı bir öneri motoru, zevkine en yakın içerikleri buluyor. Her aday, favorilerinin **her biriyle ayrı ayrı** karşılaştırılıp en iyi eşleşme skoru alınıyor (çeşitli zevklerin birbirini "sulandırması" engellenir).

### ❤️ Favoriler ve Geri Bildirim
- Favori listesi oluştur, film/dizi ara ve doğrudan ekle
- **✅ Beğendim / 🚫 Beğenmedim** — beğenmediklerin bir daha çarkta/listede çıkmaz; beğendiklerin gizlenmez, sadece kaydedilir
- Ayrı bir "Geri Bildirimlerim" sayfasından işaretlerini istediğin zaman geri alabilirsin

### 🎬 Zengin İçerik Bilgisi
- **Nerede izlenir** — Türkiye'deki yayın platformu bilgisi (Netflix, Prime Video vb.)
- **Fragman gömme** — YouTube fragmanı doğrudan uygulama içinde oynatılır
- **Paylaşılabilir sonuç kartı** — Poster + başlık + puan içeren özel tasarım bir görsel otomatik oluşturulur, indirilebilir veya doğrudan (mobilde) WhatsApp/Instagram gibi uygulamalara paylaşılabilir

### 🎨 Tasarım
Koyu (Netflix esintili) tema, mobil uyumlu responsive tasarım.

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Arayüz | [Streamlit](https://streamlit.io/) |
| Veri kaynağı | [TMDB API](https://www.themoviedb.org/documentation/api) |
| Öneri motoru | scikit-learn (TF-IDF + Cosine Similarity) |
| Görsel oluşturma | Pillow (PIL) |
| Test | pytest + Streamlit `AppTest` |

---

## 📁 Proje Yapısı

```
film_carki/
├── app.py                          # Ana Streamlit uygulaması
├── requirements.txt                 # Python bağımlılıkları
├── test_app.py                      # Otomatik test paketi (pytest)
├── .env                              # TMDB_API_KEY (git'e gitmez)
├── .streamlit/
│   └── config.toml                  # Koyu tema ayarları
├── utils/
│   ├── tmdb_client.py                # TMDB API istemcisi
│   ├── movie_filters.py              # Ruh hali / tür tanımları
│   ├── favorites_manager.py          # Favori yönetimi (JSON kalıcı)
│   ├── feedback_manager.py           # Beğendim/Beğenmedim yönetimi
│   └── share_card.py                 # Paylaşılabilir görsel oluşturma
└── ml/
    ├── recommendation_engine.py      # TF-IDF öneri motoru
    └── components/
        └── roulette_wheel.py         # Çark bileşeni (HTML/CSS/JS)
```

---

## 🚀 Kurulum

### Gereksinimler
- Python 3.10+
- Ücretsiz bir [TMDB API anahtarı](https://www.themoviedb.org/settings/api)

### Adımlar

```powershell
# 1. Projeyi klonla
git clone https://github.com/Hiranursozeri/cineroulette.git
cd cineroulette

# 2. Sanal ortam oluştur ve aktive et
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate         # macOS/Linux

# 3. Bağımlılıkları kur
pip install -r requirements.txt

# 4. .env dosyası oluştur
echo "TMDB_API_KEY=senin_api_anahtarin" > .env

# 5. Çalıştır
streamlit run app.py
```

Uygulama varsayılan olarak `http://localhost:8501` adresinde açılır.

---

## 🧪 Test

Proje, gerçek bir API anahtarına veya internete ihtiyaç duymayan (tüm TMDB çağrıları sahte verilerle değiştirilmiş) kapsamlı bir otomatik test paketi içerir:

```powershell
pip install pytest
pytest test_app.py -v
```

Test paketi şunları kapsar: filtre modu geçişleri, çark/kart destesi akışı, favoriler, AI önerileri, beğendim/beğenmedim geri bildirimi, fragman gömme, paylaşılabilir görsel oluşturma ve daha fazlası.

---

## 🗺️ Geliştirme Yol Haritası

- [x] **Faz 1** — Gelişmiş filtreleme (ruh hali, tür, puan, yıl, süre, anahtar kelime eşleme)
- [x] **Faz 2** — Favorilerden çark/kart çevirme
- [x] **Faz 3** — Özgünleştirme (kart destesi, beğendim/beğenmedim, film arama, fragman, paylaşılabilir kart)
- [ ] **Faz 4** — Canlıya alma (Streamlit Community Cloud)

---

## 📄 Lisans

Bu proje kişisel/eğitim amaçlı geliştirilmiştir. TMDB verisi [TMDB Kullanım Şartları](https://www.themoviedb.org/documentation/api/terms-of-use) kapsamında kullanılmaktadır. Bu ürün TMDB tarafından onaylanmamıştır veya TMDB ile ilişkili değildir.

---

<p align="center">Made with 🎬 and a little bit of luck.</p>
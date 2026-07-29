# 🎰 CineRoulette

**Ne izleyeceğine karar veremedin mi? Çarkı çevir, ya da bir kart çek.**

CineRoulette, TMDB (The Movie Database) verisiyle çalışan, ruh haline göre film/dizi öneren, eğlenceli bir "seçim ritüeli" (dönen çark veya kart destesi) sunan bir web uygulamasıdır. Streamlit ile geliştirilmiş, [Streamlit Community Cloud](https://streamlit.io/cloud) üzerinde canlı olarak yayında.

🔗 **Canlı demo:** [cineroulette-ceqqhowxiaquscdmighkvz.streamlit.app](https://cineroulette-ceqqhowxiaquscdmighkvz.streamlit.app)

---

## ✨ Özellikler

### 🎯 Akıllı Filtreleme
- **Ruh Haline Göre** — Ağlamalık, Heyecan Lazım, Korku Gecesi, Düşündürücü gibi ruh hallerine göre öneri. Tek bir ruh hali seçildiğinde, TMDB anahtar kelimeleriyle (tearjerker, supernatural, psychological thriller vb.) gerçek bir "tema" eşlemesi yapılır — sadece tür eşleşmesi değil.
- **Türe Göre** — Klasik tür bazlı filtreleme. **Katı birincil-tür kontrolü** ile çalışır: bir film "Komedi" olarak seçildiğinde, Komedi'nin o filmin TMDB'de listelenen **birincil (dominant) türü** olması şart koşulur — "Parazit" ya da "Moana" gibi Komedi'yi sadece ikincil/yan tür olarak taşıyan filmler artık çıkmaz.
- **Favorilerimden** — Kendi favori listenden rastgele seçim
- **Rastgele** — Kaliteli, geniş bir içerik havuzundan rastgele seçim

Ruh hali ve tür filtreleri birbirini dışlar (aynı anda ikisi de seçilemez). Ek filtreler: puan aralığı, yapım yılı aralığı, süre (film için), içerik türü (film/dizi). Havuz, çeşitliliği artırmak için her zaman ~60 sonuca kadar genişletilir — aynı birkaç filmin sürekli tekrarlanmasını önler.

### 🎡 İki Farklı Seçim Ritüeli
- **Çark** — Klasik dönen çark animasyonu, sonucu merkezi bir pop-up'ta gösterir
- **🃏 Kart Destesi** — Yelpaze şeklinde açılmış, yüzü kapalı kartlardan birini seç, anında açılsın

### 🤖 AI Destekli Öneriler
Favorilerine göre TF-IDF tabanlı bir öneri motoru, zevkine en yakın içerikleri buluyor. Her aday, favorilerinin **her biriyle ayrı ayrı** karşılaştırılıp en iyi eşleşme skoru alınıyor (çeşitli zevklerin birbirini "sulandırması" engellenir).

### ❤️ Favoriler ve Geri Bildirim
- Doğrudan film/dizi arayıp favorilere ekleme (filtrelerden geçmeye gerek yok)
- **✅ Beğendim / 🚫 Beğenmedim** — beğenmediklerin bir daha çarkta/listede çıkmaz; beğendiklerin gizlenmez, sadece kaydedilir (pozitif bir işaret)
- Ayrı bir "Geri Bildirimlerim" sayfasından işaretlerini istediğin zaman geri alabilirsin

### 🎬 Zengin İçerik Bilgisi
- **Nerede izlenir** — Türkiye'deki yayın platformu bilgisi (Netflix, Prime Video vb.)
- **Fragman gömme** — YouTube fragmanı doğrudan uygulama içinde oynatılır
- **Paylaşılabilir sonuç kartı** — Poster + başlık + puan içeren özel tasarım bir görsel otomatik oluşturulur; indirilebilir veya (mobil tarayıcılarda) doğrudan WhatsApp/Instagram gibi uygulamalara "gerçek görsel" olarak paylaşılabilir

### 👥 Çoklu Kullanıcı Desteği
Her ziyaretçiye benzersiz bir oturum kimliği atanır (URL'de görünmez bir `?sid=...` parametresi olarak taşınır). Favoriler ve geri bildirimler **her kullanıcıya özel ayrı dosyalarda** tutulur — farklı ziyaretçilerin verileri asla birbirine karışmaz veya üzerine yazılmaz. Kimlik URL'de tutulduğu için, sayfa yenilense (F5) bile aynı veriye geri dönülebilir.

### 🎨 Tasarım
Koyu (Netflix esintili) tema, mobil uyumlu responsive tasarım (çark ve kart destesi dar ekranlarda otomatik küçülür).

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Arayüz | [Streamlit](https://streamlit.io/) |
| Veri kaynağı | [TMDB API](https://www.themoviedb.org/documentation/api) |
| Öneri motoru | scikit-learn (TF-IDF + Cosine Similarity) |
| Görsel oluşturma | Pillow (PIL) |
| Barındırma | Streamlit Community Cloud |
| Test | pytest + Streamlit `AppTest` |

---

## 📁 Proje Yapısı

```
film_carki/
├── app.py                          # Ana Streamlit uygulaması
├── requirements.txt                 # Python bağımlılıkları
├── test_app.py                      # Otomatik test paketi (pytest)
├── README.md
├── .env                              # TMDB_API_KEY (yerel geliştirme, git'e gitmez)
├── .streamlit/
│   └── config.toml                  # Koyu tema ayarları
├── data/                             # Kullanıcı bazlı favori/geri bildirim dosyaları (git'e gitmez)
├── utils/
│   ├── tmdb_client.py                # TMDB API istemcisi
│   ├── movie_filters.py              # Ruh hali / tür tanımları
│   ├── favorites_manager.py          # Favori yönetimi (oturum bazlı, JSON kalıcı)
│   ├── feedback_manager.py           # Beğendim/Beğenmedim yönetimi (oturum bazlı)
│   └── share_card.py                 # Paylaşılabilir görsel oluşturma
└── ml/
    ├── recommendation_engine.py      # TF-IDF öneri motoru
    └── components/
        └── roulette_wheel.py         # Çark bileşeni (HTML/CSS/JS)
```

---

## 🚀 Kurulum (Yerel Geliştirme)

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

## ☁️ Canlıya Alma (Streamlit Community Cloud)

Kod, hem yerel `.env` dosyasını hem canlı ortamda Streamlit'in **Secrets** sistemini destekleyecek şekilde yazılmıştır — hiçbir kod değişikliği gerekmez:

1. [share.streamlit.io](https://share.streamlit.io) → GitHub ile giriş yap
2. "Create app" → reponu, `main` branch'ini ve `app.py` dosya yolunu seç
3. "Advanced settings" → Secrets kısmına:
   ```toml
   TMDB_API_KEY = "gerçek_api_anahtarın"
   ```
4. Deploy

> ⚠️ **Ücretsiz katman sınırları:** ~1 GB bellek, 12 saat trafik almazsa uyku modu, sadece 1 özel (private) uygulama hakkı.

---

## 🧪 Test

Gerçek bir API anahtarına veya internete ihtiyaç duymayan (tüm TMDB çağrıları sahte verilerle değiştirilmiş) kapsamlı bir otomatik test paketi:

```powershell
pip install pytest
pytest test_app.py -v
```

Test paketi şunları kapsar: filtre modu geçişleri, katı tür eşleşmesi, çark/kart destesi akışı, favoriler, AI önerileri, beğendim/beğenmedim geri bildirimi, fragman gömme, paylaşılabilir görsel oluşturma, **ve çoklu kullanıcı oturum izolasyonu**.

---

## 🗺️ Geliştirme Yol Haritası

- [x] **Faz 1** — Gelişmiş filtreleme (ruh hali, tür, puan, yıl, süre, anahtar kelime eşleme, katı birincil tür kontrolü)
- [x] **Faz 2** — Favorilerden çark/kart çevirme
- [x] **Faz 3** — Özgünleştirme (kart destesi, beğendim/beğenmedim, film arama, fragman, paylaşılabilir kart)
- [x] **Faz 4** — Canlıya alma (Streamlit Community Cloud, Secrets desteği, çoklu kullanıcı oturum izolasyonu, temel SEO)
  - [ ] Gerçek kullanıcılarla çoklu kişi testi (devam ediyor)
  - [ ] Özel alan adı (opsiyonel)

---

## 📄 Lisans

Bu proje kişisel/eğitim amaçlı geliştirilmiştir. TMDB verisi [TMDB Kullanım Şartları](https://www.themoviedb.org/documentation/api/terms-of-use) kapsamında kullanılmaktadır. Bu ürün TMDB tarafından onaylanmamıştır veya TMDB ile ilişkili değildir.

---

<p align="center">Made with 🎬 and a little bit of luck.</p>
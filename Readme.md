# 🎰 CineRoulette

**Ne izleyeceğine karar veremedin mi? Çarkı çevir, ya da bir kart çek.**

CineRoulette, [TMDB (The Movie Database)](https://www.themoviedb.org/) verisiyle çalışan, ruh haline göre film/dizi öneren, eğlenceli bir "seçim ritüeli" (dönen çark veya kart destesi) sunan bir web uygulamasıdır. Streamlit ile geliştirilmiş, [Streamlit Community Cloud](https://streamlit.io/cloud) üzerinde canlı olarak yayında ve birden fazla kullanıcıyı aynı anda, birbirinin verisine karışmadan destekler.

🔗 **Canlı demo:** [cineroulette-ceqqhowxiaquscdmighkvz.streamlit.app](https://cineroulette-ceqqhowxiaquscdmighkvz.streamlit.app)

---

## 📖 İçindekiler

- [Özellikler](#-özellikler)
- [Nasıl Çalışır](#️-nasıl-çalışır)
- [Teknoloji Yığını](#️-teknoloji-yığını)
- [Proje Yapısı](#-proje-yapısı)
- [Kurulum](#-kurulum-yerel-geliştirme)
- [Canlıya Alma](#️-canlıya-alma-streamlit-community-cloud)
- [Test](#-test)
- [Bilinen Kısıtlamalar](#️-bilinen-kısıtlamalar)
- [Lisans](#-lisans)

---

## ✨ Özellikler

### 🎯 Akıllı Filtreleme

Sidebar'da dört filtreleme modu var, **birbirini dışlarlar** (aynı anda ikisi birden aktif olamaz — böylece "Ağlamalık + Komedi" gibi anlamsız kombinasyonlar oluşmaz):

| Mod | Ne yapar |
|---|---|
| 🎭 **Ruh Haline Göre** | Ağlamalık, Heyecan Lazım, Korku Gecesi, Düşündürücü. Tek bir ruh hali seçildiğinde, TMDB anahtar kelimeleriyle (ör. "tearjerker", "supernatural", "psychological thriller") gerçek bir *tema* eşlemesi yapılır — yalnızca tür eşleşmesi değil. |
| 🎬 **Türe Göre** | Klasik tür bazlı filtreleme. **Katı birincil-tür kontrolü** ile çalışır: bir film "Komedi" olarak seçildiğinde, Komedi'nin o filmin TMDB'de listelenen **birincil (dominant) türü** olması şart koşulur. "Parazit" ya da "Moana" gibi Komedi'yi sadece ikincil/yan tür olarak taşıyan filmler artık listede çıkmaz. |
| ❤️ **Favorilerimden** | Çark/kart, tamamen kendi favori listenden besleniyor. |
| 🎲 **Rastgele** | Ruh hali/tür filtrelerini yok sayıp, kaliteli ve geniş bir havuzdan tamamen rastgele seçim yapar. |

Ek olarak: **puan aralığı**, **yapım yılı aralığı**, **süre** (sadece filmlerde — TMDB dizilerde süre filtresini desteklemiyor) ve **içerik türü** (film/dizi) filtreleri her modda kullanılabilir.

Havuz, çeşitliliği artırmak için TMDB'den her zaman ~60 sonuca kadar (3 sayfa) genişletilir — aynı birkaç "en popüler" filmin sürekli tekrarlanmasını önler. "Tüm sonuçları listele" bölümünde ayrıca "Daha fazla göster" ile havuzu daha da büyütebilirsin.

### 🎡 İki Farklı Seçim Ritüeli

- **🎰 Çark** — Klasik dönen çark animasyonu (HTML/CSS/JS ile elden yazılmış, dış kütüphane kullanmadan), sonucu ekranın tam ortasında bir pop-up'ta (`st.dialog`) gösterir.
- **🃏 Kart Destesi** — Havuzdan seçilen 8 kart, gerçek bir iskambil destesi gibi hafifçe döndürülmüş ve üst üste binmiş şekilde ("yelpaze") gösterilir. Bir karta tıklayınca anında açılır — çarkın aksine bekleme animasyonu yoktur.

Her iki mod da aynı sonuç pop-up'ını, aynı favorileme/geri bildirim akışını paylaşır.

### 🤖 AI Destekli Öneriler

Favorilerine göre TF-IDF (metin benzerliği) tabanlı bir öneri motoru çalışır. Her aday içerik, favorilerinin **her biriyle ayrı ayrı** karşılaştırılıp en iyi eşleşme skoru alınır — bu sayede çeşitli zevklerin (ör. hem korku hem romantik komedi sevmek) birbirini "sulandırıp" tüm skorları düşürmesi engellenir. Tür eşleşmesine metin benzerliğinden çok daha yüksek ağırlık verilir. Hesaplama, sayfa her etkileşimde otomatik tetiklenmez — sadece "Önerileri Hesapla" butonuna basınca çalışır (gereksiz TMDB isteklerini önlemek için).

### ❤️ Favoriler ve Geri Bildirim

- **Film/Dizi Ara** — Favoriler sayfasında doğrudan isimle arama yapıp ekleyebilirsin, filtrelerden geçmen gerekmez.
- **✅ Beğendim / 🚫 Beğenmedim** — Her içerik kartında ve sonuç pop-up'ında bulunur.
  - *Beğenmedim* dediğin içerik bir daha çarkta/kart destesinde/listede/AI önerilerinde **çıkmaz**, ve favorideyse otomatik olarak favorilerden de kaldırılır.
  - *Beğendim* tamamen olumlu bir işarettir — o içeriği gizlemez, sadece kaydeder (favorilemekten farklı, daha "hafif" bir onay).
- **"👍👎 Geri Bildirimlerim"** sayfasında Beğendiklerim / Beğenmediklerim listelerini görüp, "↩️ Geri Al" ile fikrini değiştirebilirsin.

### 🎬 Zengin İçerik Bilgisi

- **📺 Nerede izlenir** — TMDB'nin `watch/providers` verisiyle, Türkiye'deki yayın platformu bilgisi (Netflix, Prime Video, kiralama/satın alma seçenekleri).
- **🎬 Fragman gömme** — TMDB'nin video verisinden YouTube fragmanı bulunup uygulama içinde doğrudan oynatılır (Trailer > Teaser > herhangi bir video önceliğiyle). Gömülü oynatıcı bazı kurumsal/okul Google hesaplarında kısıtlanabildiği için, her zaman "YouTube'da aç" yedek linki de gösterilir.
- **📤 Paylaşılabilir sonuç kartı** — Poster + film başlığı + puan + "CineRoulette" markası içeren özel bir görsel, Pillow ile anlık olarak oluşturulur. İndirilebilir, ya da (mobil tarayıcılarda, Web Share API destekleniyorsa) doğrudan WhatsApp/Instagram gibi uygulamalara gerçek bir görsel dosyası olarak paylaşılabilir.

### 👥 Çoklu Kullanıcı Desteği

Her ziyaretçiye ilk girişinde benzersiz bir oturum kimliği atanır ve bu kimlik URL'de görünmez bir `?sid=...` parametresi olarak taşınır. Favoriler ve geri bildirimler bu kimliğe özel, **birbirinden tamamen ayrı dosyalarda** (`data/favorites_<kimlik>.json`, `data/feedback_<kimlik>.json`) tutulur — farklı ziyaretçilerin verileri asla karışmaz veya birbirinin üzerine yazılmaz. Kimlik URL'de tutulduğu için, sayfa yenilense (F5) bile kullanıcı kendi verisine geri döner; sadece tarayıcı adres çubuğundaki `?sid=` kısmı silinir/paylaşılırsa yeni bir oturum başlar.

### 🎨 Tasarım

Koyu (Netflix esintili) tema — `.streamlit/config.toml` ile resmi Streamlit tema sistemi kullanılarak uygulanır (yerleşik bileşenlerin — dropdown, slider, metin kutusu vb. — hepsi tutarlı görünür). Çark ve kart destesi, dar (mobil) ekranlarda otomatik küçülüp taşmayı önler. Temel SEO meta etiketleri (açıklama, Open Graph, Twitter Card) sayfaya JS ile enjekte edilir.

---

## ⚙️ Nasıl Çalışır

1. Sidebar'dan bir filtreleme modu ve (varsa) alt seçimler yapılır.
2. Seçimlere göre TMDB'nin `discover` uç noktasından bir içerik havuzu çekilir (3 dakika önbelleğe alınır, gereksiz tekrar isteklerini önler).
3. Havuzdan rastgele 20 içerik, çark ya da kart destesi için örneklenir.
4. Kullanıcı çarkı çevirir ya da bir kart seçer; kazanan, merkezi bir pop-up'ta (poster, puan, nerede izlenir, fragman, paylaşım seçenekleriyle) gösterilir.
5. Kullanıcı isterse favorilere ekler, beğendim/beğenmedim işaretler, ya da sonucu paylaşır.

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
│   ├── tmdb_client.py                # TMDB API istemcisi (discover, arama, video, watch providers)
│   ├── movie_filters.py              # Ruh hali / tür tanımları, anahtar kelime eşlemeleri
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

Gerçek bir API anahtarına veya internete ihtiyaç duymayan (tüm TMDB çağrıları sahte verilerle değiştirilmiş) kapsamlı bir otomatik test paketi mevcut:

```powershell
pip install pytest
pytest test_app.py -v
```

Test paketi şunları kapsar: filtre modu geçişleri, katı tür eşleşmesi, çark/kart destesi akışı, favoriler, AI önerileri, beğendim/beğenmedim geri bildirimi, fragman gömme, paylaşılabilir görsel oluşturma ve çoklu kullanıcı oturum izolasyonu.

---

## ⚠️ Bilinen Kısıtlamalar

- **Kalıcılık:** Favoriler/geri bildirimler sunucudaki JSON dosyalarında tutulur; Streamlit Community Cloud uygulaması yeniden başlatılırsa (ör. uzun süre trafik almadıktan sonra) bu veriler kaybolabilir. Gerçek bir üretim ortamı için bir veritabanı (PostgreSQL, Firebase vb.) kullanılması önerilir.
- **"Görseli Doğrudan Paylaş" özelliği** (Web Share API), masaüstü tarayıcılarda genellikle desteklenmez; en iyi deneyim mobil Chrome/Safari'de yaşanır.
- **Fragman gömme**, bazı kurumsal/okul Google hesaplarının politikaları nedeniyle bazı kullanıcılarda kısıtlanabilir (bu durumda "YouTube'da aç" linki devreye girer).
- Bu proje kişisel/eğitim amaçlıdır; ölçekli, çok sayıda eşzamanlı kullanıcıya hizmet vermek için tasarlanmamıştır.

---

## 📄 Lisans

Bu proje kişisel/eğitim amaçlı geliştirilmiştir. TMDB verisi [TMDB Kullanım Şartları](https://www.themoviedb.org/documentation/api/terms-of-use) kapsamında kullanılmaktadır. Bu ürün TMDB tarafından onaylanmamıştır veya TMDB ile ilişkili değildir.

---

<p align="center">Made with 🎬 and a little bit of luck.</p>
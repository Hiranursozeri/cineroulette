# 🎰 CineRoulette

**Ne izleyeceğine karar veremedin mi? Çarkı çevir, ya da bir kart çek.**

CineRoulette, [TMDB (The Movie Database)](https://www.themoviedb.org/) verisiyle çalışan, ruh haline göre film/dizi öneren, eğlenceli bir "seçim ritüeli" (dönen çark veya kart destesi) sunan bir web uygulamasıdır. Streamlit ile geliştirilmiş, [Streamlit Community Cloud](https://streamlit.io/cloud) üzerinde canlı olarak yayında; birden fazla kullanıcıyı aynı anda, birbirinin verisine karışmadan destekler.

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

Sidebar'da dört filtreleme modu var, **birbirini dışlarlar**:

| Mod | Ne yapar |
|---|---|
| 🎭 **Ruh Haline Göre** | Ağlamalık, Heyecan Lazım, Korku Gecesi, Düşündürücü. Tek bir ruh hali seçildiğinde, TMDB anahtar kelimeleriyle (tearjerker, supernatural, psychological thriller vb.) gerçek bir *tema* eşlemesi yapılır. |
| 🎬 **Türe Göre** | **Katı birincil-tür kontrolü** ile çalışır: bir film "Komedi" olarak seçildiğinde, Komedi'nin o filmin TMDB'de listelenen **birincil (dominant) türü** olması şart koşulur — "Parazit" ya da "Moana" gibi Komedi'yi sadece ikincil/yan tür olarak taşıyan filmler artık listede çıkmaz. |
| ❤️ **Favorilerimden** | Çark/kart, tamamen kendi favori listenden besleniyor. |
| 🎲 **Rastgele** | Kaliteli, geniş bir içerik havuzundan tamamen rastgele seçim. |

Ruh hali/tür seçilmeden çark ya da kart destesi hiç görünmez — kullanıcıya net bir "önce seç" yönlendirmesi çıkar. Ek filtreler: puan aralığı, yapım yılı aralığı, süre (film için), içerik türü. Havuz, çeşitliliği artırmak için TMDB'den her zaman ~60 sonuca kadar (3 sayfa) genişletilir.

### 🎡 İki Farklı Seçim Ritüeli

- **🎰 Çark** — Elden yazılmış (HTML/CSS/JS) dönen çark animasyonu, sonucu merkezi bir pop-up'ta gösterir.
- **🃏 Kart Destesi** — Yelpaze şeklinde açılmış, yüzü kapalı 8 kart; birine tıklayınca (karıştırma animasyonuyla) anında açılır.

### 🤖 AI Destekli Öneriler

Favorilerine göre TF-IDF tabanlı bir öneri motoru çalışır. Her aday, favorilerinin **her biriyle ayrı ayrı** karşılaştırılıp en iyi eşleşme skoru alınır (çeşitli zevklerin birbirini sulandırması engellenir), tür eşleşmesine metin benzerliğinden çok daha yüksek ağırlık verilir.

### ❤️ Favoriler ve Geri Bildirim

- **Film/Dizi Ara** — Doğrudan isimle arayıp favorilere ekleme.
- **✅ Beğendim / 🚫 Beğenmedim** — *Beğenmedim* dediğin içerik bir daha hiçbir yerde çıkmaz (favorideyse oradan da kalkar); *Beğendim* sadece olumlu bir kayıttır, gizlemez.
- **"👍👎 Geri Bildirimlerim"** sayfasından işaretlerini **"↩️ Geri Al"** ile geri alabilirsin.

### 🎬 Zengin İçerik Bilgisi

- Sonuç listesindeki **her kartta** kısa bir açıklama ve isteğe bağlı (tıklanınca yüklenen) bir **fragman** bölümü var.
- Çark/kart sonucu pop-up'ında: **📺 Nerede izlenir** (Türkiye platform bilgisi), **🎬 Fragman** (YouTube, gömülü oynatıcı + yedek link), **📤 Paylaş** (özel tasarım bir görsel otomatik oluşturulur; indirilebilir veya mobilde doğrudan WhatsApp/Instagram'a "gerçek görsel" olarak paylaşılabilir).

### 👥 Çoklu Kullanıcı Desteği ve Kalıcı Depolama

- Her ziyaretçiye benzersiz bir oturum kimliği atanır (URL'de görünmez bir `?sid=...` parametresi), böylece sayfa yenilense (F5) bile veriler kaybolmaz, farklı ziyaretçilerin verileri asla karışmaz.
- Kalıcı depolama olarak **Supabase (Postgres)** kullanılır — Streamlit Community Cloud'un ücretsiz katmanı uygulamayı uykuya yollayıp yeniden başlatsa bile favoriler/geri bildirimler **kaybolmaz** (Supabase bilgileri tanımlı değilse otomatik olarak yerel dosya sistemine düşer, geliştirme için Supabase şart değildir).
- **Performans:** Veriler bu tarayıcı oturumunda sadece **ilk seferde** Supabase'den okunur ve `st.session_state`'te tutulur; sonraki tüm okumalar bellekten anında cevap verir, sadece gerçek değişiklikler (ekleme/işaretleme) ağa yazılır.

### 🎨 Tasarım

Koyu (Netflix esintili) tema, mobil uyumlu responsive tasarım (çark ve kart destesi dar ekranlarda otomatik küçülür). Türkçe karakterler (ğ, ş, ı, ö, ü, ç) projeye gömülü bir font (DejaVu Sans) ile hangi sunucuda çalışırsa çalışsın garanti doğru görüntülenir.

---

## ⚙️ Nasıl Çalışır

1. Sidebar'dan bir filtreleme modu ve alt seçimler yapılır.
2. TMDB'nin `discover` uç noktasından bir içerik havuzu çekilir (önbelleğe alınır).
3. Havuzdan rastgele 20 içerik, çark/kart destesi için örneklenir.
4. Kullanıcı çarkı çevirir ya da bir kart seçer; kazanan merkezi bir pop-up'ta gösterilir.
5. Kullanıcı favorilere ekler, beğendim/beğenmedim işaretler ya da sonucu paylaşır — bu veriler Supabase'e (ya da yerelde dosyaya) kaydedilir.

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Arayüz | [Streamlit](https://streamlit.io/) |
| Veri kaynağı | [TMDB API](https://www.themoviedb.org/documentation/api) |
| Kalıcı depolama | [Supabase](https://supabase.com/) (Postgres) |
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
├── supabase_schema.sql               # Supabase tablo tanımları
├── README.md
├── .env                              # TMDB_API_KEY, SUPABASE_URL, SUPABASE_KEY (yerel, git'e gitmez)
├── .streamlit/
│   └── config.toml                  # Koyu tema ayarları
├── assets/
│   └── fonts/                       # Türkçe karakter desteği için gömülü font (DejaVu Sans)
├── data/                             # Supabase yapılandırılmamışsa kullanılan yerel yedek dosyalar (git'e gitmez)
├── utils/
│   ├── tmdb_client.py                # TMDB API istemcisi
│   ├── movie_filters.py              # Ruh hali / tür tanımları
│   ├── favorites_manager.py          # Favori yönetimi (Supabase + oturum önbellekli)
│   ├── feedback_manager.py           # Beğendim/Beğenmedim yönetimi (Supabase + oturum önbellekli)
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
- (Opsiyonel) Ücretsiz bir [Supabase projesi](https://supabase.com/) — kurulmazsa uygulama otomatik olarak yerel dosya sistemine düşer

### Adımlar

```powershell
git clone https://github.com/Hiranursozeri/cineroulette.git
cd cineroulette

python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate         # macOS/Linux

pip install -r requirements.txt

# .env dosyası oluştur:
# TMDB_API_KEY=senin_api_anahtarin
# SUPABASE_URL=https://xxxxx.supabase.co       (opsiyonel)
# SUPABASE_KEY=senin_supabase_anahtarin          (opsiyonel)

streamlit run app.py
```

Uygulama `http://localhost:8501` adresinde açılır.

---

## ☁️ Canlıya Alma (Streamlit Community Cloud)

1. [share.streamlit.io](https://share.streamlit.io) → GitHub ile giriş yap → "Create app"
2. Repo, `main` branch, `app.py` dosya yolunu seç
3. "Advanced settings" → Secrets:
   ```toml
   TMDB_API_KEY = "gerçek_api_anahtarın"
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_KEY = "gerçek_supabase_anahtarın"
   ```
4. Deploy

Supabase kullanacaksan, önce `supabase_schema.sql` dosyasının içeriğini Supabase panelindeki **SQL Editor**'da bir kez çalıştırman gerekir (tabloları oluşturur).

---

## 🧪 Test

Gerçek bir API anahtarına veya internete ihtiyaç duymayan kapsamlı bir otomatik test paketi:

```powershell
pip install pytest
pytest test_app.py -v
```

Test paketi şunları kapsar: filtre modu geçişleri, katı tür eşleşmesi, çark/kart destesi akışı, favoriler, AI önerileri, beğendim/beğenmedim geri bildirimi, fragman gömme, paylaşılabilir görsel oluşturma, çoklu kullanıcı oturum izolasyonu ve Supabase önbellekleme performansı.

---

## ⚠️ Bilinen Kısıtlamalar

- **Ücretsiz katman:** Streamlit Community Cloud, ~1 GB bellek ve 12 saat trafik almazsa uyku moduyla sınırlıdır. Supabase kullanıldığında veriler bu durumdan etkilenmez, ama uygulamanın kendisi uyanma sırasında birkaç saniye gecikme yaşayabilir.
- **"Görseli Doğrudan Paylaş"** (Web Share API), masaüstü tarayıcılarda genellikle desteklenmez; en iyi deneyim mobil Chrome/Safari'de yaşanır.
- **Fragman gömme**, bazı kurumsal/okul Google hesaplarının politikaları nedeniyle bazı kullanıcılarda kısıtlanabilir ("YouTube'da aç" yedek linki devreye girer).
- Supabase tabloları RLS (Row Level Security) olmadan çalışır — hassas veri (şifre, ödeme bilgisi vb.) tutmadığı için kabul edilebilir bir basitleştirme, ama üretim ölçeğinde bir uygulama için ek güvenlik katmanları gerekir.
- Bu proje kişisel/eğitim amaçlıdır; büyük ölçekli, çok sayıda eşzamanlı kullanıcıya hizmet vermek için tasarlanmamıştır.

---

## 📄 Lisans

Bu proje kişisel/eğitim amaçlı geliştirilmiştir. TMDB verisi [TMDB Kullanım Şartları](https://www.themoviedb.org/documentation/api/terms-of-use) kapsamında kullanılmaktadır. Bu ürün TMDB tarafından onaylanmamıştır veya TMDB ile ilişkili değildir.

---

<p align="center">Made with 🎬 and a little bit of luck.</p>
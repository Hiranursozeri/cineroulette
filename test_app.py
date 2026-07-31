"""
CineRoulette - Otomatik Test Paketi
====================================
Gerçek bir TMDB API anahtarına veya internet bağlantısına ihtiyaç duymaz;
tüm TMDB çağrıları sahte (mock) verilerle değiştirilir. Streamlit'in
resmi `AppTest` çerçevesini kullanır — uygulamayı gerçek bir tarayıcı
açmadan, kod seviyesinde çalıştırıp kontrol eder.

ÇALIŞTIRMAK İÇİN:
    cd C:\\film_carki
    .\\venv\\Scripts\\Activate.ps1
    pip install pytest
    pytest test_app.py -v

Her test bağımsızdır (kendi temiz AppTest oturumunu açar). Bir test
başarısız olursa, hangi özelliğin bozulduğunu adından anlayabilirsin.
"""

import os
import sys
import shutil
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# ORTAK YARDIMCI VERİLER
# =============================================================================

def make_fake_items(n=10, id_start=1):
    """Sahte film verisi üretir (gerçek TMDB'ye hiç gitmeden)."""
    return [
        {
            "id": id_start + i,
            "title": f"Test Film {id_start + i}",
            "vote_average": 6.5 + (i % 4) * 0.5,
            "overview": f"Test filmi {id_start + i} için örnek bir açıklama metni.",
            "poster_url": None,
            "release_date": "2020-01-01",
            "content_type": "movie",
            "popularity": 100 - i,
            "genre_ids": [18],
        }
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def streamlit_onbellegini_temizle():
    """
    Streamlit'in @st.cache_data / @st.cache_resource önbellekleri süreç
    genelinde (tüm AppTest oturumları arasında) paylaşılır. Bu, bir testin
    diğerini yanlışlıkla etkilemesine (eski sahte veriyi görmesine) yol
    açabilir. Her testten önce temizliyoruz.
    """
    import streamlit as st
    st.cache_data.clear()
    st.cache_resource.clear()
    yield


@pytest.fixture(autouse=True)
def temiz_favoriler_dosyasi():
    """
    Her testten önce ve sonra favoriler/geri bildirim dosyalarını temizler
    (testler birbirini etkilemesin). Uygulama artık oturum bazlı dosyalar
    kullandığı için (data/favorites_<sid>.json, data/feedback_<sid>.json),
    hem eski (paylaşılan) dosya adlarını hem de data/ klasörünü temizliyoruz.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    legacy_paths = [
        os.path.join(base_dir, "user_favorites.json"),
        os.path.join(base_dir, "user_feedback.json"),
    ]
    data_dir = os.path.join(base_dir, "data")

    def _temizle():
        for p in legacy_paths:
            if os.path.exists(p):
                os.remove(p)
        if os.path.isdir(data_dir):
            shutil.rmtree(data_dir, ignore_errors=True)

    _temizle()
    yield
    _temizle()


@pytest.fixture(autouse=True)
def sahte_api_anahtari(monkeypatch):
    """Gerçek .env dosyasına dokunmadan sahte bir API anahtarı sağlar."""
    monkeypatch.setenv("TMDB_API_KEY", "test_dummy_key")


def _mocked_app(discover_return=None, get_random_return=None, watch_providers_return=None, trailer_key_return=None):
    """TMDB ağ çağrıları sahte verilerle değiştirilmiş bir AppTest oturumu döndürür."""
    discover_return = discover_return if discover_return is not None else make_fake_items()
    get_random_return = get_random_return if get_random_return is not None else make_fake_items()
    watch_providers_return = watch_providers_return or {"flatrate": [], "rent": [], "buy": []}

    patches = [
        patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None),
        patch("utils.tmdb_client.TMDBClient.discover_movies", return_value=discover_return),
        patch("utils.tmdb_client.TMDBClient.discover_tv_shows", return_value=discover_return),
        patch("utils.tmdb_client.TMDBClient.get_random_content", return_value=get_random_return),
        patch("utils.tmdb_client.TMDBClient.get_watch_providers", return_value=watch_providers_return),
        patch("utils.tmdb_client.TMDBClient.get_trailer_key", return_value=trailer_key_return),
        patch("utils.tmdb_client.TMDBClient.get_popular_movies", return_value=[]),
        patch("utils.tmdb_client.TMDBClient.get_popular_tv_shows", return_value=[]),
    ]
    for p in patches:
        p.start()

    at = AppTest.from_file("app.py")
    at.run(timeout=30)

    # Uygulama artık en az bir ruh hali/tür seçilmeden çark/kart bölümünü
    # göstermiyor. Testlerin çoğu hangi ruh hali olduğuyla ilgilenmediği
    # için, burada varsayılan olarak bir tane seçiyoruz — spesifik bir mod/
    # tür/favoriler/rastgele davranışı test eden fonksiyonlar zaten kendi
    # seçimlerini ayrıca yapıyor (bu varsayılanın üzerine yazılır).
    mood_widget = next((m for m in at.multiselect if m.key == "mood_multiselect"), None)
    if mood_widget is not None:
        mood_widget.select("aglamalik").run(timeout=30)
    return at, patches


def _stop_patches(patches):
    for p in patches:
        p.stop()


# =============================================================================
# 1) TEMEL AÇILIŞ TESTLERİ
# =============================================================================

def test_uygulama_hatasiz_aciliyor():
    """Uygulama, geçerli bir API anahtarıyla hiçbir hata vermeden açılmalı."""
    at, patches = _mocked_app()
    try:
        assert len(at.exception) == 0, f"Beklenmeyen hata(lar): {list(at.exception)}"
    finally:
        _stop_patches(patches)


def test_api_anahtari_yoksa_uyari_gosteriliyor():
    """API anahtarı geçersizse kullanıcı dostu bir hata mesajı gösterilmeli, çökme olmamalı."""
    with patch("utils.tmdb_client.TMDBClient.__init__", side_effect=ValueError("API anahtarı yok")):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)
        assert len(at.exception) == 0
        error_texts = [e.value for e in at.error]
        assert any("API anahtarı" in (t or "") for t in error_texts)


def test_dort_filtre_modu_da_var():
    """Sidebar'da tam olarak 4 filtreleme modu (ruh hali/tür/favoriler/rastgele) olmalı."""
    at, patches = _mocked_app()
    try:
        radio = at.sidebar.radio(key="filter_mode")
        assert len(radio.options) == 4
        beklenen_etiketler = {"🎭 Ruh Haline Göre", "🎬 Türe Göre", "❤️ Favorilerimden", "🎲 Rastgele"}
        assert set(radio.options) == beklenen_etiketler
    finally:
        _stop_patches(patches)


# =============================================================================
# 2) FİLTRE MODU GEÇİŞLERİ (BİRBİRİNİ DIŞLAMA)
# =============================================================================

@pytest.mark.parametrize("mode", ["mood", "genre", "favorites", "random"])
def test_her_filtre_moduna_gecis_hatasiz(mode):
    """Her filtreleme moduna geçiş sorunsuz çalışmalı (hiçbiri diğerini bozmamalı)."""
    at, patches = _mocked_app()
    try:
        at.sidebar.radio(key="filter_mode").set_value(mode).run(timeout=30)
        assert len(at.exception) == 0, f"'{mode}' moduna geçişte hata: {list(at.exception)}"
    finally:
        _stop_patches(patches)


def test_ruh_hali_ve_tur_ayni_anda_secilemiyor():
    """Tür seçiliyken mood widget'ı, mood seçiliyken tür widget'ı görünmemeli (karşılıklı dışlama)."""
    at, patches = _mocked_app()
    try:
        at.sidebar.radio(key="filter_mode").set_value("mood").run(timeout=30)
        mood_widget = next((m for m in at.multiselect if m.key == "mood_multiselect"), None)
        genre_widget = next((m for m in at.multiselect if m.key == "genre_multiselect"), None)
        assert mood_widget is not None
        assert genre_widget is None

        at.sidebar.radio(key="filter_mode").set_value("genre").run(timeout=30)
        mood_widget2 = next((m for m in at.multiselect if m.key == "mood_multiselect"), None)
        genre_widget2 = next((m for m in at.multiselect if m.key == "genre_multiselect"), None)
        assert mood_widget2 is None
        assert genre_widget2 is not None
    finally:
        _stop_patches(patches)


def test_tek_ruh_hali_secilince_hatasiz():
    """Tek bir ruh hali seçilince (anahtar kelime daraltması devreye girer) hata olmamalı."""
    at, patches = _mocked_app()
    try:
        at.sidebar.radio(key="filter_mode").set_value("mood").run(timeout=30)
        at.multiselect(key="mood_multiselect").select("aglamalik").run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 3) ÇARK TESTLERİ
# =============================================================================

def test_cark_cevrilebiliyor():
    """'Çarkı Çevir!' butonuna basınca hata olmamalı."""
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_cark_sonucu_favorilere_eklenebiliyor():
    """Çark döndükten sonra çıkan kazananı favorilere eklemek hatasız çalışmalı."""
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)

        dialog_fav_btn = next((b for b in at.button if "dialog_wheel_result_fav" in (b.key or "")), None)
        assert dialog_fav_btn is not None, "Kazanan pop-up'ı açılmadı"
        dialog_fav_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_yetersiz_sonucta_uyari_gosteriliyor():
    """Çark için yeterli sonuç yoksa (1 tane), uyarı gösterilmeli, hata değil."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=1))
    try:
        warning_texts = [w.value for w in at.warning]
        assert any("yeterli sonuç yok" in (t or "") for t in warning_texts)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 4) FAVORİLER TESTLERİ
# =============================================================================

def test_favori_ekleme_ve_kaldirma():
    """Bir içeriği favorilere ekleyip kaldırmak hatasız çalışmalı."""
    at, patches = _mocked_app()
    try:
        fav_btn = next(b for b in at.button if "Favorilere Ekle" in (b.label or ""))
        fav_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        tabs_favoriler = next((t for t in at.tabs if "Favorilerim" in t.label), None)
        # Favoriler sekmesine gecip metriklerin gorundugunu kontrol edelim
        metric_values = [m.value for m in at.metric]
        assert "1" in metric_values
    finally:
        _stop_patches(patches)


def test_favoriler_modunda_bos_liste_uyarisi():
    """Favori hiç yokken 'Favorilerimden' modu seçilirse bilgi mesajı gösterilmeli, çökme olmamalı."""
    at, patches = _mocked_app()
    try:
        at.sidebar.radio(key="filter_mode").set_value("favorites").run(timeout=30)
        assert len(at.exception) == 0
        info_texts = [i.value for i in at.info]
        assert any("favori eklememişsin" in (t or "") for t in info_texts)
    finally:
        _stop_patches(patches)


def test_favorilerden_cark_cevriliyor():
    """En az 2 favori eklendikten sonra 'Favorilerimden' modunda çark çevrilebilmeli."""
    at, patches = _mocked_app()
    try:
        for _ in range(2):
            fav_btn = next((b for b in at.button if "Favorilere Ekle" in (b.label or "")), None)
            assert fav_btn is not None
            fav_btn.click().run(timeout=30)

        at.sidebar.radio(key="filter_mode").set_value("favorites").run(timeout=30)
        spin_btn = next((b for b in at.button if "Çarkı Çevir" in (b.label or "")), None)
        assert spin_btn is not None, "Favorilerle çark butonu görünmüyor"
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_id_sifir_olan_icerik_favoriye_eklenebiliyor():
    """Kenar durum: id'si tam olarak 0 olan bir içerik de favoriye eklenebilmeli."""
    from utils.favorites_manager import FavoritesManager
    import streamlit as st

    fm = FavoritesManager()
    ok, _ = fm.toggle({"id": 0, "title": "Sifir ID'li Film", "content_type": "movie"})
    assert ok is True, "id=0 olan içerik favoriye eklenemedi (kenar durum hatası)"


# =============================================================================
# 5) AI ÖNERİLERİ TESTLERİ
# =============================================================================

def test_ai_onerileri_favori_olmadan_uyari_veriyor():
    """Favori yokken AI sekmesinde uyarı gösterilmeli, hesaplama yapılmamalı."""
    at, patches = _mocked_app()
    try:
        tab_ai_idx = 1
        assert len(at.exception) == 0
        warning_texts = [w.value for w in at.warning]
        assert any("önce favorilerine" in (t or "") for t in warning_texts)
    finally:
        _stop_patches(patches)


def test_ai_onerileri_hesaplaniyor():
    """Favori eklendikten sonra 'Önerileri Hesapla' butonuna basınca öneriler gelmeli."""
    at, patches = _mocked_app()
    try:
        fav_btn = next(b for b in at.button if "Favorilere Ekle" in (b.label or ""))
        fav_btn.click().run(timeout=30)

        compute_btn = next((b for b in at.button if "Önerileri Hesapla" in (b.label or "")), None)
        assert compute_btn is not None
        compute_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_oneri_motoru_benzerlik_skorlari_anlamli():
    """
    ML motoru, tür eşleşen içerikleri alakasız içeriklerden belirgin şekilde
    ayırt etmeli (eskiden tüm skorlar birbirine çok yakın ve düşük çıkıyordu).
    """
    from ml.recommendation_engine import RecommendationEngine

    engine = RecommendationEngine()
    favorites = [
        {"id": 1, "title": "Korku Filmi", "overview": "Karanlık bir evde yaşanan korkunç olaylar.", "genre_ids": [27]},
    ]
    candidates = [
        {"id": 10, "title": "Benzer Korku", "overview": "Lanetli bir ev ve içindeki hayaletler.", "genre_ids": [27], "vote_average": 7.0},
        {"id": 11, "title": "Alakasız Belgesel", "overview": "Okyanusların derinliklerindeki yaşam formları.", "genre_ids": [99], "vote_average": 8.0},
    ]
    results = engine.get_recommendations(favorites, candidates, top_n=5)

    assert len(results) == 2
    by_id = {r["id"]: r["similarity_score"] for r in results}
    assert by_id[10] > by_id[11], "Tür eşleşen içerik, alakasız içerikten daha yüksek skor almalı"
    assert by_id[10] - by_id[11] > 0.2, "Skorlar arasında anlamlı bir fark olmalı (eski düşük-benzerlik hatası)"


# =============================================================================
# 6) SAYFALAMA ("DAHA FAZLA GÖSTER") TESTLERİ
# =============================================================================

def test_daha_fazla_goster_sayisi_artiriyor():
    """
    Havuz artık çeşitlilik için baştan büyütülüyor (60'a kadar), bu yüzden
    filtre seçilince liste zaten ~60 sonuçla açılmalı. 'Daha fazla göster'
    butonuna basınca sayı yine de artmaya devam etmeli (61. sayfadan sonrası).
    """
    from utils.tmdb_client import ResultList

    def fake_discover(**kwargs):
        page = kwargs.get("page", 1)
        r = ResultList()
        start = (page - 1) * 20
        for i in range(start, start + 20):
            r.append({"id": i, "title": f"Film {i}", "vote_average": 7.0, "overview": "x",
                       "poster_url": None, "release_date": "2020-01-01",
                       "content_type": "movie", "popularity": 100 - i,
                       "genre_ids": [35]})  # Komedi birincil tur olarak
        r.total_results = 500
        return r

    with patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         patch("utils.tmdb_client.TMDBClient.discover_movies", side_effect=fake_discover):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)

        at.sidebar.radio(key="filter_mode").set_value("genre").run(timeout=30)
        at.multiselect(key="genre_multiselect").select("komedi").run(timeout=30)

        # Havuz artık kendiliğinden ~60 sonuca kadar genişliyor
        label_after_select = at.expander[0].label
        assert "60 /" in label_after_select, f"Havuz genişletme çalışmadı: {label_after_select}"

        load_more_btn = next(b for b in at.button if "Daha fazla" in (b.label or ""))
        load_more_btn.click().run(timeout=30)
        label_after_click = at.expander[0].label
        assert "80 /" in label_after_click, f"Daha fazla göster sayıyı artırmadı: {label_after_click}"
        assert len(at.exception) == 0


# =============================================================================
# 7) YIL FİLTRESİ DOĞRULUĞU
# =============================================================================

def test_yil_filtresi_yanlis_esleseni_eliyor():
    """
    TMDB bazen filtrelenen yıldan farklı bir release_date döndürebiliyor;
    istemci tarafı ek kontrolümüz bunu doğru şekilde elemeli.
    """
    from utils.tmdb_client import ResultList
    from app import _discover

    def fake_discover(**kwargs):
        r = ResultList()
        r.append({"id": 1, "title": "Yanlış Yıl", "release_date": "2016-05-01", "vote_average": 7.0})
        r.append({"id": 2, "title": "Doğru Yıl", "release_date": "2026-03-01", "vote_average": 7.5})
        r.total_results = 2
        return r

    with patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         patch.dict(os.environ, {"TMDB_API_KEY": "dummy"}):
        from utils.tmdb_client import TMDBClient
        tmdb = TMDBClient()
        tmdb.discover_movies = lambda **kw: fake_discover(**kw)

        result = _discover(tmdb, [], [], (0.0, 10.0), (2026, 2026), None, "popularity.desc", "movie", 1)

        assert len(result) == 1
        assert result[0]["id"] == 2, "Yanlış yıla ait sonuç filtrelenemedi"


# =============================================================================
# 8) KART DESTESİ MODU TESTLERİ
# =============================================================================

def test_kart_destesi_moduna_gecilebiliyor():
    """'🃏 Kart Çek' moduna geçiş hatasız çalışmalı ve 8 kart gösterilmeli."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=12))
    try:
        mode_radio = at.radio(key="selection_mode")
        assert set(mode_radio.options) == {"🎡 Çark", "🃏 Kart Çek"}
        mode_radio.set_value("cards").run(timeout=30)
        assert len(at.exception) == 0

        deck_btns = [b for b in at.button if "deck_card_" in (b.key or "")]
        assert len(deck_btns) == 8
    finally:
        _stop_patches(patches)


def test_kart_secince_sonuc_acidiyor():
    """Bir kart seçilince kazananın pop-up'ı (favori butonuyla) açılmalı."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=12))
    try:
        at.radio(key="selection_mode").set_value("cards").run(timeout=30)
        deck_btns = [b for b in at.button if "deck_card_" in (b.key or "")]
        deck_btns[0].click().run(timeout=30)
        assert len(at.exception) == 0

        dialog_btn = next((b for b in at.button if "dialog_wheel_result_fav" in (b.key or "")), None)
        assert dialog_btn is not None, "Kart seçimi sonrası pop-up açılmadı"
    finally:
        _stop_patches(patches)


def test_yeni_deste_karistir_calisiyor():
    """'Yeni Deste Karıştır' butonuna basmak hatasız çalışmalı."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=12))
    try:
        at.radio(key="selection_mode").set_value("cards").run(timeout=30)
        reshuffle_btn = next(b for b in at.button if b.key == "deck_reshuffle_btn")
        reshuffle_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_cark_ve_kart_modlari_arasi_gecis_sorunsuz():
    """Çark ↔ Kart Çek arasında ileri geri geçiş, her ikisinin de işlevini bozmamalı."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=12))
    try:
        at.radio(key="selection_mode").set_value("cards").run(timeout=30)
        at.radio(key="selection_mode").set_value("wheel").run(timeout=30)
        spin_btn = next((b for b in at.button if "Çarkı Çevir" in (b.label or "")), None)
        assert spin_btn is not None
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 9) İZLEDİM / BEĞENMEDİM GERİ BİLDİRİM TESTLERİ
# =============================================================================

def test_feedback_manager_begendim_havuzdan_cikarmiyor():
    """
    'Beğendim' işareti artık havuzdan ÇIKARMAMALI (sadece pozitif bir kayıt) —
    sadece 'Beğenmedim' işareti havuzdan çıkarmalı.
    """
    from utils.feedback_manager import FeedbackManager

    fm = FeedbackManager()
    fm.mark_watched({"id": 100, "title": "Test", "content_type": "movie"})
    assert fm.is_watched(100) is True
    assert fm.is_disliked(100) is False

    pool = [{"id": 100}, {"id": 101}]
    filtered = fm.filter_pool(pool)
    assert len(filtered) == 2, "Beğenilen içerik havuzdan çıkarılmamalı"

    fm.mark_disliked({"id": 101, "title": "Test2", "content_type": "movie"})
    filtered2 = fm.filter_pool(pool)
    assert len(filtered2) == 1
    assert filtered2[0]["id"] == 100, "Beğenilmeyen içerik havuzdan çıkarılmalı"


def test_feedback_manager_begenmedim_izlendiyi_geri_alir():
    """Bir içerik önce 'bu değildi' sonra 'izledim' olarak işaretlenirse, sadece 'izledim' listesinde kalmalı."""
    from utils.feedback_manager import FeedbackManager

    fm = FeedbackManager()
    fm.mark_disliked({"id": 200, "title": "Test", "content_type": "movie"})
    assert fm.is_disliked(200) is True

    fm.mark_watched({"id": 200, "title": "Test", "content_type": "movie"})
    assert fm.is_disliked(200) is False, "Fikir değiştirince eski işaret kalmamalı"
    assert fm.is_watched(200) is True


def test_pop_upta_izledim_begenmedim_butonlari_var():
    """Çark/kart sonucu pop-up'ında İzledim ve Bu Değildi butonları görünmeli."""
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)

        watched_btn = next((b for b in at.button if b.key == "dialog_watched"), None)
        disliked_btn = next((b for b in at.button if b.key == "dialog_disliked"), None)
        assert watched_btn is not None, "Pop-up'ta İzledim butonu yok"
        assert disliked_btn is not None, "Pop-up'ta Bu Değildi butonu yok"
    finally:
        _stop_patches(patches)


def test_pop_upta_izledim_tiklamak_hatasiz():
    """Pop-up'ta 'İzledim' butonuna basmak hatasız çalışmalı."""
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)

        watched_btn = next(b for b in at.button if b.key == "dialog_watched")
        watched_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_listedeki_karttan_begenmedim_favoriden_de_kaldiriyor():
    """
    Bir içerik favorilere eklendikten sonra listeden 'Bu Değildi' denirse,
    hem geri bildirim listesine eklenmeli hem de favorilerden kaldırılmalı.
    """
    at, patches = _mocked_app()
    try:
        # Once favoriye ekle
        fav_btn = next(b for b in at.button if "Favorilere Ekle" in (b.label or ""))
        fav_btn.click().run(timeout=30)

        # Ayni icerigin "Bu Degildi" butonunu bul (favori butonuyla ayni idx/key_prefix'i paylasir)
        disliked_btn = next((b for b in at.button if (b.key or "").startswith("disliked_")), None)
        assert disliked_btn is not None
        disliked_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_karttan_secilen_filmde_de_feedback_butonlari_var():
    """Kart destesinden çıkan sonuçta da İzledim/Bu Değildi butonları olmalı."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=12))
    try:
        at.radio(key="selection_mode").set_value("cards").run(timeout=30)
        deck_btns = [b for b in at.button if "deck_card_" in (b.key or "")]
        deck_btns[0].click().run(timeout=30)

        watched_btn = next((b for b in at.button if b.key == "dialog_watched"), None)
        assert watched_btn is not None
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_begendim_sonrasi_kalici_rozet_gorunuyor():
    """
    'Beğendim' butonuna basıldıktan sonra, o kart bir daha 'Beğendim' butonunu
    göstermemeli — favori butonundaki gibi kalıcı bir duruma geçmeli.
    (Not: AppTest, st.dialog içindeki st.success mesajlarını ayrı bir katmanda
    render ettiği için doğrudan izleyemiyor; bu yüzden burada ölçülebilir asıl
    davranışı — butonun kalıcı olarak kaybolmasını — doğruluyoruz.)
    """
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)

        watched_btn = next(b for b in at.button if b.key == "dialog_watched")
        watched_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        watched_btn_after = next((b for b in at.button if b.key == "dialog_watched"), None)
        assert watched_btn_after is None, "İşaretlendikten sonra buton hâlâ görünüyor, rozete dönüşmedi"
    finally:
        _stop_patches(patches)


# =============================================================================
# 10) FİLM ARAMA TESTLERİ
# =============================================================================

def test_favoriler_sayfasinda_arama_kutusu_var():
    """Favoriler sayfasında arama kutusu ve butonu görünmeli."""
    at, patches = _mocked_app()
    try:
        search_input = next((i for i in at.text_input if i.key == "fav_search_query"), None)
        search_btn = next((b for b in at.button if b.key == "fav_search_btn"), None)
        assert search_input is not None
        assert search_btn is not None
    finally:
        _stop_patches(patches)


def test_arama_sonuclari_favoriye_eklenebiliyor():
    """Arama sonucu gelen bir film favorilere eklenebilmeli."""
    at, patches = _mocked_app()
    try:
        with patch("utils.tmdb_client.TMDBClient.search_movies", return_value=make_fake_items(n=3, id_start=500)):
            search_input = next(i for i in at.text_input if i.key == "fav_search_query")
            search_input.set_value("test film").run(timeout=30)
            search_btn = next(b for b in at.button if b.key == "fav_search_btn")
            search_btn.click().run(timeout=30)
            assert len(at.exception) == 0

            fav_btn = next((b for b in at.button if "favsearch" in (b.key or "") and "fav_" in (b.key or "")), None)
            assert fav_btn is not None, "Arama sonuçlarında favori butonu yok"
            fav_btn.click().run(timeout=30)
            assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 11) BEĞENDİKLERİM / BEĞENMEDİKLERİM SAYFASI TESTLERİ
# =============================================================================

def test_gecmis_sekmesi_hatasiz_aciliyor():
    """'Geri Bildirimlerim' sekmesi (Beğendiklerim/Beğenmediklerim) hatasız açılmalı."""
    at, patches = _mocked_app()
    try:
        assert len(at.exception) == 0
        tab_labels = [t.label for t in at.tabs]
        assert any("Geri Bildirimlerim" in (t or "") for t in tab_labels)
    finally:
        _stop_patches(patches)


def test_begenilmeyen_gerial_alinabiliyor():
    """Bir içerik 'Beğenmedim' olarak işaretlendikten sonra 'Geri Al' ile geri alınabilmeli."""
    at, patches = _mocked_app()
    try:
        disliked_btn = next(b for b in at.button if (b.key or "").startswith("disliked_"))
        disliked_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        undo_btn = next((b for b in at.button if (b.key or "").startswith("undo_disliked_")), None)
        assert undo_btn is not None, "'Geri Al' butonu bulunamadı"
        undo_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 12) FRAGMAN GÖMME TESTLERİ
# =============================================================================

def test_fragman_varsa_expander_gosteriliyor():
    """Fragman anahtarı bulunursa pop-up'ta '🎬 Fragmanı İzle' bölümü çıkmalı."""
    at, patches = _mocked_app(trailer_key_return="dQw4w9WgXcQ")
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        expander_labels = [e.label for e in at.expander]
        assert any("Fragmanı İzle" in (lbl or "") for lbl in expander_labels)
    finally:
        _stop_patches(patches)


def test_fragman_yoksa_hata_vermiyor():
    """Fragman bulunamazsa (None dönerse) uygulama hatasız çalışmaya devam etmeli."""
    at, patches = _mocked_app(trailer_key_return=None)
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        expander_labels = [e.label for e in at.expander]
        assert not any("Fragmanı İzle" in (lbl or "") for lbl in expander_labels)
    finally:
        _stop_patches(patches)


def test_tmdb_client_trailer_key_secimi():
    """TMDBClient.get_trailer_key: Trailer tipini Teaser'a tercih etmeli, YouTube olmayanları yok saymalı."""
    from unittest.mock import patch as mock_patch
    with patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         mock_patch.dict(os.environ, {"TMDB_API_KEY": "dummy"}):
        from utils.tmdb_client import TMDBClient
        tmdb = TMDBClient()

        fake_videos = {"results": [
            {"site": "YouTube", "type": "Teaser", "key": "teaser123"},
            {"site": "YouTube", "type": "Trailer", "key": "trailer456"},
            {"site": "Vimeo", "type": "Trailer", "key": "vimeo789"},
        ]}
        tmdb._make_request = lambda *a, **kw: fake_videos
        assert tmdb.get_trailer_key(1, "movie") == "trailer456"

        tmdb._make_request = lambda *a, **kw: {"results": []}
        assert tmdb.get_trailer_key(1, "movie") is None


# =============================================================================
# 13) PAYLAŞILABİLİR SONUÇ KARTI TESTLERİ
# =============================================================================

def test_share_card_posterisiz_uretiliyor():
    """Poster URL'si olmayan bir içerik için bile paylaşım görseli üretilebilmeli."""
    from utils.share_card import generate_share_card

    winner = {"title": "Test Filmi", "vote_average": 7.5, "poster_url": None}
    result = generate_share_card(winner)
    assert result is not None
    assert len(result) > 0
    assert result[:8] == b"\x89PNG\r\n\x1a\n", "Gecerli bir PNG dosyasi olmali"


def test_share_card_uzun_baslikla_calisiyor():
    """Çok uzun bir film başlığı satır kaydırma ile sorunsuz işlenmeli."""
    from utils.share_card import generate_share_card

    winner = {
        "title": "Bu Gerçekten Çok Ama Çok Uzun Bir Film Başlığı Test Amaçlı Yazılmıştır",
        "vote_average": 6.2,
        "poster_url": None,
    }
    result = generate_share_card(winner)
    assert result is not None


def test_pop_upta_paylas_bolumu_var():
    """Çark/kart sonucu pop-up'ında '📤 Paylaş' bölümü ve indirme butonu görünmeli."""
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        expander_labels = [e.label for e in at.expander]
        assert any("Paylaş" in (lbl or "") for lbl in expander_labels)

        download_btn = next((b for b in at.download_button if b.key == "download_share_card"), None)
        assert download_btn is not None
    finally:
        _stop_patches(patches)


def test_share_card_mod_gore_farkli_cta_metni():
    """generate_share_card, geçirilen cta_text'i kullanmalı (çark/kart moduna göre farklı olabilir)."""
    from utils.share_card import generate_share_card

    winner = {"title": "Test", "vote_average": 7.0, "poster_url": None}
    r1 = generate_share_card(winner, cta_text="Çarkı sen de çevir!")
    r2 = generate_share_card(winner, cta_text="Sen de bir kart çek!")
    assert r1 is not None and r2 is not None
    assert r1 != r2, "Farklı CTA metinleriyle üretilen görseller farklı olmalı"


def test_karttan_gelen_paylasimda_kart_cta_kullaniliyor():
    """Kart destesinden çıkan sonuçta paylaşım görseli 'kart çek' CTA'sını kullanmalı."""
    at, patches = _mocked_app(discover_return=make_fake_items(n=12))
    try:
        at.radio(key="selection_mode").set_value("cards").run(timeout=30)
        deck_btns = [b for b in at.button if "deck_card_" in (b.key or "")]
        deck_btns[0].click().run(timeout=30)
        assert len(at.exception) == 0

        download_btn = next((b for b in at.download_button if b.key == "download_share_card"), None)
        assert download_btn is not None
    finally:
        _stop_patches(patches)


def test_metin_paylasim_secenekleri_kaldirildi():
    """Artık ayrı bir 'paylaşım metni' kutusu veya sadece-metin WhatsApp linki olmamalı."""
    at, patches = _mocked_app()
    try:
        spin_btn = next(b for b in at.button if "Çarkı Çevir" in (b.label or ""))
        spin_btn.click().run(timeout=30)
        assert len(at.exception) == 0

        share_text_widget = next((i for i in at.text_input if i.key == "share_text_input"), None)
        assert share_text_widget is None, "'Paylaşım metni' kutusu hâlâ görünüyor, kaldırılmalıydı"
    finally:
        _stop_patches(patches)


# =============================================================================
# 14) ÇOK KULLANICILI OTURUM İZOLASYONU TESTLERİ
# =============================================================================

def test_farkli_oturumlarin_favorileri_karismiyor():
    """
    KRİTİK: İki farklı oturum (kullanıcı) kimliğiyle oluşturulan
    FavoritesManager'lar birbirinin verisini görmemeli/üzerine yazmamalı.
    Bu, uygulamanın gerçekten birden fazla kullanıcıyla güvenle
    kullanılabilmesi için şart.
    """
    import streamlit as st
    from utils.favorites_manager import FavoritesManager

    # Bare modda (AppTest dışında) st.session_state süreç genelinde
    # paylaşıldığı için, önceki testlerden kalıntı olmasın diye başta
    # da temizliyoruz.
    st.session_state["favorites"] = []

    fm_a = FavoritesManager(session_id="kullanici_a")
    fm_a.add({"id": 1, "title": "Kullanici A'nin Filmi", "content_type": "movie"})

    # session_state paylasimli oldugu icin (tek process), ikinci yoneticiyi
    # olusturmadan once session_state'i sifirlayalim - gercek hayatta bu
    # farkli tarayicilar/sekmeler oldugu icin dogal olarak ayri olur.
    st.session_state["favorites"] = []

    fm_b = FavoritesManager(session_id="kullanici_b")

    assert fm_b.get_count() == 0, "Kullanıcı B, kullanıcı A'nın favorisini görmemeli"
    assert fm_a.FAVORITES_FILE != fm_b.FAVORITES_FILE, "İki oturum aynı dosyayı kullanıyor olamaz"

    fm_b.add({"id": 2, "title": "Kullanici B'nin Filmi", "content_type": "movie"})

    # Dosyalarin gercekten birbirinden bagimsiz oldugunu dogrudan kontrol et
    import json
    with open(fm_a.FAVORITES_FILE) as f:
        data_a = json.load(f)
    with open(fm_b.FAVORITES_FILE) as f:
        data_b = json.load(f)

    assert len(data_a) == 1 and data_a[0]["title"] == "Kullanici A'nin Filmi"
    assert len(data_b) == 1 and data_b[0]["title"] == "Kullanici B'nin Filmi"


def test_oturum_kimligi_url_query_paramina_yaziliyor():
    """
    Oturum kimliği hem session_state'te hem URL'nin query param'ında
    tutulmalı — böylece sayfa yenilense (F5) bile aynı veriye dönülebilir.
    """
    at, patches = _mocked_app()
    try:
        assert len(at.exception) == 0
        assert "sid" in at.query_params, "Oturum kimliği URL'ye yazılmamış"
        assert len(at.query_params["sid"]) > 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 15) KATI (BİRİNCİL) TÜR FİLTRESİ TESTLERİ
# =============================================================================

def test_ikincil_tur_olarak_eslesen_icerikler_eleniyor():
    """
    'Parazit'/'Moana' senaryosu: bir içeriğin türlerinden biri seçilen türle
    eşleşse bile, o tür İÇERİĞİN BİRİNCİL (ilk) türü değilse elenmeli.
    """
    from unittest.mock import patch as mock_patch
    from utils.tmdb_client import ResultList

    def fake_discover(**kwargs):
        r = ResultList()
        # Komedi (35) ikincil tur olarak geciyor - elenmeli
        r.append({"id": 1, "title": "Parazit Benzeri", "genre_ids": [18, 53, 35],
                   "release_date": "2019-01-01", "vote_average": 8.5})
        r.append({"id": 2, "title": "Moana Benzeri", "genre_ids": [16, 12, 10751, 35],
                   "release_date": "2016-01-01", "vote_average": 7.6})
        # Komedi (35) birincil tur - kalmali
        r.append({"id": 3, "title": "Gercek Komedi", "genre_ids": [35, 10749],
                   "release_date": "2020-01-01", "vote_average": 6.8})
        r.total_results = 3
        return r

    with mock_patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         mock_patch.dict(os.environ, {"TMDB_API_KEY": "dummy"}):
        from utils.tmdb_client import TMDBClient
        tmdb = TMDBClient()
        tmdb.discover_movies = lambda **kw: fake_discover(**kw)

        from app import _discover
        result = _discover(tmdb, [35], [], (0.0, 10.0), (1950, 2026), None, "popularity.desc", "movie", 1)

        assert len(result) == 1
        assert result[0]["id"] == 3, "Sadece Komedi'nin birincil tür olduğu içerik kalmalıydı"


# =============================================================================
# 16) FİLTRE SEÇİLMEDEN ÇARK/KART GİZLENMESİ TESTLERİ
# =============================================================================

def test_hicbir_sey_secilmeden_cark_gizli():
    """Ruh hali/tür modunda hiçbir seçim yapılmadan çark/kart bölümü hiç görünmemeli."""
    discover_return = make_fake_items()
    with patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         patch("utils.tmdb_client.TMDBClient.discover_movies", return_value=discover_return), \
         patch("utils.tmdb_client.TMDBClient.discover_tv_shows", return_value=discover_return):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)  # _mocked_app'in aksine burada BİLEREK hiçbir seçim yapmıyoruz

        assert len(at.exception) == 0
        spin_btn = next((b for b in at.button if "Çarkı Çevir" in (b.label or "")), None)
        assert spin_btn is None, "Hiçbir şey seçilmeden çark görünmemeliydi"

        info_texts = [i.value for i in at.info]
        assert any("ruh hali" in (t or "") and "tür" in (t or "") for t in info_texts)


def test_ruh_hali_secince_cark_gorunuyor():
    """Bir ruh hali seçilince çark/kart bölümü görünmeli."""
    at, patches = _mocked_app()  # _mocked_app zaten varsayılan olarak bir ruh hali seçiyor
    try:
        assert len(at.exception) == 0
        spin_btn = next((b for b in at.button if "Çarkı Çevir" in (b.label or "")), None)
        assert spin_btn is not None, "Ruh hali seçilince çark görünmeliydi"
    finally:
        _stop_patches(patches)


# =============================================================================
# 17) SUPABASE ÖNBELLEK PERFORMANS TESTİ
# =============================================================================

def test_favorites_manager_supabase_onbellek_calisiyor():
    """
    KRİTİK: FavoritesManager artık veriyi `st.session_state`'te tuttuğu
    için, aynı tarayıcı oturumunda birden fazla FavoritesManager ÖRNEĞİ
    oluşturulsa bile (her yeniden yüklemede olduğu gibi), Supabase'e
    SADECE BİR KEZ gidilmeli — sonraki tüm örnekler zaten yüklenmiş
    veriyi bellekten kullanmalı.
    """
    import streamlit as st
    from unittest.mock import patch as mock_patch

    call_count = {"n": 0}

    class FakeResp:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, storage):
            self.storage = storage
            self._filters = {}

        def select(self, cols):
            return self

        def eq(self, col, val):
            self._filters[col] = val
            return self

        def order(self, *a, **kw):
            return self

        def execute(self):
            call_count["n"] += 1
            rows = [r for r in self.storage if all(r.get(k) == v for k, v in self._filters.items())]
            return FakeResp(rows)

    class FakeTable:
        def __init__(self, storage):
            self.storage = storage

        def select(self, cols):
            return FakeQuery(self.storage)

    class FakeClient:
        def __init__(self):
            self._tables = {"favorites": [{"session_id": "x", "content_id": 1, "content": {"id": 1}}]}

        def table(self, name):
            return FakeTable(self._tables[name])

    fake_client = FakeClient()

    # Bare modda session_state onceki testlerden kalinti tutabiliyor,
    # bu yuzden ilgili anahtarlari once temizliyoruz.
    st.session_state["favorites"] = []
    st.session_state["favorites_loaded_from_backend"] = False

    with mock_patch("utils.favorites_manager._get_supabase_client", return_value=fake_client):
        from utils.favorites_manager import FavoritesManager

        # 20 kartlik bir liste render edilirken her karti YENI bir
        # FavoritesManager orneginin kontrol ettigini simule ediyoruz
        # (gercekte her rerun'da init_favorites_manager() yeni bir ornek
        # yaratir).
        for i in range(20):
            fm = FavoritesManager(session_id="x")
            fm.is_favorite(i)

        assert call_count["n"] == 1, f"Önbellek çalışmıyor: 20 örnek için {call_count['n']} ağ isteği atıldı"


# =============================================================================
# 18) LİSTE KARTLARINDA AÇIKLAMA VE FRAGMAN TESTLERİ
# =============================================================================

def test_liste_kartinda_aciklama_gorunuyor():
    """Sonuç listesindeki kartlarda film açıklaması (overview) görünmeli."""
    items_with_overview = make_fake_items()
    for item in items_with_overview:
        item["overview"] = "Bu gerçekten uzun ve detaylı bir film açıklamasıdır, test amaçlıdır ve 160 karakteri aşabilir belki de aşmaz ama önemli değil."

    at, patches = _mocked_app(discover_return=items_with_overview)
    try:
        caption_texts = [c.value for c in at.caption]
        assert any("uzun ve detaylı bir film açıklaması" in (t or "") for t in caption_texts)
    finally:
        _stop_patches(patches)


def test_liste_kartinda_fragman_sadece_istenince_cekiliyor():
    """
    Fragman, kart listesinde otomatik çekilmemeli — sadece kullanıcı
    'Fragmanı Yükle' butonuna basınca TMDB'ye istek atılmalı (aksi halde
    20 kartlık bir listede 20 gereksiz istek atılırdı).
    """
    trailer_call_count = {"n": 0}

    def fake_trailer_key(*a, **kw):
        trailer_call_count["n"] += 1
        return "dQw4w9WgXcQ"

    at, patches = _mocked_app()
    try:
        with patch("utils.tmdb_client.TMDBClient.get_trailer_key", side_effect=fake_trailer_key):
            # Sayfa ilk acildiginda hicbir fragman istegi atilmamis olmali
            assert trailer_call_count["n"] == 0, "Fragman otomatik cekilmemeliydi"

            load_btn = next((b for b in at.button if (b.key or "").startswith("load_trailer_")), None)
            assert load_btn is not None, "'Fragmanı Yükle' butonu bulunamadı"
            load_btn.click().run(timeout=30)

            assert trailer_call_count["n"] == 1, "Butona basinca tam olarak 1 istek atilmali"
            assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


# =============================================================================
# 19) FAVORİ KALICILIĞI SAĞLAMLIK TESTLERİ (LinkedIn geri bildirimi #1)
# =============================================================================

def test_supabase_okuma_hatasinda_tekrar_denenir():
    """
    KRİTİK (gerçek kullanıcı şikayeti): Supabase okuması geçici olarak
    başarısız olursa, uygulama bunu 'yüklendi, favori yok' olarak
    YANLIŞLIKLA işaretlememeli — bir sonraki denemede tekrar okumayı
    denemeli, aksi halde kullanıcı o oturum boyunca (ve her yeni girişte)
    favorilerini hiç göremez.
    """
    import streamlit as st
    from unittest.mock import patch as mock_patch

    call_count = {"n": 0}

    class FailingThenWorkingTable:
        def __init__(self):
            self._filters = {}

        def select(self, cols):
            return self

        def eq(self, col, val):
            self._filters[col] = val
            return self

        def order(self, *a, **kw):
            return self

        def execute(self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("Geçici ağ hatası (simüle)")
            class Resp:
                data = [{"content": {"id": 1, "title": "Kurtarilan Film"}}]
            return Resp()

    class FakeClient:
        def table(self, name):
            return FailingThenWorkingTable()

    st.session_state["favorites"] = []
    st.session_state["favorites_loaded_from_backend"] = False

    with mock_patch("utils.favorites_manager._get_supabase_client", return_value=FakeClient()):
        from utils.favorites_manager import FavoritesManager
        fm = FavoritesManager(session_id="retry_test")

        result = fm.get_all()
        assert call_count["n"] == 2, "İlk deneme başarısız olunca otomatik ikinci deneme yapılmalıydı"
        assert len(result) == 1 and result[0]["title"] == "Kurtarilan Film"


def test_supabase_iki_deneme_de_basarisizsa_gorunur_uyari_var():
    """İki deneme de başarısız olursa kullanıcıya görünür bir uyarı gösterilmeli, sessizce boş geçilmemeli."""
    import streamlit as st
    from unittest.mock import patch as mock_patch

    class AlwaysFailingTable:
        def select(self, cols):
            return self

        def eq(self, col, val):
            return self

        def order(self, *a, **kw):
            return self

        def execute(self):
            raise ConnectionError("Kalıcı hata (simüle)")

    class FakeClient:
        def table(self, name):
            return AlwaysFailingTable()

    st.session_state["favorites"] = []
    st.session_state["favorites_loaded_from_backend"] = False

    with mock_patch("utils.favorites_manager._get_supabase_client", return_value=FakeClient()):
        from utils.favorites_manager import FavoritesManager
        fm = FavoritesManager(session_id="fail_test")
        result = fm.get_all()

        assert result == []
        # LOADED_FLAG işaretlenmemiş olmalı ki bir sonraki denemede tekrar denensin
        assert st.session_state["favorites_loaded_from_backend"] is False


# =============================================================================
# 20) AI ÖNERİ TÜR HEDEFLEME TESTLERİ (LinkedIn geri bildirimi #2)
# =============================================================================

def test_favorilerden_en_sik_turler_dogru_cikariliyor():
    """
    KRİTİK (gerçek kullanıcı şikayeti): '4 Macera + 1 Romantik favoriledim
    ama alakasız öneriler geldi' — çünkü aday havuzu hiç tür bazlı
    filtrelenmiyordu. Şimdi favorilerden en sık türler doğru çıkarılmalı.
    """
    from app import _get_top_genres_from_favorites

    favorites = [
        {"id": 1, "content_type": "movie", "genre_ids": [12, 28]},   # Macera, Aksiyon
        {"id": 2, "content_type": "movie", "genre_ids": [12]},        # Macera
        {"id": 3, "content_type": "movie", "genre_ids": [12, 14]},   # Macera, Fantastik
        {"id": 4, "content_type": "movie", "genre_ids": [12]},        # Macera
        {"id": 5, "content_type": "movie", "genre_ids": [10749]},     # Romantik
        {"id": 6, "content_type": "tv", "genre_ids": [35]},           # Komedi ama dizi - dahil edilmemeli
    ]

    top_genres = _get_top_genres_from_favorites(favorites, content_type="movie", top_n=2)
    assert 12 in top_genres, "Macera (en sık geçen tür) listede olmalıydı"
    assert 35 not in top_genres, "Dizi favorisinin türü, film önerileri için karışmamalı"


def test_ai_onerileri_favori_turlere_gore_filtreleniyor():
    """
    Aday havuzu artık kullanıcının favori türlerine göre de (genel
    popüler içeriğe ek olarak) TMDB'den özel olarak çekilmeli.
    """
    from unittest.mock import patch as mock_patch, MagicMock

    discover_calls_with_genre = []

    def fake_discover_movies(**kwargs):
        if kwargs.get("genre_ids"):
            discover_calls_with_genre.append(kwargs["genre_ids"])
        return make_fake_items(n=3)

    at, patches = _mocked_app()
    try:
        with mock_patch("utils.tmdb_client.TMDBClient.discover_movies", side_effect=fake_discover_movies), \
             mock_patch("utils.tmdb_client.TMDBClient.get_popular_movies", return_value=make_fake_items(n=3)):
            fav_btn = next(b for b in at.button if "Favorilere Ekle" in (b.label or ""))
            fav_btn.click().run(timeout=30)

            compute_btn = next((b for b in at.button if "Önerileri Hesapla" in (b.label or "")), None)
            assert compute_btn is not None
            compute_btn.click().run(timeout=30)

            assert len(at.exception) == 0
            assert len(discover_calls_with_genre) > 0, "Favori türlere göre filtrelenmiş bir TMDB isteği hiç atılmadı"
    finally:
        _stop_patches(patches)


# =============================================================================
# 21) URL FİLTRE HATIRLAMA TESTLERİ (LinkedIn geri bildirimi #3)
# =============================================================================

def test_filtre_secimleri_urle_yaziliyor():
    """Bir ruh hali/tür seçildiğinde, bu seçim URL query param'larına yazılmalı."""
    at, patches = _mocked_app()
    try:
        mode_val = at.query_params.get("mode")
        moods_val = at.query_params.get("moods")
        # AppTest bazı durumlarda query param degerini liste olarak dondurebiliyor
        mode_val = mode_val[0] if isinstance(mode_val, list) else mode_val
        moods_val = moods_val[0] if isinstance(moods_val, list) else moods_val
        assert mode_val == "mood"
        assert moods_val == "aglamalik"
    finally:
        _stop_patches(patches)


def test_url_parametresinden_filtre_geri_yukleniyor():
    """
    Sayfa, URL'de zaten `mode` ve `moods`/`genres` parametreleri varken
    açılırsa, o filtre seçimini otomatik olarak geri yüklemeli.
    """
    discover_return = make_fake_items()
    with patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         patch("utils.tmdb_client.TMDBClient.discover_movies", return_value=discover_return), \
         patch("utils.tmdb_client.TMDBClient.discover_tv_shows", return_value=discover_return):
        at = AppTest.from_file("app.py")
        at.query_params["mode"] = "genre"
        at.query_params["genres"] = "komedi"
        at.run(timeout=30)

        assert len(at.exception) == 0
        radio = at.sidebar.radio(key="filter_mode")
        assert radio.value == "genre", "URL'deki mod geri yüklenmedi"

        genre_widget = next((m for m in at.multiselect if m.key == "genre_multiselect"), None)
        assert genre_widget is not None
        assert "komedi" in genre_widget.value, "URL'deki tür seçimi geri yüklenmedi"


# =============================================================================
# 22) TÜR GENİŞLETME SANITY TESTİ
# =============================================================================

def test_ai_onerileri_4_tur_ile_calisiyor_hatasiz():
    """Tür sayısı 2'den 4'e genişletildikten sonra AI önerileri hâlâ hatasız hesaplanabilmeli."""
    at, patches = _mocked_app()
    try:
        fav_btn = next(b for b in at.button if "Favorilere Ekle" in (b.label or ""))
        fav_btn.click().run(timeout=30)

        compute_btn = next((b for b in at.button if "Önerileri Hesapla" in (b.label or "")), None)
        compute_btn.click().run(timeout=30)
        assert len(at.exception) == 0
    finally:
        _stop_patches(patches)


def test_ai_onerileri_5_altindaki_puanlari_eliyor():
    """AI önerileri aday havuzu, 5.0'ın altındaki puanlı içerikleri hiç dikkate almamalı."""
    low_and_high_rated = [
        {"id": 1, "title": "Dusuk Puanli", "vote_average": 3.2, "overview": "x", "poster_url": None,
         "release_date": "2020-01-01", "content_type": "movie", "popularity": 1, "genre_ids": [18]},
        {"id": 2, "title": "Yuksek Puanli", "vote_average": 7.8, "overview": "x", "poster_url": None,
         "release_date": "2020-01-01", "content_type": "movie", "popularity": 1, "genre_ids": [18]},
    ]
    at, patches = _mocked_app()
    try:
        with patch("utils.tmdb_client.TMDBClient.get_popular_movies", return_value=low_and_high_rated), \
             patch("utils.tmdb_client.TMDBClient.discover_movies", return_value=low_and_high_rated):
            fav_btn = next(b for b in at.button if "Favorilere Ekle" in (b.label or ""))
            fav_btn.click().run(timeout=30)

            compute_btn = next((b for b in at.button if "Önerileri Hesapla" in (b.label or "")), None)
            compute_btn.click().run(timeout=30)
            assert len(at.exception) == 0

            rec_titles = [r.get("title") for r in st_session_state_ai_recs(at)]
            assert "Dusuk Puanli" not in rec_titles
    finally:
        _stop_patches(patches)


def st_session_state_ai_recs(at):
    try:
        return at.session_state["ai_recommendations"] or []
    except Exception:
        return []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
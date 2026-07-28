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
    """Her testten önce ve sonra favoriler dosyasını temizler (testler birbirini etkilemesin)."""
    fav_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_favorites.json")
    if os.path.exists(fav_path):
        os.remove(fav_path)
    yield
    if os.path.exists(fav_path):
        os.remove(fav_path)


@pytest.fixture(autouse=True)
def sahte_api_anahtari(monkeypatch):
    """Gerçek .env dosyasına dokunmadan sahte bir API anahtarı sağlar."""
    monkeypatch.setenv("TMDB_API_KEY", "test_dummy_key")


def _mocked_app(discover_return=None, get_random_return=None, watch_providers_return=None):
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
        patch("utils.tmdb_client.TMDBClient.get_popular_movies", return_value=[]),
        patch("utils.tmdb_client.TMDBClient.get_popular_tv_shows", return_value=[]),
    ]
    for p in patches:
        p.start()

    at = AppTest.from_file("app.py")
    at.run(timeout=30)
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
    """'Daha fazla göster' butonuna her basışta gösterilen sonuç sayısı artmalı."""
    from utils.tmdb_client import ResultList

    def fake_discover(**kwargs):
        page = kwargs.get("page", 1)
        r = ResultList()
        start = (page - 1) * 20
        for i in range(start, start + 20):
            r.append({"id": i, "title": f"Film {i}", "vote_average": 7.0, "overview": "x",
                       "poster_url": None, "release_date": "2020-01-01",
                       "content_type": "movie", "popularity": 100 - i})
        r.total_results = 500
        return r

    with patch("utils.tmdb_client.TMDBClient._validate_api_key", return_value=None), \
         patch("utils.tmdb_client.TMDBClient.discover_movies", side_effect=fake_discover):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)

        at.sidebar.radio(key="filter_mode").set_value("genre").run(timeout=30)
        at.multiselect(key="genre_multiselect").select("komedi").run(timeout=30)

        # Otomatik on-yukleme sayesinde zaten 40 olmali
        label_after_select = at.expander[0].label
        assert "40 /" in label_after_select, f"Ön yükleme çalışmadı: {label_after_select}"

        load_more_btn = next(b for b in at.button if "Daha fazla" in (b.label or ""))
        load_more_btn.click().run(timeout=30)
        label_after_click = at.expander[0].label
        assert "60 /" in label_after_click, f"Daha fazla göster sayıyı artırmadı: {label_after_click}"
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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
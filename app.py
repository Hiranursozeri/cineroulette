import random
import time
import streamlit as st
from typing import Optional

from utils.tmdb_client import TMDBClient
from utils.favorites_manager import FavoritesManager
from utils.movie_filters import (
    MOOD_FILTERS, GENRE_FILTERS, RANDOM_FILTER,
    AI_RECOMMENDATION_FILTER, FilterConfig,
    get_tv_genre_ids,
)

from ml.components.roulette_wheel import render_roulette_wheel
from ml.recommendation_engine import RecommendationEngine

# =============================================================================
# SAYFA YAPILANDIRMASI
# =============================================================================

st.set_page_config(
    page_title="CineRoulette 🎬",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Koyu (Netflix tarzı) tema
st.markdown("""
<style>
    .stApp {
        background-color: #141414;
        color: #f5f5f5;
    }

    section[data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }

    .main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 4px 20px;
        border-bottom: 1px solid #2a2a2a;
        margin-bottom: 24px;
    }
    .main-header h1 {
        font-size: 28px;
        font-weight: 700;
        color: #fff;
        margin: 0;
    }
    .main-header h1 span { color: #e50914; }
    .main-header p {
        color: #999;
        font-size: 13px;
        margin: 2px 0 0;
    }

    .section-title {
        font-size: 17px;
        font-weight: 600;
        color: #f5f5f5;
        margin: 4px 0 14px;
    }

    .content-card {
        background: #1f1f1f;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 12px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .content-card:hover {
        transform: translateY(-4px);
        border-color: #e50914;
    }

    .similarity-badge {
        background: #2a9d8f;
        color: #fff;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }

    /* Streamlit widget'larını koyu temaya uydur */
    div[data-testid="stMetric"] {
        background: #1f1f1f;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 10px;
    }
    .stButton > button {
        border-radius: 8px;
        border: 1px solid #3a3a3a;
        background: #262626;
        color: #f5f5f5;
    }
    .stButton > button:hover {
        border-color: #e50914;
        color: #fff;
    }
    .stTabs [data-baseweb="tab"] {
        color: #999;
    }
    .stTabs [aria-selected="true"] {
        color: #fff !important;
    }

    /* Üstteki varsayılan beyaz Streamlit araç çubuğunu koyu temaya uydur */
    header[data-testid="stHeader"] {
        background-color: #141414;
    }
    div[data-testid="stDecoration"] {
        background-image: none;
        background-color: #141414;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# İNİTİALİZASYON
# =============================================================================

@st.cache_resource
def init_tmdb_client() -> Optional[TMDBClient]:
    """TMDB istemcisini başlat."""
    try:
        return TMDBClient()
    except ValueError:
        return None


@st.cache_resource
def init_ml_engine() -> RecommendationEngine:
    """ML motorunu başlat."""
    return RecommendationEngine()


def init_favorites_manager() -> FavoritesManager:
    """Favori yöneticisini başlat (her oturumda yeni)."""
    return FavoritesManager()


# =============================================================================
# FİLTRE YARDIMCILARI
# =============================================================================

SORT_OPTIONS = {
    "Popülerlik": "popularity.desc",
    "Puan (yüksekten düşüğe)": "vote_average.desc",
    "Yeni çıkanlar": "release_date.desc",
}


def get_mood_genre_ids(selected_moods: list[str]) -> list[int]:
    """Seçilen ruh hallerinin tür ID'lerini birleştirir (bu grup içinde OR mantığı)."""
    ids: set[int] = set()
    for key in selected_moods:
        fc = MOOD_FILTERS.get(key)
        if fc and fc.genre_ids:
            ids.update(fc.genre_ids)
    return list(ids)


def get_genre_genre_ids(selected_genres: list[str]) -> list[int]:
    """Seçilen türlerin tür ID'lerini birleştirir (bu grup içinde OR mantığı)."""
    ids: set[int] = set()
    for key in selected_genres:
        fc = GENRE_FILTERS.get(key)
        if fc and fc.genre_ids:
            ids.update(fc.genre_ids)
    return list(ids)


def resolve_sort_by(sort_label: str, content_type: str) -> str:
    """Sıralama etiketini TMDB'nin beklediği sort_by string'ine çevirir."""
    sort_value = SORT_OPTIONS.get(sort_label, "popularity.desc")
    if content_type == "tv" and sort_value.startswith("release_date"):
        return sort_value.replace("release_date", "first_air_date")
    return sort_value


def _discover(
    tmdb: TMDBClient,
    genre_ids: list[int],
    min_rating: float,
    sort_by: str,
    content_type: str,
    page: int,
) -> list[dict]:
    """Tek bir kategori grubu (sadece mood ya da sadece genre) için TMDB isteği."""
    query_genre_ids = genre_ids
    if content_type == "tv" and query_genre_ids:
        query_genre_ids = get_tv_genre_ids(query_genre_ids)

    if content_type == "movie":
        return tmdb.discover_movies(
            genre_ids=query_genre_ids or None,
            min_vote_average=min_rating,
            min_vote_count=100,
            sort_by=sort_by,
            page=page,
        ) or []
    else:
        return tmdb.discover_tv_shows(
            genre_ids=query_genre_ids or None,
            min_vote_average=min_rating,
            min_vote_count=100,
            sort_by=sort_by,
            page=page,
        ) or []


@st.cache_data(ttl=180, show_spinner=False)
def fetch_filtered_pool(
    _tmdb: TMDBClient,
    mood_genre_ids: tuple[int, ...],
    genre_genre_ids: tuple[int, ...],
    min_rating: float,
    sort_label: str,
    content_type: str,
    random_mode: bool,
    page: int = 1,
) -> list[dict]:
    """
    Filtre panelinden gelen seçimlere göre içerik havuzu getirir.

    ÖNEMLİ: Ruh hali ve tür seçimleri birbirine göre "VE" (AND) mantığıyla
    uygulanır — ör. "Ağlamalık" (Dram) + "Animasyon" seçilirse sonuç hem
    dram HEM animasyon olan içerikler olur, sadece biri değil. Aynı grubun
    içinde (ör. birden fazla ruh hali) seçimler "VEYA" (OR) ile çalışır.
    TMDB'nin `with_genres` parametresi tek bir çağrıda hem AND hem OR'u
    aynı anda desteklemediği için, iki grup da doluysa iki ayrı istek atıp
    sonuçların kesişimini (id bazlı) alıyoruz.

    `st.cache_data` ile önbelleğe alınıyor: aynı filtrelerle her widget
    etkileşiminde (ör. çarkı çevirme) TMDB'ye tekrar istek atmak yerine
    3 dakika boyunca aynı sonucu tekrar kullanıyoruz. `_tmdb` altçizgiyle
    başlıyor çünkü TMDBClient nesnesi cache anahtarına dahil edilemez
    (hash'lenemez), sadece çağrı için kullanılır.
    """
    tmdb = _tmdb
    try:
        if random_mode:
            return tmdb.get_random_content(
                content_type=content_type,
                min_vote_average=min_rating or RANDOM_FILTER.min_vote_average,
                min_vote_count=RANDOM_FILTER.min_vote_count,
                count=16,
            )

        sort_by = resolve_sort_by(sort_label, content_type)
        mood_ids = list(mood_genre_ids)
        genre_ids = list(genre_genre_ids)

        if mood_ids and genre_ids:
            # Her iki grup da seçili: iki ayrı sorgu atıp kesişimi al (AND).
            pool_a = _discover(tmdb, mood_ids, min_rating, sort_by, content_type, page)
            pool_b = _discover(tmdb, genre_ids, min_rating, sort_by, content_type, page=1)
            ids_b = {item.get("id") for item in pool_b}
            return [item for item in pool_a if item.get("id") in ids_b]

        # Sadece biri (ya da hiçbiri) seçili: tek sorgu, grup içi OR yeterli.
        combined_ids = mood_ids or genre_ids
        return _discover(tmdb, combined_ids, min_rating, sort_by, content_type, page)
    except Exception as e:
        st.error(f"İçerik yüklenirken hata: {e}")
        return []


def fetch_ai_recommendations(
    tmdb: TMDBClient,
    ml_engine: RecommendationEngine,
    favorites: list[dict],
    content_type: str,
) -> list[dict]:
    """AI tabanlı öneriler getir."""
    if not favorites:
        return []

    try:
        candidate_pool = []

        if content_type == "movie":
            candidate_pool.extend(tmdb.get_popular_movies(page=1))
            candidate_pool.extend(tmdb.get_popular_movies(page=2))
            candidate_pool.extend(tmdb.discover_movies(
                min_vote_average=7.5,
                min_vote_count=1000,
                page=1,
            ))
        else:
            candidate_pool.extend(tmdb.get_popular_tv_shows(page=1))
            candidate_pool.extend(tmdb.get_popular_tv_shows(page=2))
            candidate_pool.extend(tmdb.discover_tv_shows(
                min_vote_average=7.5,
                min_vote_count=500,
                page=1,
            ))

        seen_ids = set()
        unique_pool = []
        for item in candidate_pool:
            if item.get("id") not in seen_ids:
                seen_ids.add(item.get("id"))
                unique_pool.append(item)

        recommendations = ml_engine.get_recommendations(
            favorites=favorites,
            candidate_pool=unique_pool,
            top_n=12,
        )

        # ML motoru aynı içeriği (farklı favorilerle eşleştiği için) birden
        # fazla kez döndürebiliyor. Aşağıdaki `_render_content_card_body`
        # her karta content_id + başlığa dayalı bir buton anahtarı (key)
        # üretiyor; aynı id iki kez gelirse Streamlit
        # `StreamlitDuplicateElementKey` hatası fırlatır. Burada id'ye göre
        # tekilleştiriyoruz.
        seen_rec_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            rec_id = rec.get("id")
            if rec_id not in seen_rec_ids:
                seen_rec_ids.add(rec_id)
                unique_recommendations.append(rec)

        return unique_recommendations
    except Exception as e:
        st.error(f"AI önerileri hesaplanırken hata: {e}")
        return []


# =============================================================================
# GÖRÜNTÜLEME
# =============================================================================

def _render_content_card_body(
    content: dict,
    fav_manager: FavoritesManager,
    show_similarity: bool,
    idx: int = 0,
    key_prefix: str = "grid",
) -> None:
    """Bir içerik kartının gövdesini render eder (context manager'dan bağımsız)."""
    poster_url = content.get("poster_url") or TMDBClient.PLACEHOLDER_POSTER
    st.image(poster_url, width="stretch")

    title = content.get("title", "Bilinmiyor")
    st.markdown(f"**{title}**")

    vote_avg = content.get("vote_average", 0)
    release_date = content.get("release_date", "")
    year = release_date[:4] if release_date else "—"

    if vote_avg >= 8.0:
        rating_display = f"🌟 {vote_avg:.1f}"
    elif vote_avg >= 7.0:
        rating_display = f"⭐ {vote_avg:.1f}"
    else:
        rating_display = f"✨ {vote_avg:.1f}"

    st.caption(f"{rating_display} | 📅 {year}")

    if show_similarity and "similarity_score" in content:
        score = content["similarity_score"]
        st.caption(f"🎯 Benzerlik: %{score * 100:.0f}")

    content_id = content.get("id")
    is_fav = fav_manager.is_favorite(content_id)

    btn_label = "❤️ Favorilerde" if is_fav else "🤍 Favorilere Ekle"
    btn_key = f"fav_{key_prefix}_{idx}_{content_id}"

    if st.button(btn_label, key=btn_key, width="stretch"):
        is_now_fav, message = fav_manager.toggle(content)
        st.toast(f"{'❤️' if is_now_fav else '💔'} {message}: {title}")
        st.rerun()


def display_content_card(
    content: dict,
    fav_manager: FavoritesManager,
    show_similarity: bool = False,
    col=None,
    idx: int = 0,
    key_prefix: str = "grid",
) -> None:
    """
    Tek bir içerik kartı göster.

    NOT: Önceki sürümde `col` parametresi hiçbir zaman fonksiyona
    geçirilmiyordu, bu yüzden `container = col if col else st` satırı
    Streamlit modülünün kendisini bir context manager gibi kullanmaya
    çalışıyor ve `TypeError: 'module' object does not support the
    context manager protocol` hatası veriyordu. Artık `col` gerçekten
    geçirildiğinde onunla, geçirilmediğinde (çağıran zaten kendi
    `with cols[i]:` bloğunun içindeyse) doğrudan render ederek bu
    sorunu çözüyoruz.
    """
    if col is not None:
        with col:
            _render_content_card_body(content, fav_manager, show_similarity, idx=idx, key_prefix=key_prefix)
    else:
        _render_content_card_body(content, fav_manager, show_similarity, idx=idx, key_prefix=key_prefix)


def display_content_grid(
    items: list[dict],
    fav_manager: FavoritesManager,
    show_similarity: bool = False,
    key_prefix: str = "grid",
) -> None:
    """İçerik grid'i göster."""
    if not items:
        st.warning("🔍 Bu kriterlere uygun içerik bulunamadı.")
        return

    cols = st.columns(3)

    for idx, item in enumerate(items):
        with cols[idx % 3]:
            _render_content_card_body(item, fav_manager, show_similarity, idx=idx, key_prefix=key_prefix)
            st.divider()


def display_favorites_page(fav_manager: FavoritesManager) -> None:
    """Favoriler sayfasını göster."""
    st.header("❤️ Favorilerim")

    favorites = fav_manager.get_all()

    if not favorites:
        st.info(
            "📭 Henüz favori eklememişsin.\n\n"
            "Film veya dizileri keşfederken **'Favorilere Ekle'** butonuna tıklayarak "
            "listeni oluşturabilirsin!"
        )
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Favori", len(favorites))
    with col2:
        movies = [f for f in favorites if f.get("content_type") == "movie"]
        st.metric("Film", len(movies))
    with col3:
        shows = [f for f in favorites if f.get("content_type") == "tv"]
        st.metric("Dizi", len(shows))

    st.divider()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Tümünü Temizle", type="secondary"):
            fav_manager.clear_all()
            st.toast("Tüm favoriler temizlendi!")
            st.rerun()

    cols = st.columns(3)
    for idx, fav in enumerate(favorites):
        with cols[idx % 3]:
            poster_url = fav.get("poster_url") or fav.get("poster_path")
            if poster_url and not poster_url.startswith("http"):
                poster_url = f"https://image.tmdb.org/t/p/w342{poster_url}"

            if poster_url:
                st.image(poster_url, width="stretch")

            st.markdown(f"**{fav.get('title', 'Bilinmiyor')}**")

            vote_avg = fav.get("vote_average", 0)
            content_type = "🎬 Film" if fav.get("content_type") == "movie" else "📺 Dizi"
            st.caption(f"⭐ {vote_avg:.1f} | {content_type}")

            if st.button("💔 Kaldır", key=f"remove_{idx}_{fav.get('id')}"):
                fav_manager.remove(fav.get("id"))
                st.toast(f"💔 {fav.get('title')} favorilerden kaldırıldı!")
                st.rerun()

            st.divider()


# =============================================================================
# ANA SAYFA (ÇARK + TEK FİLTRE PANELİ)
# =============================================================================

@st.dialog("🎉 Çarktan çıkan film", width="small")
def _show_winner_dialog(winner: dict, fav_manager: FavoritesManager) -> None:
    """Kazanan içeriği ekranın tam ortasında bir modal pencerede göster."""
    st.image(winner.get("poster_url") or TMDBClient.PLACEHOLDER_POSTER, width="stretch")
    st.markdown(f"### {winner.get('title', 'Bilinmiyor')}")
    st.markdown(f"⭐ **Puan:** {winner.get('vote_average', 0):.1f}")
    st.markdown(f"📝 {(winner.get('overview') or 'Açıklama yok.')[:280]}...")

    is_fav = fav_manager.is_favorite(winner.get("id"))
    btn_text = "❤️ Zaten Favorilerde" if is_fav else "❤️ Favorilere Ekle"
    if st.button(btn_text, key="dialog_wheel_result_fav", width="stretch"):
        if not is_fav:
            fav_manager.add(winner)
            st.toast(f"❤️ {winner.get('title')} favorilere eklendi!")
            st.rerun()


def render_home_tab(tmdb: TMDBClient, fav_manager: FavoritesManager) -> None:
    """Filtre paneli + ortada çark + genişletilebilir tam sonuç listesi."""

    mood_options = list(MOOD_FILTERS.keys())
    genre_options = list(GENRE_FILTERS.keys())

    with st.sidebar:
        st.markdown('<div class="section-title">🎯 Filtreler</div>', unsafe_allow_html=True)

        selected_moods = st.multiselect(
            "Ruh hali",
            options=mood_options,
            format_func=lambda k: f"{MOOD_FILTERS[k].icon} {MOOD_FILTERS[k].label}",
        )
        selected_genres = st.multiselect(
            "Tür",
            options=genre_options,
            format_func=lambda k: f"{GENRE_FILTERS[k].icon} {GENRE_FILTERS[k].label}",
        )
        min_rating = st.slider("Min puan", 0.0, 10.0, 6.0, 0.5)
        sort_label = st.selectbox("Sırala", options=list(SORT_OPTIONS.keys()))
        content_type = st.selectbox(
            "İçerik türü",
            options=["movie", "tv"],
            format_func=lambda x: "🎥 Film" if x == "movie" else "📺 Dizi",
        )
        random_mode = st.checkbox("🎲 Rastgele mod", help="Filtreleri yok sayıp kaliteli rastgele içerik getirir")

    mood_genre_ids = get_mood_genre_ids(selected_moods)
    genre_genre_ids = get_genre_genre_ids(selected_genres)

    filters_signature = (
        tuple(sorted(selected_moods)),
        tuple(sorted(selected_genres)),
        min_rating,
        sort_label,
        content_type,
        random_mode,
    )
    if st.session_state.get("filters_signature") != filters_signature:
        st.session_state.filters_signature = filters_signature
        st.session_state.wheel_winner = None
        st.session_state.spin_seed = st.session_state.get("spin_seed", 0)

    with st.spinner("İçerikler yükleniyor..."):
        pool = fetch_filtered_pool(
            _tmdb=tmdb,
            mood_genre_ids=tuple(sorted(mood_genre_ids)),
            genre_genre_ids=tuple(sorted(genre_genre_ids)),
            min_rating=min_rating,
            sort_label=sort_label,
            content_type=content_type,
            random_mode=random_mode,
        )

    if random_mode:
        st.caption("🎲 Rastgele mod açık: ruh hali/tür seçimlerin yok sayılıyor, kaliteli içerik havuzundan rastgele seçiliyor.")
    elif not selected_moods and not selected_genres:
        st.caption("ℹ️ Herhangi bir ruh hali/tür seçmedin — bu yüzden herhangi bir kategoriye göre ayırt etmeden, sadece popülerliğe/puana göre genel içerikler gösteriliyor. Belirli bir kategoriye göre daraltmak için soldan ruh hali veya tür seç.")
    else:
        chosen = [MOOD_FILTERS[k].label for k in selected_moods] + [GENRE_FILTERS[k].label for k in selected_genres]
        st.caption(f"🎯 Uygulanan filtreler: {', '.join(chosen)}")

    wheel_items = pool[:8]

    st.session_state.setdefault("spin_seed", 0)
    st.session_state.setdefault("wheel_winner", None)

    if len(wheel_items) < 2:
        st.warning("🔍 Çark için yeterli sonuç yok. Filtreleri biraz gevşetmeyi dene.")
        return

    wcol1, wcol2, wcol3 = st.columns([1, 2, 1])
    with wcol2:
        st.markdown('<div class="section-title" style="text-align:center;">🎰 Film Çarkı</div>', unsafe_allow_html=True)

        spin_clicked = st.button("🎰 Çarkı Çevir!", width="stretch", type="primary")

        if spin_clicked:
            st.session_state.wheel_winner = random.choice(wheel_items)
            st.session_state.spin_seed += 1

        winning_index = None
        autoplay = False
        winner = st.session_state.wheel_winner
        if winner is not None:
            try:
                winning_index = wheel_items.index(winner)
                autoplay = spin_clicked
            except ValueError:
                winner = None
                st.session_state.wheel_winner = None

        render_roulette_wheel(
            wheel_items,
            winning_index=winning_index,
            autoplay=autoplay,
            spin_seed=st.session_state.spin_seed,
        )

        if spin_clicked and winner is not None:
            # Çark ~4 saniyelik bir CSS animasyonuyla dönüyor (tarayıcıda,
            # iframe içinde). Kazananı hemen göstermek yerine kısa bir
            # bekleme koyup afişin çark tamamen durmadan ekrana düşmesini
            # engelliyoruz.
            with st.spinner("Çark dönüyor..."):
                time.sleep(3.2)
            _show_winner_dialog(winner, fav_manager)

    st.divider()
    with st.expander(f"📋 Tüm sonuçları listele ({len(pool)} sonuç)"):
        display_content_grid(pool, fav_manager, show_similarity=False, key_prefix="home")


# =============================================================================
# ANA UYGULAMA
# =============================================================================

def main():
    """Ana uygulama fonksiyonu."""

    st.markdown(
        """
        <div class="main-header">
            <div>
                <h1>Cine<span>Roulette</span></h1>
                <p>Ne izleyeceğine karar veremedin mi? Çarkı çevir.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tmdb = init_tmdb_client()

    if not tmdb:
        st.error(
            "⚠️ **TMDB API anahtarı bulunamadı!**\n\n"
            "Lütfen aşağıdaki adımları takip edin:\n\n"
            "1. [TMDB](https://www.themoviedb.org/) sitesine üye olun\n"
            "2. Hesap ayarlarından API anahtarı alın\n"
            "3. Proje klasöründe `.env` dosyası oluşturun\n"
            "4. `TMDB_API_KEY=sizin_api_anahtariniz` şeklinde ekleyin"
        )
        with st.expander("📝 Örnek .env dosyası"):
            st.code("TMDB_API_KEY=abc123xyz789", language="text")
        return

    ml_engine = init_ml_engine()
    fav_manager = init_favorites_manager()

    tab_home, tab_ai, tab_favorites = st.tabs(["🎰 Anasayfa", "🤖 AI Önerileri", "❤️ Favorilerim"])

    with tab_home:
        render_home_tab(tmdb, fav_manager)

    with tab_ai:
        st.markdown('<div class="section-title">🤖 Senin İçin Öneriler</div>', unsafe_allow_html=True)
        st.caption(AI_RECOMMENDATION_FILTER.description)

        ai_content_type = st.selectbox(
            "İçerik türü",
            options=["movie", "tv"],
            format_func=lambda x: "🎥 Film" if x == "movie" else "📺 Dizi",
            key="ai_content_type",
        )

        favorites = fav_manager.get_for_ml()
        if not favorites:
            st.warning(
                "🤖 AI önerileri için önce favorilerine birkaç film/dizi eklemelisin!\n\n"
                "**Nasıl yapılır:**\n"
                "1. Anasayfa'dan beğendiğin filmlere 'Favorilere Ekle' butonuna tıkla\n"
                "2. Bu sekmeye geri dön"
            )
        else:
            # NOT: Öneriler eskiden her sayfa etkileşiminde (ör. Anasayfa'da
            # filtre değiştirmede) arka planda otomatik hesaplanıyordu — bu,
            # görünmeden TMDB'ye 4-6 istek atıp tüm uygulamayı yavaşlatıyordu.
            # Artık sadece kullanıcı butona bastığında hesaplanıyor.
            st.session_state.setdefault("ai_recommendations", None)
            st.session_state.setdefault("ai_recommendations_key", None)

            cache_key = (ai_content_type, tuple(sorted(f.get("id") for f in favorites)))
            compute_clicked = st.button("🔄 Önerileri Hesapla", type="primary", key="ai_compute_btn")

            if compute_clicked:
                with st.spinner("Öneriler hesaplanıyor..."):
                    st.session_state.ai_recommendations = fetch_ai_recommendations(
                        tmdb=tmdb,
                        ml_engine=ml_engine,
                        favorites=favorites,
                        content_type=ai_content_type,
                    )
                    st.session_state.ai_recommendations_key = cache_key

            if st.session_state.ai_recommendations_key != cache_key:
                st.info("Favorilerin veya seçtiğin içerik türü değişti. Güncel öneriler için yukarıdaki butona bas.")
            elif st.session_state.ai_recommendations is not None:
                display_content_grid(st.session_state.ai_recommendations, fav_manager, show_similarity=True, key_prefix="ai")

    with tab_favorites:
        display_favorites_page(fav_manager)


if __name__ == "__main__":
    main()
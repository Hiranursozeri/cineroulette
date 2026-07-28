import random
import time
import datetime
import streamlit as st
from typing import Optional

from utils.tmdb_client import TMDBClient, ResultList
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


def get_mood_keyword_ids(selected_moods: list[str]) -> list[int]:
    """
    Sadece TEK bir ruh hali seçiliyse, o ruh halinin TMDB anahtar
    kelimelerini (ör. Ağlamalık -> "tearjerker") döndürür. Bu, ruh hali
    filtresinin salt tür eşlemesinden öteye geçip gerçekten o temaya uygun
    içerikleri bulmasını sağlar.

    Birden fazla ruh hali seçiliyse boş liste döner — çünkü hangi
    keyword'ün hangi türle eşleşmesi gerektiği belirsizleşir (ör. "Ağlamalık
    + Korku Gecesi" seçiliyse "tearjerker" keyword'ü korku filmlerine de
    uygulanır mı, belirsiz). Bu durumda salt tür bazlı filtrelemeye dönülür.
    """
    if len(selected_moods) != 1:
        return []
    fc = MOOD_FILTERS.get(selected_moods[0])
    return list(fc.keyword_ids) if fc and fc.keyword_ids else []


def resolve_sort_by(sort_label: str, content_type: str) -> str:
    """Sıralama etiketini TMDB'nin beklediği sort_by string'ine çevirir."""
    sort_value = SORT_OPTIONS.get(sort_label, "popularity.desc")
    if content_type == "tv" and sort_value.startswith("release_date"):
        return sort_value.replace("release_date", "first_air_date")
    return sort_value


def _discover(
    tmdb: TMDBClient,
    genre_ids: list[int],
    keyword_ids: list[int],
    rating_range: tuple[float, float],
    year_range: tuple[int, int],
    runtime_range: Optional[tuple[int, int]],
    sort_by: str,
    content_type: str,
    page: int,
):
    """Tek bir kategori grubu (sadece mood ya da sadece genre) için TMDB isteği."""
    query_genre_ids = genre_ids
    if content_type == "tv" and query_genre_ids:
        query_genre_ids = get_tv_genre_ids(query_genre_ids)

    common_kwargs = dict(
        genre_ids=query_genre_ids or None,
        keyword_ids=keyword_ids or None,
        min_vote_average=rating_range[0],
        max_vote_average=rating_range[1],
        # Oy sayısı filtresi kaldırıldı (kullanıcı için anlamsız/kafa
        # karıştırıcıydı) — sadece hiç oy almamış tamamen boş kayıtları
        # elemek için düşük, sabit bir taban bırakıyoruz.
        min_vote_count=5,
        year_from=year_range[0],
        year_to=year_range[1],
        sort_by=sort_by,
        page=page,
    )

    if content_type == "movie":
        if runtime_range is not None:
            common_kwargs["runtime_min"] = runtime_range[0]
            common_kwargs["runtime_max"] = runtime_range[1]
        result = tmdb.discover_movies(**common_kwargs)
    else:
        result = tmdb.discover_tv_shows(**common_kwargs)

    # TMDB'nin `primary_release_date.gte/lte` filtresi bazen filmin
    # gösterdiğimiz `release_date` alanından FARKLI bir bölgesel/birincil
    # tarihe göre eşleşiyor (ör. "2026" filtrelesen bile ekranda "2016"
    # yazan bir film çıkabiliyor). Bunu kesin olarak önlemek için,
    # döndürülen her öğeyi gösterdiğimiz release_date'in gerçek yılına göre
    # istemci tarafında bir kez daha süzüyoruz.
    y_from, y_to = year_range
    filtered = []
    for item in result:
        date_str = item.get("release_date") or ""
        try:
            year = int(date_str[:4])
        except (ValueError, TypeError):
            continue  # Tarihi bilinmeyen içerik, yıl filtresiyle tutarlı olmadığı için dahil edilmiyor
        if y_from <= year <= y_to:
            filtered.append(item)

    total = getattr(result, "total_results", len(filtered))
    new_result = ResultList(filtered)
    new_result.total_results = total
    return new_result


@st.cache_data(ttl=180, show_spinner=False)
def fetch_filtered_pool(
    _tmdb: TMDBClient,
    mood_genre_ids: tuple[int, ...],
    mood_keyword_ids: tuple[int, ...],
    genre_genre_ids: tuple[int, ...],
    rating_range: tuple[float, float],
    year_range: tuple[int, int],
    runtime_range: Optional[tuple[int, int]],
    sort_label: str,
    content_type: str,
    random_mode: bool,
) -> tuple[list[dict], int]:
    """
    Filtre panelinden gelen seçimlere göre içerik havuzu getirir.

    ÖNEMLİ: Ruh hali ve tür filtreleri artık arayüzde birbirini dışlıyor —
    kullanıcı ya ruh haline ya da türe göre filtreliyor, ikisine birden
    değil (ör. "Ağlamalık + Komedi" gibi anlamsız kombinasyonlar mümkün
    değil). Bu yüzden `mood_genre_ids` ve `genre_genre_ids`'den sadece biri
    doluyken, biz de sadece o grubu tek bir sorguda (grup içi VEYA/OR
    mantığıyla) kullanıyoruz.

    `mood_keyword_ids`: sadece TEK bir ruh hali seçiliyken doldurulur (ör.
    "Ağlamalık" -> "tearjerker" anahtar kelimesi). Bu, ruh hali filtresinin
    sadece tür eşlemesi değil, gerçek "tema" bazlı bir eşleme yapmasını
    sağlıyor.

    Sonuç sayısı azsa (< 8, çark için yetersiz), otomatik olarak 1-2 sayfa
    daha çekip havuzu büyütmeye çalışır.

    Returns:
        (içerik_listesi, tmdb_toplam_sonuç_sayısı) tuple'ı.

    `st.cache_data` ile önbelleğe alınıyor: aynı filtrelerle her widget
    etkileşiminde (ör. çarkı çevirme) TMDB'ye tekrar istek atmak yerine
    3 dakika boyunca aynı sonucu tekrar kullanıyoruz. `_tmdb` altçizgiyle
    başlıyor çünkü TMDBClient nesnesi cache anahtarına dahil edilemez
    (hash'lenemez), sadece çağrı için kullanılır.
    """
    tmdb = _tmdb
    try:
        if random_mode:
            items = tmdb.get_random_content(
                content_type=content_type,
                min_vote_average=rating_range[0] or RANDOM_FILTER.min_vote_average,
                min_vote_count=RANDOM_FILTER.min_vote_count,
                count=16,
            )
            return items, len(items)

        sort_by = resolve_sort_by(sort_label, content_type)
        mood_ids = list(mood_genre_ids)
        keyword_ids = list(mood_keyword_ids)
        genre_ids = list(genre_genre_ids)

        # Ruh hali ve tür karşılıklı dışlayıcı olduğu için burada her zaman
        # sadece biri dolu olur (ya da ikisi de boş = filtre yok).
        combined_ids = mood_ids or genre_ids
        combined_keywords = keyword_ids if mood_ids else []

        def _fetch(page: int):
            pool = _discover(tmdb, combined_ids, combined_keywords, rating_range, year_range, runtime_range, sort_by, content_type, page)
            return list(pool), getattr(pool, "total_results", len(pool))

        results, total_results = _fetch(page=1)

        # Havuz çark için yetersizse (ve daha fazla sonuç varsa) ek sayfalar çek.
        page = 2
        while len(results) < 8 and page <= 3 and total_results > len(results):
            more, _ = _fetch(page=page)
            existing_ids = {item.get("id") for item in results}
            results.extend(item for item in more if item.get("id") not in existing_ids)
            page += 1

        return results, total_results
    except Exception as e:
        st.error(f"İçerik yüklenirken hata: {e}")
        return [], 0


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

    st.caption("💡 İpucu: Anasayfa'daki filtre panelinden **'❤️ Favorilerimden'** modunu seçerek çarkı doğrudan bu listeden çevirebilirsin.")

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
def _show_winner_dialog(winner: dict, fav_manager: FavoritesManager, tmdb: TMDBClient) -> None:
    """Kazanan içeriği ekranın tam ortasında bir modal pencerede göster."""
    st.image(winner.get("poster_url") or TMDBClient.PLACEHOLDER_POSTER, width="stretch")
    st.markdown(f"### {winner.get('title', 'Bilinmiyor')}")
    st.markdown(f"⭐ **Puan:** {winner.get('vote_average', 0):.1f}")
    st.markdown(f"📝 {(winner.get('overview') or 'Açıklama yok.')[:280]}...")

    # Nerede izlenir — sadece burada, tek bir içerik için sorgulanıyor
    # (tüm havuz için sorgulamak gereksiz yere çok fazla istek atardı).
    try:
        providers = tmdb.get_watch_providers(winner.get("id"), winner.get("content_type", "movie"))
    except Exception:
        providers = {"flatrate": [], "rent": [], "buy": []}

    flatrate = providers.get("flatrate", [])
    if flatrate:
        st.caption("📺 Nerede izlenir: " + ", ".join(flatrate))
    elif providers.get("rent") or providers.get("buy"):
        options = providers.get("rent", []) + providers.get("buy", [])
        st.caption("💰 Kiralama/satın alma: " + ", ".join(sorted(set(options))))
    else:
        st.caption("📺 Bu içerik için Türkiye'de platform bilgisi bulunamadı.")

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

        # Ruh hali, tür ve favoriler artık birbirini dışlıyor — "Ağlamalık +
        # Komedi" gibi anlamsız kombinasyonlar imkansız, ve "favorilerimden
        # çevir" artık ayrı bir sekmede değil, buradaki filtrelerden biri.
        filter_mode = st.radio(
            "Nasıl filtrelemek istersin?",
            options=["mood", "genre", "favorites", "random"],
            format_func=lambda k: {
                "mood": "🎭 Ruh Haline Göre",
                "genre": "🎬 Türe Göre",
                "favorites": "❤️ Favorilerimden",
                "random": "🎲 Rastgele",
            }[k],
            key="filter_mode",
        )

        selected_moods: list[str] = []
        selected_genres: list[str] = []

        if filter_mode == "mood":
            selected_moods = st.multiselect(
                "Ruh hali",
                options=mood_options,
                format_func=lambda k: f"{MOOD_FILTERS[k].icon} {MOOD_FILTERS[k].label}",
                key="mood_multiselect",
            )
        elif filter_mode == "genre":
            selected_genres = st.multiselect(
                "Tür",
                options=genre_options,
                format_func=lambda k: f"{GENRE_FILTERS[k].icon} {GENRE_FILTERS[k].label}",
                key="genre_multiselect",
            )

        # Favoriler modunda TMDB filtreleri (puan/oy/yıl/süre/tür) anlamsız —
        # favori listen zaten sabit ve küçük bir küme. Bu yüzden bu modda
        # sadece favoriler kullanılıyor, aşağıdaki filtreler gizleniyor.
        if filter_mode == "favorites":
            fav_count = fav_manager.get_count()
            st.caption(f"❤️ {fav_count} favorin arasından çark dönecek.")
            rating_range = (0.0, 10.0)
            year_range = (1950, datetime.date.today().year)
            content_type = "movie"
            runtime_range = None
            random_mode = False
        elif filter_mode == "random":
            rating_range = st.slider("Min puan", 0.0, 10.0, (7.0, 10.0), 0.5)
            content_type = st.selectbox(
                "İçerik türü",
                options=["movie", "tv"],
                format_func=lambda x: "🎥 Film" if x == "movie" else "📺 Dizi",
                key="random_content_type",
            )
            year_range = (1950, datetime.date.today().year)
            runtime_range = None
            random_mode = True
        else:
            rating_range = st.slider("Puan aralığı", 0.0, 10.0, (6.0, 10.0), 0.5)
            current_year = datetime.date.today().year
            year_range = st.slider("Yapım yılı aralığı", 1950, current_year, (1990, current_year))
            content_type = st.selectbox(
                "İçerik türü",
                options=["movie", "tv"],
                format_func=lambda x: "🎥 Film" if x == "movie" else "📺 Dizi",
            )
            runtime_range = None
            if content_type == "movie":
                runtime_range = st.slider("Süre (dakika)", 0, 240, (0, 240), 10)
            else:
                st.caption("ℹ️ TMDB, dizilerde süre filtresini desteklemiyor.")
            random_mode = False

    mood_genre_ids = get_mood_genre_ids(selected_moods)
    mood_keyword_ids = get_mood_keyword_ids(selected_moods)
    genre_genre_ids = get_genre_genre_ids(selected_genres)

    # Havuzu çekerken sabit bir varsayılan sıralama kullanıyoruz. Kullanıcıya
    # gösterilen "Sırala" seçimi artık aşağıda, "Tüm sonuçları listele"
    # bölümünde ve sadece o listenin görünüm sırasını etkiliyor — havuzun
    # kendisini değiştirmiyor, bu yüzden filters_signature'a dahil değil.
    default_sort_label = "Popülerlik"

    filters_signature = (
        filter_mode,
        tuple(sorted(selected_moods)),
        tuple(sorted(selected_genres)),
        rating_range,
        year_range,
        runtime_range,
        content_type,
        random_mode,
    )
    if st.session_state.get("filters_signature") != filters_signature:
        st.session_state.filters_signature = filters_signature
        st.session_state.wheel_winner = None
        st.session_state.spin_seed = st.session_state.get("spin_seed", 0)

    if filter_mode == "favorites":
        pool = fav_manager.get_all()
        total_results = len(pool)
    else:
        with st.spinner("İçerikler yükleniyor..."):
            pool, total_results = fetch_filtered_pool(
                _tmdb=tmdb,
                mood_genre_ids=tuple(sorted(mood_genre_ids)),
                mood_keyword_ids=tuple(sorted(mood_keyword_ids)),
                genre_genre_ids=tuple(sorted(genre_genre_ids)),
                rating_range=rating_range,
                year_range=year_range,
                runtime_range=runtime_range,
                sort_label=default_sort_label,
                content_type=content_type,
                random_mode=random_mode,
            )

    if filter_mode == "favorites":
        if not pool:
            st.info(
                "📭 Henüz favori eklememişsin.\n\n"
                "Bir mod veya tür seçip beğendiğin içerikleri **'Favorilere Ekle'** "
                "ile listene ekleyebilir, sonra buradan çevirebilirsin."
            )
            return
        st.caption(f"❤️ Favorilerinden çark dönüyor ({total_results} favori).")
    elif random_mode:
        st.caption(f"🎲 Rastgele mod: ruh hali/tür seçimlerin yok sayılıyor, kaliteli içerik havuzundan rastgele seçiliyor ({total_results} sonuç).")
    elif not selected_moods and not selected_genres:
        st.caption(f"ℹ️ Herhangi bir ruh hali/tür seçmedin — sadece popülerliğe/puana göre genel içerikler gösteriliyor (toplam {total_results:,} sonuç). Belirli bir kategoriye göre daraltmak için soldan ruh hali veya tür seç.".replace(",", "."))
    else:
        chosen = [MOOD_FILTERS[k].label for k in selected_moods] + [GENRE_FILTERS[k].label for k in selected_genres]
        st.caption(f"🎯 Uygulanan filtreler: {', '.join(chosen)} — toplam {total_results:,} sonuç".replace(",", "."))
        if mood_keyword_ids:
            st.caption("🔍 Tek ruh hali seçili olduğu için tür eşleşmesinin ötesinde, o temaya uygun anahtar kelimeyle de daraltıldı (ör. gerçekten 'hüzünlü' etiketli filmler).")

    wheel_items = random.sample(pool, min(20, len(pool))) if pool else []

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
            _show_winner_dialog(winner, fav_manager, tmdb)

    _render_full_results_section(
        tmdb, fav_manager, pool, total_results, filters_signature,
        mood_genre_ids, genre_genre_ids, mood_keyword_ids,
        rating_range, year_range, runtime_range,
        content_type, default_sort_label,
    )


@st.fragment
def _render_full_results_section(
    tmdb: TMDBClient,
    fav_manager: FavoritesManager,
    pool: list[dict],
    total_results: int,
    filters_signature: tuple,
    mood_genre_ids: list[int],
    genre_genre_ids: list[int],
    mood_keyword_ids: list[int],
    rating_range: tuple[float, float],
    year_range: tuple[int, int],
    runtime_range: Optional[tuple[int, int]],
    content_type: str,
    default_sort_label: str,
) -> None:
    """
    "Tüm sonuçları listele" bölümü — kendi sayfalama durumunu tutuyor.
    `pool` sadece ilk sayfayı (~20 sonuç) temsil eder; kullanıcı "Daha
    fazla göster" ile ek TMDB sayfaları isteyebilir. Bu, çarkın küçük
    örnekleminden (max 20 rastgele) tamamen bağımsız çalışır.

    `@st.fragment` ile işaretli: "Daha fazla göster" butonuna basınca
    SADECE bu bölüm yeniden çiziliyor, tüm sayfa değil — bu yüzden çark ve
    sidebar yerinde kalıyor, tarayıcı sayfanın başına atlamıyor.
    """
    if st.session_state.get("list_pool_sig") != filters_signature:
        st.session_state["list_pool_sig"] = filters_signature
        st.session_state["list_pool_items"] = list(pool)
        st.session_state["list_pool_page"] = 1

        # Filtre değiştiğinde, kullanıcı hiç tıklamadan bir sayfa daha
        # (toplam ~40 sonuç) önden yüklüyoruz. Bu, "Daha fazla göster"
        # butonuna olan ihtiyacı azaltarak sayfa kayması sorununu daha az
        # sıklıkla yaşatıyor (kökten çözmüyor ama etkisini azaltıyor).
        if total_results > len(pool):
            sort_by = resolve_sort_by(default_sort_label, content_type)
            combined_ids = list(mood_genre_ids) or list(genre_genre_ids)
            combined_keywords = list(mood_keyword_ids) if mood_genre_ids else []
            try:
                extra = _discover(
                    tmdb, combined_ids, combined_keywords,
                    rating_range, year_range, runtime_range,
                    sort_by, content_type, page=2,
                )
                existing_ids = {item.get("id") for item in st.session_state["list_pool_items"]}
                st.session_state["list_pool_items"].extend(
                    item for item in extra if item.get("id") not in existing_ids
                )
                st.session_state["list_pool_page"] = 2
            except Exception:
                pass  # Ön yükleme başarısız olursa sessizce 1. sayfayla devam

    st.session_state.setdefault("list_pool_items", list(pool))
    st.session_state.setdefault("list_pool_page", 1)

    display_pool = st.session_state["list_pool_items"]

    st.divider()
    with st.expander(
        f"📋 Tüm sonuçları listele ({len(display_pool)} / {total_results:,} sonuç)".replace(",", "."),
        expanded=st.session_state.get("list_expanded_once", False),
    ):
        st.session_state["list_expanded_once"] = True
        if display_pool:
            list_sort_label = st.selectbox(
                "Sırala",
                options=list(SORT_OPTIONS.keys()),
                key="list_sort_label",
                help="Sadece bu listenin görünüm sırasını değiştirir, çarktaki havuzu etkilemez.",
            )
            sort_keys = {
                "Popülerlik": lambda item: item.get("popularity", 0),
                "Puan (yüksekten düşüğe)": lambda item: item.get("vote_average", 0),
                "Yeni çıkanlar": lambda item: item.get("release_date") or "",
            }
            sorted_pool = sorted(display_pool, key=sort_keys.get(list_sort_label, sort_keys["Popülerlik"]), reverse=True)
        else:
            sorted_pool = display_pool

        display_content_grid(sorted_pool, fav_manager, show_similarity=False, key_prefix="home")

        max_pages = 10  # TMDB'yi gereksiz zorlamamak için makul bir tavan
        can_load_more = len(display_pool) < total_results and st.session_state["list_pool_page"] < max_pages

        if can_load_more:
            if st.button("📥 Daha fazla göster (+20)", key="load_more_btn", width="stretch"):
                next_page = st.session_state["list_pool_page"] + 1
                sort_by = resolve_sort_by(default_sort_label, content_type)
                combined_ids = list(mood_genre_ids) or list(genre_genre_ids)
                combined_keywords = list(mood_keyword_ids) if mood_genre_ids else []
                with st.spinner("Daha fazla sonuç yükleniyor..."):
                    more = _discover(
                        tmdb, combined_ids, combined_keywords,
                        rating_range, year_range, runtime_range,
                        sort_by, content_type, next_page,
                    )
                existing_ids = {item.get("id") for item in st.session_state["list_pool_items"]}
                st.session_state["list_pool_items"].extend(
                    item for item in more if item.get("id") not in existing_ids
                )
                st.session_state["list_pool_page"] = next_page
                # Sadece bu fragment'ı yeniden çalıştır (tüm sayfayı değil) —
                # böylece sayfa başa sarmıyor, çark ve sidebar yerinde kalıyor.
                try:
                    st.rerun(scope="fragment")
                except Exception:
                    # Bazı ortamlarda fragment-scope rerun desteklenmeyebilir;
                    # bu durumda normal (tüm sayfa) yeniden çalıştırmaya düş.
                    st.rerun()
        elif display_pool and len(display_pool) >= total_results:
            st.caption("✅ Tüm sonuçlar yüklendi.")


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

    # "Daha fazla göster" gibi butonlar her tıklamada bir yeniden çalıştırma
    # (rerun) tetikliyor ve Streamlit sayfayı yeniden çizerken tarayıcı
    # kaydırma konumunu kaybedip başa dönebiliyor. Bu script, kaydırma
    # konumunu sürekli kaydedip her yeniden çizimden hemen sonra geri
    # yüklüyor — böylece kullanıcı bulunduğu yerde kalıyor.
    st.iframe(
        """
        <script>
        try {
            const mainDoc = window.parent.document;
            const scrollKey = 'cineroulette_scroll_y';

            const selectors = [
                '[data-testid="stAppViewContainer"]',
                '[data-testid="stMain"]',
                'section.main',
            ];
            let container = null;
            for (const sel of selectors) {
                const el = mainDoc.querySelector(sel);
                if (el) { container = el; break; }
            }
            if (!container) { container = mainDoc.documentElement; }

            const restore = () => {
                const saved = window.parent.sessionStorage.getItem(scrollKey);
                if (saved !== null) {
                    container.scrollTop = parseInt(saved, 10);
                    window.parent.scrollTo(0, parseInt(saved, 10));
                }
            };
            // Streamlit rerun sonrası DOM'un tam oturması icin kisa bir gecikmeyle de deneyelim.
            restore();
            setTimeout(restore, 50);
            setTimeout(restore, 200);

            const save = () => {
                const y = container.scrollTop || window.parent.scrollY || 0;
                window.parent.sessionStorage.setItem(scrollKey, y);
            };
            container.addEventListener('scroll', save);
            window.parent.addEventListener('scroll', save);
        } catch (e) {
            // Sandbox/erişim kısıtlaması olursa sessizce yoksay — sayfanın
            // geri kalanını bozmasın.
        }
        </script>
        """,
        height=1,
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
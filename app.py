import random
import time
import datetime
import base64
import json
import uuid
import streamlit as st
from typing import Optional

from utils.tmdb_client import TMDBClient, ResultList
from utils.favorites_manager import FavoritesManager
from utils.feedback_manager import FeedbackManager
from utils.share_card import generate_share_card
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
    page_title="CineRoulette 🎬 - Ne İzleyeceğine Karar Ver",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit'in `set_page_config`'i meta açıklama / sosyal medya önizleme
# etiketlerini (Open Graph, Twitter Card) desteklemiyor — bunları JS ile
# sayfanın gerçek <head> kısmına ekliyoruz. Bu hem Google'ın arama
# sonuçlarında gösterdiği açıklamayı hem de WhatsApp/Twitter gibi
# uygulamalarda linki paylaşınca çıkan önizleme kartını iyileştirir.
st.iframe(
    """
    <script>
    (function() {
        try {
            const head = window.parent.document.head;
            const metaTags = [
                {name: "description", content: "CineRoulette — Ne izleyeceğine karar veremedin mi? Ruh haline göre film/dizi öner, çarkı çevir ya da bir kart çek. Ücretsiz, hesap gerektirmez."},
                {property: "og:title", content: "CineRoulette 🎬 - Ne İzleyeceğine Karar Ver"},
                {property: "og:description", content: "Ruh haline göre film/dizi öner, çarkı çevir ya da bir kart çek."},
                {property: "og:type", content: "website"},
                {name: "twitter:card", content: "summary"},
                {name: "twitter:title", content: "CineRoulette 🎬"},
                {name: "twitter:description", content: "Ne izleyeceğine karar veremedin mi? Çarkı çevir ya da bir kart çek."},
            ];
            metaTags.forEach(function(tagInfo) {
                const key = tagInfo.name ? "name" : "property";
                const value = tagInfo.name || tagInfo.property;
                let el = head.querySelector('meta[' + key + '="' + value + '"]');
                if (!el) {
                    el = window.parent.document.createElement("meta");
                    el.setAttribute(key, value);
                    head.appendChild(el);
                }
                el.setAttribute("content", tagInfo.content);
            });
        } catch (e) {
            // Sandbox kısıtlaması olursa sessizce geç, sayfanın geri kalanını bozmasın.
        }
    })();
    </script>
    """,
    height=1,
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
        min-height: 2.6rem;
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


def get_or_create_session_id() -> str:
    """
    Her tarayıcı oturumu (ziyaretçi) için benzersiz bir kimlik üretir/döndürür.

    ÖNEMLİ: Uygulama artık birden fazla gerçek kullanıcı tarafından aynı anda
    kullanılabildiği için, favoriler/geri bildirimler bu kimliğe özel ayrı
    dosyalarda tutulur — aksi halde tüm ziyaretçilerin verileri tek bir ortak
    dosyada birbirinin üzerine yazılırdı.

    Kimlik hem `st.session_state`'te (bu oturum boyunca) hem de URL'nin
    query param'ında (`?sid=...`) tutulur — böylece kullanıcı sayfayı
    yenilese (F5) bile aynı kimliğe (ve dolayısıyla aynı favori/geri
    bildirim verisine) geri dönebilir.
    """
    if "session_id" not in st.session_state:
        existing = st.query_params.get("sid")
        if existing:
            st.session_state["session_id"] = existing
        else:
            new_id = uuid.uuid4().hex[:16]
            st.session_state["session_id"] = new_id
            st.query_params["sid"] = new_id
    return st.session_state["session_id"]


def init_favorites_manager(session_id: str) -> FavoritesManager:
    """Favori yöneticisini başlat (bu oturuma özel dosyayla)."""
    return FavoritesManager(session_id=session_id)


def init_feedback_manager(session_id: str) -> FeedbackManager:
    """İzledim/beğenmedim geri bildirim yöneticisini başlat (bu oturuma özel dosyayla)."""
    return FeedbackManager(session_id=session_id)


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

    # KATI TÜR FİLTRESİ: TMDB, bir filmi "Komedi" seçince bile o filmin
    # TÜM türlerinden herhangi birinde Komedi geçiyorsa döndürür — ör.
    # "Parazit" (Komedi, Gerilim, Dram) veya "Moana" (Animasyon, Macera,
    # Komedi, Aile) gibi filmler, Komedi asıl/baskın türleri olmadığı halde
    # çıkabiliyor. Bunu önlemek için, seçilen türlerden en az birinin o
    # filmin TMDB'de listelediği BİRİNCİL (ilk) tür olmasını şart koşuyoruz.
    if query_genre_ids:
        genre_id_set = set(query_genre_ids)
        filtered = [
            item for item in filtered
            if (item.get("genre_ids") or [None])[0] in genre_id_set
        ]

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

        # Çeşitliliği artırmak için her zaman daha büyük bir aday havuzu
        # hedefliyoruz (sadece sonuç azken değil) — yoksa havuz hep aynı
        # ~20 "en popüler" sonuçla sınırlı kalıyor ve çark/kart tekrar tekrar
        # aynı birkaç filmi gösteriyordu.
        target_pool_size = 60
        page = 2
        while len(results) < target_pool_size and page <= 3 and total_results > len(results):
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
    feedback_manager: FeedbackManager,
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

    if feedback_manager.is_watched(content_id):
        st.success("Beğendin", icon="✅")
    elif feedback_manager.is_disliked(content_id):
        st.error("Beğenmedin", icon="🚫")
    else:
        fb_col1, fb_col2 = st.columns(2)
        with fb_col1:
            if st.button("✅ Beğendim", key=f"watched_{key_prefix}_{idx}_{content_id}", width="stretch"):
                feedback_manager.mark_watched(content)
                st.toast(f"✅ '{title}' beğendiğin olarak kaydedildi.")
                st.rerun()
        with fb_col2:
            if st.button("🚫 Beğenmedim", key=f"disliked_{key_prefix}_{idx}_{content_id}", width="stretch"):
                feedback_manager.mark_disliked(content)
                if is_fav:
                    fav_manager.remove(content_id)
                st.toast(f"🚫 '{title}' bir daha önerilmeyecek.")
                st.rerun()



def display_content_card(
    content: dict,
    fav_manager: FavoritesManager,
    feedback_manager: FeedbackManager,
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
            _render_content_card_body(content, fav_manager, feedback_manager, show_similarity, idx=idx, key_prefix=key_prefix)
    else:
        _render_content_card_body(content, fav_manager, feedback_manager, show_similarity, idx=idx, key_prefix=key_prefix)


def display_content_grid(
    items: list[dict],
    fav_manager: FavoritesManager,
    feedback_manager: FeedbackManager,
    show_similarity: bool = False,
    key_prefix: str = "grid",
) -> None:
    """İçerik grid'i göster."""
    if not items:
        st.warning("🔍 Bu kriterlere uygun içerik bulunamadı.")
        return

    st.caption("🌟 = 8+ puan · ⭐ = 7-7.9 puan · ✨ = 7'nin altı")

    cols = st.columns(3)

    for idx, item in enumerate(items):
        with cols[idx % 3]:
            _render_content_card_body(item, fav_manager, feedback_manager, show_similarity, idx=idx, key_prefix=key_prefix)
            st.divider()


def display_favorites_page(tmdb: TMDBClient, fav_manager: FavoritesManager, feedback_manager: FeedbackManager) -> None:
    """Favoriler sayfasını göster."""
    st.header("❤️ Favorilerim")

    # ---- ARAMA: favorileri sıfırdan oluşturabilmek için ----
    st.markdown('<div class="section-title">🔍 Film / Dizi Ara</div>', unsafe_allow_html=True)
    st.caption("Aklındaki filmi doğrudan ara, favorilere ekle — filtrelerden geçmene gerek yok.")

    s_col1, s_col2, s_col3 = st.columns([3, 1.2, 1])
    with s_col1:
        search_query = st.text_input(
            "Ara", key="fav_search_query", label_visibility="collapsed",
            placeholder="Film veya dizi adı yaz...",
        )
    with s_col2:
        search_type = st.selectbox(
            "Tür", options=["movie", "tv"], key="fav_search_type", label_visibility="collapsed",
            format_func=lambda x: "🎥 Film" if x == "movie" else "📺 Dizi",
        )
    with s_col3:
        search_clicked = st.button("🔍 Ara", key="fav_search_btn", width="stretch", type="primary")

    st.session_state.setdefault("fav_search_results", None)
    st.session_state.setdefault("fav_search_query_done", "")

    if search_clicked and search_query.strip():
        with st.spinner("Aranıyor..."):
            if search_type == "movie":
                results = tmdb.search_movies(search_query.strip())
            else:
                results = tmdb.search_tv_shows(search_query.strip())
        st.session_state["fav_search_results"] = results
        st.session_state["fav_search_query_done"] = search_query.strip()

    if st.session_state["fav_search_results"] is not None:
        results = st.session_state["fav_search_results"]
        if results:
            st.caption(f"'{st.session_state['fav_search_query_done']}' için {len(results)} sonuç bulundu.")
            display_content_grid(results[:12], fav_manager, feedback_manager, show_similarity=False, key_prefix="favsearch")
        else:
            st.warning(f"'{st.session_state['fav_search_query_done']}' için sonuç bulunamadı.")

    st.divider()

    favorites = fav_manager.get_all()

    if not favorites:
        st.info(
            "📭 Henüz favori eklememişsin.\n\n"
            "Yukarıdan arama yaparak ya da film/dizileri keşfederken **'Favorilere Ekle'** "
            "butonuna tıklayarak listeni oluşturabilirsin!"
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

    st.caption("💡 İpucu: Anasayfa'daki filtre panelinden **'❤️ Favorilerimden'** modunu seçerek çarkı veya kart destesini doğrudan bu listeden çalıştırabilirsin.")

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


def display_feedback_page(fav_manager: FavoritesManager, feedback_manager: FeedbackManager) -> None:
    """Beğendiğim / Beğenmediğim listelerini gösterir, geri alma imkanı sunar."""
    st.header("👍👎 Beğendiklerim / Beğenmediklerim")
    st.caption(
        "Beğendiğin içerikler çarkta/listede görünmeye devam eder — sadece "
        "beğenmediklerin gizlenir. Fikrini değiştirirsen buradan geri alabilirsin."
    )

    liked_tab, disliked_tab = st.tabs(["✅ Beğendiklerim", "🚫 Beğenmediklerim"])

    with liked_tab:
        liked_items = feedback_manager.get_watched_list()
        if not liked_items:
            st.info("📭 Henüz hiçbir şeyi 'Beğendim' olarak işaretlemedin.")
        else:
            st.caption(f"{len(liked_items)} içerik")
            cols = st.columns(3)
            for idx, item in enumerate(liked_items):
                with cols[idx % 3]:
                    st.markdown(f"**{item.get('title', 'Bilinmiyor')}**")
                    content_label = "🎬 Film" if item.get("content_type") == "movie" else "📺 Dizi"
                    st.caption(content_label)
                    if st.button("↩️ Geri Al", key=f"undo_watched_{idx}_{item.get('id')}", width="stretch"):
                        feedback_manager.unmark(item.get("id"))
                        st.toast(f"↩️ '{item.get('title')}' için işaret geri alındı.")
                        st.rerun()
                    st.divider()

    with disliked_tab:
        disliked_items = feedback_manager.get_disliked_list()
        if not disliked_items:
            st.info("📭 Henüz hiçbir şeyi 'Beğenmedim' olarak işaretlemedin.")
        else:
            st.caption(f"{len(disliked_items)} içerik — bunlar çarkta/listede/AI önerilerinde gizleniyor.")
            cols = st.columns(3)
            for idx, item in enumerate(disliked_items):
                with cols[idx % 3]:
                    st.markdown(f"**{item.get('title', 'Bilinmiyor')}**")
                    content_label = "🎬 Film" if item.get("content_type") == "movie" else "📺 Dizi"
                    st.caption(content_label)
                    if st.button("↩️ Geri Al", key=f"undo_disliked_{idx}_{item.get('id')}", width="stretch"):
                        feedback_manager.unmark(item.get("id"))
                        st.toast(f"↩️ '{item.get('title')}' tekrar gösterilecek.")
                        st.rerun()
                    st.divider()


# =============================================================================
# ANA SAYFA (ÇARK + TEK FİLTRE PANELİ)
# =============================================================================

@st.dialog("🎉 Seçilen Film", width="small")
def _show_winner_dialog(
    winner: dict,
    fav_manager: FavoritesManager,
    feedback_manager: FeedbackManager,
    tmdb: TMDBClient,
    mode: str = "wheel",
) -> None:
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

    try:
        trailer_key = tmdb.get_trailer_key(winner.get("id"), winner.get("content_type", "movie"))
    except Exception:
        trailer_key = None

    if trailer_key:
        with st.expander("🎬 Fragmanı İzle"):
            st.video(f"https://www.youtube.com/watch?v={trailer_key}")
            st.caption(f"Gömülü oynatıcı çalışmazsa (bazı Google hesabı/ağ kısıtlamalarında olabiliyor): [YouTube'da aç](https://www.youtube.com/watch?v={trailer_key})")

    with st.expander("📤 Paylaş"):
        cta_text = "Çarkı sen de çevir!" if mode == "wheel" else "Sen de bir kart çek!"
        share_image = generate_share_card(winner, cta_text=cta_text)
        clapper_emoji = "\U0001F3AC"  # 🎬 — dosya kodlaması bozulmalarına karşı Unicode kaçış kodu kullanıyoruz
        share_caption = f"Bana bu film çıktı! {clapper_emoji} {winner.get('title', 'Bilinmiyor')}"

        if share_image:
            st.image(share_image, width="stretch")

            # Native paylaşım: tarayıcı destekliyorsa (çoğunlukla mobil
            # Chrome/Safari) gerçek görseli doğrudan WhatsApp/Instagram gibi
            # uygulamalara "resim" olarak gönderir — link değil, dosyanın
            # kendisi. Masaüstü tarayıcılarda genelde desteklenmez, bu durumda
            # aşağıdaki "İndir" butonuyla elle paylaşmak gerekir.
            image_b64 = base64.b64encode(share_image).decode("utf-8")
            share_caption_js = json.dumps(share_caption)
            st.iframe(
                f"""
                <div style="font-family: -apple-system, sans-serif;">
                <button id="native-share-btn" style="
                    width: 100%; padding: 10px; border-radius: 8px;
                    background: #e50914; color: white; border: none;
                    font-size: 14px; font-weight: 600; cursor: pointer;
                ">📱 Görseli Doğrudan Paylaş (WhatsApp/Instagram vb.)</button>
                <p id="native-share-fallback" style="display:none; color:#999; font-size:12px; margin-top:8px;">
                    Bu tarayıcı doğrudan resim paylaşımını desteklemiyor — lütfen aşağıdaki "İndir" butonunu kullan.
                </p>
                <script>
                document.getElementById('native-share-btn').addEventListener('click', async () => {{
                    try {{
                        const byteCharacters = atob("{image_b64}");
                        const byteNumbers = new Array(byteCharacters.length);
                        for (let i = 0; i < byteCharacters.length; i++) {{
                            byteNumbers[i] = byteCharacters.charCodeAt(i);
                        }}
                        const byteArray = new Uint8Array(byteNumbers);
                        const file = new File([byteArray], "cineroulette.png", {{ type: "image/png" }});

                        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                            await navigator.share({{ files: [file], text: {share_caption_js} }});
                        }} else {{
                            document.getElementById('native-share-fallback').style.display = 'block';
                        }}
                    }} catch (e) {{
                        document.getElementById('native-share-fallback').style.display = 'block';
                    }}
                }});
                </script>
                </div>
                """,
                height=70,
            )

            safe_title = "".join(c for c in winner.get("title", "film") if c.isalnum() or c in " _-").strip() or "film"
            st.download_button(
                "📥 Görseli İndir",
                data=share_image,
                file_name=f"{safe_title}_cineroulette.png",
                mime="image/png",
                key="download_share_card",
                width="stretch",
            )
        else:
            st.caption("Paylaşım görseli oluşturulamadı.")

    is_fav = fav_manager.is_favorite(winner.get("id"))
    btn_text = "❤️ Zaten Favorilerde" if is_fav else "❤️ Favorilere Ekle"
    if st.button(btn_text, key="dialog_wheel_result_fav", width="stretch"):
        if not is_fav:
            fav_manager.add(winner)
            st.toast(f"❤️ {winner.get('title')} favorilere eklendi!")
            st.rerun()

    winner_id = winner.get("id")
    if feedback_manager.is_watched(winner_id):
        st.success("Beğendin", icon="✅")
    elif feedback_manager.is_disliked(winner_id):
        st.error("Beğenmedin", icon="🚫")
    else:
        fb_col1, fb_col2 = st.columns(2)
        with fb_col1:
            if st.button("✅ Beğendim", key="dialog_watched", width="stretch"):
                feedback_manager.mark_watched(winner)
                st.toast(f"✅ '{winner.get('title')}' beğendiğin olarak kaydedildi.")
                st.rerun()
        with fb_col2:
            if st.button("🚫 Beğenmedim", key="dialog_disliked", width="stretch"):
                feedback_manager.mark_disliked(winner)
                if is_fav:
                    fav_manager.remove(winner_id)
                st.toast(f"🚫 '{winner.get('title')}' bir daha önerilmeyecek.")
                st.rerun()


def _render_card_deck(items: list[dict], fav_manager: FavoritesManager, feedback_manager: FeedbackManager, tmdb: TMDBClient) -> None:
    """
    Yüzü kapalı kart destesi — çarka alternatif bir seçim ritüeli.
    Kullanıcı 8 karttan birini seçer, o kart anında açılıp (çarktaki gibi
    merkezi pop-up ile) sonucu gösterir. Çarkın aksine bekleme animasyonu
    olmadığı için sonuç gecikmesiz gösteriliyor.

    Kartlar, gerçek bir iskambil destesi gibi hafifçe yelpaze açılmış
    (döndürülmüş ve üst üste binmiş) şekilde gösteriliyor — bunu
    `st.container(key=...)` ile elde ediyoruz, çünkü Streamlit bu durumda
    otomatik olarak `st-key-<key>` CSS sınıfı üretiyor ve biz de bu sınıfı
    hedefleyerek SADECE bu deste bloğuna özel stil veriyoruz (sayfadaki
    diğer sütun/buton düzenlerini etkilemiyor).
    """
    st.session_state.setdefault("deck_seed", 0)

    deck_items = items[:8]

    st.markdown('<div class="section-title" style="text-align:center;">🃏 Kart Destesi</div>', unsafe_allow_html=True)
    st.caption("Bir kart seç, açılsın — hangi film çıkacağını önceden bilmiyorsun.")

    # Sadece bu deste bloğuna özel yelpaze (fan) stili.
    st.markdown(
        """
        <style>
        .st-key-card_deck_fan {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 0 !important;
            padding: 20px 0 28px;
        }
        .st-key-card_deck_fan > div {
            margin-left: -28px;
            transition: transform 0.15s ease, z-index 0s;
        }
        .st-key-card_deck_fan > div:first-child { margin-left: 0; }
        .st-key-card_deck_fan button {
            width: 80px !important;
            height: 118px !important;
            padding: 8px !important;
            border-radius: 10px 10px 12px 12px !important;
            border: 1.5px solid #4a4a4a !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            overflow: hidden;
            color: transparent !important;
            background-color: #141414 !important;
            background-image:
                repeating-linear-gradient(45deg, #2a2a2a 0, #2a2a2a 3px, transparent 3px, transparent 10px),
                repeating-linear-gradient(-45deg, #2a2a2a 0, #2a2a2a 3px, transparent 3px, transparent 10px),
                linear-gradient(160deg, #831010, #e50914 40%, #831010 70%) !important;
            background-size: 100% 100%, 100% 100%, 100% 100% !important;
            position: relative;
        }
        /* Dar (mobil) ekranlarda kartları küçültüp örtüşmeyi azaltıyoruz,
           böylece 8 kart yatayda taşmadan sığıyor. */
        @media (max-width: 480px) {
            .st-key-card_deck_fan button {
                width: 46px !important;
                height: 70px !important;
            }
            .st-key-card_deck_fan > div {
                margin-left: -16px;
            }
        }
        .st-key-card_deck_fan button::before {
            content: "";
            position: absolute;
            inset: 8px;
            border: 1.5px solid rgba(255,255,255,0.55);
            border-radius: 5px;
            pointer-events: none;
        }
        .st-key-card_deck_fan button:hover {
            border-color: #f5c518 !important;
            box-shadow: 0 8px 18px rgba(0,0,0,0.6);
        }

        /* KARIŞTIRMA ANİMASYONU: Deste her render edildiğinde (ilk açılışta
           ve "Yeni Deste Karıştır" ile) kartlar ortadan, küçük ve dönüşsüz
           bir halde belirip, birer birer (gecikmeli) kendi yelpaze
           konumlarına "dağıtılıyor" gibi yerleşiyor. */
        @keyframes dealCard1 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(-18deg) translateY(14px); } }
        @keyframes dealCard2 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(-13deg) translateY(7px); } }
        @keyframes dealCard3 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(-8deg) translateY(3px); } }
        @keyframes dealCard4 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(-3deg); } }
        @keyframes dealCard5 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(3deg); } }
        @keyframes dealCard6 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(8deg) translateY(3px); } }
        @keyframes dealCard7 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(13deg) translateY(7px); } }
        @keyframes dealCard8 { from { opacity:0; transform: scale(0.4) rotate(0deg) translateY(40px); } to { opacity:1; transform: rotate(18deg) translateY(14px); } }
        .st-key-card_deck_fan > div:nth-child(1) button { animation: dealCard1 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.00s; }
        .st-key-card_deck_fan > div:nth-child(2) button { animation: dealCard2 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.05s; }
        .st-key-card_deck_fan > div:nth-child(3) button { animation: dealCard3 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.10s; }
        .st-key-card_deck_fan > div:nth-child(4) button { animation: dealCard4 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.15s; }
        .st-key-card_deck_fan > div:nth-child(5) button { animation: dealCard5 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.20s; }
        .st-key-card_deck_fan > div:nth-child(6) button { animation: dealCard6 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.25s; }
        .st-key-card_deck_fan > div:nth-child(7) button { animation: dealCard7 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.30s; }
        .st-key-card_deck_fan > div:nth-child(8) button { animation: dealCard8 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; animation-delay: 0.35s; }

        .st-key-card_deck_fan > div:hover button {
            transform: translateY(-18px) scale(1.08) !important;
            z-index: 20;
            position: relative;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    clicked_item = None
    with st.container(key="card_deck_fan", horizontal=True):
        for i, item in enumerate(deck_items):
            key = f"deck_card_{st.session_state['deck_seed']}_{i}"
            if st.button("🂠", key=key, help=f"{i + 1}. kart"):
                clicked_item = item

    col_a, col_b, col_c = st.columns([1, 1.4, 1])
    with col_b:
        st.caption(f"🂡 Deste #{st.session_state['deck_seed'] + 1}")
        if st.button("🔄 Yeni Deste Karıştır", key="deck_reshuffle_btn", width="stretch"):
            st.session_state["deck_seed"] += 1
            st.toast("🔀 Deste karıştırıldı!")
            st.rerun()

    if clicked_item is not None:
        _show_winner_dialog(clicked_item, fav_manager, feedback_manager, tmdb, mode="cards")


def render_home_tab(tmdb: TMDBClient, fav_manager: FavoritesManager, feedback_manager: FeedbackManager) -> None:
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
            st.caption(f"❤️ {fav_count} favorin arasından seçim yapılacak.")
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

    if filter_mode in ("mood", "genre") and not selected_moods and not selected_genres:
        st.info("👈 Devam etmeden önce soldan bir **ruh hali** ya da **tür** seç.")
        return

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

    # "İzledim" veya "Bu değildi" olarak işaretlenmiş içerikler, hangi
    # modda olursak olalım havuzdan çıkarılıyor — bir daha karşımıza çıkmasınlar.
    pool_before_feedback = len(pool)
    pool = feedback_manager.filter_pool(pool)
    excluded_count = pool_before_feedback - len(pool)

    if filter_mode == "favorites":
        if not pool:
            if pool_before_feedback > 0:
                st.info("📭 Favorilerindeki her şeyi beğenmemiş görünüyorsun. Yeni favoriler ekle!")
            else:
                st.info(
                    "📭 Henüz favori eklememişsin.\n\n"
                    "Bir mod veya tür seçip beğendiğin içerikleri **'Favorilere Ekle'** "
                    "ile listene ekleyebilir, sonra buradan çevirebilirsin."
                )
            return
        st.caption(f"❤️ Favorilerinden seçim yapılıyor ({total_results} favori).")
    elif random_mode:
        st.caption(f"🎲 Rastgele mod: ruh hali/tür seçimlerin yok sayılıyor, kaliteli içerik havuzundan rastgele seçiliyor ({total_results} sonuç).")
    else:
        chosen = [MOOD_FILTERS[k].label for k in selected_moods] + [GENRE_FILTERS[k].label for k in selected_genres]
        st.caption(f"🎯 Uygulanan filtreler: {', '.join(chosen)} — toplam {total_results:,} sonuç".replace(",", "."))
        if mood_keyword_ids:
            st.caption("🔍 Tek ruh hali seçili olduğu için tür eşleşmesinin ötesinde, o temaya uygun anahtar kelimeyle de daraltıldı (ör. gerçekten 'hüzünlü' etiketli filmler).")

    if excluded_count > 0:
        st.caption(f"🚫 {excluded_count} içerik beğenmediğin için gizlendi.")

    wheel_items = random.sample(pool, min(20, len(pool))) if pool else []

    st.session_state.setdefault("spin_seed", 0)
    st.session_state.setdefault("wheel_winner", None)

    if len(wheel_items) < 2:
        st.warning("🔍 Seçim için yeterli sonuç yok. Filtreleri biraz gevşetmeyi dene.")
        return

    wcol1, wcol2, wcol3 = st.columns([1, 2, 1])
    with wcol2:
        selection_mode = st.radio(
            "Nasıl seçelim?",
            options=["wheel", "cards"],
            format_func=lambda k: "🎡 Çark" if k == "wheel" else "🃏 Kart Çek",
            horizontal=True,
            key="selection_mode",
        )
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

        if selection_mode == "cards":
            _render_card_deck(wheel_items, fav_manager, feedback_manager, tmdb)
        else:
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
                _show_winner_dialog(winner, fav_manager, feedback_manager, tmdb, mode="wheel")

    _render_full_results_section(
        tmdb, fav_manager, feedback_manager, pool, total_results, filters_signature,
        mood_genre_ids, genre_genre_ids, mood_keyword_ids,
        rating_range, year_range, runtime_range,
        content_type, default_sort_label,
    )


@st.fragment
def _render_full_results_section(
    tmdb: TMDBClient,
    fav_manager: FavoritesManager,
    feedback_manager: FeedbackManager,
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

        # `pool` artık fetch_filtered_pool içinde çeşitliliği artırmak için
        # zaten en fazla 3 sayfaya (60 sonuca) kadar önden getiriliyor, bu
        # yüzden burada ayrıca bir sayfa daha çekmeye gerek yok — bu sadece
        # aynı sayfayı tekrar isteyip israf ederdi. "Daha fazla göster"
        # butonu, zaten kapsanan sayfalardan hemen sonrasından devam etsin
        # diye kabaca kaç sayfanın karşılandığını tahmin ediyoruz.
        st.session_state["list_pool_page"] = max(1, -(-len(pool) // 20))  # yukarı yuvarlama

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

        display_content_grid(sorted_pool, fav_manager, feedback_manager, show_similarity=False, key_prefix="home")

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
                <p>Ne izleyeceğine karar veremedin mi? Çarkı çevir ya da bir kart çek.</p>
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
    session_id = get_or_create_session_id()
    fav_manager = init_favorites_manager(session_id)
    feedback_manager = init_feedback_manager(session_id)

    tab_home, tab_ai, tab_favorites, tab_feedback = st.tabs(
        ["🎰 Anasayfa", "🤖 AI Önerileri", "❤️ Favorilerim", "👍👎 Geri Bildirimlerim"]
    )

    with tab_home:
        render_home_tab(tmdb, fav_manager, feedback_manager)

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
                    recs = fetch_ai_recommendations(
                        tmdb=tmdb,
                        ml_engine=ml_engine,
                        favorites=favorites,
                        content_type=ai_content_type,
                    )
                    st.session_state.ai_recommendations = feedback_manager.filter_pool(recs)
                    st.session_state.ai_recommendations_key = cache_key

            if st.session_state.ai_recommendations_key != cache_key:
                st.info("Favorilerin veya seçtiğin içerik türü değişti. Güncel öneriler için yukarıdaki butona bas.")
            elif st.session_state.ai_recommendations is not None:
                display_content_grid(st.session_state.ai_recommendations, fav_manager, feedback_manager, show_similarity=True, key_prefix="ai")

    with tab_favorites:
        display_favorites_page(tmdb, fav_manager, feedback_manager)

    with tab_feedback:
        display_feedback_page(fav_manager, feedback_manager)


if __name__ == "__main__":
    main()
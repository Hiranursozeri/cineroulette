import streamlit as st
from typing import Optional
from utils.tmdb_client import TMDBClient
from utils.favorites_manager import FavoritesManager

# movie_filters olduğundan emin oluyoruz:
from utils.movie_filters import (
    MOOD_FILTERS, GENRE_FILTERS, RANDOM_FILTER, 
    AI_RECOMMENDATION_FILTER, FilterConfig, 
    get_tv_genre_ids, get_all_modes
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

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        color: white;
        text-align: center;
    }
    
    .content-card {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        height: 100%;
    }
    
    .content-card:hover {
        transform: translateY(-5px);
    }
    
    .favorite-btn {
        font-size: 24px;
        cursor: pointer;
        transition: transform 0.2s ease;
    }
    
    .favorite-btn:hover {
        transform: scale(1.2);
    }
    
    .similarity-badge {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        color: white;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .mode-description {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
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
    except ValueError as e:
        return None


@st.cache_resource
def init_ml_engine() -> RecommendationEngine:
    """ML motorunu başlat."""
    return RecommendationEngine()


def init_favorites_manager() -> FavoritesManager:
    """Favori yöneticisini başlat (her oturumda yeni)."""
    return FavoritesManager()


# =============================================================================
# VERİ ÇEKME
# =============================================================================

def fetch_filtered_content(
    tmdb: TMDBClient,
    filter_config: FilterConfig,
    content_type: str,
    page: int = 1,
) -> list[dict]:
    """Filtre yapılandırmasına göre içerik getir."""
    try:
        if filter_config.is_random:
            return tmdb.get_random_content(
                content_type=content_type,
                min_vote_average=filter_config.min_vote_average or 7.0,
                min_vote_count=filter_config.min_vote_count or 1000,
                count=12,
            )
        
        genre_ids = filter_config.genre_ids
        if content_type == "tv" and genre_ids:
            genre_ids = get_tv_genre_ids(genre_ids)
        
        if content_type == "movie":
            return tmdb.discover_movies(
                genre_ids=genre_ids,
                min_vote_average=filter_config.min_vote_average,
                min_vote_count=filter_config.min_vote_count,
                sort_by=filter_config.sort_by,
                page=page,
            )
        else:
            return tmdb.discover_tv_shows(
                genre_ids=genre_ids,
                min_vote_average=filter_config.min_vote_average,
                min_vote_count=filter_config.min_vote_count,
                sort_by=filter_config.sort_by,
                page=page,
            )
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
        # Geniş bir aday havuzu oluştur
        candidate_pool = []
        
        # Popüler içerikler
        if content_type == "movie":
            candidate_pool.extend(tmdb.get_popular_movies(page=1))
            candidate_pool.extend(tmdb.get_popular_movies(page=2))
            # Yüksek puanlı içerikler
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
        
        # Duplikatları kaldır
        seen_ids = set()
        unique_pool = []
        for item in candidate_pool:
            if item.get("id") not in seen_ids:
                seen_ids.add(item.get("id"))
                unique_pool.append(item)
        
        # ML motoru ile önerileri hesapla
        recommendations = ml_engine.get_recommendations(
            favorites=favorites,
            candidate_pool=unique_pool,
            top_n=12,
        )
        
        return recommendations
    
    except Exception as e:
        st.error(f"AI önerileri hesaplanırken hata: {e}")
        return []


# =============================================================================
# GÖRÜNTÜLEME
# =============================================================================

def display_content_card(
    content: dict,
    fav_manager: FavoritesManager,
    show_similarity: bool = False,
    col=None,
) -> None:
    """Tek bir içerik kartı göster."""
    container = col if col else st
    
    with container:
        # Poster
        poster_url = content.get("poster_url", TMDBClient.PLACEHOLDER_POSTER)
        st.image(poster_url, use_container_width=True)
        
        # Başlık
        title = content.get("title", "Bilinmiyor")
        st.markdown(f"**{title}**")
        
        # Meta bilgiler
        vote_avg = content.get("vote_average", 0)
        release_date = content.get("release_date", "")
        year = release_date[:4] if release_date else "—"
        
        # Puan emoji
        if vote_avg >= 8.0:
            rating_display = f"🌟 {vote_avg:.1f}"
        elif vote_avg >= 7.0:
            rating_display = f"⭐ {vote_avg:.1f}"
        else:
            rating_display = f"✨ {vote_avg:.1f}"
        
        st.caption(f"{rating_display} | 📅 {year}")
        
        # Benzerlik skoru (AI önerileri için)
        if show_similarity and "similarity_score" in content:
            score = content["similarity_score"]
            st.caption(f"🎯 Benzerlik: %{score*100:.0f}")
        
        # Favori butonu
        content_id = content.get("id")
        is_fav = fav_manager.is_favorite(content_id)
        
        btn_label = "❤️ Favorilerde" if is_fav else "🤍 Favorilere Ekle"
        btn_key = f"fav_{content_id}_{content.get('title', '')[:10]}"
        
        if st.button(btn_label, key=btn_key, use_container_width=True):
            is_now_fav, message = fav_manager.toggle(content)
            st.toast(f"{'❤️' if is_now_fav else '💔'} {message}: {title}")
            st.rerun()


def display_content_grid(
    items: list[dict],
    fav_manager: FavoritesManager,
    show_similarity: bool = False,
) -> None:
    """İçerik grid'i göster."""
    if not items:
        st.warning("🔍 Bu kriterlere uygun içerik bulunamadı.")
        return
    
    cols = st.columns(3)
    
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            display_content_card(
                content=item,
                fav_manager=fav_manager,
                show_similarity=show_similarity,
            )
            st.divider()


def display_wheel_section(
    items: list[dict],
    fav_manager: FavoritesManager,
) -> None:
    """Çark bölümünü göster."""
    if not items:
        st.warning("Çark için yeterli içerik bulunamadı.")
        return
    
    st.subheader("🎰 Film Çarkı")
    st.info("👆 Çarka tıklayarak şansını dene! Çark durduğunda çıkan filmi favorilerine ekleyebilirsin.")
    
    # Çarkı render et
    wheel_items = items[:8]  # Maksimum 8 dilim
    render_roulette_wheel(wheel_items, height=700)
    
    # Çark sonucu için session state kontrolü
    if "wheel_result" in st.session_state and st.session_state.wheel_result:
        result = st.session_state.wheel_result
        
        st.divider()
        st.subheader("🎉 Çarktan Çıkan Film")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(result.get("poster_url", ""), width=200)
        
        with col2:
            st.markdown(f"### {result.get('title', 'Bilinmiyor')}")
            st.markdown(f"⭐ **Puan:** {result.get('vote_average', 0):.1f}")
            st.markdown(f"📝 **Özet:** {result.get('overview', 'Açıklama yok.')[:300]}...")
            
            # Favori butonu
            is_fav = fav_manager.is_favorite(result.get("id"))
            btn_text = "❤️ Zaten Favorilerde" if is_fav else "❤️ Favorilere Ekle"
            
            if st.button(btn_text, key="wheel_result_fav"):
                if not is_fav:
                    fav_manager.add(result)
                    st.toast(f"❤️ {result.get('title')} favorilere eklendi!")
                    st.rerun()


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
    
    # İstatistikler
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
    
    # Temizle butonu
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Tümünü Temizle", type="secondary"):
            fav_manager.clear_all()
            st.toast("Tüm favoriler temizlendi!")
            st.rerun()
    
    # Favorileri göster
    cols = st.columns(3)
    
    for idx, fav in enumerate(favorites):
        with cols[idx % 3]:
            # Poster
            poster_url = fav.get("poster_url") or fav.get("poster_path")
            if poster_url and not poster_url.startswith("http"):
                poster_url = f"[image.tmdb.org](https://image.tmdb.org/t/p/w342{poster_url})"
            
            if poster_url:
                st.image(poster_url, use_container_width=True)
            
            # Bilgiler
            st.markdown(f"**{fav.get('title', 'Bilinmiyor')}**")
            
            vote_avg = fav.get("vote_average", 0)
            content_type = "🎬 Film" if fav.get("content_type") == "movie" else "📺 Dizi"
            st.caption(f"⭐ {vote_avg:.1f} | {content_type}")
            
            # Kaldır butonu
            if st.button("💔 Kaldır", key=f"remove_{fav.get('id')}"):
                fav_manager.remove(fav.get("id"))
                st.toast(f"💔 {fav.get('title')} favorilerden kaldırıldı!")
                st.rerun()
            
            st.divider()


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar(fav_manager: FavoritesManager) -> tuple[str, str, str, bool]:
    """
    Sidebar'ı render et.
    
    Returns:
        (mod, alt_seçim, içerik_türü, çark_modu) tuple'ı
    """
    with st.sidebar:
        # Logo
        st.markdown(
            """
            <div style="text-align: center; padding: 10px;">
                <span style="font-size: 48px;">🎰</span>
                <h2 style="margin: 0;">CineRoulette</h2>
                <p style="color: gray; font-size: 12px;">Ne izleyeceğine karar veremedin mi?</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.divider()
        
        # Mod seçimi
        st.subheader("🎯 Seçim Modu")
        
        modes = get_all_modes()
        mode = st.radio(
            label="Mod seç",
            options=list(modes.keys()),
            format_func=lambda x: modes[x],
            label_visibility="collapsed",
        )
        
        st.divider()
        
        # Alt seçim (moda göre değişir)
        sub_selection = None
        
        if mode == "mood":
            st.subheader("🎭 Ruh Halin Nasıl?")
            mood_options = list(MOOD_FILTERS.keys())
            sub_selection = st.radio(
                label="Mod seç",
                options=mood_options,
                format_func=lambda x: f"{MOOD_FILTERS[x].icon} {MOOD_FILTERS[x].label}",
                label_visibility="collapsed",
            )
        
        elif mode == "genre":
            st.subheader("🎬 Hangi Tür?")
            genre_options = list(GENRE_FILTERS.keys())
            sub_selection = st.radio(
                label="Tür seç",
                options=genre_options,
                format_func=lambda x: f"{GENRE_FILTERS[x].icon} {GENRE_FILTERS[x].label}",
                label_visibility="collapsed",
            )
        
        elif mode == "random":
            st.subheader("🎲 Hazır mısın?")
            st.write("Rastgele ama kaliteli içerikler!")
            sub_selection = "random"
        
        elif mode == "ai":
            st.subheader("🤖 AI Öneri Motoru")
            fav_count = fav_manager.get_count()
            if fav_count > 0:
                st.success(f"✅ {fav_count} favori analiz edilecek")
            else:
                st.warning("⚠️ Önce favorilere film ekle!")
            sub_selection = "ai"
        
        elif mode == "favorites":
            st.subheader("❤️ Favorilerin")
            fav_count = fav_manager.get_count()
            st.info(f"📊 {fav_count} içerik favorilerinde")
            sub_selection = "favorites"
        
        st.divider()
        
        # İçerik türü (favorites hariç)
        content_type = "movie"
        if mode != "favorites":
            st.subheader("📺 İçerik Türü")
            content_type = st.selectbox(
                label="Tür",
                options=["movie", "tv"],
                format_func=lambda x: "🎥 Film" if x == "movie" else "📺 Dizi",
                label_visibility="collapsed",
            )
        
        st.divider()
        
        # Çark modu toggle
        use_wheel = False
        if mode in ["mood", "genre", "random"]:
            st.subheader("🎰 Görünüm")
            view_mode = st.radio(
                label="Görünüm seç",
                options=["grid", "wheel"],
                format_func=lambda x: "📋 Liste" if x == "grid" else "🎡 Çark",
                label_visibility="collapsed",
                horizontal=True,
            )
            use_wheel = view_mode == "wheel"
        
        st.divider()
        
        # Footer
        st.caption("TMDB API ile desteklenmektedir")
        st.image(
            "[themoviedb.org](https://www.themoviedb.org/assets/2/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg)",
            width=120,
        )
    
    return mode, sub_selection, content_type, use_wheel


# =============================================================================
# ANA İÇERİK
# =============================================================================

def render_main_content(
    tmdb: TMDBClient,
    ml_engine: RecommendationEngine,
    fav_manager: FavoritesManager,
    mode: str,
    sub_selection: str,
    content_type: str,
    use_wheel: bool,
) -> None:
    """Ana içeriği render et."""
    
    # Başlık
    st.markdown(
        """
        <div class="main-header">
            <h1>🎬 CineRoulette</h1>
            <p>Mükemmel filmi veya diziyi keşfet!</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Favoriler sayfası
    if mode == "favorites":
        display_favorites_page(fav_manager)
        return
    
    # Filtre belirleme
    filter_config = None
    section_title = ""
    show_similarity = False
    
    if mode == "mood":
        filter_config = MOOD_FILTERS.get(sub_selection)
        section_title = f"{filter_config.icon} {filter_config.label}" if filter_config else ""
    
    elif mode == "genre":
        filter_config = GENRE_FILTERS.get(sub_selection)
        section_title = f"{filter_config.icon} {filter_config.label}" if filter_config else ""
    
    elif mode == "random":
        filter_config = RANDOM_FILTER
        section_title = "🎲 Rastgele Seçimler"
    
    elif mode == "ai":
        filter_config = AI_RECOMMENDATION_FILTER
        section_title = "🤖 Senin İçin Öneriler"
        show_similarity = True
    
    # Mod açıklaması
    if filter_config:
        st.markdown(
            f"""
            <div class="mode-description">
                <h3>{filter_config.icon} {filter_config.label}</h3>
                <p>{filter_config.description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    # İçerik yükleme
    content_label = "Film" if content_type == "movie" else "Dizi"
    
    # Yenile butonu
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"{section_title} ({content_label})")
    with col2:
        refresh = st.button("🔄 Yenile", use_container_width=True)
    
    # Sayfa yönetimi
    page_key = f"page_{mode}_{sub_selection}_{content_type}"
    if page_key not in st.session_state or refresh:
        st.session_state[page_key] = 1
    
    # İçerik çekme
    items = []
    
    with st.spinner("İçerikler yükleniyor..."):
        try:
            if mode == "ai":
                favorites = fav_manager.get_for_ml()
                if favorites:
                    items = fetch_ai_recommendations(
                        tmdb=tmdb,
                        ml_engine=ml_engine,
                        favorites=favorites,
                        content_type=content_type,
                    )
                else:
                    st.warning(
                        "🤖 AI önerileri için önce favorilerine birkaç film/dizi eklemelisin!\n\n"
                        "**Nasıl yapılır:**\n"
                        "1. Soldaki menüden farklı bir mod seç\n"
                        "2. Beğendiğin filmlere 'Favorilere Ekle' butonuna tıkla\n"
                        "3. Bu sayfaya geri dön"
                    )
                    return
            
            elif filter_config:
                items = fetch_filtered_content(
                    tmdb=tmdb,
                    filter_config=filter_config,
                    content_type=content_type,
                    page=st.session_state[page_key],
                )
        
        except Exception as e:
            st.error(f"İçerik yüklenirken bir hata oluştu: {e}")
            return
    
    # İçerik gösterimi
    if items:
        if use_wheel:
            display_wheel_section(items, fav_manager)
        else:
            display_content_grid(items, fav_manager, show_similarity)
            
            # Sayfa navigasyonu
            if mode != "ai":  # AI önerileri için sayfalama yok
                st.divider()
                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                
                with nav_col1:
                    if st.session_state[page_key] > 1:
                        if st.button("⬅️ Önceki", use_container_width=True):
                            st.session_state[page_key] -= 1
                            st.rerun()
                
                with nav_col2:
                    st.markdown(
                        f"<p style='text-align: center;'>Sayfa {st.session_state[page_key]}</p>",
                        unsafe_allow_html=True,
                    )
                
                with nav_col3:
                    if st.button("Sonraki ➡️", use_container_width=True):
                        st.session_state[page_key] += 1
                        st.rerun()
    else:
        if mode != "ai":
            st.error(
                "😕 İçerik yüklenemedi.\n\n"
                "**Olası nedenler:**\n"
                "- TMDB API anahtarı geçersiz olabilir\n"
                "- İnternet bağlantısı sorunu olabilir\n"
                "- Seçilen filtrelerle eşleşen içerik bulunamadı"
            )


# =============================================================================
# ANA UYGULAMA
# =============================================================================

def main():
    """Ana uygulama fonksiyonu."""
    
    # Servisleri başlat
    tmdb = init_tmdb_client()
    
    if not tmdb:
        st.title("🎬 CineRoulette")
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
    
    # Sidebar
    mode, sub_selection, content_type, use_wheel = render_sidebar(fav_manager)
    
    # Ana içerik
    render_main_content(
        tmdb=tmdb,
        ml_engine=ml_engine,
        fav_manager=fav_manager,
        mode=mode,
        sub_selection=sub_selection,
        content_type=content_type,
        use_wheel=use_wheel,
    )


if __name__ == "__main__":
    main()

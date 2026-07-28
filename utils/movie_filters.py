# utils/movie_filters.py
"""
Mod ve tür filtrelerini FilterConfig nesneleri olarak tanımlar.
app.py bu modülden MOOD_FILTERS, GENRE_FILTERS, RANDOM_FILTER,
AI_RECOMMENDATION_FILTER, FilterConfig, get_tv_genre_ids, get_all_modes
isimlerini import eder.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FilterConfig:
    """Bir filtre modunun tüm görsel + sorgu bilgilerini tutar."""
    icon: str
    label: str
    description: str
    genre_ids: Optional[list[int]] = field(default_factory=list)
    keyword_ids: Optional[list[int]] = field(default_factory=list)
    min_vote_average: Optional[float] = None
    min_vote_count: Optional[int] = None
    sort_by: str = "popularity.desc"
    is_random: bool = False


# =============================================================================
# RUH HALİ (MOOD) FİLTRELERİ
# =============================================================================
MOOD_FILTERS: dict[str, FilterConfig] = {
    "aglamalik": FilterConfig(
        icon="😢",
        label="Ağlamalık",
        description="Duygusal, hüzünlü filmler için hazır ol.",
        genre_ids=[18],  # Drama
        keyword_ids=[156924],  # tearjerker (TMDB'de doğrulanmış keyword ID)
        min_vote_average=7.0,
        min_vote_count=500,
    ),
    "kafa_dagitmalik": FilterConfig(
        icon="😄",
        label="Kafa Dağıtmalık",
        description="Eğlenceli ve hafif içerikler.",
        genre_ids=[35],  # Komedi
        keyword_ids=[304995],  # feel-good (TMDB'de doğrulanmış keyword ID)
        min_vote_average=6.0,
        min_vote_count=300,
    ),
    "heyecan_lazim": FilterConfig(
        icon="🔥",
        label="Heyecan Lazım",
        description="Aksiyon ve macera dolu bir macera.",
        genre_ids=[28, 12],  # Aksiyon, Macera
        # NOT: Bu ruh hali için güvenilir/geniş bir TMDB keyword'ü
        # doğrulayamadım (uydurmaktansa boş bırakmayı tercih ettim).
        # Sadece tür bazlı filtreleme uygulanıyor.
        min_vote_average=6.5,
        min_vote_count=500,
    ),
    "korku_gecesi": FilterConfig(
        icon="👻",
        label="Korku Gecesi",
        description="Işıkları kapat ve arkana bakma!",
        genre_ids=[27],  # Korku
        keyword_ids=[6152],  # supernatural (TMDB'de doğrulanmış keyword ID)
        min_vote_average=5.5,
        min_vote_count=200,
    ),
    "dusundurucu": FilterConfig(
        icon="🧠",
        label="Düşündürücü",
        description="Beyin yakan, derin hikayeler.",
        genre_ids=[18, 9648],  # Drama, Gizem
        keyword_ids=[12565],  # psychological thriller (TMDB'de doğrulanmış keyword ID)
        min_vote_average=7.0,
        min_vote_count=300,
    ),
}


# =============================================================================
# TÜR (GENRE) FİLTRELERİ
# =============================================================================
GENRE_FILTERS: dict[str, FilterConfig] = {
    "aksiyon": FilterConfig(
        icon="💥", label="Aksiyon", description="Nefes kesen aksiyon sahneleri.",
        genre_ids=[28], min_vote_count=300,
    ),
    "macera": FilterConfig(
        icon="🗺️", label="Macera", description="Keşif ve macera dolu hikayeler.",
        genre_ids=[12], min_vote_count=300,
    ),
    "animasyon": FilterConfig(
        icon="🎨", label="Animasyon", description="Her yaştan izleyici için animasyonlar.",
        genre_ids=[16], min_vote_count=200,
    ),
    "komedi": FilterConfig(
        icon="😂", label="Komedi", description="Kahkaha garantili yapımlar.",
        genre_ids=[35], min_vote_count=300,
    ),
    "korku": FilterConfig(
        icon="🎃", label="Korku", description="Ürkütücü ve gerilim dolu yapımlar.",
        genre_ids=[27], min_vote_count=200,
    ),
    "bilim_kurgu": FilterConfig(
        icon="🚀", label="Bilim Kurgu", description="Geleceğe ve uzaya yolculuk.",
        genre_ids=[878], min_vote_count=200,
    ),
}


# =============================================================================
# RASTGELE VE AI FİLTRELERİ (tekil objeler)
# =============================================================================
RANDOM_FILTER = FilterConfig(
    icon="🎲",
    label="Bana Bırak!",
    description="Kaliteli ama tamamen rastgele bir seçim.",
    min_vote_average=7.0,
    min_vote_count=1000,
    is_random=True,
)

AI_RECOMMENDATION_FILTER = FilterConfig(
    icon="🤖",
    label="Senin Sevdiklerine Benzer",
    description="Favorilerine göre AI'nin sana özel önerileri.",
)


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

# TMDB'de film ve dizi tür ID'leri kısmen farklıdır.
_MOVIE_TO_TV_GENRE_MAP: dict[int, int] = {
    28: 10759,   # Aksiyon -> Action & Adventure
    12: 10759,   # Macera -> Action & Adventure
    16: 16,      # Animasyon -> Animation
    35: 35,      # Komedi -> Comedy
    27: 9648,    # Korku -> Mystery (TV'de doğrudan Korku türü yok)
    878: 10765,  # Bilim Kurgu -> Sci-Fi & Fantasy
    18: 18,      # Drama -> Drama
    9648: 9648,  # Gizem -> Mystery
}


def get_tv_genre_ids(genre_ids: Optional[list[int]]) -> list[int]:
    """Film tür ID'lerini TMDB'nin dizi tür ID'lerine çevirir."""
    if not genre_ids:
        return []
    mapped = {_MOVIE_TO_TV_GENRE_MAP.get(gid, gid) for gid in genre_ids}
    return list(mapped)


def get_all_modes() -> dict[str, str]:
    """Sidebar'daki ana mod seçimi için {mode_key: label} döndürür."""
    return {
        "mood": "🎭 Ruh Haline Göre",
        "genre": "🎬 Türe Göre",
        "random": "🎲 Rastgele",
        "ai": "🤖 AI Önerileri",
        "favorites": "❤️ Favorilerim",
    }
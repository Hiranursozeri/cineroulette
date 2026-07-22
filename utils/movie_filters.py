# utils/filters.py

# Mod Filtreleri
MOOD_FILTERS = {
    "Ağlamalık": "Duygusal, hüzünlü filmler için hazır ol.",
    "Kafa Dağıtmalık": "Eğlenceli ve hafif içerikler.",
    "Heyecan Lazım": "Aksiyon ve macera dolu bir macera.",
    "Korku Gecesi": "Işıkları kapat ve arkana bakma!",
    "Düşündürücü": "Beyin yakan, derin hikayeler."
}

# Tür Filtreleri
GENRE_FILTERS = {
    "Aksiyon": 28,
    "Macera": 12,
    "Animasyon": 16,
    "Komedi": 35,
    "Korku": 27,
    "Bilim Kurgu": 878
}

# Diğer Sabitler
RANDOM_FILTER = "Bana Bırak!"
AI_RECOMMENDATION_FILTER = "Senin Sevdiklerine Benzer"

class FilterConfig:
    def __init__(self, mode_name, description):
        self.name = mode_name
        self.description = description

def get_all_modes():
    return list(MOOD_FILTERS.keys())

def get_tv_genre_ids():
    return GENRE_FILTERS
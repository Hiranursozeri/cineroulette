"""
ML Öneri Motoru
---------------
TF-IDF ve Kosinüs Benzerliği ile içerik tabanlı öneriler.
"""

import numpy as np
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.movie_filters import MOOD_FILTERS, GENRE_FILTERS


class RecommendationEngine:
    """
    İçerik tabanlı öneri motoru.
    
    Kullanıcının favori içeriklerinin overview ve tür bilgilerini
    analiz ederek benzer içerikler önerir.
    """
    
    def __init__(self):
        """TF-IDF vektörleştiriciyi başlat."""
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words=None,  # Türkçe için özel stop words eklenebilir
            ngram_range=(1, 2),  # Unigram ve bigram
            min_df=1,
            max_df=0.95,
        )
        
        # Türkçe stop words (basit liste)
        self.turkish_stop_words = {
            "bir", "bu", "ve", "ile", "için", "de", "da", "den", "dan",
            "mi", "mı", "mu", "mü", "ne", "ama", "ancak", "çok", "daha",
            "en", "gibi", "her", "hiç", "kadar", "ki", "o", "olan", "onu",
            "onun", "sonra", "şey", "ya", "zaman",
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Metni ön işle."""
        if not text:
            return ""
        
        # Küçük harfe çevir
        text = text.lower()
        
        # Stop words'leri kaldır
        words = text.split()
        words = [w for w in words if w not in self.turkish_stop_words]
        
        return " ".join(words)
    
    def _create_content_string(self, content: dict) -> str:
        """
        İçerikten analiz için metin oluştur.
        Overview + türler birleştirilir.
        """
        parts = []
        
        # Overview
        overview = content.get("overview", "")
        if overview:
            parts.append(self._preprocess_text(overview))
        
        # Türler (genre_ids varsa ID'leri metin olarak ekle)
        genre_ids = content.get("genre_ids", [])
        if genre_ids:
            # Tür eşleşmesi, düz konu/olay örgüsü metin örtüşmesinden çok
            # daha güvenilir bir "zevk" sinyali olduğu için ağırlığını
            # belirgin şekilde artırıyoruz.
            genre_str = " ".join([f"genre_{g}" for g in genre_ids] * 8)
            parts.append(genre_str)
        
        return " ".join(parts)
    
    def get_recommendations(
        self,
        favorites: list[dict],
        candidate_pool: list[dict],
        top_n: int = 9,
        collab_scores: dict = None,
    ) -> list[dict]:
        """
        Favorilere göre en benzer içerikleri bul.

        ÖNEMLİ TASARIM NOTU: Önceki sürüm tüm favorileri TEK bir
        "harmanlanmış" metin profiline karıştırıp adayları o profille
        karşılaştırıyordu. Kullanıcının favorileri çeşitliyse (ör. hem
        korku hem romantik komedi sevmesi), bu harmanlama sinyali
        sulandırıyor ve her adayın benzerlik skorunu yapay olarak
        düşürüyordu. Artık her aday, favorilerin HER BİRİYLE ayrı ayrı
        karşılaştırılıyor ve en yüksek (en iyi eşleşen) skor alınıyor —
        yani bir aday sadece TEK bir favoriye bile çok benziyorsa yüksek
        puan alabiliyor.

        YENİ: `collab_scores` — TMDB'nin kendi öneri motorundan gelen bir
        sinyal. Bir aday, kullanıcının favorilerinden kaçının TMDB
        önerilerinde ortak çıktıysa, o kadar güçlü bir "gerçek kullanıcı
        davranışı" desteği alır ve nihai skoru buna göre yukarı çekilir.
        Bu, TMDB'nin milyonlarca kullanıcısının izleme davranışından
        beslenen gerçek bir collaborative filtering sinyali — bizim kendi
        metin benzerliğimizden çok daha güvenilir.

        Args:
            favorites: Kullanıcının favori içerikleri
            candidate_pool: Öneri havuzu (filtrelenmiş içerikler)
            top_n: Döndürülecek öneri sayısı
            collab_scores: {content_id: kaç favoride ortak çıktığı} sözlüğü

        Returns:
            Benzerlik skoruna göre sıralanmış içerik listesi
        """
        if not favorites or not candidate_pool:
            return []

        collab_scores = collab_scores or {}

        # Favori ID'lerini al (önerilerde göstermemek için)
        favorite_ids = {fav.get("id") for fav in favorites}

        # Adayları favori olmayanlarla filtrele
        candidates = [
            c for c in candidate_pool
            if c.get("id") not in favorite_ids
        ]

        if not candidates:
            return []

        favorite_texts = [self._create_content_string(fav) for fav in favorites]
        valid_favorite_texts = [t for t in favorite_texts if t.strip()]

        candidate_texts = [self._create_content_string(c) for c in candidates]

        valid_candidates = []
        valid_texts = []
        for c, text in zip(candidates, candidate_texts):
            if text.strip():
                valid_candidates.append(c)
                valid_texts.append(text)

        if not valid_texts or not valid_favorite_texts:
            return candidates[:top_n]

        try:
            # TF-IDF vektörlerini favoriler + adaylar birlikte, tek bir
            # ortak kelime dağarcığı üzerinden oluşturuyoruz.
            all_texts = valid_favorite_texts + valid_texts
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)

            n_fav = len(valid_favorite_texts)
            favorite_vectors = tfidf_matrix[:n_fav]
            candidate_vectors = tfidf_matrix[n_fav:]

            # (n_candidates, n_favorites) matrisi: her adayın HER favoriye
            # göre benzerliği. Aday başına en yüksek olanı (max) alıyoruz.
            sim_matrix = cosine_similarity(candidate_vectors, favorite_vectors)
            raw_scores = sim_matrix.max(axis=1)

            for i, candidate in enumerate(valid_candidates):
                text_score = float(raw_scores[i])
                collab_count = collab_scores.get(candidate.get("id"), 0)
                # TMDB'nin collaborative sinyalini metin benzerliğine
                # ekliyoruz — her ortak öneri +0.15 katkı, en fazla 3
                # tanesiyle sınırlı (tek bir aşırı-popüler öğe her şeyi
                # ele geçirmesin diye).
                collab_boost = 0.15 * min(collab_count, 3)
                candidate["similarity_score"] = text_score + collab_boost
                candidate["_collab_count"] = collab_count

            valid_candidates.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            top_candidates = valid_candidates[:top_n]

            # GÖRÜNTÜLEME İÇİN ÖLÇEKLEME: Ham TF-IDF kosinüs benzerliği
            # doğası gereği küçük çıkar (metinler doğal dil olduğu için
            # kelime örtüşmesi sınırlı) — matematiksel olarak yanlış değil,
            # ama kullanıcıya "hiçbiri benzemiyor" hissi veriyor. Sıralama
            # zaten doğru olduğu için, bu grubun kendi iç aralığını
            # kullanıcıya daha anlamlı gelecek bir yüzde aralığına
            # (%35-%95) yeniden ölçekliyoruz. Bu sadece GÖSTERİM amaçlı;
            # hangi filmin daha iyi eşleştiği bilgisini değiştirmiyor.
            if top_candidates:
                scores = [c["similarity_score"] for c in top_candidates]
                lo, hi = min(scores), max(scores)
                if hi > lo:
                    for c in top_candidates:
                        c["similarity_score"] = 0.35 + 0.60 * (c["similarity_score"] - lo) / (hi - lo)
                else:
                    for c in top_candidates:
                        c["similarity_score"] = 0.6

            return top_candidates

        except Exception as e:
            print(f"[ML] Öneri hesaplama hatası: {e}")
            return candidates[:top_n]
    
    def get_similarity_explanation(self, score: float) -> str:
        """Benzerlik skoru için açıklama döndür."""
        if score >= 0.5:
            return "🎯 Çok yüksek benzerlik"
        elif score >= 0.3:
            return "✨ Yüksek benzerlik"
        elif score >= 0.15:
            return "👍 Orta benzerlik"
        elif score >= 0.05:
            return "🔍 Düşük benzerlik"
        else:
            return "🌟 Keşfet"
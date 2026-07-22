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
            # Her tür ID'sini 3 kez ekle (ağırlık artırmak için)
            genre_str = " ".join([f"genre_{g}" for g in genre_ids] * 3)
            parts.append(genre_str)
        
        return " ".join(parts)
    
    def get_recommendations(
        self,
        favorites: list[dict],
        candidate_pool: list[dict],
        top_n: int = 9,
    ) -> list[dict]:
        """
        Favorilere göre en benzer içerikleri bul.
        
        Args:
            favorites: Kullanıcının favori içerikleri
            candidate_pool: Öneri havuzu (filtrelenmiş içerikler)
            top_n: Döndürülecek öneri sayısı
        
        Returns:
            Benzerlik skoruna göre sıralanmış içerik listesi
        """
        if not favorites or not candidate_pool:
            return []
        
        # Favori ID'lerini al (önerilerde göstermemek için)
        favorite_ids = {fav.get("id") for fav in favorites}
        
        # Adayları favori olmayanlarla filtrele
        candidates = [
            c for c in candidate_pool 
            if c.get("id") not in favorite_ids
        ]
        
        if not candidates:
            return []
        
        # Favori metinlerini birleştir (tek profil vektörü)
        favorite_texts = [
            self._create_content_string(fav) 
            for fav in favorites
        ]
        combined_favorite_text = " ".join(favorite_texts)
        
        # Aday metinlerini oluştur
        candidate_texts = [
            self._create_content_string(c) 
            for c in candidates
        ]
        
        # Boş metinleri kontrol et
        if not combined_favorite_text.strip():
            return candidates[:top_n]
        
        valid_candidates = []
        valid_texts = []
        
        for c, text in zip(candidates, candidate_texts):
            if text.strip():
                valid_candidates.append(c)
                valid_texts.append(text)
        
        if not valid_texts:
            return candidates[:top_n]
        
        try:
            # TF-IDF vektörlerini oluştur
            all_texts = [combined_favorite_text] + valid_texts
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Favori profili ile adaylar arasındaki benzerliği hesapla
            favorite_vector = tfidf_matrix[0:1]
            candidate_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(favorite_vector, candidate_vectors)[0]
            
            # Benzerlik skorlarını adaylara ekle
            for i, candidate in enumerate(valid_candidates):
                candidate["similarity_score"] = float(similarities[i])
            
            # Skora göre sırala
            valid_candidates.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            
            return valid_candidates[:top_n]
        
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

"""
Favori Yönetimi
---------------
Kullanıcı favorilerini session state ve JSON ile yönetir.
"""

import json
import os
from datetime import datetime
from typing import Optional
import streamlit as st


class FavoritesManager:
    """Kullanıcı favorilerini yöneten sınıf."""
    
    FAVORITES_FILE = "user_favorites.json"
    SESSION_KEY = "favorites"
    
    def __init__(self):
        """Favorileri başlat."""
        self._init_session_state()
        self._load_from_file()
    
    def _init_session_state(self) -> None:
        """Session state'i başlat."""
        if self.SESSION_KEY not in st.session_state:
            st.session_state[self.SESSION_KEY] = []
    
    def _load_from_file(self) -> None:
        """Favorileri dosyadan yükle."""
        if os.path.exists(self.FAVORITES_FILE):
            try:
                with open(self.FAVORITES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Session state'i dosyadan güncelle (eğer boşsa)
                    if not st.session_state[self.SESSION_KEY]:
                        st.session_state[self.SESSION_KEY] = data
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Favorites] Dosya okuma hatası: {e}")
    
    def _save_to_file(self) -> None:
        """Favorileri dosyaya kaydet."""
        try:
            with open(self.FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state[self.SESSION_KEY], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[Favorites] Dosya yazma hatası: {e}")
    
    def add(self, content: dict) -> bool:
        """
        İçeriği favorilere ekle.
        
        Args:
            content: Film/dizi verisi
        
        Returns:
            Başarılı ise True
        """
        content_id = content.get("id")
        
        if content_id is None:
            return False
        
        # Zaten favorilerde mi?
        if self.is_favorite(content_id):
            return False
        
        # Favori kaydı oluştur
        favorite_entry = {
            "id": content_id,
            "title": content.get("title", content.get("name", "Bilinmiyor")),
            "poster_path": content.get("poster_path"),
            "poster_url": content.get("poster_url"),
            "overview": content.get("overview", ""),
            "vote_average": content.get("vote_average", 0),
            "release_date": content.get("release_date", content.get("first_air_date", "")),
            "genre_ids": content.get("genre_ids", []),
            "content_type": content.get("content_type", "movie"),
            "added_at": datetime.now().isoformat(),
        }
        
        st.session_state[self.SESSION_KEY].append(favorite_entry)
        self._save_to_file()
        return True
    
    def remove(self, content_id: int) -> bool:
        """
        İçeriği favorilerden kaldır.
        
        Args:
            content_id: İçerik ID'si
        
        Returns:
            Başarılı ise True
        """
        favorites = st.session_state[self.SESSION_KEY]
        
        for i, fav in enumerate(favorites):
            if fav.get("id") == content_id:
                favorites.pop(i)
                self._save_to_file()
                return True
        
        return False
    
    def toggle(self, content: dict) -> tuple[bool, str]:
        """
        Favori durumunu değiştir.
        
        Returns:
            (yeni_durum, mesaj) tuple'ı
        """
        content_id = content.get("id")
        
        if self.is_favorite(content_id):
            self.remove(content_id)
            return False, "Favorilerden kaldırıldı"
        else:
            self.add(content)
            return True, "Favorilere eklendi"
    
    def is_favorite(self, content_id: int) -> bool:
        """İçeriğin favorilerde olup olmadığını kontrol et."""
        return any(
            fav.get("id") == content_id 
            for fav in st.session_state[self.SESSION_KEY]
        )
    
    def get_all(self) -> list[dict]:
        """Tüm favorileri döndür."""
        return st.session_state[self.SESSION_KEY].copy()
    
    def get_count(self) -> int:
        """Favori sayısını döndür."""
        return len(st.session_state[self.SESSION_KEY])
    
    def clear_all(self) -> None:
        """Tüm favorileri temizle."""
        st.session_state[self.SESSION_KEY] = []
        self._save_to_file()
    
    def get_for_ml(self) -> list[dict]:
        """
        ML motoru için optimize edilmiş favori listesi döndür.
        Sadece gerekli alanları içerir.
        """
        return [
            {
                "id": fav.get("id"),
                "title": fav.get("title"),
                "overview": fav.get("overview", ""),
                "genre_ids": fav.get("genre_ids", []),
                "content_type": fav.get("content_type", "movie"),
            }
            for fav in self.get_all()
            if fav.get("overview")  # Overview olmayan içerikleri atla
        ]
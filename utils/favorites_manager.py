"""
Favori Yönetimi
---------------
Kullanıcı favorilerini yönetir. Kalıcı depolama olarak Supabase (Postgres)
kullanır — bu sayede Streamlit Community Cloud'un ücretsiz katmanında
uygulama uykuya dalıp yeniden başlasa bile veriler KAYBOLMAZ (yerel JSON
dosyaları sunucunun geçici diskinde tutulduğu için o diskle birlikte silinir,
Supabase ise ayrı, gerçekten kalıcı bir veritabanıdır).

Supabase bilgileri (SUPABASE_URL, SUPABASE_KEY) tanımlı değilse (ör. yerel
geliştirmede Supabase kurmak istemeyen biri için), otomatik olarak eski
oturum-bazlı JSON dosya sistemine düşer — böylece Supabase kurmadan da
uygulama çalışmaya devam eder.
"""

import json
import os
from datetime import datetime
from typing import Optional
import streamlit as st

_DATA_DIR = "data"


def _get_supabase_client():
    """
    Supabase istemcisini oluşturur. Bilgiler (Secrets veya .env) yoksa
    None döner — çağıran taraf bunu görüp dosya tabanlı yedek sisteme düşer.
    """
    try:
        from supabase import create_client
    except ImportError:
        return None

    url = None
    key = None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass
    url = url or os.getenv("SUPABASE_URL")
    key = key or os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        print(f"[Favorites] Supabase bağlantı hatası: {e}")
        return None


class FavoritesManager:
    """Kullanıcı favorilerini yöneten sınıf (Supabase öncelikli, dosya yedekli)."""

    SESSION_KEY = "favorites"

    def __init__(self, session_id: Optional[str] = None):
        self._session_id = session_id or "local"
        self._client = _get_supabase_client()

        if self._client is None:
            # Supabase yoksa eski oturum-bazlı JSON dosya sistemine düş.
            if session_id:
                os.makedirs(_DATA_DIR, exist_ok=True)
                self.FAVORITES_FILE = os.path.join(_DATA_DIR, f"favorites_{session_id}.json")
            else:
                self.FAVORITES_FILE = "user_favorites.json"
            self._init_session_state()
            self._load_from_file()
        else:
            self.FAVORITES_FILE = None  # Supabase kullanılıyor, dosyaya gerek yok

    # -------------------------------------------------------------------
    # Dosya tabanlı yedek sistem (Supabase yapılandırılmamışsa kullanılır)
    # -------------------------------------------------------------------

    def _init_session_state(self) -> None:
        if self.SESSION_KEY not in st.session_state:
            st.session_state[self.SESSION_KEY] = []

    def _load_from_file(self) -> None:
        if os.path.exists(self.FAVORITES_FILE):
            try:
                with open(self.FAVORITES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not st.session_state[self.SESSION_KEY]:
                        st.session_state[self.SESSION_KEY] = data
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Favorites] Dosya okuma hatası: {e}")

    def _save_to_file(self) -> None:
        try:
            with open(self.FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state[self.SESSION_KEY], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[Favorites] Dosya yazma hatası: {e}")

    # -------------------------------------------------------------------
    # Genel API (her iki depolama biçiminde de aynı şekilde çalışır)
    # -------------------------------------------------------------------

    def get_all(self) -> list[dict]:
        """Tüm favorileri döndür."""
        if self._client is not None:
            try:
                response = (
                    self._client.table("favorites")
                    .select("content")
                    .eq("session_id", self._session_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                return [row["content"] for row in response.data]
            except Exception as e:
                print(f"[Favorites] Supabase okuma hatası: {e}")
                return []
        return list(st.session_state[self.SESSION_KEY])

    def is_favorite(self, content_id: int) -> bool:
        """Bir içeriğin favori olup olmadığını kontrol et."""
        if content_id is None:
            return False
        if self._client is not None:
            try:
                response = (
                    self._client.table("favorites")
                    .select("content_id")
                    .eq("session_id", self._session_id)
                    .eq("content_id", content_id)
                    .execute()
                )
                return len(response.data) > 0
            except Exception as e:
                print(f"[Favorites] Supabase okuma hatası: {e}")
                return False
        return any(fav.get("id") == content_id for fav in st.session_state[self.SESSION_KEY])

    def add(self, content: dict) -> bool:
        """Favorilere ekle."""
        content_id = content.get("id")
        if content_id is None:
            return False

        if self._client is not None:
            try:
                self._client.table("favorites").upsert({
                    "session_id": self._session_id,
                    "content_id": content_id,
                    "content": content,
                }).execute()
                return True
            except Exception as e:
                print(f"[Favorites] Supabase yazma hatası: {e}")
                return False

        if self.is_favorite(content_id):
            return False
        st.session_state[self.SESSION_KEY].append(content)
        self._save_to_file()
        return True

    def remove(self, content_id: int) -> bool:
        """Favorilerden çıkar."""
        if content_id is None:
            return False

        if self._client is not None:
            try:
                self._client.table("favorites").delete().eq("session_id", self._session_id).eq("content_id", content_id).execute()
                return True
            except Exception as e:
                print(f"[Favorites] Supabase silme hatası: {e}")
                return False

        before = len(st.session_state[self.SESSION_KEY])
        st.session_state[self.SESSION_KEY] = [
            fav for fav in st.session_state[self.SESSION_KEY] if fav.get("id") != content_id
        ]
        removed = len(st.session_state[self.SESSION_KEY]) < before
        if removed:
            self._save_to_file()
        return removed

    def toggle(self, content: dict) -> tuple[bool, str]:
        """Favori durumunu değiştir (ekle/çıkar). (yeni_durum, mesaj) döner."""
        content_id = content.get("id")
        if self.is_favorite(content_id):
            self.remove(content_id)
            return False, "Favorilerden kaldırıldı"
        self.add(content)
        return True, "Favorilere eklendi"

    def get_count(self) -> int:
        return len(self.get_all())

    def clear_all(self) -> None:
        """Tüm favorileri temizle."""
        if self._client is not None:
            try:
                self._client.table("favorites").delete().eq("session_id", self._session_id).execute()
            except Exception as e:
                print(f"[Favorites] Supabase temizleme hatası: {e}")
            return
        st.session_state[self.SESSION_KEY] = []
        self._save_to_file()

    def get_for_ml(self) -> list[dict]:
        """AI öneri motoru için sadeleştirilmiş favori listesi."""
        return [
            {
                "id": f.get("id"),
                "title": f.get("title"),
                "overview": f.get("overview", ""),
                "genre_ids": f.get("genre_ids", []),
                "content_type": f.get("content_type", "movie"),
            }
            for f in self.get_all()
        ]
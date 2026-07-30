"""
Geri Bildirim Yönetimi (Beğendim / Beğenmedim)
-----------------------------------------------
Kullanıcının "beğendim" veya "beğenmedim" olarak işaretlediği içerikleri
yönetir. Sadece "beğenmedim" olanlar çarkta/kart destesinde/listede/AI
önerilerinde gizlenir.

ÖNEMLİ - PERFORMANS: Veriler `st.session_state`'te tutulur ve SADECE bu
tarayıcı oturumunda İLK kez ihtiyaç duyulduğunda Supabase'den okunur.
Sonraki tüm okumalar bellekten, ağa hiç gitmeden cevap verir. Sadece
gerçek bir değişiklik (işaretleme/geri alma) olduğunda Supabase'e yazılır.

Kalıcı depolama olarak Supabase (Postgres) kullanır; bilgiler tanımlı
değilse otomatik olarak eski oturum-bazlı JSON dosya sistemine düşer.
"""

import json
import os
from datetime import datetime
from typing import Optional
import streamlit as st

_DATA_DIR = "data"


@st.cache_resource(show_spinner=False)
def _create_cached_supabase_client(url: str, key: str):
    """Gerçek Supabase bağlantısını kurar; `@st.cache_resource` ile sadece bir kez çalışır."""
    from supabase import create_client
    return create_client(url, key)


def _get_supabase_client():
    """Supabase istemcisini oluşturur (önbellekli); bilgiler yoksa None döner."""
    try:
        import supabase  # noqa: F401
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
        return _create_cached_supabase_client(url, key)
    except Exception as e:
        print(f"[Feedback] Supabase bağlantı hatası: {e}")
        return None


class FeedbackManager:
    """Kullanıcının beğendim/beğenmedim geri bildirimlerini yöneten sınıf (oturum içi önbellekli)."""

    SESSION_KEY = "feedback"  # {"watched": [...], "disliked": [...]}
    LOADED_FLAG_KEY = "feedback_loaded_from_backend"

    def __init__(self, session_id: Optional[str] = None):
        self._session_id = session_id or "local"
        self._client = _get_supabase_client()

        if self._client is None:
            if session_id:
                os.makedirs(_DATA_DIR, exist_ok=True)
                self.FEEDBACK_FILE = os.path.join(_DATA_DIR, f"feedback_{session_id}.json")
            else:
                self.FEEDBACK_FILE = "user_feedback.json"
        else:
            self.FEEDBACK_FILE = None

        if self.SESSION_KEY not in st.session_state:
            st.session_state[self.SESSION_KEY] = {"watched": [], "disliked": []}
        if self.LOADED_FLAG_KEY not in st.session_state:
            st.session_state[self.LOADED_FLAG_KEY] = False

    # -------------------------------------------------------------------
    # İlk yükleme (bu tarayıcı oturumunda sadece bir kez çalışır)
    # -------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if st.session_state[self.LOADED_FLAG_KEY]:
            return

        if self._client is not None:
            try:
                response = (
                    self._client.table("feedback")
                    .select("content_id, status, content")
                    .eq("session_id", self._session_id)
                    .execute()
                )
                st.session_state[self.SESSION_KEY] = {
                    "watched": [row["content"] for row in response.data if row["status"] == "watched"],
                    "disliked": [row["content"] for row in response.data if row["status"] == "disliked"],
                }
            except Exception as e:
                print(f"[Feedback] Supabase okuma hatası: {e}")
        else:
            self._load_from_file()

        st.session_state[self.LOADED_FLAG_KEY] = True

    # -------------------------------------------------------------------
    # Dosya tabanlı yedek sistem (Supabase yapılandırılmamışsa kullanılır)
    # -------------------------------------------------------------------

    def _load_from_file(self) -> None:
        if os.path.exists(self.FEEDBACK_FILE):
            try:
                with open(self.FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    st.session_state[self.SESSION_KEY] = {
                        "watched": data.get("watched", []),
                        "disliked": data.get("disliked", []),
                    }
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Feedback] Dosya okuma hatası: {e}")

    def _save_to_file(self) -> None:
        try:
            with open(self.FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state[self.SESSION_KEY], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[Feedback] Dosya yazma hatası: {e}")

    def _make_entry(self, content: dict) -> dict:
        return {
            "id": content.get("id"),
            "title": content.get("title", content.get("name", "Bilinmiyor")),
            "content_type": content.get("content_type", "movie"),
            "marked_at": datetime.now().isoformat(),
        }

    def _remove_from_bucket(self, bucket: str, content_id: int) -> None:
        items = st.session_state[self.SESSION_KEY][bucket]
        st.session_state[self.SESSION_KEY][bucket] = [i for i in items if i.get("id") != content_id]

    # -------------------------------------------------------------------
    # Genel API — okumalar bellekten anında cevap verir, yazmalar hem
    # yerel listeyi hem (varsa) Supabase'i günceller.
    # -------------------------------------------------------------------

    def mark_watched(self, content: dict) -> bool:
        """İçeriği 'beğendim' olarak işaretle (varsa 'beğenmedim'den çıkarır)."""
        content_id = content.get("id")
        if content_id is None:
            return False
        self._ensure_loaded()

        self._remove_from_bucket("disliked", content_id)
        self._remove_from_bucket("watched", content_id)
        st.session_state[self.SESSION_KEY]["watched"].insert(0, self._make_entry(content))

        if self._client is not None:
            try:
                self._client.table("feedback").upsert({
                    "session_id": self._session_id,
                    "content_id": content_id,
                    "status": "watched",
                    "content": self._make_entry(content),
                }).execute()
            except Exception as e:
                print(f"[Feedback] Supabase yazma hatası: {e}")
        else:
            self._save_to_file()
        return True

    def mark_disliked(self, content: dict) -> bool:
        """İçeriği 'beğenmedim' olarak işaretle (varsa 'beğendim'den çıkarır)."""
        content_id = content.get("id")
        if content_id is None:
            return False
        self._ensure_loaded()

        self._remove_from_bucket("watched", content_id)
        self._remove_from_bucket("disliked", content_id)
        st.session_state[self.SESSION_KEY]["disliked"].insert(0, self._make_entry(content))

        if self._client is not None:
            try:
                self._client.table("feedback").upsert({
                    "session_id": self._session_id,
                    "content_id": content_id,
                    "status": "disliked",
                    "content": self._make_entry(content),
                }).execute()
            except Exception as e:
                print(f"[Feedback] Supabase yazma hatası: {e}")
        else:
            self._save_to_file()
        return True

    def unmark(self, content_id: int) -> None:
        """Bir içeriğin işaretini kaldır (geri al)."""
        self._ensure_loaded()
        self._remove_from_bucket("watched", content_id)
        self._remove_from_bucket("disliked", content_id)

        if self._client is not None:
            try:
                self._client.table("feedback").delete().eq("session_id", self._session_id).eq("content_id", content_id).execute()
            except Exception as e:
                print(f"[Feedback] Supabase silme hatası: {e}")
        else:
            self._save_to_file()

    def is_watched(self, content_id: int) -> bool:
        self._ensure_loaded()
        return any(i.get("id") == content_id for i in st.session_state[self.SESSION_KEY]["watched"])

    def is_disliked(self, content_id: int) -> bool:
        self._ensure_loaded()
        return any(i.get("id") == content_id for i in st.session_state[self.SESSION_KEY]["disliked"])

    def get_excluded_ids(self) -> set:
        """Sadece 'beğenmedim' olanlar çark/kart/liste/AI önerilerinden gizlenir."""
        self._ensure_loaded()
        return {i.get("id") for i in st.session_state[self.SESSION_KEY]["disliked"]}

    def get_watched_count(self) -> int:
        return len(self.get_watched_list())

    def get_disliked_count(self) -> int:
        return len(self.get_disliked_list())

    def get_watched_list(self) -> list[dict]:
        self._ensure_loaded()
        return list(st.session_state[self.SESSION_KEY]["watched"])

    def get_disliked_list(self) -> list[dict]:
        self._ensure_loaded()
        return list(st.session_state[self.SESSION_KEY]["disliked"])

    def filter_pool(self, items: list[dict]) -> list[dict]:
        """Bir içerik listesinden beğenilmeyenleri çıkarır."""
        excluded = self.get_excluded_ids()
        return [item for item in items if item.get("id") not in excluded]
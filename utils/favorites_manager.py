"""
Favori Yönetimi
---------------
Kullanıcı favorilerini yönetir. Kalıcı depolama olarak Supabase (Postgres)
kullanır — bu sayede Streamlit Community Cloud'un ücretsiz katmanında
uygulama uykuya dalıp yeniden başlasa bile veriler KAYBOLMAZ.

ÖNEMLİ - PERFORMANS: Supabase her çağrıda gerçek bir ağ isteği yapar.
Favori listesi `st.session_state`'te tutulur ve SADECE bu tarayıcı
oturumunda İLK kez ihtiyaç duyulduğunda Supabase'den okunur. Sonraki tüm
okumalar (is_favorite, get_all vb.) doğrudan bellekten, ağa hiç gitmeden
cevap verir. Sadece gerçek bir değişiklik (ekleme/çıkarma) olduğunda
Supabase'e yazılır — ve bu yazma, sonucu beklemeden yerel listeyi de
anında güncellediği için kullanıcı arayüzü gecikme hissetmez.

Supabase bilgileri (SUPABASE_URL, SUPABASE_KEY) tanımlı değilse, otomatik
olarak eski oturum-bazlı JSON dosya sistemine düşer.
"""

import json
import os
from typing import Optional
import streamlit as st

_DATA_DIR = "data"


@st.cache_resource(show_spinner=False)
def _create_cached_supabase_client(url: str, key: str):
    """
    Gerçek Supabase bağlantısını kurar. `@st.cache_resource` ile
    işaretlendiği için bu SADECE BİR KEZ (uygulama ömrü boyunca) çalışır.
    """
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
        print(f"[Favorites] Supabase bağlantı hatası: {e}")
        return None


class FavoritesManager:
    """Kullanıcı favorilerini yöneten sınıf (Supabase öncelikli, dosya yedekli, oturum içi önbellekli)."""

    SESSION_KEY = "favorites"
    LOADED_FLAG_KEY = "favorites_loaded_from_backend"

    def __init__(self, session_id: Optional[str] = None):
        self._session_id = session_id or "local"
        self._client = _get_supabase_client()

        if self._client is None:
            if session_id:
                os.makedirs(_DATA_DIR, exist_ok=True)
                self.FAVORITES_FILE = os.path.join(_DATA_DIR, f"favorites_{session_id}.json")
            else:
                self.FAVORITES_FILE = "user_favorites.json"
        else:
            self.FAVORITES_FILE = None

        if self.SESSION_KEY not in st.session_state:
            st.session_state[self.SESSION_KEY] = []
        if self.LOADED_FLAG_KEY not in st.session_state:
            st.session_state[self.LOADED_FLAG_KEY] = False

    # -------------------------------------------------------------------
    # İlk yükleme (bu tarayıcı oturumunda sadece bir kez çalışır)
    # -------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """
        Favori listesini, bu tarayıcı oturumunda henüz yüklenmediyse
        arka uçtan (Supabase ya da dosya) bir kez çeker. Zaten
        yüklenmişse hiçbir şey yapmaz — bu, her rerun'da tekrar tekrar
        ağa gitmeyi önleyen asıl mekanizma.

        ÖNEMLİ (düzeltilen hata): Önceki sürümde, Supabase okuması
        BAŞARISIZ olsa bile "yüklendi" olarak işaretleniyordu — yani
        geçici bir ağ hatası olduğunda kullanıcı o oturum boyunca hiç
        favori göremiyordu, bir dahaki girişte de aynı sorun sürüyordu
        (gerçek kullanıcılardan gelen "favorilerim kayboluyor" şikayeti
        büyük ihtimalle buydu). Artık: bir deneme daha yapılıyor, hâlâ
        başarısız olursa LOADED_FLAG işaretlenmiyor (bir sonraki
        etkileşimde tekrar denenir) ve kullanıcıya görünür bir uyarı
        gösteriliyor.
        """
        if st.session_state[self.LOADED_FLAG_KEY]:
            return

        if self._client is not None:
            last_error = None
            for attempt in range(2):  # ilk deneme + 1 yeniden deneme
                try:
                    response = (
                        self._client.table("favorites")
                        .select("content")
                        .eq("session_id", self._session_id)
                        .order("created_at", desc=True)
                        .execute()
                    )
                    st.session_state[self.SESSION_KEY] = [row["content"] for row in response.data]
                    st.session_state[self.LOADED_FLAG_KEY] = True
                    return
                except Exception as e:
                    last_error = e
                    print(f"[Favorites] Supabase okuma hatası (deneme {attempt + 1}/2): {e}")

            # İki deneme de başarısız oldu — sessizce boş göstermek yerine
            # kullanıcıyı bilgilendiriyoruz, ve LOADED_FLAG'i işaretlemiyoruz
            # ki bir sonraki etkileşimde tekrar denensin.
            st.warning(
                "⚠️ Favorilerin şu anda yüklenemedi (bağlantı sorunu olabilir). "
                "Bir şeye tıklayarak tekrar denenecek."
            )
            return

        self._load_from_file()
        st.session_state[self.LOADED_FLAG_KEY] = True

    # -------------------------------------------------------------------
    # Dosya tabanlı yedek sistem (Supabase yapılandırılmamışsa kullanılır)
    # -------------------------------------------------------------------

    def _load_from_file(self) -> None:
        if os.path.exists(self.FAVORITES_FILE):
            try:
                with open(self.FAVORITES_FILE, "r", encoding="utf-8") as f:
                    st.session_state[self.SESSION_KEY] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Favorites] Dosya okuma hatası: {e}")

    def _save_to_file(self) -> None:
        try:
            with open(self.FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state[self.SESSION_KEY], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[Favorites] Dosya yazma hatası: {e}")

    # -------------------------------------------------------------------
    # Genel API — okumalar bellekten anında cevap verir, yazmalar hem
    # yerel listeyi hem (varsa) Supabase'i günceller.
    # -------------------------------------------------------------------

    def get_all(self) -> list[dict]:
        self._ensure_loaded()
        return list(st.session_state[self.SESSION_KEY])

    def is_favorite(self, content_id: int) -> bool:
        if content_id is None:
            return False
        self._ensure_loaded()
        return any(item.get("id") == content_id for item in st.session_state[self.SESSION_KEY])

    def add(self, content: dict) -> bool:
        content_id = content.get("id")
        if content_id is None:
            return False
        self._ensure_loaded()

        if self.is_favorite(content_id):
            return False

        # Önce yerel listeyi güncelle (kullanıcı anında sonucu görür),
        # sonra kalıcı depoya yaz.
        st.session_state[self.SESSION_KEY].insert(0, content)

        if self._client is not None:
            try:
                self._client.table("favorites").upsert({
                    "session_id": self._session_id,
                    "content_id": content_id,
                    "content": content,
                }).execute()
            except Exception as e:
                print(f"[Favorites] Supabase yazma hatası: {e}")
        else:
            self._save_to_file()
        return True

    def remove(self, content_id: int) -> bool:
        if content_id is None:
            return False
        self._ensure_loaded()

        before = len(st.session_state[self.SESSION_KEY])
        st.session_state[self.SESSION_KEY] = [
            fav for fav in st.session_state[self.SESSION_KEY] if fav.get("id") != content_id
        ]
        removed = len(st.session_state[self.SESSION_KEY]) < before
        if not removed:
            return False

        if self._client is not None:
            try:
                self._client.table("favorites").delete().eq("session_id", self._session_id).eq("content_id", content_id).execute()
            except Exception as e:
                print(f"[Favorites] Supabase silme hatası: {e}")
        else:
            self._save_to_file()
        return True

    def toggle(self, content: dict) -> tuple[bool, str]:
        """Favori durumunu değiştir (ekle/çıkar). (yeni_durum, mesaj) döner."""
        content_id = content.get("id")
        if self.is_favorite(content_id):
            self.remove(content_id)
            return False, "Favorilerden kaldırıldı"
        self.add(content)
        return True, "Favorilere eklendi"

    def get_count(self) -> int:
        self._ensure_loaded()
        return len(st.session_state[self.SESSION_KEY])

    def clear_all(self) -> None:
        self._ensure_loaded()
        st.session_state[self.SESSION_KEY] = []
        if self._client is not None:
            try:
                self._client.table("favorites").delete().eq("session_id", self._session_id).execute()
            except Exception as e:
                print(f"[Favorites] Supabase temizleme hatası: {e}")
        else:
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
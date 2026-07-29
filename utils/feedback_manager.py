"""
Geri Bildirim Yönetimi (İzledim / Beğenmedim)
-----------------------------------------------
Kullanıcının "izledim" veya "bu değildi" olarak işaretlediği içerikleri
session state ve JSON ile kalıcı olarak yönetir. Bu içerikler, bir daha
çarkta/kart destesinde/sonuç listesinde ve AI önerilerinde gösterilmez.
"""

import json
import os
from datetime import datetime
import streamlit as st


class FeedbackManager:
    """Kullanıcının izledim/beğenmedim geri bildirimlerini yöneten sınıf."""

    FEEDBACK_FILE = "user_feedback.json"
    SESSION_KEY = "feedback"  # {"watched": [...], "disliked": [...]}

    def __init__(self):
        self._init_session_state()
        self._load_from_file()

    def _init_session_state(self) -> None:
        if self.SESSION_KEY not in st.session_state:
            st.session_state[self.SESSION_KEY] = {"watched": [], "disliked": []}

    def _load_from_file(self) -> None:
        if os.path.exists(self.FEEDBACK_FILE):
            try:
                with open(self.FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not st.session_state[self.SESSION_KEY]["watched"] and not st.session_state[self.SESSION_KEY]["disliked"]:
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

    def _remove_from(self, bucket: str, content_id: int) -> None:
        items = st.session_state[self.SESSION_KEY][bucket]
        st.session_state[self.SESSION_KEY][bucket] = [i for i in items if i.get("id") != content_id]

    def mark_watched(self, content: dict) -> bool:
        """İçeriği 'izledim' olarak işaretle (varsa 'beğenmedim' listesinden çıkarır)."""
        content_id = content.get("id")
        if content_id is None:
            return False
        self._remove_from("disliked", content_id)
        self._remove_from("watched", content_id)
        st.session_state[self.SESSION_KEY]["watched"].append(self._make_entry(content))
        self._save_to_file()
        return True

    def mark_disliked(self, content: dict) -> bool:
        """İçeriği 'bu değildi' olarak işaretle (varsa 'izledim' listesinden çıkarır)."""
        content_id = content.get("id")
        if content_id is None:
            return False
        self._remove_from("watched", content_id)
        self._remove_from("disliked", content_id)
        st.session_state[self.SESSION_KEY]["disliked"].append(self._make_entry(content))
        self._save_to_file()
        return True

    def unmark(self, content_id: int) -> None:
        """Bir içeriğin her iki listeden de işaretini kaldır (geri al)."""
        self._remove_from("watched", content_id)
        self._remove_from("disliked", content_id)
        self._save_to_file()

    def is_watched(self, content_id: int) -> bool:
        return any(i.get("id") == content_id for i in st.session_state[self.SESSION_KEY]["watched"])

    def is_disliked(self, content_id: int) -> bool:
        return any(i.get("id") == content_id for i in st.session_state[self.SESSION_KEY]["disliked"])

    def get_excluded_ids(self) -> set:
        """
        Çark/kart/liste/AI önerilerinden hariç tutulması gereken ID'ler.

        ÖNEMLİ: Sadece "beğenmedim" olarak işaretlenenler gizlenir.
        "Beğendim" olumlu bir işarettir, bir daha görünmeyi ENGELLEMEZ —
        aksi halde beğendiğin bir filmin bir daha hiç çıkmaması, sanki
        onu da "istemiyorum" demişsin gibi garip bir his verir.
        """
        return {i.get("id") for i in st.session_state[self.SESSION_KEY]["disliked"]}

    def get_watched_count(self) -> int:
        return len(st.session_state[self.SESSION_KEY]["watched"])

    def get_disliked_count(self) -> int:
        return len(st.session_state[self.SESSION_KEY]["disliked"])

    def get_watched_list(self) -> list[dict]:
        """Beğenilen içeriklerin tam listesini döndürür (yönetim sayfası için)."""
        return list(st.session_state[self.SESSION_KEY]["watched"])

    def get_disliked_list(self) -> list[dict]:
        """Beğenilmeyen içeriklerin tam listesini döndürür (yönetim sayfası için)."""
        return list(st.session_state[self.SESSION_KEY]["disliked"])

    def filter_pool(self, items: list[dict]) -> list[dict]:
        """Bir içerik listesinden izlenmiş/beğenilmemiş olanları çıkarır."""
        excluded = self.get_excluded_ids()
        return [item for item in items if item.get("id") not in excluded]
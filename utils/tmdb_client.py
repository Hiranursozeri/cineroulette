"""
TMDB API İstemcisi
------------------
Geliştirilmiş hata yönetimi ve detaylı film bilgisi desteği.
"""

import os
import random
import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class TMDBClient:
    """TMDB API ile etkileşim için istemci sınıfı."""
    
   # 19. satırdan itibaren şunları yapıştır:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    # Placeholder görsel URL'leri
    PLACEHOLDER_POSTER = "https://via.placeholder.com/342x513/1a1a2e/fff"
    def __init__(self):
        """API anahtarını yükle ve doğrula."""
        self.api_key = os.getenv("TMDB_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "TMDB_API_KEY bulunamadı! "
                "Lütfen .env dosyasına API anahtarınızı ekleyin."
            )
        
        # API bağlantısını test et
        self._validate_api_key()
    
    def _validate_api_key(self) -> None:
        """API anahtarının geçerli olduğunu doğrula."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/configuration",
                params={"api_key": self.api_key},
                timeout=5,
            )
            if response.status_code == 401:
                raise ValueError("TMDB API anahtarı geçersiz!")
        except requests.exceptions.RequestException:
            pass  # Bağlantı hatalarını başlatma sırasında yoksay
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        API'ye istek gönder ve yanıtı döndür.
        
        Geliştirilmiş hata yönetimi ile.
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        request_params = {
            "api_key": self.api_key,
            "language": "tr-TR",
        }
        
        if params:
            request_params.update(params)
        
        try:
            response = requests.get(url, params=request_params, timeout=15)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            print(f"[TMDB] Zaman aşımı: {endpoint}")
            return None
        
        except requests.exceptions.HTTPError as e:
            print(f"[TMDB] HTTP Hatası ({response.status_code}): {e}")
            return None
        
        except requests.exceptions.ConnectionError:
            print(f"[TMDB] Bağlantı hatası: {endpoint}")
            return None
        
        except requests.exceptions.RequestException as e:
            print(f"[TMDB] İstek hatası: {e}")
            return None
        
        except ValueError as e:
            print(f"[TMDB] JSON parse hatası: {e}")
            return None
    
    def get_poster_url(
        self,
        poster_path: Optional[str],
        size: str = "w342",
    ) -> str:
        """
        Film/dizi afişinin tam URL'sini oluştur.
        Poster yoksa placeholder döndür.
        """
        if poster_path:
            return f"{self.IMAGE_BASE_URL}/{size}{poster_path}"
        return self.PLACEHOLDER_POSTER
    
    def get_backdrop_url(
        self,
        backdrop_path: Optional[str],
        size: str = "w780",
    ) -> Optional[str]:
        """Arka plan görselinin URL'sini oluştur."""
        if backdrop_path:
            return f"{self.IMAGE_BASE_URL}/{size}{backdrop_path}"
        return None
    
    # =========================================================================
    # TEMEL METODLAR
    # =========================================================================
    
    def get_popular_movies(self, page: int = 1) -> list[dict]:
        """Popüler filmleri getir."""
        data = self._make_request("/movie/popular", {"page": page})
        if data and "results" in data:
            return self._enrich_results(data["results"], "movie")
        return []
    
    def get_popular_tv_shows(self, page: int = 1) -> list[dict]:
        """Popüler dizileri getir."""
        data = self._make_request("/tv/popular", {"page": page})
        if data and "results" in data:
            return self._enrich_results(data["results"], "tv")
        return []
    
    def _enrich_results(
        self,
        results: list[dict],
        content_type: str,
    ) -> list[dict]:
        """Sonuçlara içerik türü ekle ve eksik alanları doldur."""
        enriched = []
        for item in results:
            item["content_type"] = content_type
            item["poster_url"] = self.get_poster_url(item.get("poster_path"))
            
            # Başlık standardizasyonu
            if content_type == "tv":
                item["title"] = item.get("name", "Bilinmeyen Dizi")
                item["release_date"] = item.get("first_air_date", "")
            else:
                item["title"] = item.get("title", "Bilinmeyen Film")
            
            enriched.append(item)
        return enriched
    
    # =========================================================================
    # FİLTRELİ ARAMA
    # =========================================================================
    
    def discover_movies(
        self,
        genre_ids: Optional[list[int]] = None,
        min_vote_average: Optional[float] = None,
        min_vote_count: Optional[int] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
    ) -> list[dict]:
        """Filtrelere göre film keşfet."""
        params = {
            "sort_by": sort_by,
            "page": page,
            "include_adult": False,
            "include_video": False,
        }
        
        if genre_ids:
            params["with_genres"] = "|".join(str(g) for g in genre_ids)
        
        if min_vote_average is not None:
            params["vote_average.gte"] = min_vote_average
        
        if min_vote_count is not None:
            params["vote_count.gte"] = min_vote_count
        
        data = self._make_request("/discover/movie", params)
        if data and "results" in data:
            return self._enrich_results(data["results"], "movie")
        return []
    
    def discover_tv_shows(
        self,
        genre_ids: Optional[list[int]] = None,
        min_vote_average: Optional[float] = None,
        min_vote_count: Optional[int] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
    ) -> list[dict]:
        """Filtrelere göre dizi keşfet."""
        params = {
            "sort_by": sort_by,
            "page": page,
            "include_adult": False,
        }
        
        if genre_ids:
            params["with_genres"] = "|".join(str(g) for g in genre_ids)
        
        if min_vote_average is not None:
            params["vote_average.gte"] = min_vote_average
        
        if min_vote_count is not None:
            params["vote_count.gte"] = min_vote_count
        
        data = self._make_request("/discover/tv", params)
        if data and "results" in data:
            return self._enrich_results(data["results"], "tv")
        return []
    
    # =========================================================================
    # DETAYLI BİLGİ
    # =========================================================================
    
    def get_movie_details(self, movie_id: int) -> Optional[dict]:
        """Film detaylarını getir (türler dahil)."""
        data = self._make_request(f"/movie/{movie_id}")
        if data:
            data["content_type"] = "movie"
            data["poster_url"] = self.get_poster_url(data.get("poster_path"))
            return data
        return None
    
    def get_tv_details(self, tv_id: int) -> Optional[dict]:
        """Dizi detaylarını getir."""
        data = self._make_request(f"/tv/{tv_id}")
        if data:
            data["content_type"] = "tv"
            data["title"] = data.get("name", "Bilinmeyen Dizi")
            data["poster_url"] = self.get_poster_url(data.get("poster_path"))
            return data
        return None
    
    def get_content_details(
        self,
        content_id: int,
        content_type: str,
    ) -> Optional[dict]:
        """İçerik türüne göre detay getir."""
        if content_type == "movie":
            return self.get_movie_details(content_id)
        return self.get_tv_details(content_id)
    
    # =========================================================================
    # TÜR BİLGİLERİ
    # =========================================================================
    
    def get_movie_genres(self) -> dict[int, str]:
        """Film türlerini getir (id -> name mapping)."""
        data = self._make_request("/genre/movie/list")
        if data and "genres" in data:
            return {g["id"]: g["name"] for g in data["genres"]}
        return {}
    
    def get_tv_genres(self) -> dict[int, str]:
        """Dizi türlerini getir."""
        data = self._make_request("/genre/tv/list")
        if data and "genres" in data:
            return {g["id"]: g["name"] for g in data["genres"]}
        return {}
    
    # =========================================================================
    # RASTGELE SEÇİM
    # =========================================================================
    
    def get_random_content(
        self,
        content_type: str = "movie",
        min_vote_average: float = 7.0,
        min_vote_count: int = 1000,
        count: int = 12,
    ) -> list[dict]:
        """Rastgele ama kaliteli içerik getir."""
        all_items = []
        
        # Rastgele 3 sayfa seç
        random_pages = random.sample(range(1, 50), min(3, 49))
        
        for page in random_pages:
            try:
                if content_type == "movie":
                    items = self.discover_movies(
                        min_vote_average=min_vote_average,
                        min_vote_count=min_vote_count,
                        page=page,
                    )
                else:
                    items = self.discover_tv_shows(
                        min_vote_average=min_vote_average,
                        min_vote_count=min_vote_count,
                        page=page,
                    )
                all_items.extend(items)
            except Exception as e:
                print(f"[TMDB] Rastgele içerik hatası: {e}")
                continue
        
        if all_items:
            random.shuffle(all_items)
            return all_items[:count]
        
        return []
    
    # =========================================================================
    # ARAMA
    # =========================================================================
    
    def search_movies(self, query: str, page: int = 1) -> list[dict]:
        """Film ara."""
        data = self._make_request("/search/movie", {"query": query, "page": page})
        if data and "results" in data:
            return self._enrich_results(data["results"], "movie")
        return []
    
    def search_tv_shows(self, query: str, page: int = 1) -> list[dict]:
        """Dizi ara."""
        data = self._make_request("/search/tv", {"query": query, "page": page})
        if data and "results" in data:
            return self._enrich_results(data["results"], "tv")
        return []

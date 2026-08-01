import requests
from android_utils import log

from constants import ANILIST_GRAPHQL_URL, QUERIES, SHIKIMORI_API_ANIMES


def fetch_anilist_data(query_str, variables):
    try:
        r = requests.post(
            ANILIST_GRAPHQL_URL,
            json={"query": query_str, "variables": variables},
            headers={"User-Agent": "ANI", "Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()["data"]
        if "Media" in data:
            return data["Media"]
        if "Page" in data and data["Page"]["media"]:
            return data["Page"]["media"][0]
        return None
    except Exception as e:
        log(f"[ANI] AniList error: {e}")
        return None


def fetch_by_id(anime_id):
    return fetch_anilist_data(QUERIES["media"], {"id": anime_id})


def fetch_by_mal_id(mal_id):
    return fetch_anilist_data(QUERIES["mal"], {"idMal": mal_id})


def fetch_anilist(search):
    return fetch_anilist_data(QUERIES["search"], {"search": search})


def search_shikimori(query, cache):
    ck = f"shiki_simple_{query.lower().strip()}"
    if ck in cache:
        return cache[ck]
    try:
        if str(query).strip().isdigit():
            full = requests.get(
                f"{SHIKIMORI_API_ANIMES}/{query.strip()}",
                headers={"User-Agent": "ANI"},
                timeout=8,
            )
            if full.status_code == 200:
                result = full.json()
                if result:
                    cache[ck] = result
                    return result
        resp = requests.get(
            SHIKIMORI_API_ANIMES,
            params={"search": query, "limit": 1, "order": "ranked", "censored": "false"},
            headers={"User-Agent": "ANI"},
            timeout=8,
        )
        resp.raise_for_status()
        items = resp.json()
        if items:
            full = requests.get(
                f"{SHIKIMORI_API_ANIMES}/{items[0]['id']}",
                headers={"User-Agent": "ANI"},
                timeout=8,
            )
            full.raise_for_status()
            result = full.json()
            if result:
                cache[ck] = result
                return result
    except Exception:
        pass
    return None


def multi_search_anilist(query):
    try:
        r = requests.post(
            ANILIST_GRAPHQL_URL,
            json={"query": QUERIES["multi_search"], "variables": {"q": query}},
            headers={"User-Agent": "ANI", "Content-Type": "application/json"},
            timeout=12,
        )
        r.raise_for_status()
        return r.json().get("data", {}).get("Page", {}).get("media", []) or []
    except Exception as e:
        log(f"[ANI] multi anilist: {e}")
        return None


def multi_search_shikimori(query):
    try:
        resp = requests.get(
            SHIKIMORI_API_ANIMES,
            params={"search": query, "limit": 50, "order": "ranked", "censored": "false"},
            headers={"User-Agent": "ANI"},
            timeout=12,
        )
        resp.raise_for_status()
        return resp.json() or []
    except Exception as e:
        log(f"[ANI] multi shiki: {e}")
        return None


def multi_search_anilist_genre(name, force_tag=False):
    def run(qstr):
        try:
            r = requests.post(
                ANILIST_GRAPHQL_URL,
                json={"query": qstr, "variables": {"g": name}},
                headers={"User-Agent": "ANI", "Content-Type": "application/json"},
                timeout=12,
            )
            r.raise_for_status()
            return r.json().get("data", {}).get("Page", {}).get("media", []) or []
        except Exception:
            return None

    first, second = (QUERIES["multi_tag"], QUERIES["multi_genre"]) if force_tag else (QUERIES["multi_genre"], QUERIES["multi_tag"])
    media = run(first)
    if media is None:
        return None
    if not media:
        media = run(second)
    return media


def multi_search_shikimori_genre(genre_id):
    try:
        resp = requests.get(
            SHIKIMORI_API_ANIMES,
            params={"genre_v2": genre_id, "limit": 50, "order": "ranked"},
            headers={"User-Agent": "ANI"},
            timeout=12,
        )
        resp.raise_for_status()
        return resp.json() or []
    except Exception as e:
        log(f"[ANI] multi shiki genre: {e}")
        return None
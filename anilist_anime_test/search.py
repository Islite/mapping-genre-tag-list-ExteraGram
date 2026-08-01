import time

from android_utils import log, run_on_ui_thread
from client_utils import run_on_queue, send_text

import api
from formatter import clean_template_output, format_media_full, get_description
from utils import is_cyrillic, show_error, show_success


def prefer_shiki(plugin, query=""):
    if plugin.primary_source == 1:
        return bool(plugin.use_shikimori)
    if plugin.use_shikimori and not plugin.use_anilist:
        return True
    return plugin.use_shikimori and is_cyrillic(query)


def cache_result(cache, cache_key, anilist_data, successful_original, shiki_data):
    packed = (anilist_data, successful_original, shiki_data, time.time())
    cache[cache_key] = packed
    if anilist_data and anilist_data.get("id") is not None:
        cache[f"data_{anilist_data.get('id')}"] = packed
    if shiki_data and shiki_data.get("id") is not None:
        cache[f"data_{shiki_data.get('id')}"] = packed
    return anilist_data, successful_original, shiki_data


def get_data_by_id_or_search(plugin, original_candidates, cache_key, cache):
    if cache_key in cache:
        c = cache[cache_key]
        return (
            c[0] if isinstance(c, tuple) else c,
            c[1] if isinstance(c, tuple) and len(c) > 1 else "",
            c[2] if isinstance(c, tuple) and len(c) > 2 else None,
        )
    anilist_data = shiki_data = None
    successful_original = ""
    first = original_candidates[0] if original_candidates else ""
    if first and first.isdigit():
        id_int = int(first)
        successful_original = first
        if plugin.direct_id_source == 0:
            if plugin.use_anilist:
                anilist_data = api.fetch_by_id(id_int)
            if anilist_data and plugin.use_shikimori:
                en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("userPreferred")
                shiki_data = api.search_shikimori(en, cache) if en else None
            if not anilist_data and plugin.use_shikimori:
                shiki_data = api.search_shikimori(first, cache)
                if shiki_data:
                    mal = shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                    if mal and plugin.use_anilist:
                        anilist_data = api.fetch_by_mal_id(mal)
        else:
            if plugin.use_shikimori:
                shiki_data = api.search_shikimori(first, cache)
            if shiki_data and plugin.use_anilist:
                mal = shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                if mal:
                    anilist_data = api.fetch_by_mal_id(mal)
                if not anilist_data:
                    en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0]
                    if en:
                        anilist_data = api.fetch_anilist(en)
            if not shiki_data and plugin.use_anilist:
                anilist_data = api.fetch_by_id(id_int)
                if anilist_data and plugin.use_shikimori:
                    en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("userPreferred")
                    shiki_data = api.search_shikimori(en, cache) if en else None
        if anilist_data or shiki_data:
            return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
        return None, "", None

    pref = prefer_shiki(plugin, first)
    if pref and plugin.use_shikimori:
        for term in original_candidates:
            shiki_data = api.search_shikimori(term, cache)
            if shiki_data:
                successful_original = term
                anilist_en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0] or term
                if plugin.use_anilist:
                    anilist_data = api.fetch_anilist(anilist_en)
                    if not anilist_data and (mal := shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")):
                        anilist_data = api.fetch_by_mal_id(mal)
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    if plugin.use_anilist:
        for term in original_candidates:
            anilist_data = api.fetch_anilist(term)
            if anilist_data:
                successful_original = term
                en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("native")
                if plugin.use_shikimori and en:
                    shiki_data = api.search_shikimori(en, cache)
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    if not pref and plugin.use_shikimori:
        for term in original_candidates:
            shiki_data = api.search_shikimori(term, cache)
            if shiki_data:
                successful_original = term
                anilist_en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0] or term
                if plugin.use_anilist:
                    anilist_data = api.fetch_anilist(anilist_en)
                    if not anilist_data and (mal := shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")):
                        anilist_data = api.fetch_by_mal_id(mal)
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    return None, "", None


def build_send_params(account, base, text, parse_mode=None):
    p = {"peer": base["peer"], "text": text, "parse_mode": parse_mode}
    if base.get("replyToMsg"):
        p["replyToMsg"] = base["replyToMsg"]
    if base.get("replyToTopMsg"):
        p["replyToTopMsg"] = base["replyToTopMsg"]
    if base.get("messageThreadId") is not None:
        p["messageThreadId"] = base["messageThreadId"]
    return p


def send_only_success(plugin, text, account, base):
    try:
        cleaned = clean_template_output(text, None, plugin.empty_ph_space_mode)
        if not cleaned.strip():
            return
        p = build_send_params(account, base, cleaned, "HTML" if plugin.enable_html_card else None)
        send_text(account=account, **p)
        show_success("Отправлено")
    except Exception as e:
        log(f"[ANI] send error: {e}")


def send_description_separate(description_raw, account, base):
    if not description_raw.strip():
        return
    try:
        p = build_send_params(account, base, f"<blockquote expandable>{description_raw}</blockquote>", "HTML")
        send_text(account=account, **p)
    except Exception as e:
        log(f"[ANI] send_description_separate error: {e}")


def send_card_and_desc(plugin, data, shiki, account, base, mapping):
    card = format_media_full(plugin, data or {}, plugin.card_template, shiki, mapping)
    send_only_success(plugin, card, account, base)
    desc = get_description(plugin, data or {}, shiki)
    if plugin.show_description and desc.strip() and not plugin.description_in_card:
        run_on_queue(lambda: send_description_separate(desc, account, base))


def process_search(plugin, account, base, original_candidates, cache, mapping):
    try:
        ck = f"data_{original_candidates[0] if original_candidates else 'empty'}"
        data, _, shiki = get_data_by_id_or_search(plugin, original_candidates, ck, cache)
        if data or shiki:
            send_card_and_desc(plugin, data, shiki, account, base, mapping)
        else:
            show_error()
    except Exception as e:
        log(f"[ANI] Search process error: {e}")
        show_error("Ошибка при поиске")


def _map_genres(raw_genres, mapping):
    main_g = mapping.universal_mapping.get("main_genres") or {}
    add_g = mapping.universal_mapping.get("additional_genres") or {}
    out = []
    for g in raw_genres or []:
        tr = main_g.get(g) or add_g.get(g) or [g]
        out.append(tr[0] if isinstance(tr, list) else tr)
    return out


def parse_anilist_media_list(media, mapping):
    results = []
    countries = mapping.universal_mapping.get("countries") or {}
    seasons = mapping.universal_mapping.get("seasons") or {}
    formats = mapping.universal_mapping.get("formats") or {}
    flags = mapping.universal_mapping.get("flags") or {}
    for m in media:
        title = m.get("title", {}).get("english") or m.get("title", {}).get("romaji") or "Unknown"
        code = m.get("countryOfOrigin") or "JP"
        flag = flags.get(code, "🇯🇵")
        cname = countries.get(code, ["Япония"])[0]
        season = m.get("season")
        year = m.get("seasonYear")
        sname = seasons.get(season, [""])[0] if season else ""
        country_line = f"{flag} {cname}, {sname} {year}г." if sname and year else f"{flag} {cname}"
        score_val = m.get("averageScore")
        fmt = m.get("format", "")
        results.append({
            "id": m.get("id"),
            "title": title,
            "genres": _map_genres(m.get("genres"), mapping),
            "cover_url": m.get("coverImage", {}).get("large", ""),
            "country_line": country_line,
            "score": f"{score_val / 10:.1f}" if score_val is not None else "?",
            "type_ru": formats.get(fmt, [fmt])[0] if fmt else "",
            "source": "anilist",
        })
    return results


def parse_shikimori_media_list(media, mapping):
    results = []
    fs = mapping.universal_mapping.get("format_shiki") or {}
    sm = mapping.universal_mapping.get("season_month") or {}
    for m in media:
        title = m.get("russian") or m.get("name") or "Unknown"
        img = m.get("image") or {}
        path = img.get("original") or img.get("preview") or ""
        cover_url = ("https://shikimori.one" + path) if path.startswith("/") else (path or "")
        country_line = "🇯🇵 Япония"
        aired = m.get("aired_on") or m.get("released_on")
        if aired:
            try:
                y, mo = aired.split("-")[:2]
                country_line = f"🇯🇵 Япония, {sm.get(str(int(mo)), sm.get(int(mo), 'зима'))} {y}г."
            except Exception:
                pass
        kind = (m.get("kind") or "").lower()
        results.append({
            "id": m.get("id"),
            "title": title,
            "genres": [],
            "cover_url": cover_url,
            "country_line": country_line,
            "score": f"{float(m.get('score')):.1f}" if m.get("score") else "?",
            "type_ru": fs.get(kind, kind.upper()),
            "source": "shikimori",
        })
    return results


def _row_from_id_data(data, shiki, mapping):
    if data:
        rid = data.get("id")
        t = data.get("title") or {}
        title = t.get("english") or t.get("romaji") or t.get("userPreferred") or "Unknown"
        cover = (data.get("coverImage") or {}).get("large") or ""
        if not cover and rid:
            cover = f"https://img.anili.st/media/{rid}"
        code = data.get("countryOfOrigin") or "JP"
        flags = mapping.universal_mapping.get("flags") or {}
        countries = mapping.universal_mapping.get("countries") or {}
        seasons = mapping.universal_mapping.get("seasons") or {}
        formats = mapping.universal_mapping.get("formats") or {}
        flag = flags.get(code, "🇯🇵")
        cname = countries.get(code, ["Япония"])[0]
        season = data.get("season")
        year = data.get("seasonYear")
        sname = seasons.get(season, [""])[0] if season else ""
        country_line = f"{flag} {cname}, {sname} {year}г." if sname and year else f"{flag} {cname}"
        score_val = data.get("averageScore")
        fmt = data.get("format", "")
        return {
            "id": rid,
            "title": title,
            "genres": _map_genres(data.get("genres"), mapping),
            "cover_url": cover,
            "country_line": country_line,
            "score": f"{score_val / 10:.1f}" if score_val is not None else "?",
            "type_ru": formats.get(fmt, [fmt])[0] if fmt else "",
            "source": "anilist",
        }
    if shiki:
        rid = shiki.get("id")
        title = shiki.get("russian") or shiki.get("name") or "Unknown"
        img = shiki.get("image") or {}
        path = img.get("original") or img.get("preview") or ""
        cover = ("https://shikimori.one" + path) if path.startswith("/") else (path or "")
        fs = mapping.universal_mapping.get("format_shiki") or {}
        kind = (shiki.get("kind") or "").lower()
        return {
            "id": rid,
            "title": title,
            "genres": [],
            "cover_url": cover,
            "country_line": "🇯🇵 Япония",
            "score": f"{float(shiki.get('score')):.1f}" if shiki.get("score") else "?",
            "type_ru": fs.get(kind, kind.upper()),
            "source": "shikimori",
        }
    return None


def multi_search_by_genre(plugin, query, pref, mapping, cache):
    shiki_id, shiki_en = mapping.resolve_shiki_genre(query)
    al_en, al_kind = mapping.resolve_anilist_genre(query)
    is_tag = al_kind == "tag"
    if pref:
        if shiki_id is not None:
            raw = api.multi_search_shikimori_genre(shiki_id)
            if raw:
                return parse_shikimori_media_list(raw, mapping), True
        name = al_en or shiki_en or query
        raw = api.multi_search_anilist_genre(name, force_tag=is_tag)
        if raw:
            return parse_anilist_media_list(raw, mapping), False
        return [], pref
    name = al_en or shiki_en or query
    raw = api.multi_search_anilist_genre(name, force_tag=is_tag)
    if raw:
        return parse_anilist_media_list(raw, mapping), False
    if shiki_id is not None:
        raw = api.multi_search_shikimori_genre(shiki_id)
        if raw:
            return parse_shikimori_media_list(raw, mapping), True
    return [], pref


def _text_multi_search(plugin, q, pref, cache, mapping):
    ck = f"multi_{pref}_{q.lower()}"
    now = time.time()
    if ck in cache and isinstance(cache[ck], tuple) and len(cache[ck]) >= 2 and now - cache[ck][-1] < 300:
        return cache[ck][0], cache[ck][1]
    results = None
    actual_shiki = False
    if pref and plugin.use_shikimori:
        raw = api.multi_search_shikimori(q)
        actual_shiki = True
        results = parse_shikimori_media_list(raw, mapping) if raw is not None else None
        if not results and plugin.use_anilist:
            raw = api.multi_search_anilist(q)
            results = parse_anilist_media_list(raw, mapping) if raw is not None else None
            actual_shiki = False
    else:
        raw = api.multi_search_anilist(q) if plugin.use_anilist else None
        results = parse_anilist_media_list(raw, mapping) if raw is not None else None
        actual_shiki = False
        if (not results) and plugin.use_shikimori:
            raw = api.multi_search_shikimori(q)
            results = parse_shikimori_media_list(raw, mapping) if raw is not None else None
            actual_shiki = True
    if results is not None:
        cache[ck] = (results, actual_shiki, time.time())
    return results, actual_shiki


def process_multi_search(plugin, query, is_genre, account, base, cache, mapping, show_popup_cb, on_select_cb):
    q = (query or "").strip()
    pref = prefer_shiki(plugin, q)
    id_row = None
    actual_shiki = pref

    if not is_genre and q.isdigit():
        ck = f"data_{q}"
        data, _, shiki = get_data_by_id_or_search(plugin, [q], ck, cache)
        if data or shiki:
            id_row = _row_from_id_data(data, shiki, mapping)
            actual_shiki = bool(shiki and not data)

    if is_genre:
        results, actual_shiki = multi_search_by_genre(plugin, q, pref, mapping, cache)
    else:
        results, text_shiki = _text_multi_search(plugin, q, pref, cache, mapping)
        if results is None and id_row is None:
            show_error("Ошибка API")
            return
        if results is None:
            results = []
        else:
            actual_shiki = text_shiki

    if id_row is not None:
        rid = id_row.get("id")
        src = id_row.get("source")
        rest = [
            r for r in (results or [])
            if not (r.get("id") == rid and r.get("source") == src)
        ]
        results = [id_row] + rest
        actual_shiki = id_row.get("source") == "shikimori"

    if results is None:
        show_error("Ошибка API")
        return
    if not results:
        show_error("Ничего не найдено" if not is_genre else "Жанр/тег не найден")
        return
    if plugin.search_ui_mode == 1:
        run_on_queue(lambda: on_select_cb(results[0], account, base))
        return
    run_on_ui_thread(lambda: show_popup_cb(results, q, actual_shiki, is_genre, account, base))


def on_popup_select(plugin, res, account, base, cache, mapping):
    try:
        anilist_data = shiki_data = None
        rid = res.get("id")
        ck = f"data_{rid}" if rid is not None else None
        if ck and ck in cache:
            c = cache[ck]
            anilist_data = c[0] if isinstance(c, tuple) else c
            shiki_data = c[2] if isinstance(c, tuple) and len(c) > 2 else None
        if res.get("source") == "shikimori":
            if not shiki_data:
                shiki_data = api.search_shikimori(str(rid), cache)
            if shiki_data and plugin.use_anilist and not anilist_data:
                mal = shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                if mal:
                    anilist_data = api.fetch_by_mal_id(mal)
                if not anilist_data:
                    en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0]
                    if en:
                        anilist_data = api.fetch_anilist(en)
        else:
            if plugin.use_anilist and rid and not anilist_data:
                anilist_data = api.fetch_by_id(int(rid))
            if anilist_data and plugin.use_shikimori and not shiki_data:
                en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("userPreferred")
                shiki_data = api.search_shikimori(en, cache) if en else None
        if anilist_data or shiki_data:
            send_card_and_desc(plugin, anilist_data, shiki_data, account, base, mapping)
        else:
            show_error()
    except Exception as e:
        log(f"[ANI] popup select: {e}")
        show_error("Ошибка при загрузке")

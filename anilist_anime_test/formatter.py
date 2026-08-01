import re
import unicodedata

from android_utils import log


def format_item(name, use_underscore, use_hash, is_spoiler=False, spoiler_format=True):
    if not name:
        return ""
    t = str(name).strip()
    if use_underscore:
        t = t.replace("-", "_").replace(" ", "_")
    elif use_hash:
        t = t.replace(" ", "")
    if use_hash:
        t = "#" + t
    if is_spoiler and spoiler_format:
        t = "<spoiler>" + t + "</spoiler>"
    return t


def process_list(
    cand, sorting, show_main, show_unlisted,
    hash_master, hash_main, hash_unlisted,
    under_master, under_main, under_unlisted,
    comma_master, comma_main, comma_unlisted,
    show_separators, separator_labels, separator_enabled,
    sep_hash, sep_under, sep_comma, spoiler_format,
    unlisted_label="прочий",
):
    if not cand:
        return ""
    groups = []
    cur_items, cur_label, cur_enabled, cur_is_main = [], None, show_main, True
    cur_hash = hash_master and hash_main
    cur_under = under_master and under_main
    cur_comma = comma_master and comma_main
    used = set()

    def flush():
        nonlocal cur_items, cur_label, cur_enabled, cur_is_main, cur_hash, cur_under, cur_comma
        if cur_enabled and cur_items:
            groups.append((cur_label if show_separators else None, cur_items[:], cur_is_main, cur_comma))
        cur_items = []

    if not sorting:
        if show_main or show_unlisted:
            fmt = [
                format_item(tr, under_master and under_main, hash_master and hash_main, sp, spoiler_format)
                for name, (tr, sp) in cand.items()
            ]
            sep = ", " if (comma_master and comma_main) else " "
            body = sep.join(f for f in fmt if f)
            return body if body else ""
        return ""

    for key in sorting:
        if key.startswith("separator_"):
            flush()
            cur_label = separator_labels.get(key, key.replace("separator_", "").replace("_", " "))
            cur_enabled = separator_enabled.get(key, True)
            cur_is_main = False
            cur_hash = hash_master and sep_hash.get(key, True)
            cur_under = under_master and sep_under.get(key, True)
            cur_comma = comma_master and sep_comma.get(key, True)
            continue
        if not cur_enabled or key in used or key not in cand:
            continue
        tr, sp = cand[key]
        fmt = format_item(tr, cur_under, cur_hash, sp, spoiler_format)
        if fmt:
            cur_items.append(fmt)
        used.add(key)
    flush()

    leftover = [
        format_item(tr, under_master and under_unlisted, hash_master and hash_unlisted, sp, spoiler_format)
        for name, (tr, sp) in cand.items() if name not in used
    ]
    leftover = [f for f in leftover if f]
    if leftover and show_unlisted:
        groups.append((unlisted_label if show_separators else None, leftover, False, comma_master and comma_unlisted))

    lines = []
    for label, group_items, is_m, use_c in groups:
        body = (", ".join(group_items) if use_c else " ".join(group_items))
        if body:
            lines.append(f"{label}: {body}" if label else body)
    return "\n".join(lines) if show_separators and len(lines) > 1 else " ".join(lines)


def process_genres(plugin, data, mapping):
    if not data or not plugin.show_genres:
        return ""
    um = mapping.universal_mapping
    all_g = set(data.get("genres") or [])
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    prom = [
        (t["name"], t.get("isMediaSpoiler", False))
        for t in (data.get("tags") or [])
        if t.get("name") in g_like and t.get("rank", 0) >= plugin.tag_min_rank
    ]
    all_g.update(p[0] for p in prom)
    main_m = um.get("main_genres", {})
    add_m = um.get("additional_genres", {})
    cand = {}
    for g in all_g:
        is_sp = next((p[1] for p in prom if p[0] == g), False)
        tr = (main_m.get(g) or add_m.get(g) or [g])
        tr = tr[0] if isinstance(tr, list) else tr
        cand[g] = (tr, is_sp)
    sorting = um.get("sorting_genres", um.get("ordered_genres", []))
    return process_list(
        cand, sorting, plugin.show_genres_main, plugin.show_genres_unlisted,
        plugin.hash_genres, plugin.hash_genres_main, plugin.hash_genres_unlisted,
        plugin.underscore_genres, plugin.underscore_genres_main, plugin.underscore_genres_unlisted,
        plugin.comma_genres, plugin.comma_genres_main, plugin.comma_genres_unlisted,
        plugin.show_separators, mapping.separator_labels, mapping.separator_enabled,
        mapping.sep_hash, mapping.sep_under, mapping.sep_comma, plugin.spoiler_format,
        "прочий жанр",
    )


def process_tags(plugin, data, mapping):
    if not data or not plugin.show_tags:
        return ""
    um = mapping.universal_mapping
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    dem = set(um.get("demographics", {}))
    all_t = {}
    for t in (data.get("tags") or []):
        name = t.get("name")
        if not name or t.get("rank", 0) < plugin.tag_min_rank or name in dem or name in g_like:
            continue
        all_t[name] = t.get("isMediaSpoiler", False)
    main_m = um.get("main_tags", {})
    add_m = um.get("additional_tags", {})
    cand = {}
    for name, sp in all_t.items():
        tr = (main_m.get(name) or add_m.get(name) or [name])
        tr = tr[0] if isinstance(tr, list) else tr
        cand[name] = (tr, sp)
    sorting = um.get("sorting_tags", um.get("ordered_tags", []))
    return process_list(
        cand, sorting, plugin.show_tags_main, plugin.show_tags_unlisted,
        plugin.hash_tags, plugin.hash_tags_main, plugin.hash_tags_unlisted,
        plugin.underscore_tags, plugin.underscore_tags_main, plugin.underscore_tags_unlisted,
        plugin.comma_tags, plugin.comma_tags_main, plugin.comma_tags_unlisted,
        plugin.show_separators, mapping.separator_labels, mapping.separator_enabled,
        mapping.sep_hash, mapping.sep_under, mapping.sep_comma, plugin.spoiler_format,
        "прочий тег",
    )


def extract_titles(plugin, data, shiki_data):
    titles = data.get("title", {}) if data else {}
    en = list(dict.fromkeys(filter(None, [
        titles.get("english"), titles.get("romaji"), titles.get("native"), titles.get("userPreferred")
    ] + (data.get("synonyms", []) if data else []))))
    en = [t for t in en if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", t))]
    if not data and shiki_data:
        en = list(dict.fromkeys(filter(None, [shiki_data.get("name")] + shiki_data.get("english", []) + shiki_data.get("synonyms", []))))
        en = [t for t in en if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", t))]
    ru = []
    if shiki_data and plugin.use_shikimori:
        ru = [shiki_data.get("russian")] + shiki_data.get("synonyms", [])
        ru = [n for n in ru if n and re.match(r"^[А-Яа-яЁё0-9\s\W]+$", n)]
    if ru:
        ru_d = ru[:plugin.extra_ru_count]
        en_d = en[:plugin.extra_en_count]
    else:
        ru_d = en[:plugin.extra_ru_count]
        en_d = en[plugin.extra_ru_count:plugin.extra_ru_count + plugin.extra_en_count]
    return (
        (ru_d[0] if ru_d else ""),
        (ru_d[1:] if len(ru_d) > 1 else []),
        (en_d[0] if en_d else ""),
        (en_d[1:] if len(en_d) > 1 else []),
    )


def get_cover_url(data, shiki_data=None):
    id_ = data.get("id") if data else ""
    return f"https://img.anili.st/media/{id_}" if id_ else ""


def get_country_info(plugin, data, mapping):
    code = data.get("countryOfOrigin", "JP") if data else "JP"
    flags = mapping.universal_mapping.get("flags") or {}
    flag = flags.get(code, "🇯🇵") if plugin.show_flag else ""
    txt = ""
    if plugin.show_country:
        txt = (mapping.universal_mapping.get("countries") or {}).get(code, ["Неизвестно"])[0]
        if plugin.hash_country:
            txt = "#" + txt
    return flag, txt, code


def get_season_year(plugin, data, shiki_data, mapping):
    season_val = year_val = ""
    if plugin.show_season or plugin.show_year:
        season_val = (mapping.universal_mapping.get("seasons") or {}).get(data.get("season"), [""])[0] if data and data.get("season") else ""
        year_val = data.get("seasonYear", "") if data else ""
        if not season_val and shiki_data and shiki_data.get("aired_on"):
            try:
                parts = shiki_data["aired_on"].split("-")
                year_val = year_val or parts[0]
                m = int(parts[1]) if len(parts) > 1 else 0
                sm = mapping.universal_mapping.get("season_month") or {}
                season_val = season_val or sm.get(str(m), sm.get(m, ""))
            except Exception:
                pass
    return (season_val if plugin.show_season else ""), (str(year_val) if year_val and year_val != "????" and plugin.show_year else "")


def get_description(plugin, data, shiki_data, force=False):
    if not force and not plugin.show_description:
        return ""
    desc = ""
    if plugin.desc_source == 0:
        if shiki_data:
            desc = shiki_data.get("description") or shiki_data.get("synopsis") or ""
    else:
        if data:
            desc = data.get("description") or ""
    return desc.strip() if desc else ""


def clean_template_output(text, vars_dict, empty_ph_space_mode=0):
    if not text:
        return ""
    empty, non_empty = set(), []
    if vars_dict:
        for k, v in vars_dict.items():
            val = str(v).strip()
            if not val:
                empty.add(k)
            else:
                non_empty.append(val)
    lines, cleaned = text.split("\n"), []
    mode = empty_ph_space_mode
    hang = re.compile(
        r"^(студии|источник|статус|длительность|формат|целевая аудитория|жанры|теги|ссылки|описание|оригинал|продолжительность серии|рейтинг|эпизоды)[\s:]*$",
        re.I | re.UNICODE,
    )
    pure = re.compile(r"^[\s|#\-–—.,;:|]+$", re.UNICODE)
    for line in lines:
        if not line.strip():
            continue
        proc = line
        for key in empty:
            ph = "{" + key + "}"
            proc = re.sub(r"\s*" + re.escape(ph), "", proc) if mode == 0 else re.sub(re.escape(ph) + r"\s*", "", proc)
            proc = proc.replace(ph, "")
        proc = proc.strip()
        if not proc:
            continue
        if vars_dict:
            has = any(v.rstrip(",").strip() and (v.rstrip(",").strip() in proc or v in proc) for v in non_empty)
            if not has and (hang.match(proc) or pure.match(proc)):
                continue
        proc = re.sub(r"\s{2,}", " ", proc)
        proc = re.sub(r",\s*,", ",", proc)
        proc = re.sub(r"\s+,", ",", proc)
        proc = re.sub(r",\s+", ", ", proc)
        cleaned.append(proc)
    res = "\n".join(cleaned)
    return re.sub(r"\n{3,}", "\n\n", res).strip()


def format_media_full(plugin, data, template, shiki_data, mapping):
    if not data and not shiki_data:
        return "Не найдено"
    main_ru, other_ru, main_en, other_en = extract_titles(plugin, data, shiki_data)
    cover = get_cover_url(data, shiki_data)
    preview = f'<a href="{cover}">&shy;</a>' if cover else ""
    flag, country_text, _ = get_country_info(plugin, data, mapping)
    season, year = get_season_year(plugin, data, shiki_data, mapping)
    ep_raw = data.get("episodes") if data else None
    st_raw = data.get("status") if data else ""
    ep_str = ""
    if plugin.show_episodes:
        ep_str = f"{ep_raw}/{ep_raw} эп." if st_raw == "FINISHED" and ep_raw else (f"?/{ep_raw} эп." if ep_raw else "? эп.")
    fmt_raw = data.get("format") if data else ""
    fmt_tr = (mapping.universal_mapping.get("formats") or {}).get(fmt_raw, [fmt_raw])[0] if fmt_raw else ""
    fmt_text = format_item(fmt_tr, plugin.underscore_format, plugin.hash_format) if plugin.show_format and fmt_tr else ""
    if plugin.ona_clarify and fmt_raw == "ONA":
        eps = data.get("episodes") if data else None
        ona = "фильм" if eps == 1 else ("сериал" if eps and eps > 1 else "")
        if ona:
            ot = (mapping.universal_mapping.get("formats_extra") or {}).get(ona, [ona])[0]
            fmt_text += " " + format_item(ot, plugin.underscore_format, plugin.hash_format)
    dem_raw = ""
    if data and "tags" in data:
        for tag in data["tags"]:
            if tag.get("rank", 0) > 90 and tag["name"] in ("Shounen", "Shoujo", "Seinen", "Josei", "Kids"):
                dem_raw = tag["name"]
                break
    dem_tr = (mapping.universal_mapping.get("demographics") or {}).get(dem_raw, [dem_raw])[0] if dem_raw else "отсутствует"
    dem_text = format_item(dem_tr, False, plugin.hash_demographic) if plugin.show_demographic and dem_tr else ""
    genres_str = process_genres(plugin, data, mapping)
    tags_str = process_tags(plugin, data, mapping)
    score = ""
    if plugin.show_score:
        if data and data.get("averageScore") is not None:
            score = f"{data.get('averageScore') / 10:.1f}/10"
        elif shiki_data and shiki_data.get("score"):
            try:
                score = f"{float(shiki_data.get('score')):.1f}/10"
            except Exception:
                score = ""
    st_tr = (mapping.universal_mapping.get("status") or {}).get(st_raw, [st_raw.lower() if st_raw else "неизвестно"])[0] if st_raw else ""
    st_text = format_item(st_tr, plugin.underscore_status, plugin.hash_status) if plugin.show_status and st_tr else ""
    dur = f"{data.get('duration', '?')} мин." if data and data.get("duration") and plugin.show_duration else ""
    src_raw = data.get("source") if data else ""
    src_tr = (mapping.universal_mapping.get("source") or {}).get(src_raw, [src_raw.lower() if src_raw else "?"])[0] if src_raw else ""
    src_text = format_item(src_tr, plugin.underscore_source, plugin.hash_source) if plugin.show_source and src_tr else ""
    studs = [s["name"] for s in data.get("studios", {}).get("nodes", [])] if data and data.get("studios") and plugin.show_studios else []
    stud_f = [format_item(sn, plugin.underscore_studios, plugin.hash_studios) for sn in studs]
    studios = ", ".join(stud_f) if plugin.comma_studios else " ".join(stud_f)
    link1 = f'<a href="https://anilist.co/anime/{data.get("id")}">{plugin.anilist_link_text}</a>' if plugin.show_link_in_full and data and data.get("id") else ""
    link2 = f'<a href="https://shikimori.one/animes/{shiki_data.get("id")}">{plugin.shikimori_link_text}</a>' if plugin.show_shikimori_link and shiki_data and shiki_data.get("id") else ""
    anime_label = "#аниме" if plugin.show_hash_anime and plugin.show_anime_label else ("аниме" if plugin.show_anime_label else "")
    desc = get_description(plugin, data, shiki_data, force=plugin.description_in_card)
    if plugin.description_in_card and desc and plugin.show_description:
        desc = f"<blockquote expandable>{desc}</blockquote>"
    else:
        desc = ""
    year_str = f"{year}г." if year and plugin.show_year_g else year
    vd = {
        "preview": preview, "a": anime_label,
        "ru1": f"<code>{main_ru}</code>" if main_ru else "",
        "ru2": f"<code>{other_ru[0]}</code>" if len(other_ru) > 0 else "",
        "ru3": f"<code>{other_ru[1]}</code>" if len(other_ru) > 1 else "",
        "ru4": f"<code>{other_ru[2]}</code>" if len(other_ru) > 2 else "",
        "ru5": f"<code>{other_ru[3]}</code>" if len(other_ru) > 3 else "",
        "en1": f"<code>{main_en}</code>" if main_en else "",
        "en2": f"<code>{other_en[0]}</code>" if len(other_en) > 0 else "",
        "en3": f"<code>{other_en[1]}</code>" if len(other_en) > 1 else "",
        "en4": f"<code>{other_en[2]}</code>" if len(other_en) > 2 else "",
        "en5": f"<code>{other_en[3]}</code>" if len(other_en) > 3 else "",
        "flag": flag, "country": country_text, "season": season, "year": year_str,
        "format": fmt_text, "audience": dem_text, "genres": genres_str, "tags": tags_str,
        "episodes": ep_str, "score": score, "status": st_text, "duration": dur,
        "source": src_text, "studios": studios, "link1": link1, "link2": link2, "description": desc,
    }
    try:
        result = template.format(**vd)
    except Exception as e:
        log(f"[ANI] Template format error: {e}")
        result = "Ошибка в шаблоне карточки"
    return clean_template_output(result, vd, plugin.empty_ph_space_mode)

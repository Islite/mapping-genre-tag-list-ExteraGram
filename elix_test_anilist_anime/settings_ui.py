from client_utils import run_on_queue
from ui.settings import Divider, Header, Input, Selector, Switch, Text
from android_utils import run_on_ui_thread
from client_utils import get_last_fragment
from ui.bulletin import BulletinHelper
from ui.alert import AlertDialogBuilder

from constants import DEFAULT_MAPPING, DEFAULT_TEMPLATE
from utils import gb


def make_switch(plugin, key, text, default, store=None, prefix=None):
    def oc(val, k=key, s=store, p=prefix):
        if s is not None:
            s[k] = bool(val)
            plugin.set_setting(f"{p}{k}", bool(val))
        else:
            plugin.set_setting(key, bool(val))
            plugin.update_settings()
    full_key = key if store is None else f"{prefix}{key}"
    return Switch(key=full_key, text=text, default=default, on_change=oc, link_alias=full_key)


def build_sep_switches(plugin, mapping, scope, kind=None):
    if kind is None:
        return [
            make_switch(
                plugin, key, mapping.separator_labels.get(key, key),
                mapping.separator_enabled.get(key, True),
                mapping.separator_enabled, "sep_enabled_",
            )
            for key in mapping.separator_keys if mapping.sep_matches_scope(key, scope)
        ]
    prefix = {"hash": "hash_sep_", "under": "underscore_sep_", "comma": "comma_sep_"}[kind]
    store = {"hash": mapping.sep_hash, "under": mapping.sep_under, "comma": mapping.sep_comma}[kind]
    mark = {"hash": "# ", "under": "_ ", "comma": ", "}[kind]
    return [
        make_switch(
            plugin, key, f"{mark}{mapping.separator_labels.get(key, key)}",
            store.get(key, True), store, prefix,
        )
        for key in mapping.separator_keys if mapping.sep_matches_scope(key, scope)
    ]


def build_format_section(plugin, mapping, kind):
    plugin.update_settings()
    has = bool(mapping.separator_keys)
    cfg = {
        "hash": {
            "prefix": "# ",
            "master_g": ("hash_genres", "отображение жанров"),
            "main_g": ("hash_genres_main", "жанры"),
            "unlist_g": ("hash_genres_unlisted", "прочие жанры"),
            "master_t": ("hash_tags", "отображение тегов"),
            "main_t": ("hash_tags_main", "теги"),
            "unlist_t": ("hash_tags_unlisted", "прочие теги"),
            "top": [
                ("show_hash_anime", "# аниме"), ("hash_country", "# страна"), ("hash_format", "# формат"),
                ("hash_demographic", "# демография"), ("hash_studios", "# студии"),
                ("hash_source", "# источник"), ("hash_status", "# статус"),
            ],
        },
        "under": {
            "prefix": "_ ",
            "master_g": ("underscore_genres", "отображение жанров"),
            "main_g": ("underscore_genres_main", "жанры"),
            "unlist_g": ("underscore_genres_unlisted", "прочие жанры"),
            "master_t": ("underscore_tags", "отображение тегов"),
            "main_t": ("underscore_tags_main", "Теги"),
            "unlist_t": ("underscore_tags_unlisted", "прочие теги"),
            "top": [
                ("underscore_format", "_ формат"), ("underscore_studios", "_ студии"),
                ("underscore_source", "_ источник"), ("underscore_status", "_ статус"),
            ],
        },
        "comma": {
            "prefix": ", ",
            "master_g": ("comma_genres", "отображение жанров"),
            "main_g": ("comma_genres_main", "жанры"),
            "unlist_g": ("comma_genres_unlisted", "прочие жанры"),
            "master_t": ("comma_tags", "отображение тегов"),
            "main_t": ("comma_tags_main", "теги"),
            "unlist_t": ("comma_tags_unlisted", "прочие теги"),
            "top": [],
            "extra": [("comma_studios", ", студии")],
        },
    }[kind]
    items = []
    for key, text in cfg["top"]:
        items.append(make_switch(plugin, key, text, getattr(plugin, key)))
    if cfg["top"]:
        items.append(Divider())
    mg_key, mg_text = cfg["master_g"]
    items.append(make_switch(
        plugin, mg_key,
        f"{cfg['prefix']}{mg_text}" if kind != "hash" else f"# {mg_text}",
        getattr(plugin, mg_key),
    ))
    if has:
        main_key, main_text = cfg["main_g"]
        items.append(make_switch(
            plugin, main_key,
            f"{cfg['prefix']}{main_text}" if kind != "hash" else f"# {main_text}",
            getattr(plugin, main_key),
        ))
        items.extend(build_sep_switches(plugin, mapping, "genres", kind))
    ug_key, ug_text = cfg["unlist_g"]
    items.append(make_switch(
        plugin, ug_key,
        f"{cfg['prefix']}{ug_text}" if kind != "hash" else f"# {ug_text}",
        getattr(plugin, ug_key),
    ))
    items.append(Divider())
    mt_key, mt_text = cfg["master_t"]
    items.append(make_switch(
        plugin, mt_key,
        f"{cfg['prefix']}{mt_text}" if kind != "hash" else f"# {mt_text}",
        getattr(plugin, mt_key),
    ))
    if has:
        main_t_key, main_t_text = cfg["main_t"]
        items.append(make_switch(
            plugin, main_t_key,
            f"{cfg['prefix']}{main_t_text}" if kind != "hash" else f"# {main_t_text}",
            getattr(plugin, main_t_key),
        ))
        items.extend(build_sep_switches(plugin, mapping, "tags", kind))
    ut_key, ut_text = cfg["unlist_t"]
    items.append(make_switch(
        plugin, ut_key,
        f"{cfg['prefix']}{ut_text}" if kind != "hash" else f"# {ut_text}",
        getattr(plugin, ut_key),
    ))
    if cfg.get("extra"):
        items.append(Divider())
        for key, text in cfg["extra"]:
            items.append(make_switch(plugin, key, text, getattr(plugin, key)))
    return items


def build_display_fields(plugin, mapping):
    plugin.update_settings()
    has = bool(mapping.separator_keys)
    items = [
        Divider(),
        make_switch(plugin, "show_anime_label", "Аниме", plugin.show_anime_label),
        make_switch(plugin, "show_flag", "Флаг страны", plugin.show_flag),
        make_switch(plugin, "show_country", "Название страны", plugin.show_country),
        make_switch(plugin, "show_season", "Сезон", plugin.show_season),
        make_switch(plugin, "show_year", "Год", plugin.show_year),
        make_switch(plugin, "show_year_g", "г.", plugin.show_year_g),
        make_switch(plugin, "show_format", "Формат", plugin.show_format),
        make_switch(plugin, "show_demographic", "Целевая аудитория", plugin.show_demographic),
        make_switch(plugin, "show_episodes", "Серии", plugin.show_episodes),
        make_switch(plugin, "show_score", "Оценка", plugin.show_score),
        make_switch(plugin, "show_status", "Статус", plugin.show_status),
        make_switch(plugin, "show_duration", "Длительность", plugin.show_duration),
        make_switch(plugin, "show_source", "Источник", plugin.show_source),
        make_switch(plugin, "show_studios", "Студии", plugin.show_studios),
        Divider(),
        make_switch(plugin, "show_genres", "Отображение жанров", plugin.show_genres),
    ]
    if has:
        items.append(make_switch(plugin, "show_genres_main", "Жанры", plugin.show_genres_main))
        items.extend(build_sep_switches(plugin, mapping, "genres"))
    items += [
        make_switch(plugin, "show_genres_unlisted", "прочие жанры", plugin.show_genres_unlisted),
        Divider(),
        make_switch(plugin, "show_tags", "Отображение тегов", plugin.show_tags),
    ]
    if has:
        items.append(make_switch(plugin, "show_tags_main", "Теги", plugin.show_tags_main))
        items.extend(build_sep_switches(plugin, mapping, "tags"))
    items += [
        make_switch(plugin, "show_tags_unlisted", "прочие теги", plugin.show_tags_unlisted),
        Divider(),
        make_switch(plugin, "show_link_in_full", "Ссылка на AniList", plugin.show_link_in_full),
        make_switch(plugin, "show_shikimori_link", "Ссылка на Shikimori", plugin.show_shikimori_link),
        Divider(),
        make_switch(plugin, "show_description", "Описание", plugin.show_description),
        Selector(
            key="description_in_card", text="Способ отправки описания", default=0,
            items=["В карточке", "Отдельно"],
            on_change=lambda _: plugin.update_settings(), link_alias="description_in_card",
        ),
        Selector(
            key="desc_source", text="Источник описания", default=0,
            items=["Shikimori", "AniList"],
            on_change=lambda _: plugin.update_settings(), link_alias="desc_source",
        ),
    ]
    return items


def show_info_alert(title, text, positive_button="Закрыть"):
    fragment = get_last_fragment()
    if not fragment or not fragment.getParentActivity():
        return
    activity = fragment.getParentActivity()
    builder = AlertDialogBuilder(activity, AlertDialogBuilder.ALERT_TYPE_MESSAGE)
    builder.set_title(title)
    builder.set_message(text)
    builder.set_positive_button(positive_button, lambda d, w: run_on_ui_thread(builder.dismiss))
    run_on_ui_thread(lambda: (builder.show(), builder.set_cancelable(True), builder.set_canceled_on_touch_outside(True)))


def build_preview(plugin, mapping):
    def fm(t, us, hs):
        if not t:
            return ""
        if hs and not us:
            t = t.replace(" ", "")
        elif us:
            t = t.replace(" ", "_")
        return ("#" + t) if hs else t

    has = bool(mapping.separator_keys)
    gl, tl = [], []
    if plugin.show_genres:
        if plugin.show_genres_main or not has:
            g = fm("жанр", plugin.underscore_genres and plugin.underscore_genres_main, plugin.hash_genres and plugin.hash_genres_main)
            if g:
                gl.append(g)
        for k in mapping.separator_keys:
            if mapping.separator_scope.get(k) not in ("genres", "both") or not mapping.separator_enabled.get(k, True):
                continue
            lab = mapping.separator_labels.get(k, k)
            prev = mapping.separator_previews.get(k, "жанр")
            m = fm(prev, plugin.underscore_genres and mapping.sep_under.get(k, True), plugin.hash_genres and mapping.sep_hash.get(k, True))
            gl.append(f"{lab}: {m}" if plugin.show_separators else m)
        if plugin.show_genres_unlisted:
            g = fm("прочий жанр", plugin.underscore_genres and plugin.underscore_genres_unlisted, plugin.hash_genres and plugin.hash_genres_unlisted)
            if g:
                gl.append(f"прочий жанр: {g}" if plugin.show_separators else g)
    if plugin.show_tags:
        if plugin.show_tags_main or not has:
            t = fm("тег", plugin.underscore_tags and plugin.underscore_tags_main, plugin.hash_tags and plugin.hash_tags_main)
            if t:
                tl.append(t)
        for k in mapping.separator_keys:
            if mapping.separator_scope.get(k) not in ("tags", "both") or not mapping.separator_enabled.get(k, True):
                continue
            lab = mapping.separator_labels.get(k, k)
            prev = mapping.separator_previews.get(k, "тег")
            m = fm(prev, plugin.underscore_tags and mapping.sep_under.get(k, True), plugin.hash_tags and mapping.sep_hash.get(k, True))
            tl.append(f"{lab}: {m}" if plugin.show_separators else m)
        if plugin.show_tags_unlisted:
            t = fm("прочий тег", plugin.underscore_tags and plugin.underscore_tags_unlisted, plugin.hash_tags and plugin.hash_tags_unlisted)
            if t:
                tl.append(f"прочий тег: {t}" if plugin.show_separators else t)
    gs = "\n".join(gl) if plugin.show_separators else " ".join(gl)
    ts = "\n".join(tl) if plugin.show_separators else " ".join(tl)
    ap = "#аниме" if plugin.show_hash_anime and plugin.show_anime_label else ("аниме" if plugin.show_anime_label else "")
    ft = fm("сериал", plugin.underscore_format, plugin.hash_format) if plugin.show_format else ""
    mv = {
        "preview": "", "a": ap,
        "ru1": "Русское название" if plugin.extra_ru_count >= 1 else "",
        "ru2": "Русское название 2" if plugin.extra_ru_count >= 2 else "",
        "ru3": "Русское название 3" if plugin.extra_ru_count >= 3 else "",
        "ru4": "Русское название 4" if plugin.extra_ru_count >= 4 else "",
        "ru5": "Русское название 5" if plugin.extra_ru_count >= 5 else "",
        "en1": "English Title" if plugin.extra_en_count >= 1 else "",
        "en2": "English Title 2" if plugin.extra_en_count >= 2 else "",
        "en3": "English Title 3" if plugin.extra_en_count >= 3 else "",
        "en4": "English Title 4" if plugin.extra_en_count >= 4 else "",
        "en5": "English Title 5" if plugin.extra_en_count >= 5 else "",
        "flag": "🇯🇵" if plugin.show_flag else "",
        "country": fm("Япония", False, plugin.hash_country) if plugin.show_country else "",
        "season": "лето" if plugin.show_season else "",
        "year": "2018г." if plugin.show_year and plugin.show_year_g else ("2018" if plugin.show_year else ""),
        "format": ft,
        "audience": fm("сёнэн", False, plugin.hash_demographic) if plugin.show_demographic else "",
        "genres": gs, "tags": ts,
        "episodes": "8/18 эп." if plugin.show_episodes else "",
        "score": "8.88/10" if plugin.show_score else "",
        "status": fm("выходит", plugin.underscore_status, plugin.hash_status) if plugin.show_status else "",
        "duration": "24 мин." if plugin.show_duration else "",
        "source": fm("оригинал", plugin.underscore_source, plugin.hash_source) if plugin.show_source else "",
        "studios": fm("MAPPA", plugin.underscore_studios, plugin.hash_studios) if plugin.show_studios else "",
        "link1": plugin.anilist_link_text if plugin.show_link_in_full else "",
        "link2": plugin.shikimori_link_text if plugin.show_shikimori_link else "",
        "description": "Описание тайтла." if plugin.show_description and plugin.description_in_card else "",
    }
    try:
        from formatter import clean_template_output
        return clean_template_output(plugin.card_template.format(**mv), mv, plugin.empty_ph_space_mode)
    except KeyError as e:
        return f"Ошибка в шаблоне: отсутствует {e}"


def create_settings(plugin, mapping, clear_search_cache, full_clear_cache):
    run_on_queue(plugin.update_settings)

    def oc(_):
        run_on_queue(plugin.update_settings)

    def on_map(_=None):
        run_on_queue(lambda: (mapping.load(force=True), _try_reload(plugin)))

    def _try_reload(p):
        try:
            p.set_setting("__internal_dummy__", True, reload_settings=True)
        except Exception:
            pass

    def prev_click(_):
        show_info_alert("Предпросмотр:", build_preview(plugin, mapping))

    return [
        Input(
            key="anime_commands", icon="msg_search", text="Команды аниме",
            default=".а, .аниме, .a, .anime", subtext="Поиск по названию и ID",
            on_change=oc, link_alias="anime_commands",
        ),
        Input(
            key="tag_commands", icon="msg_pinnedlist", text="Фильтр по жанрам",
            default="т, t", subtext="Фильтрация аниме по жанру или тегу\n\nПрименение:\n.а т жанры/теги",
            on_change=oc, link_alias="tag_commands",
        ),
        Divider(),
        Text(icon="navbar_search_tag", text="Настройки поиска", create_sub_fragment=lambda: [
            Switch(key="use_anilist", text="Поиск через AniList", default=True, on_change=oc, link_alias="use_anilist"),
            Switch(key="use_shikimori", text="Поиск через Shikimori", default=True, on_change=oc, link_alias="use_shikimori"),
            Divider(),
            Selector(key="primary_source", text="Основной поисковик", default=0, items=["AniList", "Shikimori"], on_change=oc, link_alias="primary_source"),
            Selector(key="search_ui_mode", text="Режим поиска", default=0, items=["Окно выбора", "Первое совпадение"], on_change=oc, link_alias="search_ui_mode"),
            Selector(key="direct_id_source", text="Источник ID", default=0, items=["AniList", "Shikimori"], on_change=oc, link_alias="direct_id_source"),
            Divider(),
            Text(icon="files_internal", text="Маппинги", create_sub_fragment=lambda: [
                Input(
                    key="universal_mapping", text="Универсальный маппинг", default=DEFAULT_MAPPING,
                    subtext="JSON или URL. Пусто = без перевода и разделителей",
                    on_change=on_map, link_alias="universal_mapping",
                ),
            ]),
        ]),
        Text(icon="menu_edit_appearance", text="Настройки отображения", create_sub_fragment=lambda: [
            Text(text="Предпросмотр", icon="msg_info", on_click=prev_click),
            Divider(),
            Input(
                key="card_template", icon="menu_edit_appearance", text="Шаблон", default=DEFAULT_TEMPLATE,
                subtext="Плейсхолдеры: {preview} {a} {ru1..5} {en1..5} {flag} {country} {season} {year} {format} {audience} {genres} {tags} {episodes} {score} {status} {duration} {source} {studios} {link1} {link2} {description}",
                on_change=oc, link_alias="card_template",
            ),
            Divider(),
            Text(icon="msg_settings", text="Доп. настройки", create_sub_fragment=lambda: [
                Header("Настройки доп. ссылок"),
                Input(key="anilist_link_text", text="Текст ссылки на AniList", default="AniList", on_change=oc, link_alias="anilist_link_text"),
                Input(key="shikimori_link_text", text="Текст ссылки на Shikimori", default="Shikimori", on_change=oc, link_alias="shikimori_link_text"),
                Header("Доп. переключатели"),
                Switch(key="spoiler_format", text="Спойлерные теги", default=True, on_change=oc, link_alias="spoiler_format"),
                Switch(key="ona_clarify", text="Уточнять ONA", default=False, on_change=oc, link_alias="ona_clarify"),
                Switch(key="show_separators", text="Разделители", default=True, on_change=oc, link_alias="show_separators"),
                Header("Доп. названия"),
                Selector(key="extra_ru_count", text="Max русских названий", default=1, items=["0", "1", "2", "3", "4", "5"], on_change=oc, link_alias="extra_ru_count"),
                Selector(key="extra_en_count", text="Max английских названий", default=1, items=["0", "1", "2", "3", "4", "5"], on_change=oc, link_alias="extra_en_count"),
            ]),
            Divider(),
            Text(icon="msg_reorder", text="Отображение полей", create_sub_fragment=lambda: build_display_fields(plugin, mapping)),
            Text(icon="msg_filled_general", text="Отображение #", create_sub_fragment=lambda: build_format_section(plugin, mapping, "hash")),
            Text(icon="menu_tag_edit", text="Отображение _", create_sub_fragment=lambda: build_format_section(plugin, mapping, "under")),
            Text(icon="ic_feed", text="Отображение ,", create_sub_fragment=lambda: build_format_section(plugin, mapping, "comma")),
        ]),
        Divider(),
        Text(icon="msg_filled_general", text="Форматирование текста", create_sub_fragment=lambda: [
            Header("Основная карточка"),
            Switch(key="enable_html_card", text="Включить HTML", default=True, on_change=oc, link_alias="enable_html_card"),
            Divider(),
            Header("Отдельное описание"),
            Switch(key="enable_html_desc", text="Включить HTML", default=True, on_change=oc, link_alias="enable_html_desc"),
            Divider(),
            Header("Очистка пустых плейсхолдеров"),
            Selector(
                key="empty_ph_space_mode", text="Удаление пробела", default=0,
                items=["После плейсхолдера", "До плейсхолдера"],
                on_change=oc, link_alias="empty_ph_space_mode",
            ),
        ]),
        Divider(),
        Text(icon="msg_retry", text="Очистить кэш поиска", on_click=lambda _: clear_search_cache()),
        Text(icon="msg_retry", text="Полная очистка кэша плагина", on_click=lambda _: full_clear_cache()),
    ]
import json

import requests
from android_utils import log

from constants import DEFAULT_MAPPING
from utils import gb


class MappingState:
    def __init__(self, plugin):
        self.plugin = plugin
        self.universal_mapping = {}
        self.separator_keys = []
        self.separator_labels = {}
        self.separator_previews = {}
        self.separator_scope = {}
        self.separator_enabled = {}
        self.sep_hash = {}
        self.sep_under = {}
        self.sep_comma = {}
        self._last_mapping_raw = None
        self._shiki_alias = None
        self._anilist_alias = None

    def load(self, force=False):
        raw = (self.plugin.get_setting("universal_mapping") or DEFAULT_MAPPING).strip()
        if not force and raw == self._last_mapping_raw:
            return
        self._last_mapping_raw = raw
        data = {}
        if raw:
            try:
                if raw.startswith(("http://", "https://")):
                    r = requests.get(raw, timeout=8, headers={"User-Agent": "ANI"})
                    r.raise_for_status()
                    data = r.json()
                else:
                    data = json.loads(raw)
            except Exception as e:
                log(f"[ANI] Mapping load/parse failed: {e}")
                data = {}
        self.universal_mapping = data if isinstance(data, dict) else {}
        self._extract_separators()
        self._shiki_alias = self._anilist_alias = None

    def _extract_separators(self):
        sep = self.universal_mapping.get("separator", {})
        self.separator_keys = []
        self.separator_labels = {}
        self.separator_previews = {}
        self.separator_scope = {}
        if not isinstance(sep, dict):
            return
        g_set = set(self.universal_mapping.get("sorting_genres", self.universal_mapping.get("ordered_genres", [])))
        t_set = set(self.universal_mapping.get("sorting_tags", self.universal_mapping.get("ordered_tags", [])))
        for key, value in sep.items():
            if not key.startswith("separator_"):
                continue
            if isinstance(value, dict):
                label = str(value.get("label", key)).strip()
                preview = str(value.get("preview", label)).strip()
            else:
                label = str(value).strip()
                preview = label
            if not label:
                label = key.replace("separator_", "").replace("_", " ")
            self.separator_keys.append(key)
            self.separator_labels[key] = label
            self.separator_previews[key] = preview or label
            in_g = key in g_set
            in_t = key in t_set
            self.separator_scope[key] = "both" if in_g and in_t else ("genres" if in_g else ("tags" if in_t else "unknown"))
            for store, pref, defv in (
                (self.separator_enabled, "sep_enabled_", True),
                (self.sep_hash, "hash_sep_", True),
                (self.sep_under, "underscore_sep_", True),
                (self.sep_comma, "comma_sep_", True),
            ):
                if key not in store:
                    store[key] = gb(self.plugin, f"{pref}{key}", defv)

    def sep_matches_scope(self, key, scope):
        sc = self.separator_scope.get(key, "unknown")
        if scope == "tags":
            return sc in ("tags", "both")
        if scope == "genres":
            return sc in ("genres", "both")
        return True

    def ensure_aliases(self):
        if self._shiki_alias is not None:
            return
        self._shiki_alias = {}
        for en_name, meta in (self.universal_mapping.get("shikimori") or {}).items():
            if not isinstance(meta, dict):
                continue
            gid = meta.get("id")
            if gid is None:
                continue
            try:
                gid = int(gid)
            except (TypeError, ValueError):
                continue
            rus = meta.get("russian") or []
            if not isinstance(rus, list):
                rus = [rus] if rus else []
            entry = {"id": gid, "en": en_name}
            self._shiki_alias[en_name.lower()] = entry
            for a in rus:
                if a:
                    self._shiki_alias[str(a).lower()] = entry
        self._anilist_alias = {}
        for section in ("main_genres", "additional_genres", "main_tags", "additional_tags"):
            kind = "tag" if "tag" in section else "genre"
            for en_name, aliases in (self.universal_mapping.get(section) or {}).items():
                alias_list = aliases if isinstance(aliases, list) else ([aliases] if aliases else [])
                entry = {"en": en_name, "kind": kind}
                self._anilist_alias[en_name.lower()] = entry
                for a in alias_list:
                    if a:
                        self._anilist_alias[str(a).lower()] = entry

    def resolve_shiki_genre(self, query):
        self.ensure_aliases()
        q = query.lower().strip()
        if q in self._shiki_alias:
            e = self._shiki_alias[q]
            return e["id"], e["en"]
        for key, e in self._shiki_alias.items():
            if q in key or key in q:
                return e["id"], e["en"]
        return None, None

    def resolve_anilist_genre(self, query):
        self.ensure_aliases()
        q = query.lower().strip()
        if q in self._anilist_alias:
            e = self._anilist_alias[q]
            return e["en"], e["kind"]
        for key, e in self._anilist_alias.items():
            if q in key or key in q:
                return e["en"], e["kind"]
        return None, None
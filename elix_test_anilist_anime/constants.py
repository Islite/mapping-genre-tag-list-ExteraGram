ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"
SHIKIMORI_API_ANIMES = "https://shikimori.one/api/animes"
DEFAULT_MAPPING = "https://raw.githubusercontent.com/Islite/mapping-genre-tag-list-ExteraGram/refs/heads/main/mapping_all_list.json"

QUERIES = {
    "search": "query($search:String){Page(perPage:1){media(search:$search,type:ANIME,sort:SEARCH_MATCH){id title{romaji english native userPreferred}synonyms countryOfOrigin season seasonYear format genres tags{name rank isMediaSpoiler}episodes status description averageScore duration source studios{nodes{name}}coverImage{large}}}}",
    "media": "query($id:Int){Media(id:$id,type:ANIME){id title{romaji english native userPreferred}synonyms countryOfOrigin season seasonYear format genres tags{name rank isMediaSpoiler}episodes status description averageScore duration source studios{nodes{name}}coverImage{large}}}",
    "mal": "query($idMal:Int){Media(idMal:$idMal,type:ANIME){id title{romaji english native userPreferred}synonyms countryOfOrigin season seasonYear format genres tags{name rank isMediaSpoiler}episodes status description averageScore duration source studios{nodes{name}}coverImage{large}}}",
    "multi_search": "query($q:String){Page(page:1,perPage:50){media(search:$q,type:ANIME){id title{romaji english}genres coverImage{large}format averageScore countryOfOrigin season seasonYear}}}",
    "multi_genre": "query($g:String){Page(page:1,perPage:50){media(genre:$g,type:ANIME,sort:POPULARITY_DESC){id title{romaji english}genres coverImage{large}format averageScore countryOfOrigin season seasonYear}}}",
    "multi_tag": "query($g:String){Page(page:1,perPage:50){media(tag:$g,type:ANIME,sort:POPULARITY_DESC){id title{romaji english}genres coverImage{large}format averageScore countryOfOrigin season seasonYear}}}",
}

DEFAULT_TEMPLATE = (
    "{preview}{a} {ru1}\n| {ru2}\n| {ru3}\n| {ru4}\n| {ru5}\n"
    "| {en1}\n| {en2}\n| {en3}\n| {en4}\n| {en5}\n"
    "{flag}{country}, {season} {year}\nформат {format}\nцелевая аудитория {audience}\n"
    "жанры: {genres}\nтеги: {tags}\n{link1} {link2}\n{description}\n"
    "студии: {studios}\nоригинал: {source}\nпродолжительность серии: {duration}\n"
    "статус: {status}\nрейтинг: {score}\nэпизоды: {episodes}"
)

BOOL_FLAGS = (
    "use_shikimori", "use_anilist", "show_flag", "show_country",
    "show_season", "show_year", "show_year_g", "show_format", "show_demographic", "show_genres", "show_genres_main",
    "show_genres_unlisted", "show_tags", "show_tags_main", "show_tags_unlisted", "spoiler_format", "show_anime_label",
    "show_hash_anime", "show_description", "show_episodes", "enable_html_card", "enable_html_desc", "ona_clarify",
    "show_score", "show_status", "show_duration", "show_source", "show_studios", "show_link_in_full",
    "show_shikimori_link", "show_separators", "hash_country", "hash_format", "hash_demographic", "hash_studios",
    "hash_source", "hash_status", "hash_genres", "hash_genres_main", "hash_genres_unlisted", "hash_tags",
    "hash_tags_main", "hash_tags_unlisted", "underscore_format", "underscore_studios", "underscore_source",
    "underscore_status", "underscore_genres", "underscore_genres_main", "underscore_genres_unlisted",
    "underscore_tags", "underscore_tags_main", "underscore_tags_unlisted", "comma_genres", "comma_genres_main",
    "comma_genres_unlisted", "comma_tags", "comma_tags_main", "comma_tags_unlisted", "comma_studios",
)

BOOL_DEFAULTS_FALSE = frozenset({
    "show_description", "ona_clarify", "comma_genres", "comma_tags", "comma_studios",
})
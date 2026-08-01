from android.graphics.drawable import ColorDrawable
from android.util import TypedValue
from android.view import Gravity
from android.widget import FrameLayout, LinearLayout, ScrollView, TextView
from android_utils import OnClickListener, run_on_ui_thread
from client_utils import get_last_fragment, run_on_queue
from org.telegram.messenger import AndroidUtilities
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import BackupImageView, LayoutHelper
from org.telegram.ui.ActionBar import BottomSheet


def show_popup(results, query, use_shiki, is_genre, account, base, on_select):
    frag = get_last_fragment()
    context = frag.getParentActivity() if frag else None
    if not context:
        return
    api_name = "Shikimori" if use_shiki else "AniList"
    display_q = f"#{query}" if is_genre else query
    title_text = f"Поиск аниме ({api_name}): {display_q}"
    sheet = BottomSheet(context, True)
    sheet.setAllowNestedScroll(True)
    sheet.setCanDismissWithSwipe(False)
    main = LinearLayout(context)
    main.setOrientation(LinearLayout.VERTICAL)
    main.setPadding(AndroidUtilities.dp(20), AndroidUtilities.dp(16), AndroidUtilities.dp(20), 0)
    main.setBackgroundColor(Theme.getColor(Theme.key_dialogBackground))
    title = TextView(context)
    title.setText(title_text)
    title.setTypeface(AndroidUtilities.getTypeface("fonts/rmedium.ttf"))
    title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 22)
    title.setGravity(Gravity.CENTER)
    title.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
    main.addView(title, LayoutHelper.createLinear(-1, -2, Gravity.CENTER, 0, 0, 0, 12))
    scroll = ScrollView(context)
    content = LinearLayout(context)
    content.setOrientation(LinearLayout.VERTICAL)
    content.setPadding(0, 0, 0, AndroidUtilities.dp(8))
    for i, res in enumerate(results):
        content.addView(create_row(res, context, sheet, account, base, on_select), LayoutHelper.createLinear(-1, -2))
        if i < len(results) - 1:
            divider = LinearLayout(context)
            divider.setBackgroundColor(Theme.getColor(Theme.key_divider))
            content.addView(divider, LayoutHelper.createLinear(-1, 1))
    scroll.addView(content)
    main.addView(scroll, LayoutHelper.createLinear(-1, 0, 1.0))
    close_frame = FrameLayout(context)
    close_frame.setBackground(Theme.createSimpleSelectorRoundRectDrawable(
        AndroidUtilities.dp(15),
        Theme.getColor(Theme.key_featuredStickers_addButton),
        Theme.getColor(Theme.key_featuredStickers_addButtonPressed),
    ))
    close_frame.setPadding(AndroidUtilities.dp(24), AndroidUtilities.dp(12), AndroidUtilities.dp(24), AndroidUtilities.dp(12))
    close_tv = TextView(context)
    close_tv.setText("Закрыть")
    close_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 17)
    close_tv.setTypeface(AndroidUtilities.getTypeface("fonts/rmedium.ttf"))
    close_tv.setGravity(Gravity.CENTER)
    close_tv.setTextColor(Theme.getColor(Theme.key_featuredStickers_buttonText))
    close_frame.addView(close_tv, LayoutHelper.createFrame(-1, -2, Gravity.CENTER))
    close_frame.setOnClickListener(OnClickListener(lambda v: sheet.dismiss()))
    buttons = LinearLayout(context)
    buttons.setOrientation(LinearLayout.HORIZONTAL)
    buttons.setGravity(Gravity.CENTER_HORIZONTAL)
    buttons.addView(close_frame, LayoutHelper.createLinear(-1, -2))
    main.addView(buttons, LayoutHelper.createLinear(-1, -2, Gravity.BOTTOM))
    sheet.setCustomView(main)
    sheet.show()


def create_row(res, context, sheet, account, base, on_select):
    row = LinearLayout(context)
    row.setOrientation(LinearLayout.HORIZONTAL)
    row.setPadding(AndroidUtilities.dp(12), AndroidUtilities.dp(12), AndroidUtilities.dp(12), AndroidUtilities.dp(12))
    row.setBackground(Theme.createSimpleSelectorRoundRectDrawable(
        AndroidUtilities.dp(12),
        Theme.getColor(Theme.key_dialogBackground),
        Theme.getColor(Theme.key_listSelector),
    ))
    row.setClickable(True)
    img = BackupImageView(context)
    img.setRoundRadius(AndroidUtilities.dp(8))
    placeholder = ColorDrawable(Theme.getColor(Theme.key_windowBackgroundGray))
    cover = res.get("cover_url")
    if cover:
        try:
            img.setImage(cover, None, placeholder)
        except Exception:
            img.setImageDrawable(placeholder)
    else:
        img.setImageDrawable(placeholder)
    row.addView(img, LayoutHelper.createLinear(64, 90, Gravity.CENTER_VERTICAL, 0, 0, AndroidUtilities.dp(12), 0))
    col = LinearLayout(context)
    col.setOrientation(LinearLayout.VERTICAL)
    title = TextView(context)
    title.setText(res["title"])
    title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
    title.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
    col.addView(title)
    type_score = TextView(context)
    type_score.setText(f"{res.get('type_ru', '')}, {res.get('score', '?')}/10")
    type_score.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
    type_score.setTextColor(Theme.getColor(Theme.key_dialogTextGray))
    col.addView(type_score)
    country_tv = TextView(context)
    country_tv.setText(res.get("country_line", ""))
    country_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
    country_tv.setTextColor(Theme.getColor(Theme.key_dialogTextGray))
    col.addView(country_tv)
    genres_list = res.get("genres") or []
    if genres_list:
        genres = TextView(context)
        genres.setText(", ".join(genres_list))
        genres.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
        genres.setTextColor(Theme.getColor(Theme.key_dialogTextGray))
        col.addView(genres)
    row.addView(col, LayoutHelper.createLinear(0, -2, 1.0))

    def on_click(v, r=res):
        sheet.dismiss()
        run_on_queue(lambda: on_select(r, account, base))

    row.setOnClickListener(OnClickListener(on_click))
    return row
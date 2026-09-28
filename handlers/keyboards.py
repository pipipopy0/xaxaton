from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from services.get_correct_time import get_correct_time
from handlers.answer_texts.TEXT import get_text


db = None


def add_back_button(builder: InlineKeyboardBuilder, max_id=None):

    text_back = get_text(
        key="back_btn",
        max_id=max_id,
        db=db
    )

    builder.row(
        CallbackButton(
            text=text_back,
            payload="back",
            db=db
        )
    )

    return builder.as_markup()


def get_support_inline_keyboard(max_id=None):
    text_support_btn = get_text(
        key="support_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        LinkButton(
            text=text_support_btn,
            url="https://t.me/pipipopy2"
        )
    )

    return add_back_button(builder, max_id=max_id)


def get_documents_inline_keyboard(max_id=None):
    text_terms_of_service = get_text(
        key="terms_of_service_text",
        max_id=max_id,
        db=db
    )

    text_privacy_policy = get_text(
        key="privacy_policy_text",
        max_id=max_id,
        db=db
    )

    link_terms_of_service = get_text(
        key="terms_of_service_link",
        max_id=max_id,
        db=db
    )

    link_privacy_policy = get_text(
        key="privacy_policy_link",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        LinkButton(
            text=text_terms_of_service,
            url=link_terms_of_service
        ),
        LinkButton(
            text=text_privacy_policy,
            url=link_privacy_policy
        )
    )

    return add_back_button(builder, max_id=max_id)


def get_settings_inline_keyboard(max_id=None):
    text_change_language = get_text(
        key="change_language",
        max_id=max_id,
        db=db
    )

    text_update_notifications_btn = get_text(
        key="update_notifications_btn",
        max_id=max_id,
        db=db
    )

    text_update_time_btn = get_text(
        key="update_time_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_update_time_btn,
            payload="update_time"
        )
    )

    builder.row(
        CallbackButton(
            text=text_update_notifications_btn,
            payload="update_notifications"
        )
    )

    builder.row(
        CallbackButton(
            text=text_change_language,
            payload="change_language"
        )
    )

    return add_back_button(builder, max_id=max_id)


def get_register_inline_keyboard(is_admin=False, max_id=None):
    text_what_is_kalendator = get_text(
        key="what_is_kalendator",
        max_id=max_id,
        db=db
    )

    text_connect_calendars = get_text(
        key="connect_calendars",
        max_id=max_id,
        db=db
    )

    text_support_btn = get_text(
        key="support_btn",
        max_id=max_id,
        db=db
    )

    text_admin_panel_btn = get_text(
        key="admin_panel_btn",
        max_id=max_id,
        db=db
    )

    text_settings_btn = get_text(
        key="settings_btn",
        max_id=max_id,
        db=db
    )

    text_documents_btn = get_text(
        key="documents_btn",
        max_id=max_id,
        db=db
    )

    text_manage_subscription = get_text(
        key="manage_subscription",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_what_is_kalendator,
            payload="first_info"
        )
    )

    builder.row(
        CallbackButton(
            text=text_manage_subscription,
            payload="manage_subscription"
        )
    )

    builder.row(
        CallbackButton(
            text=text_settings_btn,
            payload="settings"
        )
    )

    builder.row(
        CallbackButton(
            text=text_documents_btn,
            payload="documents"
        )
    )

    builder.row(
        CallbackButton(
            text=text_connect_calendars,
            payload="calendars_setup"
        )
    )

    builder.row(
        CallbackButton(
            text=text_support_btn,
            payload="support"
        )
    )

    if is_admin:
        builder.row(
            CallbackButton(
                text=text_admin_panel_btn,
                payload="admin_panel"
            )
        )

    return builder.as_markup()


def get_onboarding_start_inline_keyboard(max_id=None):
    text_timezone_btn = get_text(
        key="onboarding_timezone_btn",
        max_id=max_id,
        db=db
    )
    text_documents_btn = get_text(
        key="onboarding_documents_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text=text_timezone_btn,
            payload="onboarding_timezone"
        )
    )
    builder.row(
        CallbackButton(
            text=text_documents_btn,
            payload="documents"
        )
    )

    return builder.as_markup()


def get_onboarding_calendar_inline_keyboard(max_id=None):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text=get_text(
                key="onboarding_google_calendar_btn",
                max_id=max_id,
                db=db
            ),
            payload="onboarding_google_calendar"
        )
    )
    builder.row(
        CallbackButton(
            text=get_text(
                key="onboarding_apple_calendar_btn",
                max_id=max_id,
                db=db
            ),
            payload="onboarding_apple_calendar"
        )
    )
    builder.row(
        CallbackButton(
            text=get_text(
                key="onboarding_later_btn",
                max_id=max_id,
                db=db
            ),
            payload="onboarding_calendar_later"
        )
    )

    return builder.as_markup()


def _build_time_inline_keyboard(page=3, max_id=None):
    ITEMS_PER_PAGE = 5

    times = get_correct_time()

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    current_times = times[start:end]

    text_back_btn = get_text(
        key="prev_page_btn",
        max_id=max_id,
        db=db
    )

    text_forward_btn = get_text(
        key="next_page_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    for current_time in current_times:
        builder.row(
            CallbackButton(
                text=current_time["local_time"],
                payload=f"timezone:{current_time['offset']}"
            )
        )

    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            CallbackButton(
                text=text_back_btn,
                payload=f"page:{page - 1}"
            )
        )

    if end < len(times):
        nav_buttons.append(
            CallbackButton(
                text=text_forward_btn,
                payload=f"page:{page + 1}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder


def get_time_inline_keyboard(page=3, max_id=None):
    builder = _build_time_inline_keyboard(
        page=page,
        max_id=max_id
    )

    return builder.as_markup()


def get_time_inline_keyboard_with_back(page=3, max_id=None):
    builder = _build_time_inline_keyboard(
        page=page,
        max_id=max_id
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_delete_inline_keyboard(max_id=None):
    text_delete_data_btn = get_text(
        key="delete_data_btn",
        max_id=max_id,
        db=db
    )

    text_cancel_delete_btn = get_text(
        key="cancel_delete_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_delete_data_btn,
            payload="delete_data"
        )
    )

    builder.row(
        CallbackButton(
            text=text_cancel_delete_btn,
            payload="cancel_delete"
        )
    )

    return builder.as_markup()


def get_update_notifications_inline_keyboard(max_id=None):
    text_yes_btn = get_text(
        key="yes_btn",
        max_id=max_id,
        db=db
    )

    text_no_btn = get_text(
        key="no_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_yes_btn,
            payload="yes_update_notifications"
        ),
        CallbackButton(
            text=text_no_btn,
            payload="no_update_notifications"
        )
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_admin_inline_keyboard(max_id=None):
    text_admin_broadcast_btn = get_text(
        key="admin_broadcast_btn",
        max_id=max_id,
        db=db
    )

    text_admin_status_services = get_text(
        key="admin_status_services",
        max_id=max_id,
        db=db
    )

    text_admin_future_btn = get_text(
        key="admin_future_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_admin_broadcast_btn,
            payload="admin_update_notification"
        )
    )

    builder.row(
        CallbackButton(
            text=text_admin_status_services,
            payload="services_status"
        )
    )

    builder.row(
        CallbackButton(
            text=text_admin_future_btn,
            payload="passing"
        )
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_calendars_inline_keyboard(max_id=None):
    text_google_calendar_btn = get_text(
        key="google_calendar_btn",
        max_id=max_id,
        db=db
    )

    text_apple_calendar_btn = get_text(
        key="apple_calendar_btn",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_google_calendar_btn,
            payload="google_calendar"
        ),
        CallbackButton(
            text=text_apple_calendar_btn,
            payload="apple_calendar"
        )
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_inline_apple_app_specific_password_link(max_id=None):
    text_app_specific_password_link = get_text(
        key="apple_password_link",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        LinkButton(
            text=text_app_specific_password_link,
            url="https://account.apple.com"
        )
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_inline_google_app_specific_password_link(max_id=None):
    text_app_specific_password_link = get_text(
        key="google_password_link",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        LinkButton(
            text=text_app_specific_password_link,
            url="https://myaccount.google.com/apppasswords"
        )
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_inline_google_authorization(user_id, max_id=None):
    builder = InlineKeyboardBuilder()

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_inline_language_keyborad(max_id=None):
    text_russian = get_text(
        key="russian_language",
        max_id=max_id,
        db=db
    )

    text_english = get_text(
        key="english_language",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=text_russian,
            payload="russian_language"
        ),
        CallbackButton(
            text=text_english,
            payload="english_language"
        )
    )

    return add_back_button(
        builder,
        max_id=max_id
    )


def get_recconect_disconnect_calendar_keyboard(provider, max_id=None):
    text_reconnect = get_text(
        key="reconnect_calendar",
        max_id=max_id,
        db=db
    )

    text_disconnect = get_text(
        key="disconnect_calendar",
        max_id=max_id,
        db=db
    )

    builder = InlineKeyboardBuilder()

    if provider == "google":
        builder.row(
            CallbackButton(
                text=text_reconnect,
                payload="reconnect_google_calendar"
            ),
            CallbackButton(
                text=text_disconnect,
                payload="disconnect_google_calendar"
            )
        )

    elif provider == "apple":
        builder.row(
            CallbackButton(
                text=text_reconnect,
                payload="reconnect_apple_calendar"
            ),
            CallbackButton(
                text=text_disconnect,
                payload="disconnect_apple_calendar"
            )
        )

    return add_back_button(
        builder,
        max_id=max_id
    )
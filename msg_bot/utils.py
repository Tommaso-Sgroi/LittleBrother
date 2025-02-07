from telebot import types

from db.db_lite import TBDatabase


def require_auth(db: TBDatabase, bot):
    def authenticate(func):
        def wrapper(message):
            with db() as db_conn:
                if not db_conn.user_is_authed(message.from_user.id):
                    bot.send_message(message.from_user.id, "You are not authorized to use this command")
                    return None
            # user is authenticated
            func(message)
        return wrapper
    return authenticate


def empty_answer_callback_query(call: types.CallbackQuery, bot):
    """
    Just a workaround to avoid the pressed button to be highlighted for a long time
    """
    bot.answer_callback_query(call.id, "")



def override_call_message_id_with_from_user_id(call: types.CallbackQuery):
    call.message.from_user.id = call.from_user.id
    return call

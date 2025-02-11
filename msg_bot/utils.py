from telebot import types
from local_utils.logger import get_logger
from db.db_lite import TBDatabase

logger = get_logger("TelegramBotUserAuthenticator")

def authenticate_user(message, db:TBDatabase, bot):
    with db() as db_conn:
        if not db_conn.user_is_authed(message.from_user.id):
            bot.send_message(message.from_user.id, "You are not authorized to use this command")
            return False
    return True

def require_auth(db: TBDatabase, bot):
    def authenticate(func):
        def wrapper(message, *args, **kwargs):
            try:
                if not authenticate_user(message, db, bot):
                    return None
                # user is authenticated
            except Exception as e:
                bot.send_message(message.from_user.id, "An error occurred while checking your authorization")
                logger.error("Error checking user authorization: %s", e)
                return None
            func(message, *args, **kwargs)
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

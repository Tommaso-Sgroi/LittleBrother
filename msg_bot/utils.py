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
import os
from venv import logger

import telebot
import telebot.types
from telebot.formatting import format_text, mbold, hcode
from logging import DEBUG, INFO
from random import randint
from msg_bot.utils import require_auth
from db.db_lite import TBDatabase
'''
This code is a bit rushed and must, i repeat MUST, be refactored to be at least something apparently good
'''

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
DB = TBDatabase('database.db', drop_db=True)

auth_token = os.getenv("AUTH_TOKEN")
basedir_enroll_path = './registered_faces' # TODO change to an actual option
# authed_users = []
# logger = None
# logging_level = DEBUG
#
# def _init_logger():
#     from utils.logger import get_logger
#     global logger, logging_level
#     logger = get_logger(__name__)
#     logger.setLevel(logging_level)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print('start')
    bot.send_message(message.chat.id, "Howdy, how are you doing?")

@bot.message_handler(commands=['help'])
def send_help(message):
    print('help')
    bot.send_message(message.chat.id, "This bot is a telegram bot to get notifications from the camera system\n"+\
                        "You can use the following commands:\n"+\
                        "/start - Start the bot\n"+\
                        "/help - Show this message\n"+\
                        "/auth - Authenticate with your given access token\n"+\
                        "/enroll - Enroll new person in the system\n"+\
                        "")

@bot.message_handler(commands=['auth'])
def auth_user(message):
    def authenticate_user(msg):
        logger.debug('authenticating user')
        if msg.text == auth_token:
            user_id = msg.from_user.id
            # user_name = message.from_user.username
            with DB() as db:
                db.add_authed_user(user_id)
                bot.send_message(msg.chat.id, "You are now authenticated")
        else:
            bot.send_message(msg, "Wrong token")

    with DB() as db:
        if db.user_exist(message.from_user.id):
            bot.send_message(message.chat.id, "You are already authenticated")
            return None

    bot.send_message(message.from_user.id, "send the authentication token chosen by you or provided by the system")
    bot.register_next_step_handler(message, authenticate_user)




@bot.message_handler(commands=['enroll'])
@require_auth(bot=bot, db=DB)
def enroll_user(message):
    print('enroll')
    enroll_name = message.text.split(' ')
    del enroll_name[0]
    enroll_name = ' '.join(enroll_name).strip()

    if enroll_name == '':
        bot.send_message(message.chat.id, 'No name typed, aborting')
        return
    with DB() as db:
        if db.person_already_enrolled(enroll_name):
            bot.send_message(message.chat.id, f'{enroll_name} already enrolled into the system')
            return

    print('enrolling:', enroll_name)
    # bot.send_message(message.chat.id, "send a photo of person's face you want to enroll\nNOTE:todo")
    select_access_type(message, enroll_name=enroll_name)

def select_access_type(message, selected=False, enroll_name=''):
    """blacklist or whitelist"""
    print('selecting:', message.text)
    if message.text is None:
        bot.send_message(message.chat.id, 'Nothing selected, aborting')
        return

    if not selected:
        # show the message to select the access type then register the next step to enroll the person
        bot.send_message(message.chat.id, f'Enrolling {format_text(mbold(enroll_name))}:\nWrite the list\'s type:\t\n' + \
                                f'{format_text(hcode("Blacklisted or whitelisted[b / w]"))}')
        bot.register_next_step_handler(message, select_access_type, selected=True, enroll_name=enroll_name)

    else:
        # if the user has chosen a list, then check if it is a valid selection
        text = message.text.strip().lower()
        if text in ['b', 'blacklisted', 'black']:
            bot.send_message(message.chat.id, f'{enroll_name} is being blacklisted')
            text = 'b'
        elif text in ['w', 'whitelisted', 'white']:
            bot.send_message(message.chat.id, f'{enroll_name} is being whitelisted')
            text = 'w'
        else:
            bot.send_message(message.chat.id, 'NO selection has been made, aborted')
            return

        bot.send_message(message.chat.id, 'Send a person\'s picture to enroll in the system')
        bot.register_next_step_handler(message, save_photo, enroll_name=enroll_name, scope=text)

def save_photo(message, enroll_name='', scope=''):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path


    downloaded_file = bot.download_file(file_path)
    full_path = os.path.join(basedir_enroll_path, enroll_name + '.jpg')

    with open(full_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    # update the db with the new person
    with DB() as db:
        db.add_person_room_access(enroll_name, 'PLACEHOLDER', scope) # TODO change the placeholder

    bot.send_message(message.chat.id, f'{enroll_name} enrolled into the system')



def override_image(message, file_path):
    answer = message.text.lower()
    if answer in ['y', 'yes']:
        downloaded_file = bot.download_file(file_path)
        full_path = os.path.join(basedir_enroll_path, file_path)
        with open(full_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        bot.send_message(message.chat.id, 'photo has been changed')
    elif answer in ['n', 'no']:
        bot.send_message(message.chat.id, 'No change applied')
    else:
        bot.send_message(message.chat.id, 'Wrong answer, aborting...')







@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    userid = message.from_user.id
    bot.send_message(userid, 'CIAO!')
    bot.send_photo(userid, telebot.types.InputFile(os.path.join('.', 'datasets', 'spidgame.jpg' if randint(0, 1) else 'goku.jpg')))

bot.infinity_polling(logger_level=DEBUG)

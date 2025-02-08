import os

import telebot
import telebot.types
from logging import DEBUG, INFO
from random import randint

'''
This code is a bit rushed and must, i repeat MUST, be refactored to be at least something apparently good
'''

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
auth_token = os.getenv("AUTH_TOKEN")
basedir_enroll_path = './registered_faces' # TODO change to an actual option
authed_users = []

def require_auth(func):
    def wrapper(message):
        if message.from_user.id in authed_users:
            func(message)
        else:
            bot.reply_to(message, "You are not authenticated")
    return wrapper

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print('start')
    bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(commands=['help'])
def send_help(message):
    print('help')
    bot.reply_to(message, "This bot is a telegram bot to get notifications from the camera system\n"+\
                        "You can use the following commands:\n"+\
                        "/start - Start the bot\n"+\
                        "/help - Show this message\n"+\
                        "/auth - Authenticate with your given access token\n"+\
                        "/enroll - Enroll new person in the system\n"+\
                        "")

@bot.message_handler(commands=['auth'])
def auth_user(message):
    print('auth')
    bot.reply_to(message, "send the authentication token chosen by you or provided by the system")
    bot.register_next_step_handler(message, authenticate_user)


def authenticate_user(message):
    print('authing')
    if message.text == auth_token:
        user_id = message.from_user.id
        if user_id not in authed_users:
            authed_users.append(message.from_user.id)
            bot.reply_to(message, "You are now authenticated")
        else:
            bot.reply_to(message, "You are already authenticated")
    else:
        bot.reply_to(message, "Wrong token")


def write_enrolled_image():
    pass


def override_image(message, file_path):
    answer = message.text.lower()
    if answer in ['y', 'yes']:
        downloaded_file = bot.download_file(file_path)
        full_path = os.path.join(basedir_enroll_path, file_path)
        with open(full_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        bot.reply_to(message, 'photo has been changed')
    elif answer in ['n', 'no']:
        bot.reply_to(message, 'No change applied')
    else:
        bot.reply_to(message, 'Wrong answer, aborting...')

def save_photo(message, enroll_name='', scope=''):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path


    b_filename = f'b_{enroll_name}.jpg'
    w_filename = f'w_{enroll_name}.jpg'
    filename = f'{scope}_{enroll_name}.jpg'

    full_path = os.path.join(basedir_enroll_path, filename)
    print(os.path.join(basedir_enroll_path, b_filename), os.path.join(basedir_enroll_path, w_filename))
    if os.path.exists(os.path.join(basedir_enroll_path, b_filename)) or \
        os.path.exists(os.path.join(basedir_enroll_path, w_filename)):
        # ask to override photo
        bot.reply_to(message, f'*{enroll_name}* already exists, do you want to override it? [y/n]')
        bot.register_next_step_handler(message, override_image, file_path=file_path, save_path=full_path)
    else:
        downloaded_file = bot.download_file(file_path)
        print('saving photo in:', full_path)

        with open(full_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, f'{enroll_name} enrolled into the system')


def select_access_type(message, selected=False, enroll_name=''):
    """blacklist or whitelist"""
    print('selecting:', message.text)
    if message.text is None:
        bot.reply_to(message, 'Nothing selected, aborting')
        return

    if not selected:
        bot.reply_to(message, f'Enrolling *{enroll_name}*:\nWrite the list\'s type:\t\nBlacklisted or whitelisted [b/w]')
        bot.register_next_step_handler(message, select_access_type, selected=True, enroll_name=enroll_name)
    else:
        text = message.text.strip().lower()
        if text in ['b', 'blacklisted', 'black']:
            bot.reply_to(message, f'{enroll_name} is being blacklisted')
            text = 'b'
        elif text in ['w', 'whitelisted', 'white']:
            bot.reply_to(message, f'{enroll_name} is being whitelisted')
            text = 'w'
        else:
            bot.reply_to(message, 'NO selection has been made, aborted')
            return
        bot.reply_to(message, 'Send a person\'s picture to enroll in the system')
        bot.register_next_step_handler(message, save_photo, enroll_name=enroll_name, scope=text)


@bot.message_handler(commands=['enroll'])
# @require_auth
def enroll_user(message):
    print('enroll')
    enroll_name = message.text.split(' ')
    del enroll_name[0]
    enroll_name = ' '.join(enroll_name)

    if enroll_name.strip() == '':
        bot.reply_to(message, 'No name typed, aborting')
        return
    print('enrolling:', enroll_name)
    # bot.reply_to(message, "send a photo of person's face you want to enroll\nNOTE:todo")
    select_access_type(message, enroll_name=enroll_name)

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    userid = message.from_user.id
    bot.send_message(userid, 'CIAO!')
    bot.send_photo(userid, telebot.types.InputFile(os.path.join('..', 'datasets', 'spidgame.jpg' if randint(0, 1) else 'goku.jpg')))

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Create a custom keyboard markup
contact_sup_markup = ReplyKeyboardMarkup(resize_keyboard=True)
contact_sup_button = KeyboardButton('Contact Support')
contact_sup_markup.row(contact_sup_button)

# Create a custom keyboard markup for the "Go Back" button
go_back_markup = ReplyKeyboardMarkup(resize_keyboard=True)
go_back_button = KeyboardButton('Go Back')
go_back_markup.row(go_back_button)


bot.infinity_polling(logger_level=DEBUG)

import os

import telebot
import telebot.types

from random import randint

'''
all code from: https://www.freecodecamp.org/news/how-to-create-a-telegram-bot-using-python/
'''

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
auth_token = os.getenv("AUTH_TOKEN")

authed_users = []


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
                        "/enroll - Enroll yourself in the system\n"+\
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

@bot.message_handler(commands=['enroll'])
def enroll_user(message):
    print('enroll')
    bot.reply_to(message, "send a photo of your face to enroll yourself\nNOTE:todo")


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    userid = message.from_user.id
    bot.send_message(userid, 'CIAO!')
    bot.send_photo(userid, telebot.types.InputFile(os.path.join('..', 'datasets', 'spidgame.jpg' if randint(0, 1) else 'goku.jpg')))


bot.infinity_polling()

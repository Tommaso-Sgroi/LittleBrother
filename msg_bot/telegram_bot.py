import os
from venv import logger

import telebot
import telebot.types
from telebot.formatting import format_text, mbold, hcode
from logging import DEBUG, INFO
from random import randint
from msg_bot.utils import require_auth
from db.db_lite import TBDatabase
from face_recognizer.face_recognizer import FaceRecognizer
from io import BytesIO
from PIL import Image
'''
This code is a bit rushed and must, i repeat MUST, be refactored to be at least something apparently good
'''

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
DB = TBDatabase('database.db', drop_db=False)

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
    bot.send_message(message.chat.id, "This bot is a telegram bot to get notifications from the camera system\n"+\
                        "You can use the following commands:\n"+\
                        "\t/start - Start the bot\n"+\
                        "\t/help - Show this message\n"+\
                        "\t/auth - Authenticate with your given access token\n"+\
                        "\t/enroll [name] - Enroll new person in the system\n"+\
                        "\t/select - Select a camera for give/remove access the person\n"+\
                        "\t/list - List all the people enrolled in the system\n"+\
                        "\t/remove [name] - Remove a person from the system\n"+\
                        "\t/pedit [name] - edit a person name enrolled into the system"+\
                        "\t/cedit [#camera] - edit a camera name\n"+\
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


@bot.message_handler(commands=['list'])
@require_auth(bot=bot, db=DB)
def list_people(message):
    with DB() as db:
        people = db.get_people_access_names()
        print(people)
    if len(people) == 0:
        bot.send_message(message.chat.id, 'No people enrolled in the system')
        return
    bot.send_message(message.chat.id, 'People enrolled in the system:\n\t-' + '\n\t-'.join(people))

@bot.message_handler(commands=['remove'])
@require_auth(bot=bot, db=DB)
def remove_person(message):
    remove_name = message.text.split(' ')
    del remove_name[0]
    remove_name = ' '.join(remove_name).strip()

    if remove_name == '':
        bot.send_message(message.chat.id, 'No name typed, aborting')
        return
    with DB() as db:
        if not db.person_already_enrolled(remove_name):
            bot.send_message(message.chat.id, f'{remove_name} not enrolled into the system.\n you can list them with /list')
            return
        bot.send_message(message.chat.id, f"Removing {remove_name} from the system")
        db.delete_person_access_room(remove_name)
    bot.send_message(message.chat.id, f'{remove_name} removed from the system')


@bot.message_handler(commands=['enroll'])
@require_auth(bot=bot, db=DB)
def enroll_user(message):
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
        cameras = db.get_cameras()
        if len(cameras) == 0:
            bot.send_message(message.chat.id, 'No cameras available, aborting')
            return
        # bot.send_message(message.chat.id, f"Write the #camera from the following '{cameras}' to enroll the person")
    bot.send_message(message.chat.id, f"Send the photo of ({enroll_name}) the person to enroll in the system")
    bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name)


def select_camera(message, enroll_name=''):
    print('selecting camera')
    if message.text is None:
        bot.send_message(message.chat.id, 'Nothing selected, aborting')
        return

    camera_id = message.text.strip()
    if camera_id.isdigit():
        camera_id = int(camera_id)
    else:
        bot.send_message(message.chat.id, 'Invalid camera id, aborting')
        return

    with DB() as db:
        if not db.camera_exist(camera_id):
            bot.send_message(message.chat.id, 'Camera does not exist, aborting')
            return

    bot.send_message(message.chat.id, f'Camera {camera_id} selected')

    bot.send_message(message.chat.id, f'Enrolling {format_text(mbold(enroll_name))}:\nWrite the list\'s type:\t\n' + \
                     f'{format_text(hcode("Blacklisted or whitelisted[b / w]"))}')

    bot.register_next_step_handler(message, select_access_type, enroll_name=enroll_name, camera_id=camera_id)

def select_access_type(message, enroll_name:str, camera_id:int ):
    """blacklist or whitelist"""
    print('selecting:', message.text)
    if message.text is None:
        bot.send_message(message.chat.id, 'Nothing selected, aborting')
        return
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
    bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, camera_id=camera_id, scope=text)

# def enroll_photo_from_user(message, enroll_name:str, scope:str, camera_id:int, retries=3):
def enroll_photo_from_user(message, enroll_name: str, retries=3):

    fr = FaceRecognizer() # TODO get parameters from a config file
    # it's ok to instantiate everytime the face recognizer, since we are calling it few times in
    # the scenario, and purpose, of this bot

    if retries == 0:
        bot.send_message(message.chat.id, 'Too many retries, aborting')
        return
    if message.photo is None:
        bot.send_message(message.chat.id, 'No photo sent, try again')
        # bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, scope=scope, camera_id=camera_id, retries=retries-1)
        bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, retries=retries-1)

        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path

    downloaded_file = bot.download_file(file_path)  # Download the file
    image = Image.open(BytesIO(downloaded_file))    # convert the file to a PIL image

    # enroll faces
    try:
        bot.send_message(message.chat.id, 'Enrolling face, could take a while...')
        fr.enroll_face(image, enroll_name)
        # update the db with the new person
        with DB() as db:
            db.add_enrolled_person(enroll_name)
            # db.add_person_room_access(enroll_name, camera_id=camera_id, listed=scope)  # TODO change the placeholder
        bot.send_message(message.chat.id, f'{enroll_name} enrolled into the system')
    except Exception as e:
        bot.send_message(message.chat.id, f'Invalid image {str(e)}, try again')
        # bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, scope=scope, camera_id=camera_id, retries=retries-1)
        bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, retries=retries-1)
    return


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

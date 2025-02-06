import os
import re
from venv import logger

import telebot
import telebot.types as types
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
basedir_enroll_path = './registered_faces'  # TODO change to an actual option

BLACK_LISTED, WHITE_LISTED = u"\U0001F6AB", u"\U00002705"


# constants, message query types
class CommandName:
    """
    Workaround for tag data in callback_query_handler to filter the type of message.
    The data field returned by the InlineKeyboardMarkup must be:
    QueryMessageType.<YourType> + '_' + <YourData> + '_' + <YourData> + ...
    """
    LIST_PEOPLE = 'list'
    GET_ACCESS_TYPE = 'get-access-type'
    SELECT_ACCESS = 'select-access'
    CHANGE_ACCESS = 'change-access'

    @staticmethod
    def compose(type, *data) -> str:
        return f'{type}_' + '_'.join(data)

    @staticmethod
    def decompose(data) -> list[str]:
        return data.split('_')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print('start')
    bot.send_message(message.chat.id, "Howdy, how are you doing?")


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, "This bot is a telegram bot to get notifications from the camera system\n" + \
                     "You can use the following commands:\n" + \
                     "\t/start - Start the bot\n" + \
                     "\t/help - Show this message\n" + \
                     "\t/auth - Authenticate with your given access token\n" + \
                     "\t/enroll [name] - Enroll new person in the system\n" + \
                     "\t/select - Select a camera for give/remove access the person\n" + \
                     "\t/list - List all the people enrolled in the system\n" + \
                     "\t/remove [name] - Remove a person from the system\n" + \
                     "\t/pedit [name] - edit a person name enrolled into the system" + \
                     "\t/cedit [#camera] - edit a camera name\n" + \
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
            bot.send_message(msg.from_user.id, "Wrong token")

    with DB() as db:
        if db.user_exist(message.from_user.id):
            bot.send_message(message.chat.id, "You are already authenticated")
            return None

    bot.send_message(message.from_user.id, "send the authentication token chosen by you or provided by the system")
    bot.register_next_step_handler(message, authenticate_user)


@bot.message_handler(commands=[CommandName.LIST_PEOPLE])
@require_auth(bot=bot, db=DB)
def list_people(message):
    query_type = CommandName.LIST_PEOPLE

    with DB() as db:
        people = db.get_people_access_names()
    if len(people) == 0:
        bot.send_message(message.chat.id, 'No people enrolled in the system')
        return
    # convert the list of people to {text: kwargs} {str:}
    markup = telebot.util.quick_markup({
        p_name: {'callback_data': '_'.join((query_type, p_name))} for p_name in people
    }, row_width=1)

    bot.send_message(message.chat.id, 'People enrolled into the system', reply_markup=markup)

# ------------------- CALLBACKS QUERIES -------------------
def filter_callback_query(call: types.CallbackQuery, query_type: str) -> bool:
    data = CommandName.decompose(call.data)
    if query_type == data[0]:
        del data[0]
        call.data = data
        return True
    return False

@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.LIST_PEOPLE))
def select_person(call: types.CallbackQuery): # <- passes a CallbackQuery type object to your function
    """Show person information, about his access to the rooms"""
    bot.answer_callback_query(call.id, "Selected {}".format(*call.data))
    assert len(call.data) == 1
    username = call.data[0]
    with DB() as db:
        access_list = db.get_person_rooms_access_list(username)
    if len(access_list) == 0:
        bot.send_message(call.message.chat.id, f'{username} has no access to any room')
        return
    # access_list is a list of [user_name, camera_id, camera_name, listed]
    query_type = CommandName.CHANGE_ACCESS
    markup = telebot.util.quick_markup({
        f' {BLACK_LISTED if listed == "b" else WHITE_LISTED} - {camera_name}':
            {'callback_data': '_'.join((query_type, user_name, str(camera_id), listed))}
        # i hate python :(
        for user_name, camera_id, camera_name, listed in access_list
    }, row_width=2)

    print(markup)
    bot.send_message(call.message.chat.id, f'{username} accesses', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.CHANGE_ACCESS))
def select_person(call: types.CallbackQuery): # <- passes a CallbackQuery type object to your function
    """Show person information, about his access to the rooms"""
    assert len(call.data) == 3
    username, camera_id, listed = call.data

    with DB() as db:
        listed = 'w' if listed == 'b' else 'b'
        db.update_person_access_list(username, int(camera_id), listed)
        access_list = db.get_person_rooms_access_list(username)
    bot.answer_callback_query(call.id, "")

    query_type = CommandName.CHANGE_ACCESS
    markup = telebot.util.quick_markup({
        f' {BLACK_LISTED if listed == "b" else WHITE_LISTED} - {camera_name}':
            {'callback_data': '_'.join((query_type, user_name, str(camera_id), listed))}
        # i hate python2.0 :(
        for user_name, camera_id, camera_name, listed in access_list
    }, row_width=2)

    bot.send_message(call.message.chat.id, f'{username} accesses', reply_markup=markup)


# ------------------- MESSAGE HANDLERS -------------------

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
            bot.send_message(message.chat.id,
                             f'{remove_name} not enrolled into the system.\n you can list them with /list')
            return
        bot.send_message(message.chat.id, f"Removing {remove_name} from the system")
        db.delete_person_access_room(remove_name)
    bot.send_message(message.chat.id, f'{remove_name} removed from the system')


# ------------------- ENROLLMENT -------------------
@bot.message_handler(commands=['enroll'])
@require_auth(bot=bot, db=DB)
def enroll_person(message):
    bot.send_message(message.chat.id, 'Type the name of the person you want to enroll')
    bot.register_next_step_handler(message, enroll_user)


def enroll_user(message, override_enrollment=False, enroll_person_name=''):
    def get_override_answer(msg, enroll_name):
        if msg.text is None:
            bot.send_message(msg.chat.id, 'Nothing typed, aborting')
            return
        msg.text = msg.text.lower()
        if msg.text in ['y', 'yes']:
            enroll_user(msg, True, enroll_name)
        elif msg.text in ['n', 'no']:
            bot.send_message(msg.chat.id, 'No override applied, operation aborted')
        else:
            bot.send_message(msg.chat.id, 'Invalid answer, type [yes/y] or [no/n]')
            bot.register_next_step_handler(msg, get_override_answer, enroll_name)

    if message.text is None:
        bot.send_message(message.chat.id, 'Nothing typed, aborting')
        enroll_person(message)
        return

    enroll_person_name = message.text.strip() if enroll_person_name == '' else enroll_person_name
    if  re.fullmatch(r'([a-zA-Z0-9](\s)?)+', enroll_person_name) is None:
        bot.send_message(message.chat.id, 'Invalid name, only letters and spaces allowed')
        enroll_person(message)
        return

    with DB() as db:
        if not override_enrollment and db.person_already_enrolled(enroll_person_name):
            bot.send_message(message.chat.id,
                             f'{enroll_person_name} already enrolled into the system, do you want to override the image? [y/n]')
            bot.register_next_step_handler(message, get_override_answer, enroll_person_name)
            return
    bot.send_message(message.chat.id, f"Send a photo with {enroll_person_name} face to enroll in the system")
    bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_person_name,
                                   override=override_enrollment)


# def enroll_photo_from_user(message, enroll_name:str, scope:str, camera_id:int, retries=3):
def enroll_photo_from_user(message, enroll_name: str, override=False, retries=3):
    fr = FaceRecognizer()
    # it's ok to instantiate everytime the face recognizer, since we are calling it few times in
    # the scenario, and purpose, of this bot

    if retries == 0:
        bot.send_message(message.chat.id, 'Too many retries, aborting')
        return
    if message.photo is None:
        bot.send_message(message.chat.id, 'No photo sent, try again')
        # bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, scope=scope, camera_id=camera_id, retries=retries-1)
        bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, retries=retries - 1)
        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path

    downloaded_file = bot.download_file(file_path)  # Download the file
    image = Image.open(BytesIO(downloaded_file))  # convert the file to a PIL image

    # enroll faces
    try:
        bot.send_message(message.chat.id, 'Enrolling face, could take a while...')
        fr.enroll_face(image, enroll_name)
        # update the db with the new person
        if not override:
            with DB() as db:
                # TODO db do not raise any exception if the person is already enrolled
                db.add_enrolled_person(enroll_name)
            # db.add_person_room_access(enroll_name, camera_id=camera_id, listed=scope)  # TODO change the placeholder
        bot.send_message(message.chat.id, f'{enroll_name} enrolled into the system')
    except Exception as e:
        bot.send_message(message.chat.id, f'Invalid image {str(e)}, try again')
        # bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, scope=scope, camera_id=camera_id, retries=retries-1)
        bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, retries=retries - 1)
    return


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


def select_access_type(message, enroll_name: str, camera_id: int):
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
    bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_name, camera_id=camera_id,
                                   scope=text)


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
    pics = {
        1: 'goku',
        2: 'spidgame',
        3: 'photo_2025-02-06_02-51-06',
        4: 'photo_2025-02-06_02-52-06',
    }
    bot.send_photo(userid, telebot.types.InputFile(
        os.path.join('.', 'datasets', pics[randint(1, 4)] + '.jpg')
           ))


bot.infinity_polling(logger_level=DEBUG)

import os
import re
from threading import Thread
from typing import Union

import numpy as np
import telebot
import telebot.types as types
from telebot.formatting import format_text, mbold, hcode
from pathlib import Path
from random import randint
from time import time  # NEW: Import time for cooldown check

import local_utils.config
from local_utils.logger import get_logger
from msg_bot.utils import require_auth, empty_answer_callback_query, override_call_message_id_with_from_user_id, \
    authenticate_user
from db.db_lite import TBDatabase, get_database
from face_recognizer.face_recognizer import FaceRecognizer
from io import BytesIO
from PIL import Image
import cv2


config = local_utils.config.config

if config is None:
    config = local_utils.config.load_config()

bot = telebot.TeleBot(config.telegram_bot_token)
DB: TBDatabase = get_database(config.db_path, dropdb=config.drop_db)

logger = get_logger(__name__)

notification_tracker = {}

auth_token = config.auth_token
basedir_enroll_path = config.basedir_enroll_path

BLACK_LISTED, WHITE_LISTED, PERSON_UNICODE = u"\U0001F6AB", u"\U00002705", u'\U0001F464'


# constants, message query types
class CommandName:
    """
    Workaround for tag data in callback_query_handler to filter the type of message.
    The data field returned by the InlineKeyboardMarkup must be:
    QueryMessageType.<YourType> + '_' + <YourData> + '_' + <YourData> + ...
    """
    LIST_PEOPLE = 'list'
    BACK_TO_LIST_PEOPLE = 'back-list'
    GET_ACCESS_TYPE = 'get-access-type'
    SELECT_ACCESS = 'select-access'
    CHANGE_ACCESS = 'change-access'
    REMOVE_PERSON_ENROLLMENT = 'remove-p-e'
    ABORT = 'abort'
    ANSWER_ENROLL_YES_NO = 'answer-enroll-yes-no'

    @staticmethod
    def join_data(*data) -> str:
        return '_'.join(data)

    @staticmethod
    def decompose(data) -> list[str]:
        return data.split('_')

    @staticmethod
    def very_quick_markup_callback(keys: list, *data, row_width: int = 2) -> types.InlineKeyboardMarkup:
        """Very quick markup, only for callback_data"""
        markup = telebot.util.quick_markup({
            key: {'callback_data': CommandName.join_data(data)} for key in keys
        }, row_width=row_width)

        return markup


def filter_callback_query(call: types.CallbackQuery, query_type: str, override_message_id_with_from_user=False) -> bool:
    data = CommandName.decompose(call.data)
    if query_type == data[0]:
        del data[0]
        call.data = data
        return True
    return False


def add_back_button(back_to_query_type: str, markup: types.InlineKeyboardMarkup, *data):
    data = CommandName.join_data(back_to_query_type, *data)
    markup.add(types.InlineKeyboardButton(u'\U00002B05 Back', callback_data=data))
    return markup


def add_abort_button(markup: types.InlineKeyboardMarkup, button_text='Abort'):
    data = CommandName.join_data(CommandName.ABORT)
    markup.add(types.InlineKeyboardButton(u'\u26A0 ' + button_text, callback_data=data))
    return markup


@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.ABORT))
def abort_callback_query(call: types.CallbackQuery):
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.clear_reply_handlers_by_message_id(call.message.chat.id)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Operation aborted")
    bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
    return


def send_detection_img(img: Union[Image.Image, np.ndarray], *, person_detected_name: str = 'Unknown',
                       access_camera_name: str = 'Unknown camera'):
    """
    When a violation is detected we must notify all registered users.
    """
    global notification_tracker
    now = time()
    tracker = notification_tracker.get(access_camera_name)
    if tracker:
        window_start, count = tracker
        if now - window_start < 60:
            if count >= 2:
                logger.info("Cooldown active for camera: %s", access_camera_name)
                return  # Skip notification due to cooldown
            else:
                notification_tracker[access_camera_name] = (window_start, count + 1)
        else:
            notification_tracker[access_camera_name] = (now, 1)
    else:
        notification_tracker[access_camera_name] = (now, 1)

    with DB() as db:
        users = db.get_users()

    buf = BytesIO()
    if isinstance(img, Image.Image):
        img = img
    else:
        # 'img' is likely a NumPy array in BGR
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)
        # Convert from BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # Now create a PIL image
        img = Image.fromarray(img_rgb)

    img.save(buf, format='JPEG')

    caption = f'Violation detected, "{person_detected_name}" has accessed to {access_camera_name}'
    for user_id in users:
        buf.seek(0)
        bot.send_photo(chat_id=user_id, photo=buf, caption=caption)

    # global logger
    logger.info("All users notified of the violation by %s in camera %s", person_detected_name, access_camera_name)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Howdy, how are you doing?")


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, "This bot is a telegram bot to get notifications from the camera system\n" + \
                     "You can use the following commands:\n" + \
                     "\t/start - Start the bot\n" + \
                     "\t/help - Show this message\n" + \
                     "\t/auth - Authenticate with your given access token\n" + \
                     "\t/enroll - Enroll new person in the system\n" + \
                     "\t/list - List all the people enrolled in the system and manage their accesses\n" + \
                     "\t/remove - Remove a person from the system\n" + \
                     "")


@bot.message_handler(commands=['auth'])
def auth_user(message):
    def authenticate_user(msg):
        logger.debug('authenticating user')
        bot.delete_message(message_id=msg.id, chat_id=msg.chat.id)
        if msg.text == auth_token:
            user_id = msg.from_user.id
            # user_name = message.from_user.username
            try:
                with DB() as db:
                    db.add_authed_user(user_id)
                    bot.send_message(msg.chat.id, "You are now authenticated")
            except Exception as e:
                bot.send_message(msg.chat.id, f"Cannot add authenticated user: {str(e)}")
        else:
            bot.send_message(msg.from_user.id, "Wrong token")

    with DB() as db:
        if db.user_exist(message.from_user.id):
            bot.send_message(message.chat.id, "You are already authenticated")
            return None

    bot.send_message(message.from_user.id, "send the authentication token chosen by you or provided by the system")
    bot.register_next_step_handler(message, authenticate_user)


@bot.message_handler(commands=["logout"])
@require_auth(db=DB, bot=bot)
def logout(message):
    with DB() as db:
        db.delete_user(message.from_user.id)
        bot.send_message(message.chat.id, "Logged out")


@bot.message_handler(commands=['list'])
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
        PERSON_UNICODE + ' ' + p_name: {'callback_data': CommandName.join_data(query_type, p_name)} for p_name in people
    }, row_width=1)
    markup = add_abort_button(markup, 'exit')
    bot.send_message(message.chat.id, 'People enrolled into the system', reply_markup=markup)


# ------------------- CALLBACKS QUERIES -------------------


@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.BACK_TO_LIST_PEOPLE))
@require_auth(db=DB, bot=bot)
def back_to_list_people(call: types.CallbackQuery):
    call = override_call_message_id_with_from_user_id(call)
    empty_answer_callback_query(call, bot)
    bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
    list_people(call.message)


@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.LIST_PEOPLE))
@require_auth(db=DB, bot=bot)
def select_person(call: types.CallbackQuery):  # <- passes a CallbackQuery type object to your function
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
            {'callback_data': CommandName.join_data(query_type, user_name, str(camera_id), listed)}
        # i hate python :(
        for user_name, camera_id, camera_name, listed in access_list
    }, row_width=2)
    markup = add_back_button(CommandName.BACK_TO_LIST_PEOPLE, markup)
    bot.delete_message(call.message.chat.id, call.message.id)
    bot.send_message(call.message.chat.id, f'{username} accesses', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.CHANGE_ACCESS))
@require_auth(db=DB, bot=bot)
def select_person(call: types.CallbackQuery):  # <- passes a CallbackQuery type object to your function
    """Show person information, about his access to the rooms"""
    assert len(call.data) == 3
    username, camera_id, listed = call.data
    try:
        with DB() as db:
            listed = 'w' if listed == 'b' else 'b'
            db.update_person_access_list(username, int(camera_id), listed)
            db.update_person_access_list(username, int(camera_id), listed)
            access_list = db.get_person_rooms_access_list(username)
    except Exception as e:
        bot.send_message(call.message.id, f'Error: {str(e)}')
        logger.error(f'Cannot update person access list %s:', e)
        return

    bot.answer_callback_query(call.id, "")
    bot.delete_message(call.message.chat.id, call.message.id)
    query_type = CommandName.CHANGE_ACCESS

    markup = telebot.util.quick_markup({
        f' {BLACK_LISTED if listed == "b" else WHITE_LISTED} - {camera_name}':
            {'callback_data': CommandName.join_data(query_type, user_name, str(camera_id), listed)}
        # i hate python2.0 :(
        for user_name, camera_id, camera_name, listed in access_list
    }, row_width=2)
    markup = add_back_button(CommandName.BACK_TO_LIST_PEOPLE, markup)

    bot.send_message(call.message.chat.id, f'{username} accesses', reply_markup=markup)


# ------------------- MESSAGE HANDLERS -------------------

@bot.message_handler(commands=['remove'])
@require_auth(bot=bot, db=DB)
def remove_person_list(message):
    # bot.delete_message(message.chat.id, message.id)
    query_type = CommandName.REMOVE_PERSON_ENROLLMENT
    with DB() as db:
        people = db.get_people_access_names()
    if len(people) == 0:
        bot.send_message(message.chat.id, 'No people enrolled in the system')
        return
    # convert the list of people to {text: kwargs} {str:}
    markup = telebot.util.quick_markup({
        PERSON_UNICODE + ' ' + p_name: {'callback_data': CommandName.join_data(query_type, p_name)} for p_name in people
    }, row_width=1)
    markup = add_abort_button(markup)
    bot.send_message(message.chat.id, 'Select the people to remove from the system', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.REMOVE_PERSON_ENROLLMENT))
@require_auth(db=DB, bot=bot)
def remove_person(call: types.CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.id)
    query_type = CommandName.REMOVE_PERSON_ENROLLMENT
    assert len(call.data) == 1
    username = call.data[0]
    try:
        with DB() as db:
            db.delete_person_access_room(username)

            enrolls = os.listdir(basedir_enroll_path)
            for enroll in enrolls:
                enroll_stem = Path(enroll).stem
                if username == enroll_stem:
                    os.remove(os.path.join(basedir_enroll_path, enroll))
                    break
    except Exception as e:
        bot.send_message(call.message.id, f'Error: {str(e)}')
        logger.error(f'Cannot delete person from the enrollment %s:', e)
        return
    bot.answer_callback_query(call.id, f'{username} removed from the system')
    # this is a very bad approach, but it's a workaround for now
    call.message.from_user.id = call.from_user.id
    remove_person_list(call.message)

# ------------------- ENROLLMENT -------------------
@bot.message_handler(commands=['enroll'])
@require_auth(bot=bot, db=DB)
def enroll_person(message):
    # bot.delete_message(message.chat.id, message.id)
    bot.send_message(message.chat.id, 'Type the name of the person you want to enroll')
    bot.register_next_step_handler(message, enroll_user)


@bot.callback_query_handler(func=lambda call: filter_callback_query(call, CommandName.ANSWER_ENROLL_YES_NO))
def get_override_answer(call: types.CallbackQuery):
    tmp_message_id = call.message.id
    call.message.from_user.id = call.from_user.id
    if not authenticate_user(call.message, DB, bot):
        return
    call.message.id = tmp_message_id
    empty_answer_callback_query(call, bot)
    if not call.data:
        bot.send_message(call.message.id, 'Nothing typed, aborting')
        return
    answer = call.data[0].lower()
    enroll_name = call.data[1]
    if answer in ['y', 'yes']:
        enroll_user(call.message, True, enroll_name)
    elif answer in ['n', 'no']:
        bot.send_message(call.message.chat.id, 'No override applied, operation aborted')
    else:
        bot.send_message(call.message.chat.id, 'Invalid answer, select [yes/y] or [no/n]')
        bot.register_next_step_handler(call.message, get_override_answer, enroll_name)
    bot.delete_message(call.message.chat.id, call.message.id)

def enroll_user(message, override_enrollment=False, enroll_person_name=''):
    if not authenticate_user(message, DB, bot):
        return

    if message.text is None:
        bot.send_message(message.chat.id, 'Nothing typed, aborting')
        enroll_person(message)
        return

    enroll_person_name = message.text.strip() if enroll_person_name == '' else enroll_person_name
    if re.fullmatch(r'([a-zA-Z0-9](\s)?)+', enroll_person_name) is None:
        bot.send_message(message.chat.id, 'Invalid name, only letters and spaces allowed')
        enroll_person(message)
        return

    with DB() as db:
        if not override_enrollment and db.person_already_enrolled(enroll_person_name):
            markup = telebot.util.quick_markup({
                answ: {'callback_data': CommandName.join_data(CommandName.ANSWER_ENROLL_YES_NO, answ, enroll_person_name)} for answ in ['Yes', 'No']
            }, row_width=2)

            bot.send_message(message.chat.id,
                             f'{enroll_person_name} already enrolled into the system, do you want to override it with the new image?',
                             reply_markup=markup
                             )
            return
    bot.send_message(message.chat.id, f"Send a photo with {enroll_person_name} face to enroll in the system")
    bot.register_next_step_handler(message, enroll_photo_from_user, enroll_name=enroll_person_name,
                                   override=override_enrollment)


def enroll_photo_from_user(message, enroll_name: str, override=False, retries=2):
    if not authenticate_user(message, DB, bot):
        return

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
        n_faces = fr.get_faces(image)
        if not n_faces:
            raise Exception('no face detected')
        elif n_faces[0].shape[0] > 1:
            raise Exception('more than one face detected')

        fr.enroll_face(image, enroll_name)
        # update the db with the new person
        if not override:
            with DB() as db:
                db.add_enrolled_person(enroll_name)
        bot.send_message(message.chat.id, f'{enroll_name} enrolled into the system')
    except Exception as e:
        bot.send_message(message.chat.id, f'Error during enrollment: {str(e)}\nRetry!')
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


def start_bot(logger_level, skip_pending: bool):
    global bot
    logger.info('Starting bot')
    bot.polling(skip_pending=skip_pending, logger_level=logger_level)


def stop_bot():
    bot.stop_bot()


class TelegramBotThread(Thread):
    def stop(self):
        global bot
        bot.stop_bot()


'''
This code is a bit rushed and must, i repeat MUST, be refactored to be at least something apparently good.
Really wish that no one will ever see this code, it's a shame. Also i'm sorry for whoever will work on this code.
Can i be forgiven? I hope so.
Never been so ashamed and amused of my code in the same time, but i had to do this whatever it takes.
'''


if __name__ == '__main__':
    DB = get_database('database.db', dropdb=False)
    try:
        with DB() as db:
            db.add_camera(1, 'camera1')
            db.add_camera(2, 'camera2')
            db.add_camera(3, 'camera3')
            db.add_camera(4, 'camera4')
    except Exception as e:
        logger.error(f'Something went wrong: {e}')

    start_bot(0, skip_pending=True)

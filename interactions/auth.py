from common import chat_types
from telegram import Update, Chat, InlineKeyboardButton, InlineKeyboardMarkup, User as TelegramUser
from telegram.ext import CallbackContext
from model import User
from typing import Any, Callable, Optional
import random
import string
from datetime import datetime
import time

authorization_dialog_text = 'Use the buttons below to de-/authorize or register yourself to be included in this ' \
                            'group\'s statistics\n\n' \
                            'authorization count: {}\n' \
                            'users registered: {}'


def authorized(func_or_result: Optional = None, *args):
    def inner(func: Callable[[Update, CallbackContext], Any]):
        def wrapped(update: Update, context: CallbackContext):
            uid = update.effective_user.id
            if uid not in context.bot_data['users'] or not context.bot_data['users'][uid].authorized:
                print(f'User {uid} is not authorized!')
                update.effective_chat.send_message("Sorry, you're not authorized to use this bot.")
                return func_or_result
            return func(update, context)

        return wrapped

    if isinstance(func_or_result, Callable):
        return inner(func_or_result)
    else:
        return inner


def authorize_user(update: Update, context: CallbackContext):
    query = update.callback_query
    _, dialog_id, action = query.data.split(':')
    if 'dialogs' not in context.chat_data or dialog_id not in context.chat_data['dialogs']:
        query.answer('Your request was not authorized!')
        return
    uid = query.from_user.id

    if action == 'authorize':
        if uid in context.bot_data['users'] and context.bot_data['users'][uid].authorized:
            context.bot_data['users'][uid].authorized = False
            query.answer('Your authorization has been revoked!')
            context.chat_data['dialogs'][dialog_id]['authcount'] -= 1
        else:
            if query.from_user.id not in context.bot_data['users']:
                context.bot_data['users'].append(User(uid))
            context.bot_data['users'][uid].authorized = True
            query.answer('You have been authorized for using the Drill Sergeant!')
            context.chat_data['dialogs'][dialog_id]['authcount'] += 1
    elif action == 'group_reg':
        if 'users' not in context.chat_data:
            context.chat_data['users'] = set()
        if uid in context.chat_data['users']:
            context.chat_data['users'].remove(uid)
            query.answer('Your goals won\'t be included in this group\'s stats anymore!')
        else:
            context.chat_data['users'].add(uid)
            query.answer('Your goals will now be included in this group\'s stats!')

    group_user_count = len(context.chat_data['users'])
    auth_count = context.chat_data['dialogs'][dialog_id]['authcount']

    if action == 'close':
        if uid not in context.bot_data['users'] or not context.bot_data['users'][uid].authorized:
            query.answer('You don\'t have permission to close this poll')
            return

        if time.time() - context.chat_data['dialogs'][dialog_id]['close_timestamp'] > 10:
            context.chat_data['dialogs'][dialog_id]['close_timestamp'] = time.time()
            context.chat_data['dialogs'][dialog_id]['close_uid'] = query.from_user.id
            query.answer('If you really want to close the dialog for all users, press the button again')
            query.edit_message_reply_markup(reply_markup=get_auth_keyboard(context, dialog_id))

            def reset_buttons(ctx):
                if dialog_id in context.chat_data['dialogs']:
                    query.edit_message_reply_markup(reply_markup=get_auth_keyboard(context, dialog_id))

            context.job_queue.run_once(reset_buttons, 10)
            return

        if context.chat_data['dialogs'][dialog_id]['close_uid'] != query.from_user.id:
            query.answer('Only the user who pressed the button for the first time can confirm the closing!')
            return

        del context.chat_data['dialogs'][dialog_id]
        query.answer('authorization dialog closed!')

    msg_text = authorization_dialog_text.format(auth_count, group_user_count) \
               + (f'\n\n--closed by {find_user_name(query.from_user)}--' if action == 'close' else '')
    if msg_text != query.message.text:
        query.edit_message_text(msg_text,
                                reply_markup=get_auth_keyboard(context, dialog_id) if action != 'close' else None)


def find_user_name(user_data: TelegramUser):
    name = user_data.id
    if user_data.username:
        name = user_data.username
    elif user_data.first_name:
        name = user_data.first_name
        if user_data.last_name:
            name += f' {user_data.last_name}'
    return name




@chat_types('group', 'supergroup')
@authorized
def show_auth_dialog(update: Update, context: CallbackContext):
    if 'users' not in context.chat_data:
        context.chat_data['users'] = set()
    if 'dialogs' not in context.chat_data:
        context.chat_data['dialogs'] = {}
    dialog_id = ''.join(random.choice(string.ascii_letters) for _ in range(24))
    context.chat_data['dialogs'][dialog_id] = {
        'authcount': 0,
        'close_uid': -1,
        'close_timestamp': 0
    }

    group_user_count = len(context.chat_data['users'])
    auth_count = context.chat_data['dialogs'][dialog_id]['authcount']
    keyboard = get_auth_keyboard(context, dialog_id)
    update.message.reply_text(authorization_dialog_text.format(auth_count, group_user_count),
                              reply_markup=keyboard)


def get_auth_keyboard(context, dialog_id: str):
    close_text = 'Close Dialog'
    if time.time() - context.chat_data['dialogs'][dialog_id]['close_timestamp'] <= 10:
        close_text = 'Really?'

    option_template = f'auth_dialog:{dialog_id}:{{}}'
    keyboard = [[
        InlineKeyboardButton('de-/authorize me', callback_data=option_template.format('authorize')),
        InlineKeyboardButton('un-/register me for this group',
                             callback_data=option_template.format('group_reg'))
    ], [
        InlineKeyboardButton(close_text, callback_data=option_template.format('close'))
    ]]
    return InlineKeyboardMarkup(keyboard)


@chat_types('group', 'supergroup')
def auth_poll(update: Update, context: CallbackContext):
    options = ['yes', 'no']
    message = context.bot.send_poll(
        update.effective_chat.id,
        "Select 'yes' to get authorized to use the Drill Sergeant",
        options,
        is_anonymous=False,
        allows_multiple_answers=False)

    payload = {
        'auth_polls': {
            message.poll.id: {
                "options": options,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "answers": 0
            }
        }
    }

    context.bot_data.update(payload)

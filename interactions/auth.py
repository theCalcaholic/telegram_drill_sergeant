from common import chat_types
from telegram import Update, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from model import User
from typing import Any, Callable, Optional
import random
import string


def authorize_user(update: Update, context: CallbackContext):
    query = update.callback_query
    _, secret, action = query.data.split(':')
    if 'auth_secrets' not in context.bot_data or secret not in context.bot_data['auth_secrets']:
        query.answer('Your request was not authorized!')
        return
    uid = query.from_user.id
    if action == 'authorize':
        if uid in context.bot_data['users'] and context.bot_data['users'][uid].authorized:
            context.bot_data['users'][uid].authorized = False
            query.answer('Your authorization has been revoked!')
        else:
            if query.from_user.id not in context.bot_data['users']:
                context.bot_data['users'].append(User(uid))
            context.bot_data['users'][uid].authorized = True
            query.answer('You have been authorized for using the Drill Sergeant!')
        return
    elif action == 'group_registration':
        if 'users' not in context.chat_data:
            context.chat_data['users'] = set()
        if uid in context.chat_data['users']:
            context.chat_data['users'].remove(uid)
            query.answer('Your goals won\'t be included in this group\'s stats anymore!')
        else:
            context.chat_data['users'].add(uid)
            query.answer('Your goals will now be included in this group\'s stats!')
        return
    elif action == 'close':
        if uid not in context.bot_data['users'] or not context.bot_data['users'][uid].authorized:
            query.answer('You have no permission to close this poll')
            return
        context.bot_data['auth_secrets'].remove(secret)
        query.answer('authorization dialog closed!')
        query.edit_message_text(query.message.text + '\n\n--closed--')


@chat_types('group', 'supergroup')
def show_auth_dialog(update: Update, context: CallbackContext):
    secret = ''.join(random.choice(string.ascii_letters) for _ in range(24))
    if 'auth_secrets' not in context.bot_data:
        context.bot_data['auth_secrets'] = set()
    context.bot_data['auth_secrets'].add(secret)
    option_template = f'authorization_dialog:{secret}:{{}}'
    keyboard = [[
        InlineKeyboardButton('de-/authorize me', callback_data=option_template.format('authorize')),
        InlineKeyboardButton('register me for this group', callback_data=option_template.format('group_registration'))
    ], [
        InlineKeyboardButton('Close Dialog', callback_data=option_template.format('close'))
    ]]
    print(secret)
    update.message.reply_text('Use the buttons below to de-/authorize or register yourself to be included in this '
                              'group\'s statistics', reply_markup=InlineKeyboardMarkup(keyboard))


def authorize_user_old(update: Update, context: CallbackContext):
    poll_id = update.poll_answer.poll_id
    if poll_id not in context.bot_data['auth_polls']:
        return
    poll_chat: Chat = context.bot.get_chat(context.bot_data['auth_polls'][poll_id]['chat_id'])

    uid = update.poll_answer.user.id
    if update.poll_answer.option_ids[0] == 0:
        if uid not in context.bot_data['users']:
            user = User(uid)

            context.bot_data['users'].append(user)
        context.bot_data['users'][uid].authorized = True
        if 'users' not in context.dispatcher.chat_data[poll_chat.id]:
            context.dispatcher.chat_data[poll_chat.id]['users'] = set()
        context.dispatcher.chat_data[poll_chat.id]['users'].add(uid)
        print(f'{update.poll_answer.user.username} has been authorized')
    elif uid in context.bot_data['users']:
        context.bot_data['users'][uid].authorized = False
        print(f'{update.poll_answer.user.username} has been deauthorized')

    context.bot_data['auth_polls'][poll_id]['answers'] += 1
    print(update)
    if context.bot_data['auth_polls'][poll_id]['answers'] >= poll_chat.get_members_count():
        context.bot.stop_poll(context.bot_data['auth_polls'][poll_id]['chat_id'],
                              context.bot_data['auth_polls'][poll_id]['message_id'])


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

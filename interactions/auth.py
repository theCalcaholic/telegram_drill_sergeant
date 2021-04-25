from common import chat_types
from telegram import Update, Chat
from telegram.ext import CallbackContext
from model import User
from typing import Any, Callable, Optional


def authorize_user(update: Update, context: CallbackContext):
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

from telegram.ext import Dispatcher
from telegram import Update
from .constants import admin_id
from model import UserList, User
from typing import Callable, Any, TYPE_CHECKING


def chat_types(*types: ...):

    def inner(func: Callable[[Update, Any], Any]):
        def wrapped(update: Update, *args, **kwargs):
            if update.effective_chat.type not in types:
                update.message.reply_text(f'This action is only available in {" and ".join(types)} chats')
                return
            return func(update, *args, **kwargs)
        return wrapped

    return inner


def initialize(dispatcher: Dispatcher):
    if 'users' not in dispatcher.bot_data:
        dispatcher.bot_data['users'] = UserList()

    if admin_id not in dispatcher.bot_data['users']:
        dispatcher.bot_data['users'].append(User(admin_id))
        dispatcher.bot_data['users'][admin_id].authorized = True

    if 'auth_polls' not in dispatcher.bot_data:
        dispatcher.bot_data['auth_polls'] = {}

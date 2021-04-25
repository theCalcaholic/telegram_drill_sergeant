import os
import re
from telegram import Update
from telegram.ext import CallbackContext, Dispatcher
from model import UserList, User
from typing import Callable, Any, Union, List, Optional

admin_id = int(os.environ['BOT_ADMIN_ID'])

goal_schedule_types = ['daily', 'weekly', 'cron syntax']
goal_score_types = ['number of days', 'floating average', 'floating amount (x/10)']
goal_score_types_regex = r'^(number of days|floating average|floating amount .x.10.)$'
cron_pattern = re.compile(r'(?P<minute>(\d+|\*|)(/\d+)?)( *(?P<hour>(\d+|\*|)(/\d+)?))( *(?P<dom>(\d+|\*|)(/\d+)?))'
                          r'( *(?P<month>(\d+|\*|)(/\d+)?))( *(?P<dow>(\d+|\*|)(/\d+)?))')
days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Sat']


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

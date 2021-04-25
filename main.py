import os
import re
from telegram import Update, ChatAction, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler
from typing import Dict, Callable, List
from common import admin_id, initialize, chat_types, cron_pattern
from interactions import authorized, auth_poll, authorize_user, schedule_all_goal_checks, add_goal_handler
from model import Goal, User


bot_token = os.environ['TELEGRAM_API_TOKEN']


def debug_fn(func: Callable):
    def inner(*args, **kwargs):
        print(f'{func.__name__}()')
        return func(*args, **kwargs)
    return inner


@debug_fn
@authorized
@chat_types('private')
def start(update: Update, context: CallbackContext):

    context.chat_data['goal_data'] = None
    uid = update.effective_user.id
    if uid not in context.bot_data['users']:
        context.bot_data['users'].append(User(uid))
    context.bot_data['users'][uid].chat_id = update.effective_chat.id
    update.effective_message.reply_html('Welcome to the Drill Sergeant. Send /add to add a goal.')


if __name__ == '__main__':
    persistence = PicklePersistence(filename='driserbot_state')
    updater = Updater(token=bot_token, use_context=True, persistence=persistence)
    initialize(updater.dispatcher)
    schedule_all_goal_checks(updater.dispatcher)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('authorize', auth_poll))
    updater.dispatcher.add_handler(PollAnswerHandler(authorize_user))
    updater.dispatcher.add_handler(add_goal_handler)

    updater.start_polling()
    updater.idle()


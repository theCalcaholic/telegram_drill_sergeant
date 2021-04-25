import os
import re
from telegram import Update, ChatAction, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler
from typing import Dict, Callable, List
from common import admin_id, initialize, require_authorization, cron_pattern
from conversation_add_goal import add_goal_handler
from model import Goal
from apscheduler.schedulers.background import BackgroundScheduler


bot_token = os.environ['TELEGRAM_API_TOKEN']


def debug_fn(func: Callable):
    def inner(*args):
        print(f'{func.__name__}()')
        return func(*args)
    return inner


@debug_fn
def start(update: Update, context: CallbackContext):
    initialize(context)
    if update.effective_chat.type != 'private':
        return
    if not require_authorization(update, context):
        return

    context.chat_data['goal_data'] = None
    update.effective_message.reply_html('Welcome to the Drill Sergeant. Send /add to add a goal.')


@debug_fn
def authorize_user(update: Update, context: CallbackContext):
    initialize(context)

    if 'auth_polls' not in context.bot_data or update.poll_answer.poll_id not in context.bot_data:
        return

    if update.poll_answer.option_ids[0] == 0:
        context.bot_data['authorized_users'].add(update.poll_answer.user.id)
        print(f'{update.poll_answer.user.username} has been authorized')
    elif update.poll_answer.user.id in context.bot_data['authorized_users']:
        context.bot_data['authorized_users'].remove(update.poll_answer.user.id)
        print(f'{update.poll_answer.user.username} has been deauthorized')


@debug_fn
def auth_poll(update: Update, context: CallbackContext):
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    initialize(context)
    if not require_authorization(update, context):
        return
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


# def schedule_goal_check(scheduler: BackgroundScheduler, goal: Goal):
#     cron_match = cron_pattern.fullmatch(goal.cron)
#     def ask_user_for_goal():
#         goal
#     scheduler.add_job()
#
# def get_scheduler_job(goals: List[Goal]):
#
#     def notify_user():
#         pass

def schedule_goal_checks(scheduler: BackgroundScheduler, context: CallbackContext):
    goal: Goal
    for user, goals in context.bot_data['goals'].items():
        grouped_by_cron = []
        for goal in sorted(goals, key=lambda g: g.cron):
            if not grouped_by_cron or grouped_by_cron[-1][-1].cron != goal.cron:
                grouped_by_cron.append([])
            grouped_by_cron[-1][-1].append(goal)

        for goal in grouped_by_cron:
            scheduler.add_job()



if __name__ == '__main__':
    persistence = PicklePersistence(filename='driserbot_state')
    updater = Updater(token=bot_token, use_context=True, persistence=persistence)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('authorize', auth_poll))
    #updater.dispatcher.add_handler(CommandHandler('add', add_goal))
    updater.dispatcher.add_handler(PollAnswerHandler(authorize_user))
    updater.dispatcher.add_handler(add_goal_handler)

    updater.start_polling()
    updater.idle()


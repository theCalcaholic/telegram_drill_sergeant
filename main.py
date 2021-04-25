import os
import re
from telegram import Update, ChatAction, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler, CallbackQueryHandler
from typing import Dict, Callable, List
from common import admin_id, initialize, chat_types, cron_pattern, goal_score_types, telegram_markdown_special_chars
from interactions import authorized, auth_poll, authorize_user, schedule_all_goal_checks, add_goal_handler, \
    handle_goal_check_response
from model import Goal, User


bot_token = os.environ['TELEGRAM_API_TOKEN']


@authorized
@chat_types('private')
def start(update: Update, context: CallbackContext):

    context.chat_data['goal_data'] = None
    uid = update.effective_user.id
    if uid not in context.bot_data['users']:
        context.bot_data['users'].append(User(uid))
    context.bot_data['users'][uid].chat_id = update.effective_chat.id
    update.effective_message.reply_html('Welcome to the Drill Sergeant. Send /add to add a goal.')


@authorized
@chat_types('private')
def user_stats(update: Update, context: CallbackContext):
    goals = context.bot_data['users'][update.effective_user.id].goals
    stats = {goal: goal.data[-1]['score'] if len(goal.data) > 0 else 0 for goal in goals}
    stats_text = ""

    score_formats = {
        goal_score_types[0]: " streak of {}",
        goal_score_types[1]: "{:.2f} %",
        goal_score_types[2]: "{:.0d}/{:d}"
    }
    for goal in goals:
        score_escaped = score_formats[goal.score_type].format(stats[goal], goal.score_range)
        for c in telegram_markdown_special_chars:
            score_escaped = score_escaped.replace(c, f'\\{c}')
        stats_text += f"*{goal.title}*  "
        stats_text += score_escaped
        stats_text += "\n"
    update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN_V2)


def handle_stats(update: Update, context: CallbackContext):
    if update.effective_chat.type == 'private':
        return user_stats(update, context)


if __name__ == '__main__':
    persistence = PicklePersistence(filename='driserbot_state')
    updater = Updater(token=bot_token, use_context=True, persistence=persistence)

    initialize(updater.dispatcher)
    schedule_all_goal_checks(updater.dispatcher)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('authorize', auth_poll))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_goal_check_response))
    updater.dispatcher.add_handler(PollAnswerHandler(authorize_user))
    updater.dispatcher.add_handler(add_goal_handler)
    updater.dispatcher.add_handler(CommandHandler('stats', handle_stats))

    updater.start_polling()
    updater.idle()

    PicklePersistence(filename='driserbot_state').get_bot_data()


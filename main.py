import os
import re
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler, CallbackQueryHandler
from typing import Dict, Callable, List
from common import admin_id, initialize, chat_types, cron_pattern, goal_score_types, markdown_v2_escape
from interactions import authorized, auth_poll, authorize_user, schedule_all_goal_checks, add_goal_handler, \
    handle_goal_check_response, schedule_goal_check
from model import Goal, User


bot_token = os.environ['TELEGRAM_API_TOKEN']

DELETE_SELECTION = 1


@authorized
@chat_types('private')
def start(update: Update, context: CallbackContext):

    context.chat_data['goal_data'] = None
    uid = update.effective_user.id
    if uid not in context.bot_data['users']:
        context.bot_data['users'].append(User(uid))
    user = context.bot_data['users'][uid]
    user.chat_id = update.effective_chat.id
    user.name = update.effective_user.username
    if user.name is None:
        if update.effective_user.first_name is not None:
            user.name = update.effective_user.first_name + f'{update.effective_user.last_name}' \
                if update.effective_user.last_name is not None else ''

    update.effective_message.reply_html('Welcome to the Drill Sergeant. Send /add to add a goal or /help to get more '
                                        'information.')


def get_user_stats(user: User):
    goals = user.goals
    stats = {goal: goal.data[-1]['score'] if len(goal.data) > 0 else 0 for goal in goals}
    stats_text = ""

    score_formats = {
        goal_score_types[0]: " streak of {}",
        goal_score_types[1]: "{:.2f} %",
        goal_score_types[2]: "{}/{:d}"
    }
    for goal in goals:
        try:
            score_escaped = score_formats[goal.score_type].format(stats[goal], goal.score_range)
        except ValueError:
            score_escaped = "<error>"
        score_escaped = markdown_v2_escape(score_escaped)
        stats_text += f"\\- *{goal.title}*  "
        stats_text += score_escaped
        stats_text += "\n"
    return stats_text


@chat_types('private')
@authorized
def delete_dialog(update: Update, context: CallbackContext):
    keyboard: List[List[InlineKeyboardButton]] = [[]]
    uid = update.effective_user.id
    if len(context.bot_data['users'][uid].goals) == 0:
        update.message.reply_text("You have no goals registered")
        return
    for goal in context.bot_data['users'][uid].goals:
        if len(keyboard[-1]) == 4:
            keyboard.append([])
        keyboard[-1].append(InlineKeyboardButton(goal.title, callback_data=f'goal_delete:{uid}:{goal.title}'))
    keyboard.append([InlineKeyboardButton('Cancel', callback_data='goal_delete:CANCEL:')])

    update.message.reply_text('Select the goal to delete', reply_markup=InlineKeyboardMarkup(keyboard))


@chat_types('private')
@authorized
def delete_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    _, user_id, goal_title = query.data.split(':')

    query.edit_message_reply_markup()
    if user_id == 'CANCEL':
        query.answer()
        return

    user = context.bot_data['users'][int(user_id)]
    index = [g.title for g in user.goals].index(goal_title)
    schedule = user.goals[index].cron
    del user.goals[index]
    schedule_goal_check(context, user, (g for g in user.goals if g.cron == schedule), schedule)
    query.answer('The goal has been deleted.')


@authorized
def handle_stats(update: Update, context: CallbackContext):
    if update.effective_chat.type == 'private':
        text = get_user_stats(context.bot_data['users'][update.effective_user.id])
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    elif update.effective_chat.type in ['group', 'supergroup']:
        if 'users' not in context.chat_data:
            update.message.reply_text('No users have registered for this group')
            return

        print(context.chat_data['users'])

        text = ""
        for user_id in context.chat_data['users']:
            if user_id not in context.bot_data['users']:
                text += f"<This user is not registered: {user_id}>\n\n"
                continue

            user = context.bot_data['users'][user_id]
            if len(user.goals) == 0:
                print('user has no goals')
                continue
            text += markdown_v2_escape(f"============\n") + f"*{markdown_v2_escape(user.name)}:*\n"
            text += get_user_stats(user)
            text += markdown_v2_escape(f"============\n\n")
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


def show_help_message(update: Update, _):
    msg = f"Drill Sergeant lets you register Goals and supports you with achieving them\\. In order to do so, it " \
          f"will ask you whether or not you have been able to meet your goals and calculates a score to help you " \
          f"track your progress\\.\n" \
          f"\n" \
          f"*Commands*\n" \
          f"/help Show an overview over available commands\n" \
          f"/add Add a new goal\n" \
          f"/delete Delete an existing goal\n" \
          f"/stats List your goals and show how you're doing so far"

    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


if __name__ == '__main__':
    persistence = PicklePersistence(filename='driserbot_state')
    updater = Updater(token=bot_token, use_context=True, persistence=persistence)

    initialize(updater.dispatcher)
    schedule_all_goal_checks(updater.dispatcher)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('authorize', auth_poll))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_goal_check_response, pattern=r'^goal_check:.*$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(delete_goal, pattern=r'^goal_delete:.*$'))
    updater.dispatcher.add_handler(PollAnswerHandler(authorize_user))
    updater.dispatcher.add_handler(add_goal_handler)
    updater.dispatcher.add_handler(CommandHandler('stats', handle_stats))
    updater.dispatcher.add_handler(CommandHandler('delete', delete_dialog))
    updater.dispatcher.add_handler(CommandHandler('help', show_help_message))

    updater.start_polling()
    updater.idle()

    PicklePersistence(filename='driserbot_state').get_bot_data()


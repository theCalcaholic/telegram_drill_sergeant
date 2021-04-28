import os
import re
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler, CallbackQueryHandler
from typing import Dict, Callable, List
from common import admin_id, initialize, chat_types, cron_pattern, goal_score_types, markdown_v2_escape
from interactions import authorized, show_auth_dialog, authorize_user, schedule_all_goal_checks, add_goal_handler, \
    handle_goal_check_response, schedule_goal_check
from stats import handle_stats
from model import Goal, User
import random
import string

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
                                        'information.', reply_markup=ReplyKeyboardRemove())


@chat_types('private')
@authorized
def delete_dialog(update: Update, context: CallbackContext):
    keyboard: List[List[InlineKeyboardButton]] = [[]]
    uid = update.effective_user.id
    if len(context.bot_data['users'][uid].goals) == 0:
        update.message.reply_text("You have no goals registered")
        return

    dialog_id = ''.join(random.choice(string.ascii_letters) for _ in range(24))
    if 'dialogs' not in context.chat_data:
        context.chat_data['dialogs'] = {}
    context.chat_data['dialogs'][dialog_id] = {
        'goals': [g.title for g in context.bot_data['users'][uid].goals]
    }
    for i, goal_title in enumerate(context.chat_data['dialogs'][dialog_id]['goals']):
        if len(keyboard[-1]) == 4:
            keyboard.append([])
        keyboard[-1].append(InlineKeyboardButton(goal_title, callback_data=f'goal_delete:{dialog_id}:{i}'))
    keyboard.append([InlineKeyboardButton('Cancel', callback_data=f'goal_delete:{dialog_id}:CANCEL')])

    update.message.reply_text('Select the goal to delete', reply_markup=InlineKeyboardMarkup(keyboard))


@chat_types('private')
@authorized
def delete_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    _, dialog_id, goal_id = query.data.split(':')
    if 'dialogs' not in context.chat_data or dialog_id not in context.chat_data['dialogs']:
        query.answer('Could not find dialog. Closing...')
        query.edit_message_reply_markup()

    if goal_id == 'CANCEL':
        query.answer()
        query.edit_message_reply_markup()
        del context.chat_data['dialogs'][dialog_id]
        return

    goal_title = context.chat_data['dialogs'][dialog_id]['goals'][int(goal_id)]
    user_id = query.from_user.id

    query.edit_message_reply_markup()

    user = context.bot_data['users'][int(user_id)]
    goal = user.find_goal_by_title(goal_title)
    schedule = goal.cron
    user.remove_goal(goal)
    schedule_goal_check(context, user, [g for g in user.goals if g.cron == schedule], schedule)
    query.answer('The goal has been deleted.')
    query.message.reply_text(f'The goal \'{goal_title}\' has been deleted')


@chat_types('private')
@authorized
def debug(update: Update, context: CallbackContext):
    user = context.bot_data['users'][update.effective_user.id]
    update.message.reply_text(str(user))
    # for goal in user.goals:
    #     update.message.reply_text(str(goal))


@chat_types('private')
@authorized
def show_info(update: Update, context: CallbackContext):
    user = context.bot_data['users'][update.effective_user.id]
    text = f"You are registered as {user.name} (id: {user.id})\n\n"
    text += f"You have {len(user.goals)} goals registered:\n"
    text += '---\n' if len(user.goals) > 0 else ''
    for goal in user.goals:
        text += f"{str(goal)}\n---\n"

    update.message.reply_text(text)


def cancel_all(update: Update, context: CallbackContext):
    for key in list(context.chat_data.keys()):
        del context.chat_data[key]
    update.message.reply_text('All ongoing processes have been canceled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def show_help_message(update: Update, _):
    msg = f"Drill Sergeant lets you register Goals and supports you with achieving them\\. In order to do so, it " \
          f"will ask you whether or not you have been able to meet your goals and calculates a score to help you " \
          f"track your progress\\.\n" \
          f"\n" \
          f"*Commands*\n" \
          f"/help Show an overview over available commands\n" \
          f"/add Add a new goal\n" \
          f"/delete Delete an existing goal\n" \
          f"/stats List your goals and show how you're doing so far\n" \
          f"/info  List your goals and their configuration\n" \
          f"/debug Show debug information\n" \
          f"/authorize Show the authorization/group registration dialog"

    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


def print_message(update: Update, context: CallbackContext):
    from common import reaction_stickers
    for emotion in reaction_stickers.keys():
        update.message.reply_text(emotion)
        for sticker in reaction_stickers[emotion]:
            update.message.reply_sticker(sticker)


if __name__ == '__main__':
    persistence = PicklePersistence(
        filename=os.environ['PICKLE_PATH'] if 'PICKLE_PATH' in os.environ else 'driserbot_state')
    updater = Updater(token=bot_token, use_context=True, persistence=persistence)

    initialize(updater.dispatcher)
    schedule_all_goal_checks(updater.dispatcher)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('authorize', show_auth_dialog))
    updater.dispatcher.add_handler(add_goal_handler)
    updater.dispatcher.add_handler(CommandHandler('stats', handle_stats))
    updater.dispatcher.add_handler(CommandHandler('delete', delete_dialog))
    updater.dispatcher.add_handler(CommandHandler('help', show_help_message))
    updater.dispatcher.add_handler(CommandHandler('debug', debug))
    updater.dispatcher.add_handler(CommandHandler('info', show_info))
    updater.dispatcher.add_handler(CommandHandler('cancel', cancel_all))

    updater.dispatcher.add_handler(CallbackQueryHandler(handle_goal_check_response, pattern=r'^goal_check:.*$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(delete_goal, pattern=r'^goal_delete:.*$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(authorize_user, pattern=r'^auth_dialog:.*$'))

    # updater.dispatcher.add_handler(MessageHandler(Filters.sticker, print_message))

    updater.start_polling()
    updater.idle()

    PicklePersistence(filename='driserbot_state').get_bot_data()
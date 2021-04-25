from enum import Enum
from telegram import Update, ChatAction, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler
from common import days_of_week, goal_score_types, require_authorization, initialize, goal_schedule_types, \
    cron_pattern, goal_score_types_regex
from typing import Any, Dict
from model import Goal


class AddGoalState(Enum):
    CANCEL = 0
    TITLE = 1
    SCHEDULE_TYPE = 2
    DAY_OF_WEEK = 3
    DAY_OF_MONTH = 4
    CRON_SCHEDULE = 5
    SCORE_TYPE = 6
    SCORE_FLOATING_RANGE = 7
    CONFIRM = 8


def add_goal(update: Update, context: CallbackContext) -> AddGoalState:
    initialize(context)
    if not require_authorization(update, context) or update.effective_chat.type != 'private':
        return AddGoalState.CANCEl

    update.message.reply_text('Please send me a title for your goal')

    context.chat_data['goal_data'] = {'chat_id': update.effective_chat.id}
    return AddGoalState.TITLE


def add_goal_set_title(update: Update, context: CallbackContext):
    print("add_goal_set_title")
    context.chat_data['goal_data']['title'] = update.message.text
    update.message.reply_text('Perfect. Now please select the type of schedule for your goal from the given options',
                              reply_markup=ReplyKeyboardMarkup([goal_schedule_types[:2], goal_schedule_types[2:]],
                                                               one_time_keyboard=True))

    return AddGoalState.SCHEDULE_TYPE


def add_goal_set_schedule_type_daily(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'daily'
    update.message.reply_text('Alright. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


def add_goal_set_schedule_type_weekly(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'weekly'
    update.message.reply_text('Alright. Now please select the day you would like to be asked whether or not'
                              'you met your goal.',
                              reply_markup=ReplyKeyboardMarkup([['Mon', 'Tue'], ['Wed', 'Thu'],
                                                                ['Fri', 'Sat', 'Sun']], one_time_keyboard=True))
    return AddGoalState.DAY_OF_WEEK


def add_goal_set_schedule_type_cron(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'cron syntax'
    update.message.reply_text('Alright. Now please send me the cron expression which will define when to ask you'
                              'whether or not you met your goal', reply_markup=ReplyKeyboardRemove())
    return AddGoalState.CRON_SCHEDULE


def add_goal_set_day_of_week(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['day_of_week'] = update.message.text
    update.message.reply_text('Good. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


def add_goal_set_cron_schedule(update: Update, context: CallbackContext):
    if not cron_pattern.fullmatch(update.message.text):
        update.message.reply_text('This cron expression is invalid! Please try again')
        return AddGoalState.CRON_SCHEDULE

    context.chat_data['goal_data']['cron'] = update.message.text
    update.message.reply_text('Good. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


def add_goal_set_score_type(update: Update, context: CallbackContext):
    score_type = update.message.text
    context.chat_data['goal_data']['score_type'] = score_type
    if score_type == 'number of days':
        context.chat_data['goal_data']['score_range'] = -1
        goal = create_goal_from_user_input(context.chat_data['goal_data'])
        update.message.reply_text(f"The following goal will be added: \n\n"
                                  f"{get_goal_summary(goal)}",
                                  reply_markup=ReplyKeyboardMarkup([['Confirm', 'Cancel']]))
        return AddGoalState.CONFIRM
    elif score_type in ['floating average', 'floating amount (e.g. 8/10)']:
        update.message.reply_text('Please send me a number that determines, for how many days in the past the score '
                                  'will be calculated', reply_markup=ReplyKeyboardRemove())
        return AddGoalState.SCORE_FLOATING_RANGE


def add_goal_set_score_range(update: Update, context: CallbackContext):
    if not update.message.text.isdigit() or int(update.message.text) > 60:
        update.message.reply_text('Invalid value! The score range must be a positive number < 60. Please try again.')
        return AddGoalState.SCORE_FLOATING_RANGE

    context.chat_data['goal_data']['score_range'] = int(update.message.text)
    goal = create_goal_from_user_input(context.chat_data['goal_data'])
    update.message.reply_text(f"The following goal will be added: \n\n"
                              f"{get_goal_summary(goal)}",
                              reply_markup=ReplyKeyboardMarkup([['Confirm', 'Cancel']]))

    return AddGoalState.CONFIRM


def add_goal_confirm(update: Update, context: CallbackContext):
    if not require_authorization(update, context) or update.effective_chat.type != 'private':
        return

    if update.effective_user.id not in context.bot_data['goals']:
        context.bot_data['goals'][update.effective_user.id] = []

    goal = create_goal_from_user_input(context.chat_data['goal_data'])
    context.bot_data['goals'][update.effective_user.id].append(goal)
    context.chat_data['goal_data'] = None

    update.message.reply_text(f'Added goal {goal["title"]}', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def add_goal_cancel(update: Update, context: CallbackContext):
    context.chat_data['goal_data'] = None
    update.message.reply_text('Goal creation cancelled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def create_goal_from_user_input(goal_data: Dict) -> Goal:
    cron_schedule = None

    if goal_data['schedule_type'] == 'cron syntax':
        match = cron_pattern.fullmatch(goal_data['cron'])
        cron_schedule = f"0 {match.group('hour')} {match.group('dom')} {match.group('month')} {match.group('dow')}"
    elif goal_data['schedule_type'] == 'daily':
        cron_schedule = f"0 11 * * *"
    elif goal_data['schedule_type'] == 'weekly':
        cron_schedule = f"0 11 * * {days_of_week[goal_data['day_of_week']]}"

    return Goal(goal_data['title'], cron_schedule, goal_data['score_type'], goal_data['score_range'],
                goal_data['chat_id'])


def get_goal_summary(goal: Dict) -> str:
    summary = f"Title: {goal['title']}\n" \
           f"Schedule: {goal['cron']}\n" \
           f"Score: {goal['score_type']}"
    if goal['score_range'] != -1:
        summary += f"\nScore Range: {goal['score_range']}"
    return summary


add_goal_handler = ConversationHandler(
    entry_points=[CommandHandler('add', add_goal)],
    states={
        AddGoalState.TITLE:
            [MessageHandler(Filters.text & ~Filters.command, add_goal_set_title)],
        AddGoalState.SCHEDULE_TYPE: [
            MessageHandler(Filters.regex(f'^daily$'), add_goal_set_schedule_type_daily),
            MessageHandler(Filters.regex(f'^weekly$'), add_goal_set_schedule_type_weekly),
            MessageHandler(Filters.regex(f'^cron syntax$'), add_goal_set_schedule_type_cron)],
        AddGoalState.DAY_OF_WEEK:
            [MessageHandler(Filters.regex(f'^({"|".join(days_of_week)})$'), add_goal_set_day_of_week)],
        # AddGoalStates.DAY_OF_MONTH: [MessageHandler(Filters.regex(r'^\d+$'), add_goal_set_day_of_month)],
        AddGoalState.CRON_SCHEDULE:
            [MessageHandler(Filters.text & ~Filters.command, add_goal_set_cron_schedule)],
        AddGoalState.SCORE_TYPE:
            [MessageHandler(Filters.regex(goal_score_types_regex), add_goal_set_score_type)],
        AddGoalState.SCORE_FLOATING_RANGE:
            [MessageHandler(Filters.regex(r'^\d+$'), add_goal_set_score_range)],
        AddGoalState.CONFIRM:
            [MessageHandler(Filters.regex(r'^Confirm$'), add_goal_confirm),
             MessageHandler(Filters.regex(r'^Cancel$'), add_goal_cancel)]
    },
    fallbacks=[CommandHandler('Cancel', add_goal_cancel)]
)
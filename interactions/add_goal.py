import re
from enum import Enum
from telegram import Update, ChatAction, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler, CallbackQueryHandler
import cron_descriptor
from common import days_of_week, goal_score_types, chat_types, goal_schedule_types, cron_pattern, goal_score_types_regex
from interactions.auth import authorized
from interactions.goal_check import schedule_goal_check
from typing import Any, Dict
from model import Goal, User
from apscheduler.triggers.cron import CronTrigger


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
    SCHEDULE_DAILY_TIME = 9


CUSTOM_SCHEDULE_HANDLE = 'CREATE_CUSTOM_SCHEDULE'


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal(update: Update, context: CallbackContext) -> AddGoalState:

    update.message.reply_text('Please send me a title for your goal')

    context.chat_data['goal_data'] = {'chat_id': update.effective_chat.id}
    return AddGoalState.TITLE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_title(update: Update, context: CallbackContext):
    title = update.message.text.strip()
    if title in (g.title for g in context.bot_data['users'][update.effective_user.id].goals):
        update.message.reply_text('You already have a goal with that title. Please try again')
        return AddGoalState.TITLE
    context.chat_data['goal_data']['title'] = update.message.text
    update.message.reply_text('Perfect. Now please select the type of schedule for your goal from the given options',
                              reply_markup=ReplyKeyboardMarkup([goal_schedule_types[:2], goal_schedule_types[2:]],
                                                               one_time_keyboard=True))

    return AddGoalState.SCHEDULE_TYPE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_schedule_type_daily(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'daily'
    update.message.reply_text('Thanks. Now send me the time at which you want to be notified '
                              '(in the format: HH:MM, e.g. 23:59)', reply_markup=ReplyKeyboardRemove())
    return AddGoalState.SCHEDULE_DAILY_TIME


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_schedule_daily_time(update: Update, context: CallbackContext):
    if update.message is None:
        update.effective_message.reply_text('I didn\'t understand that. Please try again')
        return AddGoalState.SCHEDULE_DAILY_TIME
    match = re.match(r'(?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{1,2})', update.message.text)
    if match is None or not match.group('hour').isdigit() or not match.group('minute').isdigit() \
            or int(match.group('hour')) > 23 or int(match.group('minute')) > 59:
        update.message.reply_text("Sorry, I couldn't parse that time. Please try again (in format `23:59`)",
                                  parse_mode=ParseMode.MARKDOWN_V2)
        return AddGoalState.SCHEDULE_DAILY_TIME
    context.chat_data['goal_data']['schedule_time'] = (int(match.group('hour')), int(match.group('minute')))

    update.message.reply_text('Alright. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_schedule_type_weekly(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'weekly'
    update.message.reply_text('Alright. Now please select the day you would like to be asked whether or not'
                              'you met your goal.',
                              reply_markup=ReplyKeyboardMarkup([days_of_week[:2], days_of_week[2:4],
                                                                days_of_week[4:7]], one_time_keyboard=True))
    return AddGoalState.DAY_OF_WEEK


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_schedule_type_cron(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'cron syntax'
    update.message.reply_text('Alright. Now please send me the cron expression (see https://cron.help/) which will '
                              'define when to ask you whether or not you met your goal',
                              reply_markup=ReplyKeyboardRemove())
    return AddGoalState.CRON_SCHEDULE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_day_of_week(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['day_of_week'] = update.message.text
    update.message.reply_text('Good. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_cron_schedule(update: Update, context: CallbackContext):
    try:
        CronTrigger.from_crontab(update.message.text)
    except ValueError as e:
        update.message.reply_text(f'This cron expression is invalid ({str(e)})! Please try again')
        return AddGoalState.CRON_SCHEDULE

    context.chat_data['goal_data']['cron'] = update.message.text
    update.message.reply_text('Good. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True, ))
    return AddGoalState.SCORE_TYPE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_score_type(update: Update, context: CallbackContext):
    score_type = update.message.text
    context.chat_data['goal_data']['score_type'] = score_type
    if score_type == goal_score_types[0]:
        context.chat_data['goal_data']['score_range'] = -1
        goal = create_goal_from_user_input(context.chat_data['goal_data'])
        update.message.reply_text(f"The following goal will be added: \n\n"
                                  f"{str(goal)}",
                                  reply_markup=ReplyKeyboardMarkup([['Confirm', 'Cancel']]))
        return AddGoalState.CONFIRM
    elif score_type in goal_score_types[1:]:
        update.message.reply_text('Please send me a number that determines, for how many time periods in the past the '
                                  'score will be calculated', reply_markup=ReplyKeyboardRemove())
        return AddGoalState.SCORE_FLOATING_RANGE


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_set_score_range(update: Update, context: CallbackContext):
    if not update.message.text.isdigit() or int(update.message.text) > 60:
        update.message.reply_text('Invalid value! The score range must be a positive number < 60. Please try again.')
        return AddGoalState.SCORE_FLOATING_RANGE

    context.chat_data['goal_data']['score_range'] = int(update.message.text)
    goal = create_goal_from_user_input(context.chat_data['goal_data'])
    update.message.reply_text(f"The following goal will be added: \n\n"
                              f"{str(goal)}",
                              reply_markup=ReplyKeyboardMarkup([['Confirm', 'Cancel']]))

    return AddGoalState.CONFIRM


@authorized(ConversationHandler.END)
@chat_types('private')
def add_goal_confirm(update: Update, context: CallbackContext):

    goal = create_goal_from_user_input(context.chat_data['goal_data'])
    user = context.bot_data['users'][update.effective_user.id]
    user.add_goal(goal)
    context.chat_data['goal_data'] = None

    schedule_goal_check(context, user, [g for g in user.goals if g.cron == goal.cron], goal.cron)
    update.message.reply_text(f'Added goal {goal.title}', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def add_goal_cancel(update: Update, context: CallbackContext):
    context.chat_data['goal_data'] = None
    update.message.reply_text('Goal creation cancelled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def create_goal_from_user_input(goal_data: Dict) -> Goal:
    cron_schedule = None

    if goal_data['schedule_type'] == 'cron syntax':
        # match = cron_pattern.fullmatch(goal_data['cron'])
        # cron_schedule = f"{match.group('minute')} {match.group('hour')} {match.group('dom')} {match.group('month')} " \
        #                 f"{match.group('dow')}"
        cron_schedule = goal_data['cron']
    elif goal_data['schedule_type'] == 'daily':
        if 'schedule_time' in goal_data:
            cron_schedule = f"{ goal_data['schedule_time'][1] } { goal_data['schedule_time'][0] } * * *"
        else:
            cron_schedule = f"0 11 * * *"
    elif goal_data['schedule_type'] == 'weekly':
        cron_schedule = f"0 11 * * {goal_data['day_of_week']}"

    return Goal(goal_data['title'], cron_schedule, goal_data['score_type'], goal_data['score_range'],
                goal_data['chat_id'])




# schedule_dialog_handler = ConversationHandler(
#     entry_points=[CallbackQueryHandler(todo, pattern=f'^{CUSTOM_SCHEDULE_HANDLE}$')],
#     states={
#
#     },
#     map_to_parent={
#         ConversationHandler.END: AddGoalState.SCORE_TYPE,
#         CustomScheduleState.CANCEL: AddGoalState.CANCEL
#     }
# )


add_goal_handler = ConversationHandler(
    entry_points=[CommandHandler('add', add_goal)],
    states={
        AddGoalState.TITLE:
            [MessageHandler(Filters.text & ~Filters.command, add_goal_set_title)],
        AddGoalState.SCHEDULE_TYPE: [
            MessageHandler(Filters.regex(f'^daily$'), add_goal_set_schedule_type_daily),
            MessageHandler(Filters.regex(f'^weekly$'), add_goal_set_schedule_type_weekly),
            MessageHandler(Filters.regex(f'^cron syntax$'), add_goal_set_schedule_type_cron)],
        AddGoalState.SCHEDULE_DAILY_TIME:
            [MessageHandler(Filters.regex(r'^\d+:\d+$'), add_goal_set_schedule_daily_time)],
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

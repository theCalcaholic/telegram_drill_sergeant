import os
import re
from telegram import Update, ChatAction, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, PollHandler, \
    PollAnswerHandler, PicklePersistence, ConversationHandler
from enum import Enum
from typing import Dict, Callable


def debug_fn(func: Callable):
    def inner(*args):
        print(f'{func.__name__}()')
        return func(*args)
    return inner


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


goal_schedule_types = ['daily', 'weekly', 'cron syntax']
goal_score_types = ['number of days', 'floating average', 'floating percentage']
cron_pattern = re.compile(r'(?P<minute>(\d+/)?\*|\d+)( *(?P<hour>(\d+/)?\*|\d+))( *(?P<dom>(\d+/)?\*|\d+))'
                          r'( *(?P<month>(\d+/)?\*|\d+))( *(?P<dow>(\d+/)?\*|\d+))')
days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Sat']


@debug_fn
def require_authorization(update: Update, context: CallbackContext):
    if update.effective_user.id not in context.bot_data['authorized_users']:
        update.effective_chat.send_message("Sorry, you're not authorized to use the Drill Sergeant.")
        return False
    return True


@debug_fn
def initialize(context: CallbackContext):
    if 'authorized_users' not in context.bot_data:
        context.bot_data['authorized_users'] = set()
        context.bot_data['authorized_users'].add(int(admin_id))
    if 'goals' not in context.bot_data:
        context.bot_data['goals'] = {}


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
def add_goal(update: Update, context: CallbackContext) -> AddGoalState:
    initialize(context)
    if not require_authorization(update, context) or update.effective_chat.type != 'private':
        return AddGoalState.CANCEl

    update.message.reply_text('Please send me a title for your goal')

    context.chat_data['goal_data'] = {'ready': False}
    return AddGoalState.TITLE


@debug_fn
def add_goal_set_title(update: Update, context: CallbackContext):
    print("add_goal_set_title")
    context.chat_data['goal_data']['title'] = update.message.text
    update.message.reply_text('Perfect. Now please select the type of schedule for your goal from the given options',
                              reply_markup=ReplyKeyboardMarkup([goal_schedule_types[:2], goal_schedule_types[2:]],
                                                               one_time_keyboard=True))

    return AddGoalState.SCHEDULE_TYPE


@debug_fn
def add_goal_set_schedule_type_daily(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'daily'
    update.message.reply_text('Alright. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


@debug_fn
def add_goal_set_schedule_type_weekly(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'weekly'
    update.message.reply_text('Alright. Now please select the day you would like to be asked whether or not'
                              'you met your goal.',
                              reply_markup=ReplyKeyboardMarkup([['Mon', 'Tue'], ['Wed', 'Thu'],
                                                                ['Fri', 'Sat', 'Sun']], one_time_keyboard=True))
    return AddGoalState.DAY_OF_WEEK


@debug_fn
def add_goal_set_schedule_type_cron(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['schedule_type'] = 'cron syntax'
    update.message.reply_text('Alright. Now please send me the cron expression which will define when to ask you'
                              'whether or not you met your goal', reply_markup=ReplyKeyboardRemove())
    return AddGoalState.CRON_SCHEDULE


@debug_fn
def add_goal_set_day_of_week(update: Update, context: CallbackContext):
    context.chat_data['goal_data']['day_of_week'] = update.message.text
    update.message.reply_text('Good. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


@debug_fn
def add_goal_set_cron_schedule(update: Update, context: CallbackContext):
    if not cron_pattern.fullmatch(update.message.text):
        update.message.reply_text('This cron expression is invalid! Please try again')
        return AddGoalState.CRON_SCHEDULE

    context.chat_data['goal_data']['cron'] = update.message.text
    update.message.reply_text('Good. Now select the type of score you\'d like.',
                              reply_markup=ReplyKeyboardMarkup([[button] for button in goal_score_types],
                                                               one_time_keyboard=True))
    return AddGoalState.SCORE_TYPE


@debug_fn
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
    elif score_type in ['floating average', 'floating percentag']:
        update.message.reply_text('Please send me a number that determines, for how many days in the past the score '
                                  'will be calculated', reply_markup=ReplyKeyboardRemove())
        return AddGoalState.SCORE_FLOATING_RANGE


@debug_fn
def add_goal_set_score_range(update: Update, context: CallbackContext):
    if not update.message.text.isdigit() or int(update.message.text) > 60:
        update.message.reply_text('Invalid value! The score range must be a positive number < 60. Please try again.')
        return AddGoalState.SCORE_FLOATING_RANGE

    goal = create_goal_from_user_input(context.chat_data['goal_data'])
    update.message.reply_text(f"The following goal will be added: \n\n"
                              f"{get_goal_summary(goal)}",
                              reply_markup=ReplyKeyboardMarkup([['Confirm', 'Cancel']]))
    context.chat_data['goal_data']['score_range'] = int(update.message.text)

    return AddGoalState.CONFIRM


@debug_fn
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


@debug_fn
def add_goal_cancel(update: Update, context: CallbackContext):
    context.chat_data['goal_data'] = None
    update.message.reply_text('Goal creation cancelled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


@debug_fn
def create_goal_from_user_input(goal_data: Dict) -> Dict:
    cron_schedule = None

    if goal_data['schedule_type'] == 'cron syntax':
        match = cron_pattern.fullmatch(goal_data['cron'])
        cron_schedule = f"0 {match.group('hour')} {match.group('dom')} {match.group('month')} {match.group('dow')}"
    elif goal_data['schedule_type'] == 'daily':
        cron_schedule = f"0 11 * * *"
    elif goal_data['schedule_type'] == 'weekly':
        cron_schedule = f"0 11 * * {days_of_week[goal_data['day_of_week']]}"

    goal = {
        'title': goal_data['title'],
        'cron': cron_schedule,
        'score_type': goal_data['score_type'],
        'score_range': goal_data['score_range']
    }
    return goal


@debug_fn
def get_goal_summary(goal: Dict) -> str:
    summary = f"Title: {goal['title']}\n" \
           f"Schedule: {goal['cron']}\n" \
           f"Score: {goal['score_type']}"
    if goal['score_range'] != -1:
        summary += f"\nScore Range: {goal['score_range']}"
    return summary


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


if __name__ == '__main__':
    bot_token = os.environ['TELEGRAM_API_TOKEN']
    admin_id = os.environ['BOT_ADMIN_ID']
    persistence = PicklePersistence(filename='driserbot_state')
    updater = Updater(token=bot_token, use_context=True, persistence=persistence)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('authorize', auth_poll))
    #updater.dispatcher.add_handler(CommandHandler('add', add_goal))
    updater.dispatcher.add_handler(PollAnswerHandler(authorize_user))

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
                [MessageHandler(Filters.regex(f'^({"|".join(goal_score_types)})$'), add_goal_set_score_type)],
            AddGoalState.SCORE_FLOATING_RANGE:
                [MessageHandler(Filters.regex(r'^\d+$'), add_goal_set_score_range)],
            AddGoalState.CONFIRM: [MessageHandler(Filters.regex(r'^Confirm$'), add_goal_confirm)]
        },
        fallbacks=[CommandHandler('Cancel', add_goal_cancel)]
    )
    updater.dispatcher.add_handler(add_goal_handler)

    updater.start_polling()
    updater.idle()


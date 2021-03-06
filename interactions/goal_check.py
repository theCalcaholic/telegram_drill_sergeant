from common import reaction_stickers
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron.expressions import AllExpression
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import CallbackContext, Dispatcher
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from model import Goal, User
from typing import List, Union, Iterable
from croniter import croniter
from datetime import datetime, timedelta
import random
import string


def check_goals(context: CallbackContext):
    user_id = int(context.job.context['user_id'])
    goals: List[Goal] = list(context.job.context['goals'])
    user: User = context.bot_data['users'][user_id]
    if len(goals) == 0:
        print(f"No goals found for job {context.job.name}")
        return

    cron = croniter(goals[0].cron, datetime.now())
    time_end: datetime = cron.get_prev(ret_type=datetime)
    time_start: datetime = cron.get_prev(ret_type=datetime)
    time_period = (time_end - time_start)

    if time_period.total_seconds() / 60 < 120:
        time_string = f'{int(time_period.total_seconds() / 60)} minutes'
    elif time_period.seconds / 3600 < 24:
        time_string = f'{int(time_period.total_seconds() / 3600)} hours'
    else:
        time_string = f'{time_period.days} days'
        if time_period.seconds >= 3600:
            time_string += f', {int(time_period.seconds / 3600)} hours'

    context.bot.send_message(user.chat_id,
                             f'Please select whether or not you have met your goals during the last {time_string}')
    chat_data = context.dispatcher.chat_data[user.chat_id]
    if 'dialogs' not in chat_data:
        chat_data['dialogs'] = {}

    dialog_data = {
        'timestamp': time_end.timestamp()
    }
    for goal in goals:
        dialog_id = ''.join(random.choice(string.ascii_letters) for _ in range(24))
        chat_data['dialogs'][dialog_id] = {**dialog_data, **{'goal': goal.title}}
        keyboard = [
            [InlineKeyboardButton("yes", callback_data=f'goal_check:{dialog_id}:true'),
             InlineKeyboardButton("no", callback_data=f'goal_check:{dialog_id}:false')]
        ]
        context.bot.send_message(user.chat_id, f'Did you meet your goal {goal.title}?',
                                 reply_markup=InlineKeyboardMarkup(keyboard))


def schedule_all_goal_checks(context: Union[CallbackContext, Dispatcher]):

    for user in context.bot_data['users']:
        schedule_all_goal_checks_for_user(context, user)


def schedule_all_goal_checks_for_user(context: Union[CallbackContext, Dispatcher], user: User):
    goal: Goal
    goals: List[Goal]

    goals = user.goals
    grouped_by_cron = []
    for goal in sorted(goals, key=lambda g: g.cron):
        if not grouped_by_cron or grouped_by_cron[-1][-1].cron != goal.cron:
            grouped_by_cron.append([])
        grouped_by_cron[-1].append(goal)

    for grouped_goals in grouped_by_cron:
        schedule_goal_check(context, user, grouped_goals, grouped_goals[0].cron)


def schedule_goal_check(context: Union[CallbackContext, Dispatcher], user: User, goals: List[Goal], cron: str):
    job_name = f'{user.id}:{cron}'
    existing_jobs = context.job_queue.get_jobs_by_name(job_name)
    if len(existing_jobs) != 0:
        for job in existing_jobs:
            job.schedule_removal()
    if len(goals) == 0:
        return
    trigger = CronTrigger.from_crontab(cron)
    job = context.job_queue.run_custom(check_goals, {'trigger': trigger},
                                       context={'user_id': user.id, 'goals': goals},
                                       name=job_name)
    user.jobs.append(job)


def handle_goal_check_response(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    try:
        _, dialog_id, choice = query.data.split(':')

        if 'dialogs' not in context.chat_data or dialog_id not in context.chat_data['dialogs']:
            query.answer('Could not find that dialog. Closing automatically...')
            query.edit_message_reply_markup(reply_markup=None)
            return

        goal_title = context.chat_data['dialogs'][dialog_id]['goal']
        timestamp = context.chat_data['dialogs'][dialog_id]['timestamp']

        del context.chat_data['dialogs'][dialog_id]
    except ValueError as e:
        print(e)
        _, uid, goal_title, timestamp, choice = query.data.split(':')

    if uid not in context.bot_data['users'] \
            or goal_title not in (g.title for g in context.bot_data['users'][uid].goals):
        print(f"ERROR: Could not find goal for goal check response '{update.message}'!")
        context.bot.send_message(update.effective_chat.id,
                                 'Sorry, something went wrong. Please contact the bot developer')
        return

    goal = next(goal for goal in context.bot_data['users'][uid].goals if goal.title == goal_title)
    goal.add_data(1 if choice == 'true' else 0, datetime.fromtimestamp(float(timestamp)))
    query.answer()
    query.edit_message_text(query.message.text + (u' \u2705' if goal.data[-1]['value'] else u' \u274c'))
    if choice == 'true':
        sticker = random.choice(reaction_stickers['approval'])
    else:
        sticker = random.choice(reaction_stickers['disapproval'])
    query.message.reply_sticker(sticker)


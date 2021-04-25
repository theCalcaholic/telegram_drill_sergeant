from common import cron_pattern
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron.expressions import AllExpression
from telegram.ext import CallbackContext, Dispatcher
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from model import Goal, User
from typing import List, Union, Iterable


def check_goals(context: CallbackContext):
    user_id = int(context.job.context['user_id'])
    goals: List[Goal] = context.job.context['goals']
    user: User = context.bot_data['users'][user_id]
    context.bot.send_message(user.chat_id,
                             'Please select whether or not you have met your goals during the last period:')
    for goal in goals:
        keyboard = [
            [InlineKeyboardButton("yes", callback_data=f'goal_check:{user_id}:{goal.title}:true'),
             InlineKeyboardButton("no", callback_data=f'goal_check:{user_id}:{goal.title}:false')]
        ]
        context.bot.send_message(user.chat_id, f'Did you meet your goal {goal.title}?',
                                 reply_markup=InlineKeyboardMarkup(keyboard))


def schedule_all_goal_checks(context: Union[CallbackContext, Dispatcher]):

    for user in context.bot_data['users']:
        print(f"uid: {user.id}")
        schedule_all_goal_checks_for_user(context, user)


def schedule_all_goal_checks_for_user(context: Union[CallbackContext, Dispatcher], user: User):
    goal: Goal
    goals: List[Goal]

    goals = user.goals
    grouped_by_cron = []
    for goal in sorted(goals, key=lambda g: g.cron):
        if not grouped_by_cron or grouped_by_cron[-1][-1].cron != goal.cron:
            grouped_by_cron.append([])
        grouped_by_cron[-1][-1].append(goal)
    print(f"goals: [{'] ['.join(', '.join(g.title for g in gs) for gs in grouped_by_cron)}]")

    for grouped_goals in grouped_by_cron:
        schedule_goal_check(context, user, grouped_goals, grouped_goals[0].cron)


def schedule_goal_check(context: Union[CallbackContext, Dispatcher], user: User, goals: Iterable[Goal], cron: str):
    cron_match = cron_pattern.fullmatch(cron)
    job_name = f'{user.id}:{cron}'
    existing_jobs = context.job_queue.get_jobs_by_name(job_name)
    if len(existing_jobs) != 0:
        for job in existing_jobs:
            job.schedule_removal()
    job_kwargs = {
        'trigger': 'cron',
        'minute': cron_match.group('minute'),
        'hour': cron_match.group('hour'),
        'day': cron_match.group('dom'),
        'month': cron_match.group('month'),
        'day_of_week': cron_match.group('dow')
    }
    job = context.job_queue.run_custom(check_goals, job_kwargs,
                                       context={'user_id': user.id, 'goals': goals},
                                       name=job_name)
    user.jobs.append(job)
    print(f"Scheduled job {job.name}")
    print("trigger: ", job_kwargs)


def handle_goal_check_response(update: Update, context: CallbackContext):
    query = update.callback_query
    _, uid, goal_title, choice = query.data.split(':')
    if int(uid) not in context.bot_data['users'] \
            or goal_title not in (g.title for g in context.bot_data['users'][int(uid)].goals):
        print(f"ERROR: Could not find goal for goal check response '{update.message}'!")
        update.message.reply_text('Sorry, something went wrong. Please contact the bot developer')
        return

    goal = next(goal for goal in context.bot_data['users'][int(uid)].goals if goal.title == goal_title)
    goal.data.append(True if choice == 'true' else False)
    query.answer()
    query.edit_message_text(query.message.text + (u' \u2705' if goal.data[-1] else u' \u274c'))

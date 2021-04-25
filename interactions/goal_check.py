from common import cron_pattern
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron.expressions import AllExpression
from telegram.ext import CallbackContext
from model.Goal import Goal
from typing import List


def check_goals(context: CallbackContext):
    user_id = int(context.job.context['user_id'])
    goals: List[Goal] = context.job.context['goals']
    context.bot.send_poll()


def schedule_goal_checks(scheduler: BaseScheduler, context: CallbackContext):
    goal: Goal
    goals: List[Goal]
    for user_id in context.bot_data['users'].items():
        goals = context.bot_data['users']['user_id'].goals

        grouped_by_cron = []
        for goal in sorted(goals, key=lambda g: g.cron):
            if not grouped_by_cron or grouped_by_cron[-1][-1].cron != goal.cron:
                grouped_by_cron.append([])
            grouped_by_cron[-1][-1].append(goal)

        for grouped_goals in grouped_by_cron:
            cron = cron_pattern.fullmatch(grouped_goals[0].cron)
            job_kwargs = {
                'trigger': 'cron',
                'minute': cron.group('minute'),
                'hour': cron.group('hour'),
                'day': cron.group('dom'),
                'month': cron.group('month'),
                'day_of_week': cron.group('dow')
            }
            job = context.job_queue.run_custom(check_goals, job_kwargs,
                                               context={'user_id': user_id, 'goals': grouped_goals},
                                               name=f'{user_id}:{grouped_goals[0].cron}')
            context.bot_data[user_id]['jobs'].append(job)

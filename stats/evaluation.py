import re
from datetime import datetime, timedelta
import tempfile

import setuptools.msvc
from matplotlib import pyplot, ticker
import matplotlib.dates as mdates
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from common import goal_score_types, markdown_v2_escape
from model import User, Goal
from interactions import authorized
from typing import List


def generate_graph(goals: List[Goal]) -> str:
    fig, ax = pyplot.subplots()
    x_min = datetime.now()
    # x_max = datetime(1970, 1, 1)
    for goal in goals:
        if len(goal.data) == 0:
            continue
        ax.plot([datetime.fromtimestamp(dp['time']) for dp in goal.data],
                [dp['score'][goal_score_types[1]] for dp in goal.data],
                label=goal.title, alpha=0.7)
        if datetime.fromtimestamp(goal.data[0]['time']) < x_min:
            x_min = datetime.fromtimestamp(goal.data[0]['time'])
        # if datetime.fromtimestamp(goal.data[-1]['time']) > x_max:
        #     x_max = datetime.fromtimestamp(goal.data[-1]['time'])

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d. %m'))
    ax.set_xlim(left=max(datetime.now() - timedelta(days=100), x_min), right=datetime.now())
    ax.set_ylim(bottom=0)

    pyplot.legend(loc='best')
    pyplot.xlabel('time')
    pyplot.ylabel('score')
    fig.autofmt_xdate()

    fig_path = tempfile.mktemp('.jpg')
    fig.savefig(fig_path, bbox_inches='tight', dpi=150)
    return fig_path


def get_user_stats(user: User):
    goals = user.goals
    print(goals)
    stats = {goal: goal.data[-1]['score'][goal.score_type] if len(goal.data) > 0 else 0 for goal in goals}
    stats_text = ""

    score_formats = {
        goal_score_types[0]: " streak of {score} {interval}",
        goal_score_types[1]: "{score:.2f} % (for the last {range} {interval})",
        goal_score_types[2]: "{score}/{range:d} {interval}"
    }
    for goal in goals:
        try:
            interval = 'intervals'

            print(f'{goal.title}: {goal.cron}')
            if re.fullmatch(r'\*(/0*1)? \* \* \* \*', goal.cron) is not None:
                interval = 'minutes'
            elif re.fullmatch(r'(\*|\d+)(/0*1)? \*(/0*1)? \* \* \*', goal.cron) is not None:
                interval = 'hours'
            elif re.fullmatch(r'(\*|\d+)(/0*1)? (\*|\d+)(/0*1)? \*(/0*1)? \* \*', goal.cron) is not None:
                interval = 'days'
            elif re.fullmatch(r'(\*|\d+)(/0*1)? (\*|\d+)(/0*1)? (\*|\d+)(/0*1)? \*(/0*1)? \*', goal.cron) is not None:
                interval = 'months'
            elif re.fullmatch(r'(\*|\d+)(/0*1)? (\*|\d+)(/0*1)? (\*|\d+)(/0*1)? \* [a-zA-Z]+', goal.cron) is not None:
                interval = 'weeks'

            score_escaped = '[no data yet]' if len(goal.data) == 0 else score_formats[goal.score_type].format(
                score=stats[goal],
                range=min(goal.score_range, len(goal.data)),
                interval=interval)
        except ValueError as e:
            score_escaped = "<error>"
            print(e)
        score_escaped = markdown_v2_escape(score_escaped)
        stats_text += f"\\- *{goal.title}*  "
        stats_text += score_escaped
        stats_text += "\n"
    if stats_text == "":
        return "No goals registered"
    return stats_text


@authorized
def handle_stats(update: Update, context: CallbackContext):
    if update.effective_chat.type == 'private':
        text = get_user_stats(context.bot_data['users'][update.effective_user.id])
        fig_path = generate_graph(context.bot_data['users'][update.effective_user.id].goals)
        update.message.reply_photo(open(fig_path, 'rb'), caption=text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    elif update.effective_chat.type in ['group', 'supergroup']:
        if 'users' not in context.chat_data or len(context.chat_data['users']) == 0:
            update.message.reply_text('No users have registered for this group')
            return

        text = ""
        all_goals = []
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
            all_goals.extend(user.goals)

        if text == '':
            text = "I found no goals for this group"
        fig_path = generate_graph(all_goals)
        update.message.reply_photo(open(fig_path, 'rb'), caption=text, parse_mode=ParseMode.MARKDOWN_V2)

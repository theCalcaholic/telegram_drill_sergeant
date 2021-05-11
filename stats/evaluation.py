import re
from datetime import datetime, timedelta
import tempfile

import setuptools.msvc
from matplotlib import pyplot, ticker, use as mpl_use, transforms as mpl_transforms, colors as mpl_colors
import matplotlib.dates as mdates
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from common import goal_score_types, markdown_v2_escape
from model import User, Goal
from interactions import authorized
from typing import List, Dict, Union


mpl_use('Agg')


def find_average(all_goals_data: List[Dict[str, List[Union[datetime, float]]]], x_curr: datetime) -> float:
    summed = 0
    count = 0
    for goal in all_goals_data:
        xs = goal['x']
        ys = goal['y']
        if xs[0] > x_curr or xs[-1] < x_curr or len(xs) == 0:
            continue

        if xs[0] == x_curr:
            count += 1
            summed += ys[0]
            continue
        elif xs[-1] == x_curr:
            count += 1
            summed += ys[-1]
            continue

        bounds = next((i, i+1) for i, (x0, x1) in enumerate(zip(xs[:-1], xs[1:])) if x0 <= x_curr <= x1)
        y_0 = ys[bounds[0]]
        y_1 = ys[bounds[1]]
        x_0 = xs[bounds[0]]
        x_1 = xs[bounds[1]]
        interpolation = ((y_1 - y_0) / (x_1 - x_0).total_seconds()) * (x_curr - x_0).total_seconds() + y_0
        summed += interpolation
        count += 1

    if count == 0:
        return 0

    return summed / count


def generate_graph(goals: List[Goal], legend_full_goal_title=True) -> str:
    fig, ax = pyplot.subplots()
    x_min = datetime.now()
    x_max = datetime(1970, 1, 1)

    line_offset = 0.01
    all_goals_data = []

    for idx, goal in enumerate(goals):
        if len(goal.data) == 0:
            continue
        data = {'x': [], 'y': []}
        for dp in goal.data:
            data['x'].append(datetime.fromtimestamp(dp['time']))
            data['y'].append(dp['score'][goal_score_types[1]])
        all_goals_data.append(data)
        ax.plot(data['x'], [val - (line_offset * idx) + (line_offset * 0.5 * len(goals)) for val in data['y']],
                label=goal.title if legend_full_goal_title else str(idx), alpha=0.7)
        if datetime.fromtimestamp(goal.data[0]['time']) < x_min:
            x_min = datetime.fromtimestamp(goal.data[0]['time'])
        if datetime.fromtimestamp(goal.data[-1]['time']) > x_max:
            x_max = datetime.fromtimestamp(goal.data[-1]['time'])

    x_curr = x_min
    averages = {'x': [], 'y': []}
    avg_interval = max((x_max - x_min) / 100, timedelta(hours=1))

    while x_curr < x_max:
        averages['x'].append(x_curr)
        averages['y'].append(find_average(all_goals_data, x_curr))
        x_curr = x_curr + avg_interval
    averages['x'].append(x_max)
    averages['y'].append(find_average(all_goals_data, x_max))
    ax.fill_between(averages['x'], averages['y'], color=[(0.8, 0.1, 0.1, 0.1)], edgecolor=[(0.8, 0.1, 0.1, 0.3)])

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=range(4, 24, 4)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d. %m'))
    ax.set_xlim(left=max(datetime.now() - timedelta(days=100), x_min), right=datetime.now())
    ax.set_ylim(bottom=0, top=1.1)

    pyplot.legend(loc='best')
    pyplot.xlabel('time')
    pyplot.ylabel('score')
    fig.autofmt_xdate()

    fig_path = tempfile.mktemp('.jpg')
    fig.savefig(fig_path, bbox_inches='tight', dpi=150)
    return fig_path


def get_user_stats(user: User, bullet_string='-', numbered_offset=-1):
    goals = user.goals
    print(goals)
    stats = {goal: goal.data[-1]['score'][goal.score_type] if len(goal.data) > 0 else 0 for goal in goals}
    stats_text = ""

    score_formats = {
        goal_score_types[0]: " streak of {score} {interval}",
        goal_score_types[1]: "{score:.2f} % (for the last {range} {interval})",
        goal_score_types[2]: "{score}/{range:d} {interval}"
    }
    for idx, goal in enumerate(goals):
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
        stats_text += f"{markdown_v2_escape(bullet_string)}" \
                      f"{'' if numbered_offset == -1 else str(idx + numbered_offset)} *{markdown_v2_escape(goal.title)}*  "
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
                text += markdown_v2_escape(f"<This user is not registered: {user_id}>\n\n")
                continue

            user = context.bot_data['users'][user_id]
            if len(user.goals) == 0:
                print('user has no goals')
                continue
            user_name = '<unknown>' if user.name == '' else user.name
            text += f"\uA712 *[{markdown_v2_escape(user_name)}](tg://user?id={user.id})*:\n"
            wide_hyphen = '\uff0d'
            text += markdown_v2_escape(f"\uA714{''.join(wide_hyphen for _ in range(int(len(user.name) / 2)))}"
                                       f"{wide_hyphen * 2}\n")
            user_stats = get_user_stats(user, bullet_string='\uA714', numbered_offset=len(all_goals))
            user_stats = '\uA716'.join(user_stats.rsplit('\uA714', 1))
            text += user_stats
            text += markdown_v2_escape(f"\n")
            all_goals.extend(user.goals)

        if text == '':
            text = "I found no goals for this group"
        print(f'=====\ngroup stats:\n{text}\n=====')
        fig_path = generate_graph(all_goals, legend_full_goal_title=False)
        update.message.reply_photo(open(fig_path, 'rb'), caption=text, parse_mode=ParseMode.MARKDOWN_V2)

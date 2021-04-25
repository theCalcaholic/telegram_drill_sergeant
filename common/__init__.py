import os
import re
from telegram import Update
from telegram.ext import CallbackContext

admin_id = os.environ['BOT_ADMIN_ID']

goal_schedule_types = ['daily', 'weekly', 'cron syntax']
goal_score_types = ['number of days', 'floating average', 'floating amount (x/10)']
goal_score_types_regex = r'^(number of days|floating average|floating amount .x.10.)$'
cron_pattern = re.compile(r'(?P<minute>(\d+/)?\*|\d+)( *(?P<hour>(\d+/)?\*|\d+))( *(?P<dom>(\d+/)?\*|\d+))'
                          r'( *(?P<month>(\d+/)?\*|\d+))( *(?P<dow>(\d+/)?\*|\d+))')
days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Sat']


def require_authorization(update: Update, context: CallbackContext):
    if update.effective_user.id not in context.bot_data['authorized_users']:
        print(f'User {update.effective_user.id} is not authorized!')
        print(context.bot_data['authorized_users'])
        update.effective_chat.send_message("Sorry, you're not authorized to use the Drill Sergeant.")
        return False
    return True


def initialize(context: CallbackContext):
    print(context.bot_data)
    print(admin_id)
    if 'authorized_users' not in context.bot_data:
        context.bot_data['authorized_users'] = set()
    if len(context.bot_data['authorized_users']) == 0:
        context.bot_data['authorized_users'].add(int(admin_id))
    if 'goals' not in context.bot_data:
        context.bot_data['goals'] = {}
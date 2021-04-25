import os
import re


admin_id = int(os.environ['BOT_ADMIN_ID'])

goal_schedule_types = ['daily', 'weekly', 'cron syntax']
goal_score_types = ['number of days', 'floating average', 'floating amount (x/10)']
goal_score_types_regex = r'^(number of days|floating average|floating amount .x.10.)$'
goal_score_types_regex_comp = re.compile(goal_score_types_regex)
for t in goal_score_types:
    assert goal_score_types_regex_comp.fullmatch(t) is not None
cron_pattern = re.compile(r'(?P<minute>(\d+|\*|)(/\d+)?)( *(?P<hour>(\d+|\*|)(/\d+)?))( *(?P<dom>(\d+|\*|)(/\d+)?))'
                          r'( *(?P<month>(\d+|\*|)(/\d+)?))( *(?P<dow>(\d+|\*|)(/\d+)?))')
days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Sat']
telegram_markdown_special_chars = '_*[]()~`>#+-=|{}.!'


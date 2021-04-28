import os
import re


admin_id = int(os.environ['BOT_ADMIN_ID'])

goal_schedule_types = ['daily', 'weekly', 'cron syntax']
goal_score_types = ['number of successes', 'floating average', 'floating amount (x/10)']
goal_score_types_regex = r'^(number of successes|floating average|floating amount .x.10.)$'
goal_score_types_regex_comp = re.compile(goal_score_types_regex)
for t in goal_score_types:
    assert goal_score_types_regex_comp.fullmatch(t) is not None
cron_pattern = re.compile(r'(?P<minute>(\d+|\*|)(/\d+)?)( *(?P<hour>(\d+|\*|)(/\d+)?))( *(?P<dom>(\d+|\*|)(/\d+)?))'
                          r'( *(?P<month>(\d+|\*|)(/\d+)?))( *(?P<dow>(\d+|\*|)(/\d+)?))')
days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Sat']
telegram_markdown_special_chars = '_*[]()~`>#+-=|{}.!'

reaction_stickers = {
    'approval': [
        'CAACAgQAAxkBAAIBBWCJQZ4HS2X6MSeaI-X7MJBlgBqLAAJqAwACdpkYBYFJ6YX1HqEQHwQ',
        'CAACAgQAAxkBAAIBBmCJQcdZwFnqMDp-b96XzUQktZvtAAJOAwACdpkYBXNPPUtgrYUWHwQ',
        'CAACAgQAAxkBAAIBC2CJQhBl4HvNE8RiIXtMc-3Oz-vqAAKAAwACdpkYBWOwrBkjorzGHwQ',
        'CAACAgQAAxkBAAIBFGCJQmzyW6s_kUeYcT6BEbkMKxC7AAJMAwACdpkYBZbX_yTpQvXkHwQ',
        'CAACAgQAAxkBAAIBFWCJQoO4IDtd0Ruvbsf96k8z9eLnAAKbAwACdpkYBfVwE0nPmEdeHwQ',
        'CAACAgQAAxkBAAIBF2CJQpKRiI7R2wfFKkEJiTIoeongAAK0BgACdpkYBRKyMtEiIY5xHwQ',
        'CAACAgQAAxkBAAIBHmCJQunUWx-_xRUg8G40VtIwQim2AAK8BgACdpkYBQ9DqltDxaMWHwQ'

    ],
    'disapproval': [
        'CAACAgQAAxkBAAIBAAFgiUDKw4WfnQ1PsqpcssAb86exJQACeAMAAnaZGAXKxjjRkmB6oh8E',
        'CAACAgQAAxkBAAIBB2CJQdz3Jr1aVqOHbvM7l-CRm5jWAAKwBgACdpkYBVGa9a_8kp4fHwQ',
        'CAACAgQAAxkBAAIBCmCJQgEYEEt5bjTTYihVwPlRqZMzAAJiAwACdpkYBZipy5fETOV7HwQ',
        'CAACAgQAAxkBAAIBDWCJQjA5B0J64GHHKRoDvw6Ko86PAAJIAwACdpkYBUxE0wRym_1MHwQ',
        'CAACAgQAAxkBAAIBFmCJQpCN9yWSrkFOGgJJAAGGPAsa-gACsgYAAnaZGAUNZF0tIuvjaR8E',
        'CAACAgQAAxkBAAIBGmCJQrbxRMVWK2OU6BBE8eekCAABrQACgBcAAnaZGAXOj59gMET7IR8E'
    ],
    'proud': [
        'CAACAgQAAxkBAAIBDmCJQkB7knCdBieEvtBI42M3pKldAAJ-AwACdpkYBURkq1RMGFncHwQ',
        'CAACAgQAAxkBAAIBHWCJQss0Gci30xCOBa8_wEf2PzBVAAKLFwACdpkYBfKdxbTnz0oaHwQ'
    ]
}

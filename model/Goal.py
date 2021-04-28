from datetime import datetime
from typing import List, Dict, Union
from common.constants import goal_score_types
import cron_descriptor

cron_descriptor_options = cron_descriptor.Options()
cron_descriptor_options.use_24hour_time_format = True
# cron_descriptor_options.verbose = True #TODO: Reenable once 'every day' duplication is fixed


class Goal:

    def __init__(self, title: str = None, cron: str = None, score_type: str = None, score_range: int = -1,
                 chat_id: int = -1, data: List[Dict] = {}):
        self.title: str = title
        self.cron: str = cron
        self.score_type: str = score_type
        self.score_range: int = score_range
        self.data: List[Dict] = list(data)
        self.chat_id: int = chat_id
        self.waiting_for_data = False

    def add_data(self, value: int, time_end: datetime):
        data_point = {'value': value, 'time': time_end.timestamp(), 'score': -1}
        self.data.append(data_point)
        self.data[-1]['score'] = self.calculate_score()
        score_range = max(100, self.score_range)
        start = max(len(self.data) - score_range, 0)
        self.data = sorted(self.data, key=lambda d: d['time'])[start:]

    def calculate_score_days(self) -> int:
        score = 0
        end = len(self.data) if self.score_range == -1 else self.score_range
        for item in reversed(self.data[:end]):
            if item['value'] == 0:
                return score
            score += 1
        return score

    def calculate_score_floating_average(self, score_range: int = -1) -> float:
        if score_range == -1:
            score_range = 100. if self.score_range == -1 else self.score_range
        score_range = min(score_range, len(self.data))
        return self.calculate_score_floating_amount(score_range=score_range) / score_range

    def calculate_score_floating_amount(self, score_range: int = -1, offset=0) -> int:
        if score_range == -1:
            score_range = 100 if self.score_range == -1 else self.score_range
        score_range = min(score_range, len(self.data))
        if offset > score_range:
            return 0
        data_slice = self.data[-score_range:] if offset == 0 else self.data[-score_range:-offset]
        result = int(sum((d['value'] for d in data_slice), 0))
        return result

    def calculate_score(self) -> Dict[str, Union[int, float]]:
        scores = {
            goal_score_types[0]: self.calculate_score_days(),
            goal_score_types[1]: self.calculate_score_floating_average(),
            goal_score_types[2]: self.calculate_score_floating_amount()
        }

        return scores

    def __getstate__(self):
        return {
            'title': self.title,
            'cron': self.cron,
            'score_type': self.score_type,
            'score_range': self.score_range,
            'data': self.data,
            'waiting_for_data': self.waiting_for_data
        }

    def __setstate__(self, state):
        self.title = state['title']
        self.cron = state['cron']
        self.score_type = state['score_type']
        self.score_range = state['score_range']
        if len(state['data']) > 0 and not isinstance(state['data'][0]['score'], dict):
            self.data = list(map(lambda d: {'value': d['value'], 'time': d['time'], 'score': {
                goal_score_types[0]: d['score'] if goal_score_types[0] == self.score_type else 0,
                goal_score_types[1]: d['score'] if goal_score_types[1] == self.score_type else 0.,
                goal_score_types[2]: d['score'] if goal_score_types[2] == self.score_type else 0
            }}, state['data']))
        else:
            self.data = state['data']
        self.waiting_for_data = state['waiting_for_data']

    def __str__(self):
        summary = f"Title: {self.title}\n" \
                  f"Schedule: {cron_descriptor.ExpressionDescriptor(self.cron, cron_descriptor_options)}\n" \
                  f"Score: {self.score_type.replace('x/10', f'x/{self.score_range}')}"
        if self.score_range != -1:
            summary += f"\nScore Range: {self.score_range}"
        return summary

    def __repr__(self):
        return f"Goal(title='{self.title}', cron='{self.cron}', score_type='{self.score_type}', " \
               f"score_range={self.score_range})\n  data:\n  [{', '.join(str(i) for i in self.data)}])"

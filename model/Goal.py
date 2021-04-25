from datetime import datetime
from apscheduler.triggers.cron import CronTrigger
from typing import List, Dict, Union
from common.constants import goal_score_types
from croniter import croniter


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
        data_point = {'value': value, 'time': time_end.timestamp(), 'score': self.calculate_score()}
        self.data.append(data_point)
        start = 0
        if self.score_range != -1:
            start = max(len(self.data) - self.score_range, 0)
        self.data = sorted(self.data, key=lambda d: d['time'])[start:]

    def calculate_score_days(self) -> int:
        score = 0
        for item in reversed(self.data):
            if item['value'] == 0:
                return score
            score += 1
        return score

    def calculate_score_floating_average(self) -> float:
        return self.calculate_score_floating_amount() / self.score_range

    def calculate_score_floating_amount(self) -> float:
        count = min(self.score_range, len(self.data))
        return sum((d['value'] for d in self.data[:count]), 0.0)

    def calculate_score(self) -> Union[float, int]:
        score = float('nan')
        if self.score_type == goal_score_types[0]:
            score = self.calculate_score_days()
        elif self.score_type == goal_score_types[1]:
            score = self.calculate_score_floating_average()
        elif self.score_type == goal_score_types[2]:
            score = self.calculate_score_floating_amount()
        return score

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
        self.data = state['data']
        self.waiting_for_data = state['waiting_for_data']

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Goal(title='{self.title}', cron='{self.cron}', score_type='{self.score_type}', " \
               f"score_range={self.score_range})\n  data:\n  [{', '.join(str(i) for i in self.data)}]"

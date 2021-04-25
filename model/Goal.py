from typing import List


class Goal:

    def __init__(self, title: str = None, cron: str = None, score_type: str = None, score_range: int = -1,
                 chat_id: int = -1, data: List[int] = (), scores: List[int] = ()):
        self.title: str = title
        self.cron: str = cron
        self.score_type: str = score_type
        self.score_range: int = score_range
        self.data: List[int] = list(data)
        self.scores: List[int] = list(scores)
        self.chat_id: int = chat_id

    def __getstate__(self):
        return {
            'title': self.title,
            'cron': self.cron,
            'score_type': self.score_type,
            'score_range': self.score_range,
            'data': tuple(self.data),
            'scores': tuple(self.scores)
        }

    def __setstate__(self, state):
        self.title = state['title']
        self.cron = state['cron']
        self.score_type = state['score_type']
        self.score_range = state['score_range']
        self.data = list(state['data'])
        self.scores = list(state['scores'])

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Goal(title='{self.title}', cron='{self.cron}', score_type='{self.score_type}', " \
               f"score_range={self.score_range})\n  data:\n  [{', '.join(str(i) for i in self.data)}]"

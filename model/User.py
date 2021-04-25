from model import Goal
from typing import List


class User:
    def __init__(self, user_id: int):
        self.id = user_id
        self.goals: List[Goal] = []
        self.authorized = False

    def add_goal(self, goal: Goal):
        self.goals.append(goal)

    def remove_goal(self, goal: Goal):
        self.goals.remove(goal)

    def __setstate__(self, state):
        self.id = state['id']
        self.goals = state['goals']
        self.authorized = state['authorized']

    def __getstate__(self):
        return {'id': self.id, 'goals': self.goals, 'authorized': self.authorized}

    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id

        return super().__eq__(other)

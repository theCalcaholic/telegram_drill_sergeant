from model import Goal
from typing import List


class User:
    def __init__(self, user_id: int):
        self.id = user_id
        self.name: str = str(user_id)
        self.goals: List[Goal] = []
        self.authorized = False
        self.chat_id: int = -1
        self.jobs = []
        self.goal_polls = {}

    def add_goal(self, goal: Goal):
        self.goals.append(goal)

    def remove_goal(self, goal: Goal):
        self.goals.remove(goal)

    def find_goal_by_title(self, title: str) -> Goal:
        index = [g.title for g in self.goals].index(title)
        return self.goals[index]

    def __setstate__(self, state):
        self.id = state['id']
        self.name = state['name']
        self.goals = state['goals']
        self.authorized = state['authorized']
        self.jobs = []
        self.goal_polls = state['goal_polls']
        self.chat_id = state['chat_id']

    def __getstate__(self):
        return {'id': self.id, 'goals': self.goals, 'authorized': self.authorized, 'goal_polls': self.goal_polls,
                'chat_id': self.chat_id, 'name': self.name}

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"User(id={self.id}, authorized={self.authorized}, goals={self.goals.__repr__()},\njobs={self.jobs},\n" \
               f"goal_polls={self.goal_polls})"

from telegram.ext import ConversationHandler, Handler


class ConversationState:
    def __init__(self, idx: int, handler: Handler):
        self.id: int = idx
        self.handler: Handler = handler
        self.

class ConversationBuilder:
    id_max = 0

    def __init__(self):
        self.states = set()
        self.

    def enter(self, handler: Handler):




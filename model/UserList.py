from model import User
from typing import List, Union


class UserList(List[User]):

    def append(self, user: User) -> None:
        super().append(user)
        self.sort()

    def sort(self: List[User], *, key: None = lambda u: u.id, reverse: bool = False) -> None:
        super().sort(key=key, reverse=reverse)

    def __getitem__(self, user_id):
        if not isinstance(user_id, int):
            raise ValueError('Invalid user id (must be int)!')

        return next((user for user in self if user.id == user_id))

    def __contains__(self, item: Union[User, int]):
        if isinstance(item, int):
            try:
                next(u for u in self if u.id == item)
                return True
            except StopIteration:
                return False

        return super().__contains__(item)


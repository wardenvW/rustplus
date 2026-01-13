from typing import Callable

from ..identification import RustServer, RegisteredListener
from ..commands import ChatCommand,ChatCommandData

def Command(server_detail: RustServer, aliases: list = None, check_func: Callable = None) -> Callable:
    def wrapper(func) -> RegisteredListener:
        if isinstance(func, RegisteredListener):
            func = func.get_coro()

        command_data = ChatCommandData(func, aliases=aliases, callable_func=check_func)

        ChatCommand.REGISTERED_COMMANDS[server_detail][func.__name__] = command_data

        return RegisteredListener(func.__name__, func)
    
    return wrapper
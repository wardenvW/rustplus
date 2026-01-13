from typing import Callable

from .. import RustServer  
from ..identification import RegisteredListener
from ..events import ChatEventPayload as ChatEventManager

def ChatEvent(server_details: RustServer) -> Callable:
    def wrapper(func) -> RegisteredListener:
        if isinstance(func, RegisteredListener):
            func = func.get_coro()

        listener = RegisteredListener(func.__name__, func)
        ChatEventManager.HANDLER_LIST.register(listener, server_details)

        return listener

    return wrapper
        
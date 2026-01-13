from typing import Callable

from .. import RustServer
from ..identification import RegisteredListener
from ..events import TeamEventPayload

def TeamEvent(server_details: RustServer) -> Callable:
    def wrapper(func):
        if isinstance(func, RegisteredListener):
            func = func.get_coro()

        listener = RegisteredListener(func.__name__, func)

        TeamEventPayload.HANDLER_LIST.register(listener, server_details)

        return listener
    
    return wrapper
from typing import Callable

from .. import RustServer
from ..identification import RegisteredListener
from ..events import EntityEventPayload as EntityEventManager

def EntityEvent(server_details: RustServer, eid: int) -> Callable:
    def wrapper(func) -> RegisteredListener:
        if isinstance(func, RegisteredListener):
            func = func.get_coro()
        
        listener = RegisteredListener(str(eid), func)

        EntityEventManager.HANDLER_LIST.register(listener, server_details)
        
        return listener
    
    return wrapper
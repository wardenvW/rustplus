from collections import defaultdict
from typing import Set, Dict
from rustWplus.identification import (
    RegisteredListener,
    RustServer  
)

class HandlerList:
    def __init__(self) -> None:
        self._handlers: Dict[RustServer, Set[RegisteredListener]] = defaultdict (set)

    def register(self, listener: RegisteredListener, server_details: RustServer) -> None:
        self._handlers[server_details].add(listener)

    def unregister(self, listener: RegisteredListener, server_details: RustServer) -> None:
        self._handlers[server_details].remove(listener)

    def has(self, listener: RegisteredListener, server_details: RustServer) -> None:
        return listener in self._handlers[server_details]
    
    def unregister_all(self) -> None:
        self._handlers.clear()

    def get_handlers(self, server_details: RustServer) -> Set[RegisteredListener]:
        return self._handlers.get(server_details, set())

class EntityHandlerList(HandlerList):
    def __init__(self) -> None:
        super().__init__()
        self._handlers: Dict[RustServer, Dict[str, Set[RegisteredListener]]] = defaultdict(dict)

    def register(self, listener: RegisteredListener, server_details: RustServer) -> None:
        if server_details not in self._handlers:
            self._handlers[server_details] = defaultdict(set)
        
        if listener.listener_id not in self._handlers.get(server_details):
            self._handlers.get(server_details)[listener.listener_id] = set()

        self._handlers.get(server_details).get(listener.listener_id).add(listener)

    
    def unregister(self, listener: RegisteredListener, server_details: RustServer) -> None:
        if listener.listener_id in self._handlers.get(server_details):
            self._handlers.get(server_details).get(listener.listener_id).remove(listener)


    def has(self, listener: RegisteredListener, server_details: RustServer) -> bool:
        if (
            server_details in self._handlers
            and listener.listener_id in self._handlers.get(server_details)
        ):
            return listener in self._handlers.get(server_details).get(listener.listener_id)
        
        return False
    
    def unregister_all(self) -> None:
        self._handlers.clear()

    def get_handlers(self, server_details: RustServer) -> Dict[str, Set[RegisteredListener]]:
        return self._handlers.get(server_details, dict())

    
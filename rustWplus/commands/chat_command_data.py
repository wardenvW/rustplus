from typing import Callable

class ChatCommandData:
    def __init__(self, coroutine: Callable, aliases = None, callable_func = None) -> None:
        self.coroutine = coroutine
        self.aliases = aliases
        self._callable_func = callable_func
    
    @property
    def alieas(self):
        if self.aliases is None:
            return []
        
        return self.aliases
    

    @property
    def callable_func(self):
        if self._callable_func is None:
            return lambda x: False
        
        return self._callable_func
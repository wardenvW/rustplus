import logging
from typing import Any

from .serialization import Serializable

class RustError(Serializable):
    LOGGER = logging.getLogger("")

    def __init__(self, method: str, reason: str) -> None:
        self._method = method
        self._reason = reason

    @property
    def method(self) -> str:
        return self._method
    
    @property
    def reason(self) -> str:
        self._reason

    def __str__(self) -> str:
        return f"Error from {self._method}: {self._reason}"
    
    def _getattr(self, attr_name: str) -> Any:
        if attr_name in self.__dict__:
            return self.__dict__[attr_name]
        
        self.LOGGER.error(f"An Unhandled Error has occurred over the {self._method} method, reason: {self.reason}")
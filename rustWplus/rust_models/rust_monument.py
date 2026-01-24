from typing import List
from .serialization import Serializable
from ..gateway.rustplus_proto import AppMapMonument


    
class RustMonument(Serializable):
    def __init__(self, data: AppMapMonument) -> None:
        self._token: str = data.token
        self._x: float = data.x
        self._y: float = data.y

    @property
    def token(self) -> str:
        return self._token

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    def __eq__(self, other) -> bool:
        if isinstance(other, RustMonument):
            return (self._token == other._token)
        return False
    
    def __str__(self) -> str:
        return (
            "RustMonument[token={}, x={}, y={}]".format(
                self._token,
                self._x,
                self._y
            )
        )
    
    def __hash__(self) -> int:
        return hash((self._token, self._x, self._y))
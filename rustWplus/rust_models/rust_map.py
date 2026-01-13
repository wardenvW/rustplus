from ..gateway.rustplus_proto import AppMap 
from .serialization import Serializable
from typing import List

class RustMonument(Serializable):
    def __init__(self, token, x, y) -> None:
        self._token = token
        self._x = x
        self._y = y

    @property
    def token(self) -> str:
        return self._token
    
    @property 
    def x(self) -> float:
        return self._x
    
    @property
    def y(self) -> float:
        return self._y
    
    def __str__(self) -> str:
        return "RustMonument[token={}, x={}, y={}]".format(
            self._token,
            self._x,
            self._y
        )
    
class RustMap(Serializable):
    def __init__(self, data: AppMap) -> None:
        self._width: int = data.width
        self._height: int = data.height
        self._jpg_image: bytes = data.jpg_image
        self._ocean_margin: int = data.ocean_margin
        self._monuments = [RustMonument(monument.token, monument.x, monument.y) for monument in data.monuments]
        self._background: str = data.background

    @property
    def width(self) -> int:
        return self._width
    
    @property
    def height(self) -> int:
        return self._height
    
    @property
    def jpg_image(self) -> bytes:
        return self._jpg_image
    
    @property
    def ocean_margin(self) -> int:
        return self._ocean_margin
    
    @property
    def monuments(self) -> List[RustMonument]:
        return self._monuments
    
    @property
    def background(self) -> str:
        return self._background
    

    def __str__(self) -> None:
        return "RustMap[width={}, height={}, jpg_image={}, ocean_margin={}, monuments={}, background ={}]".format(
            self._width,
            self._height,
            self._jpg_image,
            self._ocean_margin,
            self._monuments,
            self._background
        )
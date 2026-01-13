from rustWplus.rust_models.serialization import Serializable
from typing import Union
import time

class TrackedPlayer(Serializable):
    def __init__(self, bm_id: str, server_id: str = None, nickname: str = "", online: bool = False) -> None:
        self._nickname: str = nickname
        self._bm_id: str = bm_id
        self._server_id: str = server_id
        self.online: bool = online
        self._last_logout: Union[int, None] = None
        self._last_login: Union[int, None] = None
        self._last_update: float = time.time()


    @property
    def nickname(self) -> str:
        return self._nickname
    
    @nickname.setter
    def nickname(self, value: str):
        self._nickname = value

    @property
    def bm_id(self) -> str:
        return self._bm_id
    
    @property 
    def server_id(self) -> str:
        return self._server_id
    
    @property
    def last_logout(self) -> Union[int, None]:
        return self._last_logout
    
    @property
    def last_login(self) -> Union[int, None]:
        return self._last_login
    
    def serialize(self) -> dict:
        return {
            "bm_id": self._bm_id,
            "server_id": self._server_id,
            "nickname": self._nickname,
            "online": self.online,
            "last_login": self._last_login,
            "last_logout": self._last_logout,
            "last_update": self._last_update
        }

    @classmethod
    def load_from_dict(cls, data: dict):
        player = cls(
            bm_id=data['bm_id'],
            server_id=data['server_id'],
            nickname=data.get('nickname', ""),
        )
        player.online = data.get('online', False)
        player._last_login = data.get('last_login', None)
        player._last_logout = data.get('last_logout', None)
        player._last_update = data.get('last_update', time.time())

        return player
    
    def __str__(self) -> str:
        return f"RustPlayer[nickname={self._nickname}, battlemetrics_id={self._bm_id}, online_status={self.online}]"
    
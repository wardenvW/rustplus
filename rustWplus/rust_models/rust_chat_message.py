from .serialization import Serializable
from ..gateway.rustplus_proto import AppTeamMessage

class RustChatMessage(Serializable):
    def __init__(self, chat_data: AppTeamMessage):
        self._steam_id: int = chat_data.steam_id
        self._name: str = chat_data.name
        self._message: str = chat_data.message
        self._color: str = chat_data.color
        self._time: int = chat_data.time

    @property
    def steam_id(self):
        return self._steam_id
    
    @property
    def name(self):
        return self._name
    
    @property
    def message(self):
        return self._message
    
    @property
    def color(self):
        return self._color
    
    @property
    def time(self):
        return self._time
    
    def __str__(self):
        return "RustChatMessage[steam_id={}, sender_name={}, message={}, color={}, time={}]".format(
            self._steam_id,
            self._name,
            self._message,
            self._color,self._time
            )
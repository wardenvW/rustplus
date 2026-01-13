from ..rust_models import RustChatMessage
from rustWplus.identification.handler_list import HandlerList

class ChatEventPayload:
    HANDLER_LIST =  HandlerList()

    def __init__(self, chat_message: RustChatMessage) -> None:
        self._chat_message = chat_message
    
    @property 
    def chat_message(self):
        return self._chat_message
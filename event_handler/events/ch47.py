import asyncio
import time
from rustWplus import RustSocket, Emoji
from ..utils import get_oil_info
import logging

OPENING_TIME = 900
class OilRigEvent:
    def __init__(self, oil_type: str, socket: RustSocket) -> None:
        self.oil_type: str = oil_type          # "Small" | "Large"
        self.socket: RustSocket = socket
        self.logger: logging.Logger = logging.getLogger('events')

        self.start_time = -1
        self.active: bool = False
        self.opened: bool = False

        self.task: asyncio.Task | None = None

    async def start(self):
        self.start_time = time.time()
        self.active = True
        self.opened = False

        self.logger.info(f"{self.oil_type} Oil Rig was called")
        await self.socket.send_team_message(f"{Emoji.EXCLAMATION}{self.oil_type} Oil Rig was called!")
        self.task = asyncio.create_task(self._timer())

    async def _timer(self):
        try:
            await asyncio.sleep(OPENING_TIME)
            if self.active:
                self.opened = True
                self.logger.info(f"{self.oil_type} Crate Opened!")
                await self.socket.send_team_message(
                    f"{Emoji.EXCLAMATION}Crate OPENED! {self.oil_type} Oil Rig!"
                )
        finally:
            await self.finish()

    async def finish(self):
        self.active = False
        if self.task:
            self.task.cancel()
            self.task = None

    async def time_left(self) -> int:
        if not self.active:
            return -1

        if self.opened:
            return 0
        
        left = OPENING_TIME - (time.time() - self.start_time)
        return max(0, int(left))


class CH47:
    def __init__(self, data, monuments) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        self.monuments = monuments
        
    def get_oilrig(self) -> tuple[bool, str | None]:

        return get_oil_info((self.x, self.y), self.monuments)
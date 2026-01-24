from rustWplus import RustSocket, Emoji
import time
from utils import convert_coordinates_to_grid


class Vendor:
    def __init__(self, data, socket: RustSocket, map_size) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        self.active: bool = True

        self.spawn_time: float = -1
        self.last_seen: float = -1

        self.socket: RustSocket = socket
        self.map_size: int = map_size

    async def on_spawn(self) -> None:
        self.active = True
        self.spawn_time = time.time()

        grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)
        await self.socket.send_team_message(
            f"{Emoji.EXCLAMATION}Travelling Vendor is active @ {grid}{number}"
        )

    async def on_despawn(self) -> None:
        if not self.active:
            return

        self.active = False
        self.last_seen = time.time()

        await self.socket.send_team_message(
            f"{Emoji.EXCLAMATION}Travelling Vendor is not active anymore"
        )

    async def get_info(self) -> None:
        if self.spawn_time < 0:
            await self.socket.send_team_message(
                f"{Emoji.EXCLAMATION}Travelling Vendor hasn't been active yet."
            )
            return

        if not self.active:
            time_delta = time.time() - self.last_seen
            minutes = int(time_delta) // 60
            seconds = int(time_delta) % 60

            await self.socket.send_team_message(
                f"{Emoji.EXCLAMATION}Travelling Vendor isn't active rn, last - {minutes}m{seconds:02d}s ago"
            )
            return

        grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)
        time_delta = int(time.time() - self.spawn_time) // 60

        await self.socket.send_team_message(
            f"{Emoji.EXCLAMATION}Travelling Vendor is active @ {grid}{number} ({time_delta}m already)"
        )

import time
from utils import convert_coordinates_to_grid, find_nearest_rad_town, convert_coordinates_to_map_side
from rustWplus import RustSocket, Emoji


class PatrolHelicopter:
    def __init__(self, data, map_size, socket: RustSocket, monuments) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        self.active: bool = True

        self.spawn_time: float = -1
        self.last_seen: float = -1

        self.monuments = monuments
        self.socket: RustSocket = socket
        self.map_size: int = map_size

    async def on_spawn(self) -> None:
        self.active = True
        self.spawn_time = time.time()

        side = convert_coordinates_to_map_side((self.x, self.y), self.map_size)
        await self.socket.send_team_message(f"{Emoji.EXCLAMATION}The Patrol Helicopter is active @ {side}")

    async def on_despawn(self) -> None:
        if not self.active:
            return

        self.active = False
        self.last_seen = time.time()

        await self.socket.send_team_message(f"{Emoji.EXCLAMATION}The Patrol Helicopter is leaving the Map")

    async def get_info(self) -> None:
        if self.spawn_time < 0:
            await self.socket.send_team_message("The Patrol Helicopter hasn't been active yet.")
            return

        if not self.active:
            time_delta = int(time.time() - self.last_seen) // 60
            await self.socket.send_team_message(
                f"{Emoji.EXCLAMATION}The Patrol Helicopter isn't active rn! (last {time_delta}m ago)"
            )
            return

        drop_place = find_nearest_rad_town((self.x, self.y), self.monuments) or "unknown"
        grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)
        time_delta = int(time.time() - self.spawn_time) // 60

        await self.socket.send_team_message(
            f"{Emoji.EXCLAMATION}The Patrol Helicopter is active @ {grid}{number} ({drop_place}) {time_delta}m already!"
        )

import time
from rustWplus import RustSocket, Emoji
from ..utils import find_nearest_rad_town, convert_coordinates_to_grid


class Crate:
    def __init__(self, data, socket, monuments, map_size) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        self.active: bool = True
        self.socket: RustSocket = socket

        self.spawn_time: float = -1
        self.last_seen: float = -1

        self.map_size = map_size
        self.monuments = monuments

    async def on_spawn(self) -> None:
        self.active = True
        self.spawn_time = time.time()

        drop_place = find_nearest_rad_town((self.x, self.y), self.monuments) or "unknown"
        grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)

        await self.socket.send_team_message(
            f"{Emoji.EXCLAMATION}A Locked Crate has been dropped @ {grid}{number} ({drop_place})"
        )

    async def on_despawn(self) -> None:
        if not self.active:
            return

        self.active = False
        self.last_seen = time.time()

        await self.socket.send_team_message(
            f"{Emoji.EXCLAMATION}A Locked Crate has been looted"
        )

    async def get_info(self) -> None:
        if self.spawn_time < 0:
            await self.socket.send_team_message("No Locked Crate has appeared yet.")
            return

        if self.active:
            drop_place = find_nearest_rad_town((self.x, self.y), self.monuments) or "unknown"
            grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)

            await self.socket.send_team_message(
                f"{Emoji.EXCLAMATION}Locked Crate has been dropped @ {grid}{number} ({drop_place})"
            )
        else:
            time_delta = int(time.time() - self.last_seen) // 60
            await self.socket.send_team_message(
                f"{Emoji.EXCLAMATION}Locked Crate is not active rn, last was {time_delta}m ago"
            )

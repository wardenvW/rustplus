from rustWplus import RustSocket, Emoji
from ..utils import convert_coordinates_to_grid, convert_coordinates_to_map_side, is_in_harbor, find_nearest_harbor_cords
import time

class CargoShip:
    def __init__(self, data, socket, map_size, monuments) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        self.active: bool = True
        self.socket: RustSocket = socket
        self.spawn_time: int = -1
        self.last_seen: int = -1
        self.in_harbor: bool = False

        self.map_size: int = map_size
        self.monuments = monuments
        self.can_send_message: bool = True

    async def on_spawn(self) -> None:
        self.active = True
        self.spawn_time = time.time()

        side = convert_coordinates_to_map_side((self.x, self.y), self.map_size)
        await self.socket.send_team_message(f"{Emoji.EXCLAMATION}The Cargo Ship is active @ {side}")

    async def on_despawn(self) -> None:
        self.last_seen = time.time()
        self.active = False
        self.in_harbor = False
        self.can_send_message = True

        await self.socket.send_team_message(f"{Emoji.EXCLAMATION}The Cargo Ship is leaving the Map")

    async def on_update(self, new_state) -> None:
        self.x = new_state.x
        self.y = new_state.y

        harbor_coords = find_nearest_harbor_cords((self.x, self.y), self.monuments)
        is_harbor = is_in_harbor((self.x, self.y), harbor_coords)

        if is_harbor and not self.in_harbor:
            grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)
            self.in_harbor = True

            if self.can_send_message:
                await self.socket.send_team_message(
                    f"{Emoji.EXCLAMATION}The Cargo Ship has docked @ {grid}{number} (Harbor)"
                )
                self.can_send_message = False

        elif not is_harbor and self.in_harbor:
            self.in_harbor = False
            self.can_send_message = True

    async def get_info(self) -> None:
        if self.active:
            time_delta = int(time.time() - self.spawn_time) // 60

            await self.socket.send_team_message(f"{Emoji.EXCLAMATION}The Cargo Ship is active! {time_delta}m already")
        else:
            time_delta = int(time.time() - self.last_seen) // 60
            await self.socket.send_team_message(f"{Emoji.EXCLAMATION}Last Cargo Ship was active {time_delta}m ago")
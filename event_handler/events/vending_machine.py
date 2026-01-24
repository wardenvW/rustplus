from rustWplus import RustSocket, Emoji
from utils import convert_coordinates_to_grid

class VendingMachine():
    def __init__(self, data, socket: RustSocket, map_size) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        
        self.socket: RustSocket = socket
        self.map_size: int = map_size

    async def on_spawn(self) -> None:
        grid, number = convert_coordinates_to_grid((self.x, self.y), self.map_size)

        await self.socket.send_team_message(f"{Emoji.EXCLAMATION}New Vending Machine on @ {grid}{number}")
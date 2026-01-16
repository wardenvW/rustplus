from events import CargoShip, CH47, Vendor, VendingMachine, PatrolHelicopter, Crate
from typing import List, Union
from rustWplus import RustSocket, RustError, RustMarker
import asyncio

class EventHandler:
    def __init__(self, socket: RustSocket) -> None:
        self.socket: RustSocket = socket
        self.vendor: Vendor = None
        self.crates: List[Crate] = None
        self.ch47s: List[CH47] = None
        self.vending_machines: List[VendingMachine] = None
        self.cargo: CargoShip = None
        self.patrol_heli: PatrolHelicopter = None

    
    async def start(self) -> None:
        while True:
            markers: Union[List[RustMarker], RustError] = await self.socket.get_markers()
            if isinstance(markers, RustError):
                continue

            current_events = [{'type': event.type, 'id': event.id, 'x': event.x, } for event in markers]

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.vendor_handler())
                tg.create_task(self.crates_handler())
                tg.create_task(self.ch47_handler())
                tg.create_task(self.vending_machines_handler())
                tg.create_task(self.cargo_handler())
                tg.create_task(self.patrol_heli_handler())

            await asyncio.sleep(1)

    async def vendor_handler(self) -> None:
        pass

    async def crates_handler(self) -> None:
        pass

    async def ch47_handler(self) -> None:
        pass

    async def vending_machines_handler(self) -> None:
        pass

    async def cargo_handler(self) -> None:
        pass

    async def patrol_heli_handler(self) -> None:
        pass
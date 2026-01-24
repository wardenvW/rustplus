from events import CargoShip, CH47, Vendor, VendingMachine, PatrolHelicopter, Crate, OilRigEvent
from typing import List, Union
from rustWplus import RustSocket, RustError, RustMarker, RustMonument, Emoji
import asyncio
from collections import defaultdict

OPENING_TIME = 900
class Marker:
    PlayerMarker = 1
    ExplosionMarker = 2
    VendingMachineMarker = 3
    ChinookMarker = 4
    CargoShipMarker = 5
    CrateMarker = 6
    RadiusMarker = 7
    PatrolHelicopterMarker = 8
    TravelingVendor = 9

class EventHandler:
    def __init__(self, socket: RustSocket, map_size: int = 4000) -> None:
        self.socket: RustSocket = socket

        self.vendor: Vendor | None = None
        self.crates: Crate | None = None
        self.ch47s: dict[int, CH47] = {}
        self.vending_machines: dict[int, VendingMachine] = {}
        self.cargo: CargoShip | None = None
        self.patrol_heli: PatrolHelicopter | None = None 

        self.oil_events = {
            "Small": OilRigEvent("Small", socket),
            "Large": OilRigEvent("Large", socket)
        }

        self.monuments: dict[str, list[RustMonument]] = defaultdict(list)
        self.map_size: int = map_size
    
    async def start(self) -> None:
        await self.init_monuments()

        while self.socket.ws.connection.open:
            markers: Union[List[RustMarker], RustError] = await self.socket.get_markers()
            if isinstance(markers, RustError):
                await asyncio.sleep(1)
                continue

            marker_by_id = {m.id: m for m in markers}


            await self.handle_vendor(marker_by_id)
            await self.handle_cargo(marker_by_id)
            await self.handle_patrol_heli(marker_by_id)
            await self.handle_crate(marker_by_id)

            await self.handle_ch47(marker_by_id)
            await self.handle_vending_machines(marker_by_id)
            

            await asyncio.sleep(1)

    # ----------------- SINGLE EVENTS -----------------
    async def handle_vendor(self, marker_by_id):
        marker = next(
            (m for m in marker_by_id.values() if m.type == Marker.TravelingVendor),
            None
        )

        if self.vendor is None and marker:
            self.vendor = Vendor(data=marker, socket=self.socket, map_size=self.map_size)

        if marker and (not self.vendor.active or self.vendor.id != marker.id):
            self.vendor = Vendor(data=marker, socket=self.socket, map_size=self.map_size)
            await self.vendor.on_spawn()

        elif not marker and self.vendor and self.vendor.active:
            await self.vendor.on_despawn()

        elif marker and self.vendor and self.vendor.active:
            self.vendor.x = marker.x
            self.vendor.y = marker.y


    async def handle_cargo(self, marker_by_id):
        marker = next((m for m in marker_by_id.values() if m.type == Marker.CargoShipMarker), None)

        if self.cargo is None:
            self.cargo = CargoShip(marker, self.socket, self.map_size, self.monuments)
            await self.cargo.on_spawn()

        if marker and (not self.cargo.active or self.cargo.id != marker.id):
            self.cargo = CargoShip(marker, self.socket, self.map_size, self.monuments)
            await self.cargo.on_spawn()

        elif not marker and self.cargo.active:
            await self.cargo.on_despawn()

        elif marker and self.cargo.active:
            await self.cargo.on_update(marker)

    async def handle_patrol_heli(self, marker_by_id):
        marker = next((m for m in marker_by_id.values() if m.type == Marker.PatrolHelicopterMarker), None)

        if marker and self.patrol_heli is None:
            self.patrol_heli = PatrolHelicopter(marker, self.map_size, self.socket, self.monuments)
            await self.patrol_heli.on_spawn()

        if not marker and self.patrol_heli is not None and self.patrol_heli.active:
            await self.patrol_heli.on_despawn()

        if marker and self.patrol_heli:
            self.patrol_heli.x = marker.x
            self.patrol_heli.y = marker.y
        
    async def handle_crate(self, marker_by_id):
        marker = next((m for m in marker_by_id.values() if m.type == Marker.CrateMarker), None)

        if marker and self.crates is None:
            self.crates = Crate(data=marker, socket=self.socket, monuments=self.monuments, map_size=self.map_size)
            await self.crates.on_spawn()

        if not marker and self.crates is not None and self.crates.active:
            await self.crates.on_despawn()

    # ----------------- MULTI EVENTS -----------------
    async def handle_ch47(self, marker_by_id):
        active = [m for m in marker_by_id.values() if m.type == Marker.ChinookMarker]

        for m in active:
            if m.id not in self.ch47s:
                self.ch47s[m.id] = CH47(data=m, socket=self.socket, monuments=self.monuments)
                await self.ch47s[m.id].on_spawn()

                is_oil, oil_type = self.ch47s[m.id].get_oilrig()
                if is_oil:
                    oil_event = self.oil_events[oil_type]
                    if not oil_event.active:
                        await oil_event.start()

        for id_ in list(self.ch47s.keys()):
            if id_ not in [m.id for m in active]:
                await self.ch47s[id_].on_despawn()
                del self.ch47s[id_]


    async def handle_vending_machines(self, marker_by_id):
        active = [m for m in marker_by_id.values() if m.type == Marker.VendingMachineMarker]

        for m in active:
            if m.id not in self.vending_machines:
                self.vending_machines[m.id] = VendingMachine(data=m, socket=self.socket, map_size=self.map_size)
                await self.vending_machines[m.id].on_spawn()


    async def init_monuments(self) -> None:
        monuments = await self.socket.get_monuments()
        if isinstance(monuments, RustError):
            return

        self.monuments = defaultdict(list)
        for m in monuments:
            self.monuments.setdefault(m.token, []).append(m)



from .events import CargoShip, CH47, Vendor, VendingMachine, PatrolHelicopter, Crate, OilRigEvent
from typing import List, Union, Optional
from rustWplus import RustSocket, RustError, RustMarker, RustMonument
from collections import defaultdict
import asyncio
import logging
import time

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
        self.just_start = True
        self.last_heartbeat: int = 0

        self.socket: RustSocket = socket
        self.logger: logging.Logger = logging.getLogger('events')

        self.vendor: Optional[Vendor] = None
        self.crates: Optional[Crate] = None
        self.ch47s: dict[int, CH47] = {}
        self.vending_machines: dict[int, VendingMachine] = {}
        self.cargo: Optional[CargoShip] = None
        self.patrol_heli: Optional[PatrolHelicopter] = None 

        self.oil_events = {
            "Small": OilRigEvent("Small", socket),
            "Large": OilRigEvent("Large", socket)
        }

        self.monuments: dict[str, list[RustMonument]] = defaultdict(list)
        self.map_size: int = map_size
    
    async def start(self) -> None:
        self.logger.info(f"Started monuments init [map_size={self.map_size}]")

        self.last_heartbeat = time.time() - 60

        await self.init_monuments()

        while self.socket.ws.connection.open:
            try:
                now = time.time()

                markers: Union[List[RustMarker], RustError] = await self.socket.get_markers()
                if now - self.last_heartbeat >= 60:
                    self.logger.info(
                        f"Polling active | "
                        f"tracked VM: {len(self.vending_machines)} | "
                        f"{time.strftime('%H:%M:%S')}"
                    )

                    self.last_heartbeat = time.time()

                    self.logger.debug("Markers response received")

                if isinstance(markers, RustError):
                    self.logger.warning("Catch RustError, trying to get markers again")
                    await asyncio.sleep(1)
                    continue
                
                marker_by_id = {m.id: m for m in markers}


                if self.just_start:
                    self.logger.info("Skipping old markers")
                    self.just_start = False
                    active_ids = {m.id for m in marker_by_id.values() if m.type == Marker.VendingMachineMarker}
                    for id in active_ids:
                        if id not in self.vending_machines:
                            m = marker_by_id[id]
                            self.logger.info(f"[NOW SHOWN] Added VendingMachine ({m.id}, {m.x}, {m.y})")
                            self.vending_machines[id] = VendingMachine(data=m, socket=self.socket, map_size=self.map_size)

                await self.handle_vendor(marker_by_id)
                await self.handle_cargo(marker_by_id)
                await self.handle_patrol_heli(marker_by_id)
                await self.handle_crate(marker_by_id)

                await self.handle_ch47(marker_by_id)
                await self.handle_vending_machines(marker_by_id)
                
            except Exception as e:
                self.logger.exception(f"EventHandler crashed: {e}")
                await asyncio.sleep(2)
            
            await asyncio.sleep(1)

    # ----------------- SINGLE EVENTS -----------------
    async def handle_vendor(self, marker_by_id):
        marker = next(
            (m for m in marker_by_id.values() if m.type == Marker.TravelingVendor),
            None
        )

        if self.vendor is None and marker:
            self.logger.info(f"Added first Vendor ({marker.id}, {marker.x}, {marker.y})")
            self.vendor = Vendor(data=marker, socket=self.socket, map_size=self.map_size)
            await self.vendor.on_spawn()

        elif marker and self.vendor is not None and (not self.vendor.active or self.vendor.id != marker.id):
            self.logger.info(f"Added new Vendor ({marker.id}, {marker.x}, {marker.y})")
            self.vendor = Vendor(data=marker, socket=self.socket, map_size=self.map_size)
            await self.vendor.on_spawn()

        elif not marker and self.vendor is not None and self.vendor.active:
            self.logger.info(f"Vendor despawn ({self.vendor.id}, {self.vendor.x}, {self.vendor.y})")
            await self.vendor.on_despawn()

        elif marker and self.vendor is not None and self.vendor.active:
            self.vendor.x = marker.x
            self.vendor.y = marker.y


    async def handle_cargo(self, marker_by_id):
        marker = next((m for m in marker_by_id.values() if m.type == Marker.CargoShipMarker), None)

        if self.cargo is None and marker:
            self.logger.info(f"Added first CargoShip ({marker.id}, {marker.x}, {marker.y})")
            self.cargo = CargoShip(data=marker, socket=self.socket, map_size=self.map_size, monuments=self.monuments)
            await self.cargo.on_spawn()

        elif marker and self.cargo is not None and (not self.cargo.active or self.cargo.id != marker.id):
            self.logger.info(f"Added new CargoShip ({marker.id}, {marker.x}, {marker.y})")
            self.cargo = CargoShip(data=marker, socket=self.socket, map_size=self.map_size, monuments=self.monuments)
            await self.cargo.on_spawn()

        elif not marker and self.cargo is not None and self.cargo.active:
            self.logger.info(f"Cargo Despawn ({self.cargo.id}, {self.cargo.x}, {self.cargo.y})")
            await self.cargo.on_despawn()

        elif marker and self.cargo is not None and self.cargo.active:
            await self.cargo.on_update(marker)


    async def handle_patrol_heli(self, marker_by_id):
        marker = next((m for m in marker_by_id.values() if m.type == Marker.PatrolHelicopterMarker), None)

        if marker and self.patrol_heli is None:
            self.logger.info(f"Added first PatrolHeli ({marker.id}, {marker.x}, {marker.y})")
            self.patrol_heli = PatrolHelicopter(data=marker, map_size=self.map_size, socket=self.socket, monuments=self.monuments)
            await self.patrol_heli.on_spawn()

        elif marker and self.patrol_heli is not None and (not self.patrol_heli.active or self.patrol_heli.id != marker.id):
            self.logger.info(f"Added new PatrolHeli ({marker.id}, {marker.x}, {marker.y})")
            self.patrol_heli = PatrolHelicopter(data=marker, map_size=self.map_size, socket=self.socket, monuments=self.monuments)
            await self.patrol_heli.on_spawn()

        elif not marker and self.patrol_heli is not None and self.patrol_heli.active:
            self.logger.info(f"Patrol Heli Despawn")
            await self.patrol_heli.on_despawn()

        elif marker and self.patrol_heli:
            self.patrol_heli.x = marker.x
            self.patrol_heli.y = marker.y

        
    async def handle_crate(self, marker_by_id):
        marker = next((m for m in marker_by_id.values() if m.type == Marker.CrateMarker), None)

        if marker and self.crates is None:
            self.logger.info(f"Added first Crate ({marker.id}, {marker.x}, {marker.y})")
            self.crates = Crate(data=marker, socket=self.socket, monuments=self.monuments, map_size=self.map_size)
            await self.crates.on_spawn()

        elif marker and self.crates is not None and (not self.crates.active or self.crates.id != marker.id):
            self.logger.info(f"Added new Crate ({marker.id}, {marker.x}, {marker.y})")
            self.crates = Crate(data=marker, socket=self.socket, monuments=self.monuments, map_size=self.map_size)
            await self.crates.on_spawn()

        elif not marker and self.crates is not None and self.crates.active:
            self.logger.info(f"Crate Despawn")
            await self.crates.on_despawn()


    # ----------------- MULTI EVENTS -----------------
    async def handle_ch47(self, marker_by_id):
        active = [m for m in marker_by_id.values() if m.type == Marker.ChinookMarker]

        for m in active:
            if m.id not in self.ch47s:
                self.logger.info(f"CH47 spawn ({m.id}, {m.x}, {m.y})")
                self.ch47s[m.id] = CH47(data=m, socket=self.socket, monuments=self.monuments)
                await self.ch47s[m.id].on_spawn()

                is_oil, oil_type = self.ch47s[m.id].get_oilrig()
                if is_oil and oil_type in self.oil_events:
                    oil_event = self.oil_events[oil_type]
                    if not oil_event.active:
                        self.logger.info(f"{oil_type} Oil")
                        await oil_event.start()
                else:
                    self.logger.warning(f"Unknown oil_type: {oil_type}")

        for id_ in list(self.ch47s.keys()):
            if id_ not in [m.id for m in active]:
                self.logger.info(f"CH47 Deleted ({self.ch47s[id_].id}, {self.ch47s[id_].x}, {self.ch47s[id_].y})")
                del self.ch47s[id_]


    async def handle_vending_machines(self, marker_by_id):
        active = [m for m in marker_by_id.values() if m.type == Marker.VendingMachineMarker]

        for m in active:
            if m.id not in self.vending_machines:
                self.logger.info(f"New Vending Machined added ({m.id}, {m.x}, {m.y})")
                self.vending_machines[m.id] = VendingMachine(data=m, socket=self.socket, map_size=self.map_size)
                await self.vending_machines[m.id].on_spawn()


    async def init_monuments(self) -> None:
        self.logger.info("Trying to call get_monuments()")
        monuments = await self.socket.get_monuments()
        if isinstance(monuments, RustError):
            self.logger.error(f"Got and error: {monuments}")
            return

        self.monuments = defaultdict(list)
        for m in monuments:
            self.monuments.setdefault(m.token, []).append(m)



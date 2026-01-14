from .tracked_player import TrackedPlayer
from typing import Union, Callable, Awaitable
from rustWplus.constants import BOOT_FILE
import time
import asyncio
import aiohttp
import os
import logging
import json
from dotenv import load_dotenv

load_dotenv()

INTERVAL = 15
UPDATE_RATE = 60
token = os.getenv('BM_TOKEN')
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

logger = logging.getLogger("rustWplus")

class TrackedList:
    def __init__(self, server_id: str = None) -> None:
        self._players: dict[str, TrackedPlayer] = {}
        self.server_id: str = server_id
        self._session: Union[aiohttp.ClientSession, None] = None
        self._on_status_change: Union[Callable[[TrackedPlayer, bool], Awaitable[None]], None] = None
        self.running: bool = True
        self._task: Union[asyncio.Task, None] = None

        self._lock: asyncio.Lock = asyncio.Lock()


    @property
    def players(self) -> dict[str, TrackedPlayer]:
        return self._players
    
    async def add_track(self, player: TrackedPlayer) -> None:
        if not self._session:
            raise RuntimeError("TrackedList.start() must be called before fetch_status")

        if player.bm_id is None:
            raise ValueError
        
        await self.fetch_status(player)
        self._players[player.bm_id] = player
        

        try:
            async with self._lock:
                if os.path.exists(BOOT_FILE):
                    with open(BOOT_FILE, 'r', encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {"server": {}, "paired_devices": [], "players": [], "server_bm_id": None}
                
                data["players"] = [p.serialize() for p in self._players.values()]
                with open(BOOT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)

        except Exception as e:
            print(f"Failed to update BOOT_FILE: {e}")
    
    async def fetch_status(self, player: TrackedPlayer, DEBUG: bool = True) -> None:
        try:
            url = f"https://api.battlemetrics.com/players/{player.bm_id}?include=server"

            async with self._session.get(url, headers=headers) as resp:
                data = await resp.json()
        except Exception as e:
            logger.warning(f"Failed to process player{player.nickname}: {e}")
            return

        if DEBUG:
            debug_file = f"players/debug_player_{player.bm_id}.json"
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            (f"Saved debug data to {debug_file}")

        player.nickname = data.get("data", {}).get("attributes", {}).get("name", "")
        
        old_status = player.online

        for server in data.get("included", []):
            if server.get("id") == self.server_id:
                player.online = server.get("meta", {}).get("online", False)
                break
        
        if old_status != player.online:
            if player.online:
                player._last_login = time.time()
            elif not player.online:
                player._last_logout = time.time()

        player._last_update = time.time()
        
        logger.info(f"{player.nickname} {player.bm_id} {'online' if player.online else 'offline'}")
        
                        

    def get_player(self, bm_id: str) -> Union[TrackedPlayer, None]:
        return self._players.get(bm_id)
    
    async def remove_track(self, bm_id: str):
        if bm_id in self._players:
            del self._players[bm_id]
            try:
                async with self._lock:
                    if os.path.exists(BOOT_FILE):
                        with open(BOOT_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        data = {"server": {}, "paired_devices": [], "players": [], "server_bm_id": None}
                        return
                    
                    data["players"] = [p.serialize() for p in self._players.values()]
                    with open(BOOT_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Failed to update BOOT_FILE: {e}")

    def serialize(self) -> dict:
        return {steamid: player.serialize() for steamid, player in self._players.items()}
    
    async def _update_list_status(self) -> None:
        while self.running:
            old_status = {p.bm_id: p.online for p in self._players.values()}
            changed = False

            for player in list(self._players.values()):
                if time.time() - player._last_update >= INTERVAL:
                    try:
                        await self.fetch_status(player)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"fetch_status failed for {player.bm_id}: {e}")

            for player in self._players.values():
                if player.bm_id in old_status:
                    if old_status[player.bm_id] != player.online:
                        changed = True
                        await self._on_status_change(player, player.online)

            if changed:
                try:
                    async with self._lock:
                        with open(BOOT_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        data["players"] = [p.serialize() for p in self._players.values()]

                        with open(BOOT_FILE, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"Failed to update BOOT_FILE: {e}")

            await asyncio.sleep(UPDATE_RATE)


    async def start(self) -> None:
        self.running = True
        self._session = aiohttp.ClientSession()

        while True:
            with open(BOOT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            server = data.get("server", {})
            server_bm_id = data.get("server_bm_id")

            if server and (server_bm_id or (server.get("ip") and server.get("name"))):
                break

            await asyncio.sleep(1)

        if not server_bm_id:
            server_bm_id = await self.get_server_id(server_name=server["name"], server_ip=server["ip"])

            self.server_id = server_bm_id
            data["server_bm_id"] = server_bm_id

            with open(BOOT_FILE, 'w', encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            self.server_id = server_bm_id

        self._task = asyncio.create_task(self._update_list_status())


    async def stop(self):
        self.running = False
        if self._session:
            await self._session.close()
        try:
            await self._task
        except Exception:
            pass
        self._task = None

    async def get_server_id(self, server_name: str, server_ip: str) -> Union[str, None]:
        url = "https://api.battlemetrics.com/servers"
        params = {
            "filter[game]": "rust",
            "filter[search]": server_name,  
        }

        async with self._session.get(url, params=params) as resp:
            data = await resp.json()

        candidates = []
        
        for srv in data.get("data", []):
            ip = srv["attributes"]["ip"]
            if ip == server_ip:
                candidates.append(srv)

        # уточняем по имени
        if len(candidates) > 1:
            candidates = [srv for srv in candidates if srv["attributes"]["name"].lower().strip() == server_name.lower().strip()]

        if not candidates:
            raise ValueError("Server not found")

        server_id = candidates[0]["id"]
        
        return server_id
        



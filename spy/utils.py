import os
import json
from dotenv import load_dotenv
from rustWplus import RustServer
from .spy_models import TrackedList

load_dotenv()

BM_TOKEN = os.getenv("BM_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {BM_TOKEN}",
    "Accept": "application/json"
}

async def get_server_id(player_list: TrackedList, server_name: str, server_ip: str ,DEBUG: bool = False):
    url = "https://api.battlemetrics.com/servers"
    params = {
        "filter[game]": "rust",
        "filter[search]": server_name,
    }

    async with player_list._session.get(url, headers=HEADERS, params=params) as resp:
        data = await resp.json()

    if DEBUG:
        debug_file = "debug_servers.json"
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved debug data to {debug_file}")

    if "data" in data:
        for server in data["data"]:
            if server.get("attributes").get("ip") == server_ip:
                player_list.server_id = server.get("id")
                break


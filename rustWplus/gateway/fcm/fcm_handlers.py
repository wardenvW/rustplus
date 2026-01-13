import json
import logging
from rustWplus.constants import BOOT_FILE

class FCMHandler:
    def __init__(self) -> None:
        self.logger = logging.getLogger("rustWplus.py")

    def handle(self, fcm_message):
        self.logger.info("Handling pairing notification")
        self._extract_push_info(fcm_message=fcm_message)
    
    def _extract_push_info(self, fcm_message):

        for app_data in fcm_message.app_data:
            if app_data.key == "body":
                try:
                    data = json.loads(app_data.value)
                    msg_type = data.get("type")

                    if msg_type == "server":
                        self._handle_server_pair(data)

                    elif msg_type == "entity":
                        self._handle_entity_pair(data)
                    
                    else:
                        self.logger.warning("Unknown pairing type")

                except Exception as e:
                    self.logger.error(f"Failed to extract body: {e}")

                return


    def _handle_entity_pair(self, data: dict):
        try:
            with open(BOOT_FILE, 'r', encoding='utf-8') as f:
                boot_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read boot file: {e}")
            boot_data = {"server": {}, "paired_devices": [], "players": [], "server_bm_id": None}

        entities = boot_data.get("paired_devices", [])

        entity_id = data.get("entityId")
        for entity in entities:
            if entity.get("entity_id") == entity_id:
                self.logger.info("Entity is already paired")
                return

        new_entity = {
            "entity_id": entity_id,
            "entity_type": data.get("entityType"),
            "entity_name": data.get("entityName")
        }
        entities.append(new_entity)
        boot_data["paired_devices"] = entities

        try:
            with open(BOOT_FILE, 'w', encoding='utf-8') as f:
                json.dump(boot_data, f, ensure_ascii=False, indent=2)
            self.logger.info("Saved entity info in boot.json")
        except Exception as e:
            self.logger.error(f"Failed to write boot file: {e}")

    def _handle_server_pair(self, data: dict):
        with open(BOOT_FILE, 'r', encoding='utf-8') as f:
            boot_data = json.load(f)

        old_server = boot_data.get("server", {})

        if old_server.get("ip") == data.get("ip"):
            old_server["player_token"] = data.get("playerToken", old_server.get("player_token"))
            old_server["player_id"] = data.get("playerId", old_server.get("player_id"))
            self.logger.info("Same server detected, updating token and player_id only")
        else:
            old_server = {
                "ip": data.get("ip"),
                "port": data.get("port"),
                "player_id": data.get("playerId", []),
                "player_token": data.get("playerToken", []),
                "name": data.get("name")
            }
            boot_data["players"] = []
            boot_data["paired_devices"] = []
            boot_data["server_bm_id"] = None
            self.logger.info("New server detected, replacing server info")

        boot_data["server"] = old_server 

        try:
            with open(BOOT_FILE, 'w', encoding='utf-8') as f:
                json.dump(boot_data, f, ensure_ascii=False, indent=2)
                self.logger.info("Server info saved")
        except Exception as e:
            self.logger.error(f"Failed to write server info: {e}")
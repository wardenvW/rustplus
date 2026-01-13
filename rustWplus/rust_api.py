import asyncio
from importlib import resources
from io import BytesIO
from typing import List, Union
import logging
from PIL import Image

from .commands import CommandOptions
from .identification import RustServer
from .gateway.rustplus_proto import (
    AppRequest,
    AppEmpty,
    AppSendMessage,
    AppSetEntityValue,
    AppPromoteToLeader,
    AppMapMonument,
    AppFlag,
)
from .gateway.websocket import RustWebSocket
from .rust_models import (
    RustTime,
    RustServerInfo,
    RustChatMessage,
    RustTeamInfo,
    RustMarker,
    RustMap,
    RustEntityInfo,
)
from .rust_models.rust_error import RustError
from .utils import (
    convert_time,
    generate_grid,
    fetch_avatar_icon,
    format_coords,
    convert_marker,
    convert_monument,
)
from .gateway.ratelimiter import RateLimiter
from .utils.utils import error_present

class RustSocket:
    def __init__(
            self,
            server_details: RustServer,
            ratelimiter: Union[RateLimiter, None] = None,
            command_options: Union[CommandOptions, None] = None,
            use_fp_proxy: bool = False,
            debug: bool = False
    ) -> None:
        self.server_details: RustServer = server_details
        self.command_options: Union[CommandOptions, None] = command_options
        self.logger = logging.getLogger("rustWplus.py")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.DEBUG)

        self.ws = RustWebSocket(
            self.server_details,
            self.command_options,
            use_fp_proxy,
            debug
        )
        self.seq = 1


        if ratelimiter:
            self.ratelimiter = ratelimiter
        else:
            self.ratelimiter = RateLimiter()
        
        self.ratelimiter.add_socket(self.server_details)


    async def _handle_ratelimit(self, tokens) -> None:
        while True:
            if await self.ratelimiter.can_consume(self.server_details, tokens):
                await self.ratelimiter.consume(self.server_details, tokens)
                break
            
            await asyncio.sleep(
                await self.ratelimiter.get_estimated_delay_time(self.server_details, tokens)
            )

    async def _generate_request(self, tokens:int = 1) -> AppRequest:
        await self._handle_ratelimit(tokens)

        app_request = AppRequest()
        app_request.seq = self.seq
        self.seq += 1
        app_request.player_id = self.server_details.player_id
        app_request.player_token = self.server_details.player_token

        return app_request
    
    async def connect(self) -> bool:
        if await self.ws.connect():
            await self.get_time()
            return True
        return False
    
    async def disconnect(self) -> None:
        await self.ws.disconnect()

    
    @staticmethod
    async def keep_programm_alive() -> None:
        while True:

            """
            Keeping alive, while listening events(AppMessages)
            """

            await asyncio.sleep(1)

    async def get_time(self) -> Union[RustTime, RustError]:

        """

        Gets the current in-game time from the server.

        """

        packet = await self._generate_request(tokens=1)
        packet.get_time = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_time", "No response received")
        
        if error_present(response):
            return RustError("get_time", response.response.error.error)


        return RustTime(
            response.response.time.day_length_minutes,
            convert_time(response.response.time.sunrise),
            convert_time(response.response.time.sunset),
            convert_time(response.response.time.time),
            response.response.time.time,
            response.response.time.time_scale,
        )
    
    async def get_info(self) -> Union[RustServerInfo, RustError]:
        """

        Gets Info On Server     

        """

        packet = await self._generate_request(tokens = 1)
        packet.get_info = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_info", "No response received")
        
        if error_present(response):
            return RustError("get_info", response.response.error.error)
        
        return RustServerInfo(response.response.info)
    

    async def get_team_chat(self) -> Union[List[RustChatMessage], RustError]:
        """
        
        Gets the team chat
        
        """

        packet = await self._generate_request(tokens = 1)
        packet.get_team_chat = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_team_chat", "No response received")
        
        if error_present(response):
            return RustError("get_team_chat", response.response.error.error)
        
        return [
            RustChatMessage(message) for message in response.response.team_chat.messages
        ]
    
    async def get_team_info(self) -> Union[RustTeamInfo, RustError]:
        """
        
        Gets the team info

        """

        packet = await self._generate_request(tokens = 1)
        packet.get_team_info = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_team_info", "No response received")

        if error_present(response):
            return RustError("get_team_info", response.response.error.error)
        
        return RustTeamInfo(response.response.team_info)
    
    async def get_markers(self) -> Union[List[RustMarker], RustError]:
        """
        
        Gets all server's markers
        
        """

        packet = await self._generate_request()
        packet.get_map_markers = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_map_markers", "No response received")

        if error_present(response):
            return RustError("get_map_markers", response.response.error.error)
        
        return [RustMarker(marker) for marker in response.response.map_markers]
    
    async def get_map(
            self,
            add_icons: bool = False,
            add_events: bool = False,
            add_vending_machines: bool = False,
            add_team_positions: bool = False,
            add_extra_images: dict = None,
            show_grid: bool = False,
    ) -> Union[Image.Image, RustError]:
        
        """
        Gets an image of the map from the server with the specified parameters

        add_icons: To add the monument icons
        add_events: To add the Event icons
        add_vending_machines: To add the vending icons
        add_team_positions: To add the team positions
        add_extra_images: To override the images pre-supplied with RustPlus.py
        show_grid: To add the grid to the map
        return: PIL Image

        """

        if add_extra_images is None:
            add_extra_images = {}
        
        server_info = await self.get_info()
        if isinstance(server_info, RustError):
            return server_info
        
        map_size = server_info.size

        packet = await self._generate_request(tokens = 5)
        packet.get_map = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_map", "No response received")

        if error_present(response):
            return RustError("get_map", response.response.error.error)
        
        map_packet = response.response.map
        monuments: List[AppMapMonument] = map_packet.monuments

        try:
            output = Image.open(BytesIO(map_packet.jpg_image))
        except Exception as e:
            self.logger.error(f"Error opening image: {e}")
            return RustError("get_map", str(e))
        
        output = output.crop(
            (500, 500, map_packet.height - 500, map_packet.width - 500)
        )

        output = output.resize((map_size, map_size), Image.LANCZOS).convert("RGBA")

        if show_grid:
            output.paste(grid := generate_grid(map_size), (5, 5), grid)
        
        if add_icons or add_events or add_vending_machines:
            map_markers = (
                await self.get_markers() if add_events or add_vending_machines else []
            )
            
            if add_icons:
                for monument in monuments:
                    if str(monument.token) == "DungeonBase":
                        continue
                    icon = convert_monument(str(monument.token), add_extra_images)
                    if monument.token in add_extra_images:
                        icon = icon.resize((150, 150))
                    if str(monument.token) == "train_tunnel_display_name":
                        icon = icon.resize((100, 125))
                    
                    output.paste(
                        icon,
                        (format_coords(x = int(monument.x), y = int(monument.y), map_size=map_size)),
                        icon
                    )

        if add_vending_machines:
            with resources.path("rustWplus.resources.icons", "vending_machine.png") as path:
                vending_machine = Image.open(path).convert("RGBA")
                vending_machine = vending_machine.resize((100, 100))

        
        for marker in map_markers:
            if add_events:
                if marker.type in [2, 4, 5, 6, 8]:
                    icon = convert_marker(int(marker.type), marker.rotation)
                    if marker.type == 6:
                        x, y = marker.x, marker.y
                        y = min(max(y, 0), map_size)
                        x = min(max(x, 0), map_size - 75 if x > map_size else x)
                        output.paste(icon, (int(x), map_size - int(y)), icon)
                    else:
                        output.paste(
                            icon,
                            (format_coords(int(marker.x), int(marker.y), map_size)),
                            icon
                        )
            
            if add_vending_machines and marker.type == 3:
                output.paste(
                    vending_machine,
                    (int(marker.x) - 50, map_size - int(marker.y) - 50),
                    vending_machine
                )
        if add_team_positions:
            team = await self.get_team_info()
            if team is not None:
                for member in team.members:
                    if not member.is_alive:
                        continue

                    output.paste(
                        avatar := await fetch_avatar_icon(member.steam_id, member.is_online),
                        format_coords(int(member.x), int(member.y), server_info.size),
                        avatar
                    )
        return output
    
    async def get_map_info(self) -> Union[RustMap, RustError]:
        """
        
        Raw map data

        """
        packet = await self._generate_request(tokens=5)
        packet.get_map = AppEmpty()
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_map_info", "No response received")

        if error_present(response):
            return RustError("get_map_info", response.response.error.error)
        
        return RustMap(response.response.map)
    
    async def get_entity_info(self, entity_id: int = None) -> Union[RustEntityInfo, RustError]:
        """
        Gets entity info from the server

        entity_id: The Entities ID

        """

        packet = await self._generate_request(tokens=1)
        packet.get_entity_info = AppEmpty()
        packet.entity_id = entity_id
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("get_entity_info", "No response received")

        if error_present(response):
            return RustError("get_entity_info", response.response.error.error)

        return RustEntityInfo(response.response.entity_info)
    
    async def set_entity_value(self, entity_id: int, value: bool = False) -> None:
        """
        
        To turn on/off Smart Switch
        
        """

        packet = await self._generate_request(tokens=1)
        set_value = AppSetEntityValue()
        set_value.value = value
        packet.set_entity_value = set_value
        packet.entity_id = entity_id

        return await self.ws.send_message(packet, True)





    async def set_subscription_to_entity(self, entity_id: int, value: bool = True) -> None:
        """
        Subscribes to an entity for events

        entity_id: The Entities ID
        value: The value to set the subscription to

        """
        
        packet = await self._generate_request(tokens=1)
        flag = AppFlag()
        flag.value = value
        packet.set_subscription = flag
        packet.entity_id = entity_id

        await self.ws.send_message(packet, True)

    async def check_subscription_to_entity(self, entity_id: int) -> Union[bool, RustError]:
        """
        Check if you are subscribed to an entity

        entity_id: The Entities ID
        
        """
        
        packet = await self._generate_request(tokens=1)
        packet.check_subscription = AppEmpty()
        packet.entity_id = entity_id
        response = await self.ws.send_and_get(packet)

        if response is None:
            return RustError("check_subscription_to_entity", "No response received")

        if error_present(response):
            return RustError(
                "check_subscription_to_entity", response.response.error.error
            )

        return response.response.flag.value
    

    async def promote_to_leader(self, steamid: int = None) -> None:
        """
        Promotes a given user to the team leader by their SteamID64

        steamid: The SteamID of the player to promote
        """
        packet = await self._generate_request(tokens=1)
        promote_packet = AppPromoteToLeader()
        promote_packet.steam_id = steamid
        packet.promote_to_leader = promote_packet

        await self.ws.send_and_get(packet, True)
    

    async def send_team_message(self, message: str) -> None:
        """
        
        Sends message to your in-game team chat 
        
        message: message u want to send

        """

        packet = await self._generate_request(tokens=2)
        send_message = AppSendMessage()
        send_message.message = message
        packet.send_team_message = send_message

        await self.ws.send_message(packet, True)
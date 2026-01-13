import shlex
import betterproto
from websockets.exceptions import InvalidURI, InvalidHandshake, ConnectionClosedError
from websockets.legacy.client import WebSocketClientProtocol
from websockets.client import connect
from asyncio import TimeoutError, Task
from typing import Union, Optional, Set, Dict
import logging
import asyncio

from ..proxy import ProxyValueGrabber
from ..rustplus_proto import AppMessage, AppRequest, AppError
from ...commands import CommandOptions, ChatCommand, ChatCommandTime
from ...events import (
    ProtobufEventPayload,
    EntityEventPayload,
    TeamEventPayload,
    ChatEventPayload,
)
from ...exceptions import RequestError
from ...identification import RustServer, RegisteredListener
from ...rust_models import RustChatMessage, RustTeamInfo
from ...utils import YieldingEvent, convert_time, error_present


class RustWebSocket:
    RESPONSE_TIMEOUT = 10
    def __init__(
            self,
            server_details: RustServer,
            command_options: Union[CommandOptions, None],
            use_fp_proxy: bool,
            debug: bool
    ) -> None:
        self.server_details: RustServer = server_details
        self.command_options: Union[CommandOptions, None] = command_options
        self.connection: Union[WebSocketClientProtocol, None] = None
        self.task: Union[Task, None] = None
        self.use_fp_proxy: bool = use_fp_proxy
        self.logger: logging.Logger = logging.getLogger("rustWplus.py")
        self.responses: Dict[int, YieldingEvent] = {}
        self.open: bool = False
        self.debug: bool = debug

    
    async def connect(self) -> bool:

        address = ( 
            (
                f"{'wss' if self.server_details.secure else 'ws'}://"
                + self.server_details.get_server_string()
            )
            if not self.use_fp_proxy
            else f"wss://companion-rust.facepunch.com/game/{self.server_details.ip}/{self.server_details.port}"
        ) + f"?v={ProxyValueGrabber.get_value()}"

        try:
            self.connection = await connect(
                address,
                close_timeout = 0,
                ping_interval = None,
                max_size = 1_000_000_000
            )
        except (InvalidURI, OSError, InvalidHandshake, TimeoutError) as err:
            self.logger.warning(f"Websocket connection error: {err}")
            return False
        if self.debug:
            self.logger.info(f"Websocket connection established to {address}")
        
        self.task = asyncio.create_task(self.run(), name="[RustWPlus.py] Websocket Polling Task")

        self.open = True

        return True
    
    async def disconnect(self) -> None:
        if self.connection and self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

            self.task = None

            self.open = False
            await self.connection.close()
            self.connection = None

    async def run(self) -> None:
        while self.open:
            try:
                data = await self.connection.recv()

                asyncio.create_task(self.run_proto_event(data, self.server_details))

                app_message = AppMessage()
                app_message.parse(data)

            except ConnectionClosedError as e:
                if self.debug:
                    self.logger.warning(f"Connection Interrupted: {e}")
                    break
            
            except Exception as e:
                if self.debug:
                    self.logger.exception(f"Error occurred whilst parsing the message from server: {e}")
                continue
            try:
                asyncio.create_task(self.handle_message(app_message))
            except Exception as e:
                self.logger.exception(
                    f"An Error occurred whilst handling the message from the server %s",
                    e,
                )
    
    async def send_and_get(self, request: AppRequest) -> AppMessage:
        if not await self.send_message(request):
            message = AppMessage()
            error = AppError()
            error.error = "Message Failed to send"
            message.response.seq = request.seq
            message.response.error = error
            return message
        return await self.get_response(request.seq)

    async def send_message(self, request: AppRequest, ignore_response: bool = False) -> bool:
        if self.connection is None:
            self.logger.warning("No Current WebSocket Connection")
            return False
        
        if self.debug:
            self.logger.info(f"Sending Message[{request.seq}]: {request}")
        
        if not ignore_response:
            self.responses[request.seq] = YieldingEvent()
        
        try:
            await self.connection.send(bytes(request))
        except Exception as err:
            self.logger.warning(f"WebSocket Connection Error: {err}")
            return False
        return True
            
    async def get_response(self, seq: int) -> Union[AppMessage, None]:

        response = await self.responses[seq].wait(timeout=self.RESPONSE_TIMEOUT)
        del self.responses[seq]

        return response
    
    async def handle_message(self, app_message: AppMessage) -> None:
        if self.debug:
            self.logger.info(f"Received Message[{app_message.response.seq}]: {app_message}")
        
        if error_present(app_message):
            event: YieldingEvent = self.responses.get(app_message.response.seq, None)
            if event is not None:
                if self.debug:
                    self.logger.info(f"Running Response With Error: {app_message}")
                
                event.set_with_value(app_message)
            else:
                raise RequestError(app_message.response.error.error)
        
        prefix = self.get_prefix(str(app_message.broadcast.team_message.message.message))

        if prefix is not None:
            if self.debug:
                self.logger.info(f"Attempting to run COMMAND: {app_message}")
            
            message = RustChatMessage(app_message.broadcast.team_message.message)

            parts = shlex.split(message.message)
            command = parts[0][len(prefix) :]

            data = ChatCommand.REGISTERED_COMMANDS[self.server_details].get(command, None)

            dao = ChatCommand(
                message.name,
                message.steam_id,
                ChatCommandTime(
                    convert_time(message.time),
                    message.time
                ),
                command,
                parts[1:],
            )
            if data is not None:
                await data.coroutine(dao)
            else:
                for command_name, data in ChatCommand.REGISTERED_COMMANDS[self.server_details].items():
                    if command in data.aliases or data.callable_func(command):
                        await data.coroutine(dao)
                        break

        if self.is_entity_broadcast(app_message):
            # Entity Event 
            if self.debug:
                self.logger.info(f"Running Entity Event: {app_message}")
            
            handlers = EntityEventPayload.HANDLER_LIST.get_handlers(self.server_details).get(str(app_message.broadcast.entity_changed.entity_id), [])
            for handler in handlers:
                await handler.get_coro()(EntityEventPayload(entity_changed=app_message.broadcast.entity_changed)) 

        elif self.is_team_broadcast(app_message):
            # Team Event
            if self.debug:
                self.logger.info(f"Running Team Event: {app_message}")

            handlers = TeamEventPayload.HANDLER_LIST.get_handlers(self.server_details)
            team_event = TeamEventPayload(
                app_message.broadcast.team_changed.player_id,
                RustTeamInfo(app_message.broadcast.team_changed.team_info)
            )
            for handler in handlers:
                await handler.get_coro()(team_event)


        elif self.is_message(app_message):
            # Chat Message Event
            if self.debug:
                self.logger.info(f"Running Chat Event: {app_message}")
            
            handlers = ChatEventPayload.HANDLER_LIST.get_handlers(self.server_details)
            chat_event = ChatEventPayload(
                app_message.broadcast.team_message.message
            )
            for handler in handlers:
                await handler.get_coro()(chat_event)
        
        else:
            # This means that it wasn't sent by the server and is a message from the server in response to an action
            event: YieldingEvent = self.responses.get(app_message.response.seq, None)
            if event is not None:
                if self.debug:
                    self.logger.info(f"Running Response Event: {app_message}")

                event.set_with_value(app_message)
       
    def get_prefix(self, message: str) -> Optional[str]:
        if self.command_options is None:
            return None
        
        if message.startswith(self.command_options.prefix):
            return self.command_options.prefix
        else:
            return None

    @staticmethod
    def is_message(app_message: AppMessage) -> bool:
        return betterproto.serialized_on_wire(app_message.broadcast.team_message.message)

    @staticmethod
    def is_entity_broadcast(app_message: AppMessage) -> bool:
        return betterproto.serialized_on_wire(app_message.broadcast.entity_changed)

    @staticmethod
    def is_team_broadcast(app_message: AppMessage) -> bool:
        return betterproto.serialized_on_wire(app_message.broadcast.team_changed)

    @staticmethod
    def get_proto_cost(app_request: AppRequest) -> int:

        costs = [
            (app_request.get_time, 1),
            (app_request.send_team_message, 2),
            (app_request.get_info, 1),
            (app_request.get_team_chat, 1),
            (app_request.get_team_info, 1),
            (app_request.get_map_markers, 1),
            (app_request.get_map, 5),
            (app_request.set_entity_value, 1),
            (app_request.get_entity_info, 1), 
            (app_request.promote_to_leader, 1)
        ]
        for request, cost in costs:
            if betterproto.serialized_on_wire(request):
                return cost
        raise ValueError()


    @staticmethod
    async def run_proto_event(data: Union[str, bytes], server_details: RustServer) -> None:
        handlers: Set[RegisteredListener] = ProtobufEventPayload.HANDLER_LIST.get_handlers(server_details)

        for handler in handlers:
            await handler.get_coro()(data)  
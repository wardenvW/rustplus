import asyncio
import json
import os
import logging
import time
from rustWplus import (
    RustSocket, CommandOptions, Command, RustServer, ChatCommand,
    FCMListener, RateLimiter, RustServerInfo, Emoji,
    format_time_simple, RustError
)
from rustWplus.constants import BOOT_FILE, FCM_FILE
from spy import TrackedPlayer, TrackedList

async def prepare_spying(tracking_list: TrackedList, logger: logging.Logger) -> None:
    logger.info("Preparing spy functional")

    if not os.path.exists(BOOT_FILE):
        logger.info("No boot file found, starting with empty tracking list.")
        return

    try:
        with open(BOOT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        players_list = data.get("players", [])
        loaded = 0

        for player_data in players_list:
            player = TrackedPlayer.load_from_dict(player_data)

            if player.bm_id in tracking_list.players:
                continue

            await tracking_list.add_track(player)
            loaded += 1 

        logger.info(f"Loaded {loaded} players from file.")

    except Exception as e:
        logger.warning(f"Failed to read tracked players list: {e}")

    logger.info("Spying ready!")

async def run_bot(socket: RustSocket, tracking: TrackedList, server_details: RustServer, logger: logging.Logger):
    """Запускаем команды Rust+ через WebSocket с health check"""
    logger.info("Running bot commands...")

    async def on_status_change(player: TrackedPlayer, online: bool):
        status_msg = "joined" if online else "left"
        message = f"{player.nickname} {status_msg}"
        try:
            await socket.send_team_message(f"{Emoji.EXCLAMATION}{message}")
        except RustError:
            logger.warning("Failed to send spy info")

    tracking._on_status_change = on_status_change

    # ------------------- Health Check -------------------
    async def bot_health_check():
        while True:
            await asyncio.sleep(60)

            result = await socket.get_time()

            if isinstance(result, RustError):
                logger.warning(f"[HEALTH CHECK] Server did not respond")
            else:
                logger.info(f"[HEALTH CHECK] Server OK at {time.strftime('%H:%M:%S')}")

    health_task = asyncio.create_task(bot_health_check())

    try:
        # ------------------- КОМАНДЫ -------------------
        @Command(server_details, aliases=["time", "время"])
        async def f_time(command: ChatCommand):
            result = await socket.get_time()
            if isinstance(result, RustError):
                logger.error(f"Failed to get server time: {result}")
                await socket.send_team_message("Failed to get server time")
                return
            await socket.send_team_message(format_time_simple(result))

        @Command(server_details, aliases=["pop", "онлайн"])
        async def pop(command: ChatCommand):
            try:
                info: RustServerInfo = await socket.get_info()
                await socket.send_team_message(
                    f"{Emoji.EXCLAMATION}Online {info.players}/{info.max_players}, {info.queued_players} in queue"
                )
            except RustError as e:
                logger.error(f"Failed to get server online: {e}")
        
        @Command(server_details)
        async def add(command: ChatCommand):
            if not command.args:
                await socket.send_team_message("Add id")
                return
            bm_id = command.args[0]
            player = TrackedPlayer(bm_id=bm_id, server_id=tracking.server_id)
            await tracking.add_track(player)
            await socket.send_team_message(f"{player.nickname}({bm_id}) added")

        @Command(server_details)
        async def delete(command: ChatCommand):
            if not command.args:
                await socket.send_team_message("Add id to delete")
                return
            bm_id = command.args[0]
            player = tracking.get_player(bm_id)
            if player:
                await tracking.remove_track(bm_id)
                await socket.send_team_message(f"{player.nickname} deleted")
            else:
                await socket.send_team_message(f"({bm_id}) not found")

        @Command(server_details)
        async def all(command: ChatCommand):
            for player in tracking.players.values():
                minutes = -1
                if player.online and player.last_login:
                    minutes = int((time.time() - player.last_login) // 60)
                elif not player.online and player.last_logout:
                    minutes = int((time.time() - player.last_logout) // 60)

                status = "online" if player.online else "offline"
                time_str = f"{minutes}min ago"
                await socket.send_team_message(f"{Emoji.BED}{player.nickname} {status}({time_str})")
                await asyncio.sleep(3.2)

        @Command(server_details)
        async def status(command: ChatCommand):
            if not command.args:
                await socket.send_team_message(f"{Emoji.EXCLAMATION}!status [id]")
                return
            bm_id = command.args[0]
            player = tracking.get_player(bm_id)
            if player:
                status = "online" if player.online else "offline"
                await socket.send_team_message(f"{Emoji.EXCLAMATION}{player.nickname} {status}")
            else:
                await socket.send_team_message(f"Player({bm_id}) not found.")

        # ------------------- Keep alive -------------------
        await socket.keep_programm_alive()
    
    finally:
        # Отменяем health check при завершении работы бота
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            logger.info("Health check task cancelled")



async def main():
    # ------------------- ЛОГИРОВАНИЕ -------------------
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # удаляем все старые обработчики
    root_logger.setLevel(logging.DEBUG)


    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:%(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

    logger = logging.getLogger("rustWplus")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(filename='logs.log', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # ------------------- Проверка boot.json -------------------
    default_data = {
        "server": {},
        "paired_devices": [],
        "players": [],
        "server_bm_id": None,
    }

    if not os.path.exists(BOOT_FILE):
        with open(BOOT_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False)
        logger.info("Data not found, boot.json created")
    else:
        logger.info("Loading data")

    # ------------------- FCM Listener -------------------
    if os.path.exists(FCM_FILE):
        with open(FCM_FILE, 'r') as f:
            listener = FCMListener(json.load(f))
        listener.start()
        logger.info("FCM Listener started")

    # ------------------- Слежка -------------------
    tracking = TrackedList()
    await tracking.start()
    # ------------------- Бесконечный reconnect -------------------
    while True:
        try:
            with open(BOOT_FILE, "r") as f:
                server_data = json.load(f).get("server", {})

            server_details = RustServer(
                ip=server_data.get("ip"),
                port=server_data.get("port"),
                player_id=server_data.get("player_id"),
                player_token=server_data.get("player_token")
            )

            socket = RustSocket(
                server_details=server_details,
                command_options=CommandOptions(prefix="!"),
                ratelimiter=RateLimiter().default(),
                debug=True
            )

            logger.info("Connecting to Rust+ WebSocket...")
            if await socket.connect():
                logger.info("Connected!")
                await prepare_spying(tracking, logger)
                await run_bot(socket, tracking, server_details, logger)

        except Exception as e:
            logger.exception("WebSocket crashed, reconnecting in 5 seconds")
        finally:
            if socket:
                try:
                    await socket.disconnect()
                except  Exception:
                    logger.exception("Error while closing socket")

        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())

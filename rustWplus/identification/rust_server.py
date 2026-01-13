from typing import Union

class RustServer:
    def __init__(
            self,
            ip: str,
            port: Union[str, int, None],
            player_id: int,
            player_token: int,
            secure: bool = False,
    ) -> None:
        self.ip = str(ip)
        self.port = str(port) if port is not None else port
        self.player_id = int(player_id)
        self.player_token = int(player_token)
        self.secure = secure


    def get_server_string(self) -> str:
        if self.port == None:
            return f"{self.ip}"
        return f"{self.ip}:{self.port}"
    
    def __str__(self) -> str:
        return f"{self.ip}:{self.port} {self.player_id} {self.player_token}"

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, obj: object) -> bool:
        if not isinstance(obj, RustServer):
            return False
        
        return (
            self.ip == obj.ip,
            self.port == obj.port,
            self.player_id == obj.player_id,
            self.player_token == obj.player_token
        )
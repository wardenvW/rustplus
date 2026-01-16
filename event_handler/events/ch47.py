import time

class CH47:
    def __init__(self, data) -> None:
        self.id: int = data.id
        self.x: int = data.x
        self.y: int = data.y
        self.active: bool = True
        self.type = data.type
        self.spawn_time = time.time()
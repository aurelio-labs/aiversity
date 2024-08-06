import asyncio

class PortManager:
    def __init__(self, start_port=6000, end_port=7000):
        self.start_port = start_port
        self.end_port = end_port
        self.current_port = start_port
        self.lock = asyncio.Lock()

    async def get_next_port(self):
        async with self.lock:
            port = self.current_port
            self.current_port += 1
            if self.current_port > self.end_port:
                self.current_port = self.start_port
            return port
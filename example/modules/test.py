import time
from base import BaseModule
import random

class Module(BaseModule):
    def __init__(self):
        super().__init__("test")

    def read(self) -> str:
        return {
            "random_number": random.randint(0, 100),
        }

    def pretty_print(self, data: dict) -> str:
        return f"Test data: {data['random_number']}\nAnd that's it!"
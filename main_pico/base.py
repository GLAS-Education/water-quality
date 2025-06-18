from logging import log
import json

class BaseModule:
    def __init__(self, id: str):
        self.id = id
        log("Initializing...", "info", self.id)
    
    def read(self) -> str:
        return "No data (lacking implementation of read)."

    def pretty_print(self, data: dict) -> str:
        return "Pretty print format not implemented."
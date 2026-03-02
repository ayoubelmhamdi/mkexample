from abc import ABC, abstractmethod
from typing import Protocol

class {interfacename}Protocol(Protocol):
    def greet(self) -> None: ...

class {interfacename}(ABC):
    @abstractmethod
    def greet(self) -> None:
        pass
    
    @abstractmethod
    def get_message(self) -> str:
        pass
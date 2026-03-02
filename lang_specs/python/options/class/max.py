from abc import ABC, abstractmethod

class Abstract{classname}(ABC):
    @abstractmethod
    def greet(self) -> None:
        pass

class {classname}(Abstract{classname}):
    def __init__(self, message: str = "Hello, World!") -> None:
        self._message = message
    
    @property
    def message(self) -> str:
        return self._message
    
    @message.setter
    def message(self, value: str) -> None:
        self._message = value
    
    def greet(self) -> None:
        print(self.message)

if __name__ == "__main__":
    hw = {classname}()
    hw.greet()
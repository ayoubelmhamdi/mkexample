class {classname}:
    def __init__(self, message: str = "Hello, World!") -> None:
        self._message = message
    
    @property
    def message(self) -> str:
        return self._message
    
    def greet(self) -> None:
        print(self.message)
class EmulatorIsStoppedError(Exception):
    """Raised when the emulator is stopped."""

    def __init__(self, message: str = "Emulator is stopped") -> None:
        super().__init__(message)

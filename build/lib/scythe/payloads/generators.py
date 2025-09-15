from typing import List, Generator, Any

class PayloadGenerator:
    """Base class for payload generators."""
    def __iter__(self) -> Generator[Any, None, None]:
        raise NotImplementedError

    def __call__(self) -> Generator[Any, None, None]:
        return self.__iter__()

class WordlistPayloadGenerator(PayloadGenerator):
    """Generates payloads from a file, one per line."""
    def __init__(self, filepath: str):
        self.filepath = filepath

    def __iter__(self) -> Generator[str, None, None]:
        with open(self.filepath, 'r') as f:
            for line in f:
                yield line.strip()

class StaticPayloadGenerator(PayloadGenerator):
    """Generates payloads from a static list in memory."""
    def __init__(self, payload_list: List[Any]):
        self.payload_list = payload_list

    def __iter__(self) -> Generator[Any, None, None]:
        yield from self.payload_list

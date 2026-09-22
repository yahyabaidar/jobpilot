class ImporterError(Exception):
    pass


class BaseImporter:
    source: str = ""

    def fetch(self, limit: int = 50) -> list[dict]:
        raise NotImplementedError

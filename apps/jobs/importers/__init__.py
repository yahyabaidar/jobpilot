from .arbeitnow import ArbeitnowImporter
from .base import BaseImporter, ImporterError
from .france_travail import FranceTravailImporter
from .remotive import RemotiveImporter

IMPORTERS: dict[str, type[BaseImporter]] = {
    RemotiveImporter.source: RemotiveImporter,
    ArbeitnowImporter.source: ArbeitnowImporter,
    FranceTravailImporter.source: FranceTravailImporter,
}

__all__ = [
    "IMPORTERS",
    "ImporterError",
    "BaseImporter",
    "RemotiveImporter",
    "ArbeitnowImporter",
    "FranceTravailImporter",
]

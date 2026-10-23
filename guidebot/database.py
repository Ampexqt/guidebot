"""Validated local route data. This module has no GUI or hardware dependency."""

from dataclasses import dataclass
import json
from pathlib import Path


class DatabaseError(ValueError):
    """A campus database could not be read or has an invalid structure."""


@dataclass(frozen=True)
class Destination:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...]
    description: str
    steps: tuple[str, ...]


class CampusDatabase:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DatabaseError(f"Cannot read campus database {self.path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise DatabaseError("The database must contain a JSON object.")
        if type(raw.get("schema_version")) is not int or raw["schema_version"] != 1:
            raise DatabaseError("schema_version must be 1.")
        if type(raw.get("is_placeholder")) is not bool:
            raise DatabaseError("is_placeholder must be true or false.")
        self.is_placeholder = raw["is_placeholder"]
        self.campus_name = self._text(raw, "campus_name")
        self.starting_point = self._text(raw, "starting_point")
        self.notice = self._text(raw, "notice")
        entries = raw.get("destinations")
        if not isinstance(entries, list) or not entries:
            raise DatabaseError("destinations must be a nonempty list.")
        destinations = []
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise DatabaseError("Each destination must be an object.")
            identifier = self._text(entry, "id")
            if identifier in seen:
                raise DatabaseError(f"Duplicate destination id: {identifier}")
            seen.add(identifier)
            aliases = self._strings(entry, "aliases", allow_empty=True)
            destinations.append(Destination(
                identifier, self._text(entry, "name"), self._text(entry, "category"),
                aliases, self._text(entry, "description"), self._strings(entry, "steps"),
            ))
        self.destinations = tuple(destinations)
        self._by_id = {item.id: item for item in destinations}

    @staticmethod
    def _text(data: dict, key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DatabaseError(f"{key} must be a nonempty string.")
        return value.strip()

    @staticmethod
    def _strings(data: dict, key: str, allow_empty: bool = False) -> tuple[str, ...]:
        value = data.get(key)
        if not isinstance(value, list) or (not value and not allow_empty):
            raise DatabaseError(f"{key} must be a {'possibly empty' if allow_empty else 'nonempty'} list.")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise DatabaseError(f"Every {key} entry must be a nonempty string.")
        return tuple(item.strip() for item in value)

    def search(self, query: str = "") -> tuple[Destination, ...]:
        words = query.casefold().split()
        return tuple(item for item in self.destinations if all(
            word in " ".join((item.name, item.category, item.description, *item.aliases)).casefold()
            for word in words
        ))

    def get(self, identifier: str) -> Destination:
        try:
            return self._by_id[identifier]
        except KeyError as exc:
            raise DatabaseError(f"Unknown destination: {identifier}") from exc


DEFAULT_DATABASE = Path(__file__).resolve().parent / "data" / "campus.json"

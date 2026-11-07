"""Collecte et affichage des messages de vérification."""

from dataclasses import dataclass, field

LEVELS = {"erreur": "✗", "alerte": "!", "info": "·"}


@dataclass
class Message:
    level: str
    where: str
    text: str

    def __str__(self) -> str:
        return f"{LEVELS[self.level]} {self.level:<6}  {self.where} : {self.text}"


@dataclass
class Report:
    messages: list[Message] = field(default_factory=list)

    def error(self, where: str, text: str) -> None:
        self.messages.append(Message("erreur", where, text))

    def warning(self, where: str, text: str) -> None:
        self.messages.append(Message("alerte", where, text))

    def info(self, where: str, text: str) -> None:
        self.messages.append(Message("info", where, text))

    @property
    def errors(self) -> list[Message]:
        return [m for m in self.messages if m.level == "erreur"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def print(self, verbose: bool = False) -> None:
        for m in self.messages:
            if verbose or m.level != "info":
                print(m)
        counts = {lvl: sum(m.level == lvl for m in self.messages) for lvl in LEVELS}
        print(
            f"\n{counts['erreur']} erreur(s), {counts['alerte']} alerte(s), {counts['info']} info(s)"
        )

"""Парсер robots.txt (честный краулинг).

Правила (RFC 9309):
- самый длинный совпавший путь побеждает (Allow/Disallow)
- секция конкретного User-agent приоритетнее секции "*"
- Allow/Disallow без wildcard'ов (*, $) — prefix-сравнение
- Sitemap и Crawl-delay извлекаются в любом месте файла
"""

from __future__ import annotations

import urllib.parse

DEFAULT_UA = "*"


class RobotsTxt:
    def __init__(self, text: str, base_url: str = ""):
        self.base_url = base_url.rstrip("/")
        self.groups: dict[str, list[tuple[str, str]]] = {}   # ua -> [(Allow|Disallow, path)]
        self.sitemaps: list[str] = []
        self.delays: dict[str, float] = {}
        self._parse(text)

    def _parse(self, text: str) -> None:
        current: str | None = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition(":")
            key, value = key.strip().lower(), value.strip()
            if not value:
                continue
            if key == "user-agent":
                current = value
                self.groups.setdefault(current, [])
            elif key in ("allow", "disallow") and current is not None:
                self.groups[current].append((key, value))
            elif key == "sitemap":
                self.sitemaps.append(value)
            elif key == "crawl-delay":
                try:
                    self.delays[current or DEFAULT_UA] = float(value)
                except ValueError:
                    pass

    def _rules_for(self, user_agent: str) -> list[tuple[str, str]]:
        if user_agent in self.groups:
            return self.groups[user_agent]
        if DEFAULT_UA in self.groups:
            return self.groups[DEFAULT_UA]
        return []

    def _match(self, rules: list[tuple[str, str]], path: str) -> tuple[str, str] | None:
        """Возвращает победившее правило (самое длинное совпадение)."""
        best: tuple[str, str] | None = None
        for kind, pattern in rules:
            if path.startswith(pattern):
                if best is None or len(pattern) > len(best[1]):
                    best = (kind, pattern)
        return best

    def is_allowed(self, url: str, user_agent: str = DEFAULT_UA) -> bool:
        """True — можно краулить. Пустой robots.txt (правил нет) = всё разрешено."""
        path = urllib.parse.urlparse(url).path or "/"
        rules = self._rules_for(user_agent)
        if not rules:
            return True
        winner = self._match(rules, path)
        if winner is None:
            return True
        return winner[0] == "allow"

    def crawl_delay(self, user_agent: str = DEFAULT_UA) -> float | None:
        return self.delays.get(user_agent) or self.delays.get(DEFAULT_UA)

    @classmethod
    def fetch(cls, base_url: str, timeout: int = 10) -> "RobotsTxt":
        """Скачивает robots.txt по base_url и парсит. При 404/403 — пустые правила."""
        import urllib.request

        from engine.crawl.net import DEFAULT_UA, ssl_context

        url = base_url.rstrip("/") + "/robots.txt"
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
                return cls(resp.read().decode("utf-8", errors="replace"), base_url)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410, 403):
                return cls("", base_url)
            raise
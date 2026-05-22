# Copyright (c) KAITO authors.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Scanner config schemas for output guardrails.

Each schema describes the YAML shape of one llm_guard scanner AND knows how
to build the corresponding scanner instance. To add a new scanner:
  1. Define a dataclass with `from_dict()` and `build()`
  2. Register it in SCANNER_REGISTRY below

NOTE: Validation here is the runtime safety net for cases the
admission webhook cannot cover (failurePolicy=Ignore, pre-existing
CRs, ConfigMap-mounted policies, version skew). Bad configs are
logged and skipped so the rest of the chain still runs.

TODO: Many llm_guard scanners (e.g. Toxicity, Bias, Language) do not
support redaction; pairing them with action=redact would be a no-op.
When adding such scanners, declare a per-schema `supports_redact` flag
and reject the (action=redact + non-redact scanner) combination at parse
time, instead of trying to fix it at runtime.
"""

import re
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import urlparse

import llm_guard.output_scanners as llm_guard_output_scanners
import requests
from llm_guard.input_scanners.ban_substrings import (
    MatchType as BanSubstringsMatchType,
)
from llm_guard.input_scanners.regex import MatchType as RegexMatchType
from llm_guard.util import extract_urls

# Allowed match_type values, mirrored from llm_guard's enum *values* (not names).
# Keeping these here lets us reject invalid policies at parse time instead of
# letting the error surface only when the scanner is built.
_BAN_SUBSTRINGS_MATCH_TYPES = frozenset(m.value for m in BanSubstringsMatchType)
_REGEX_MATCH_TYPES = frozenset(m.value for m in RegexMatchType)


class URLReachabilityOutputAdapter:
    def __init__(
        self,
        *,
        success_status_codes: list[int] | None = None,
        timeout: float = 5.0,
        fail_on_request_error: bool = False,
    ) -> None:
        if success_status_codes is None:
            success_status_codes = [
                requests.codes.ok,
                requests.codes.created,
                requests.codes.accepted,
            ]

        self.success_status_codes = tuple(success_status_codes)
        self.timeout = timeout
        self.fail_on_request_error = fail_on_request_error

    def _is_reachable(self, url: str) -> bool | None:
        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.RequestException:
            return None

        return response.status_code in self.success_status_codes

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        urls = extract_urls(output)
        if not urls:
            return output, True, -1.0

        unreachable_urls: list[str] = []
        request_error_urls: list[str] = []
        for url in urls:
            is_reachable = self._is_reachable(url)
            if is_reachable is True:
                continue
            if is_reachable is False:
                unreachable_urls.append(url)
                continue
            request_error_urls.append(url)

        if unreachable_urls:
            return output, False, 1.0
        if self.fail_on_request_error and request_error_urls:
            return output, False, 1.0

        return output, True, -1.0


class BlockedURLPatternOutputAdapter:
    def __init__(
        self,
        *,
        blocked_domains: list[str] | None = None,
        blocked_patterns: list[str] | None = None,
        case_sensitive: bool = False,
    ) -> None:
        self.blocked_domains = tuple(
            domain.strip().lower().rstrip(".")
            for domain in (blocked_domains or [])
            if domain.strip()
        )
        flags = 0 if case_sensitive else re.IGNORECASE
        self.blocked_patterns = tuple(
            re.compile(pattern, flags) for pattern in (blocked_patterns or [])
        )

    def _matches_blocked_domain(self, url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower().rstrip(".")
        return any(
            hostname == blocked_domain or hostname.endswith(f".{blocked_domain}")
            for blocked_domain in self.blocked_domains
        )

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        urls = extract_urls(output)
        if not urls:
            return output, True, -1.0

        sanitized_output = output
        matched_urls: list[str] = []
        for url in urls:
            if self._matches_blocked_domain(url) or any(
                pattern.search(url) for pattern in self.blocked_patterns
            ):
                matched_urls.append(url)
                sanitized_output = sanitized_output.replace(url, "[REDACTED_URL]")

        if matched_urls:
            return sanitized_output, False, 1.0

        return output, True, -1.0


@dataclass
class BanSubstringsConfig:
    supports_redact: ClassVar[bool] = True
    substrings: list[str]
    match_type: str = "word"
    case_sensitive: bool = False
    contains_all: bool = False

    @classmethod
    def from_dict(cls, raw: dict) -> "BanSubstringsConfig":
        substrings = _coerce_string_list(raw.get("substrings"))
        if not substrings:
            raise ValueError(
                "ban_substrings requires 'substrings' to be a non-empty list of strings"
            )
        match_type = str(raw.get("match_type", "word")).lower()
        if match_type not in _BAN_SUBSTRINGS_MATCH_TYPES:
            raise ValueError(
                f"ban_substrings 'match_type' must be one of "
                f"{sorted(_BAN_SUBSTRINGS_MATCH_TYPES)}, got {match_type!r}"
            )
        return cls(
            substrings=substrings,
            match_type=match_type,
            case_sensitive=_coerce_bool(
                raw.get("case_sensitive"), False, field="case_sensitive"
            ),
            contains_all=_coerce_bool(
                raw.get("contains_all"), False, field="contains_all"
            ),
        )

    def build(self, action_on_hit: str) -> Any:
        return llm_guard_output_scanners.BanSubstrings(
            substrings=list(self.substrings),
            match_type=BanSubstringsMatchType(self.match_type),
            case_sensitive=self.case_sensitive,
            contains_all=self.contains_all,
            redact=(action_on_hit == "redact"),
        )


@dataclass
class RegexConfig:
    supports_redact: ClassVar[bool] = True
    patterns: list[str]
    is_blocked: bool = True
    match_type: str = "search"

    @classmethod
    def from_dict(cls, raw: dict) -> "RegexConfig":
        patterns = _coerce_string_list(raw.get("patterns"))
        if not patterns:
            raise ValueError(
                "regex requires 'patterns' to be a non-empty list of strings"
            )
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"regex pattern {pattern!r} is not a valid regular expression: {exc}"
                ) from exc
        match_type = str(raw.get("match_type", "search")).lower()
        if match_type not in _REGEX_MATCH_TYPES:
            raise ValueError(
                f"regex 'match_type' must be one of "
                f"{sorted(_REGEX_MATCH_TYPES)}, got {match_type!r}"
            )
        return cls(
            patterns=patterns,
            is_blocked=_coerce_bool(raw.get("is_blocked"), True, field="is_blocked"),
            match_type=match_type,
        )

    def build(self, action_on_hit: str) -> Any:
        return llm_guard_output_scanners.Regex(
            patterns=list(self.patterns),
            is_blocked=self.is_blocked,
            match_type=RegexMatchType(self.match_type),
            redact=(action_on_hit == "redact"),
        )


@dataclass
class URLReachabilityConfig:
    supports_redact: ClassVar[bool] = False
    success_status_codes: list[int]
    timeout: float = 5.0
    fail_on_request_error: bool = False

    @classmethod
    def from_dict(cls, raw: dict) -> "URLReachabilityConfig":
        success_status_codes = raw.get("success_status_codes")
        if success_status_codes is None:
            success_status_codes = [
                requests.codes.ok,
                requests.codes.created,
                requests.codes.accepted,
            ]
        if not isinstance(success_status_codes, list) or not success_status_codes:
            raise ValueError(
                "url_reachability 'success_status_codes' must be a non-empty list of integers"
            )
        if not all(isinstance(code, int) for code in success_status_codes):
            raise ValueError(
                "url_reachability 'success_status_codes' must contain only integers"
            )

        timeout = raw.get("timeout", 5.0)
        if not isinstance(timeout, int | float) or timeout <= 0:
            raise ValueError("url_reachability 'timeout' must be a positive number")

        return cls(
            success_status_codes=success_status_codes,
            timeout=float(timeout),
            fail_on_request_error=_coerce_bool(
                raw.get("fail_on_request_error"),
                False,
                field="fail_on_request_error",
            ),
        )

    def build(self, action_on_hit: str) -> Any:
        return URLReachabilityOutputAdapter(
            success_status_codes=list(self.success_status_codes),
            timeout=self.timeout,
            fail_on_request_error=self.fail_on_request_error,
        )


@dataclass
class BlockedURLPatternConfig:
    supports_redact: ClassVar[bool] = True
    blocked_domains: list[str]
    blocked_patterns: list[str]
    case_sensitive: bool = False

    @classmethod
    def from_dict(cls, raw: dict) -> "BlockedURLPatternConfig":
        blocked_domains = _coerce_string_list(raw.get("blocked_domains"))
        blocked_patterns = _coerce_string_list(raw.get("blocked_patterns"))
        if not blocked_domains and not blocked_patterns:
            raise ValueError(
                "blocked_url_pattern requires at least one of 'blocked_domains' or 'blocked_patterns'"
            )
        for pattern in blocked_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"blocked_url_pattern pattern {pattern!r} is not a valid regular expression: {exc}"
                ) from exc

        return cls(
            blocked_domains=blocked_domains,
            blocked_patterns=blocked_patterns,
            case_sensitive=_coerce_bool(
                raw.get("case_sensitive"), False, field="case_sensitive"
            ),
        )

    def build(self, action_on_hit: str) -> Any:
        return BlockedURLPatternOutputAdapter(
            blocked_domains=list(self.blocked_domains),
            blocked_patterns=list(self.blocked_patterns),
            case_sensitive=self.case_sensitive,
        )


SCANNER_REGISTRY: dict[str, type] = {
    "ban_substrings": BanSubstringsConfig,
    "blocked_url_pattern": BlockedURLPatternConfig,
    "regex": RegexConfig,
    "url_reachability": URLReachabilityConfig,
}


@dataclass
class ParsedScannerConfig:
    """A scanner config that has already passed schema validation."""

    type: str
    config: Any
    action_on_hit: str | None = None


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _coerce_bool(value: Any, fallback: bool, *, field: str) -> bool:
    # bool("false") is True, so we reject non-bool inputs explicitly instead of
    # silently inverting user intent. YAML native true/false parses to Python bool.
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field!r} must be a boolean (true/false), got {value!r}")


def _coerce_int_list(value: Any, *, field: str) -> list[int]:
    if not isinstance(value, list):
        raise ValueError(f"{field!r} must be a list of integers")

    integers = [item for item in value if isinstance(item, int)]
    if len(integers) != len(value):
        raise ValueError(f"{field!r} must contain only integers")
    return integers

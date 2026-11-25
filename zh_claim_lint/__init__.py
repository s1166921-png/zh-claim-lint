"""Offline checks for structured claims in Chinese drafts."""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re

__all__ = ["Finding", "check"]

# Only one-code-point substitutions: offsets always refer to the original text.
_FOLD = {ord(ch): ord(ch) - 0xFEE0 for ch in '０１２３４５６７８９％，．－＋￥／'}
_FOLD.update({ord('￥'): '¥', ord('−'): '-', ord('　'): ' '})
_GAP = r"[ \t]*"
_NUM = r"[+\-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_UNITS = {"元": "CNY", "人民币": "CNY", "美元": "USD", "港元": "HKD",
          "港币": "HKD", "欧元": "EUR", "日元": "JPY", "英镑": "GBP"}
_SCALE = {"": 1, "万": 10000, "亿": 100000000}
_N = rf"(?<![0-9+.\-])(?<![0-9],){_NUM}"
_PAT = re.compile(
    rf"(?P<notice>(?:(?P<notice_year>[0-9]{{4}}){_GAP}年{_GAP})?第{_GAP}(?P<notice_no>[0-9]+){_GAP}号{_GAP}(?P<notice_type>公告|通告))"
    rf"|(?P<date>(?<![0-9])(?P<year>[0-9]{{4}})(?:{_GAP}年{_GAP}(?P<month_cn>[0-9]{{1,2}}){_GAP}月{_GAP}(?P<day_cn>[0-9]{{1,2}}){_GAP}日|(?P<date_sep>[-/])(?P<month>[0-9]{{1,2}})(?P=date_sep)(?P<day>[0-9]{{1,2}})(?![0-9])))"
    rf"|(?P<percent_range>(?P<low>{_N}){_GAP}%?{_GAP}[-~～–—至到]{_GAP}(?P<high>{_NUM}){_GAP}%)"
    rf"|(?P<percent>(?P<pct>{_N}){_GAP}%)"
    rf"|(?P<money>(?P<amount>{_N}){_GAP}(?P<scale>[万亿]?){_GAP}(?P<unit>{'|'.join(_UNITS)}))"
    rf"|(?P<yuan>¥{_GAP}(?P<yuan_amount>{_NUM}){_GAP}(?P<yuan_scale>[万亿])?)"
)


@dataclass(frozen=True)
class Finding:
    kind: str
    text: str
    normalized: str
    start: int
    end: int
    line: int
    column: int


def _decimal(raw: str) -> str:
    value = Decimal(raw.replace(",", ""))
    if not value:
        return "0"
    notation = format(value, "f")
    return notation.rstrip("0").rstrip(".") if "." in notation else notation


def _scaled(raw: str, scale: str) -> str:
    # Shift the decimal point without context-based rounding.
    number = Decimal(raw.replace(",", ""))
    sign, digits, exponent = number.as_tuple()
    places = {1: 0, 10000: 4, 100000000: 8}[_SCALE[scale]]
    return _decimal(format(Decimal((sign, digits, exponent + places)), "f"))


def _claims(text: str):
    for match in _PAT.finditer(text.translate(_FOLD)):
        kind = match.lastgroup
        if kind == "notice":
            year = match["notice_year"] or ""
            number = match["notice_no"].lstrip("0") or "0"
            value = f"{year}:{number}:{match['notice_type']}"
        elif kind == "date":
            year, month, day = (int(match["year"]), int(match["month"] or match["month_cn"]),
                                int(match["day"] or match["day_cn"]))
            try:
                value = date(year, month, day).isoformat()
            except ValueError:
                value = f"invalid:{year:04}-{month:02}-{day:02}"
        elif kind == "percent_range":
            kind = "percent"
            value = f"{_decimal(match['low'])}%..{_decimal(match['high'])}%"
        elif kind == "percent":
            value = f"{_decimal(match['pct'])}%"
        elif kind == "money":
            value = f"{_UNITS[match['unit']]}:{_scaled(match['amount'], match['scale'])}"
        else:
            kind = "money"
            value = f"CNY:{_scaled(match['yuan_amount'], match['yuan_scale'] or '')}"
        yield kind, value, *match.span()


def check(source: str, draft: str) -> list[Finding]:
    """Flag draft occurrences whose structured value is absent from source."""
    supported = {(kind, value) for kind, value, *_ in _claims(source)}
    starts = [0] + [m.end() for m in re.finditer(r"\r\n|[\r\n]", draft)]
    findings = []
    for kind, value, start, end in _claims(draft):
        if (kind, value) not in supported:
            line = bisect_right(starts, start)
            findings.append(Finding(kind, draft[start:end], value,
                                    start, end, line, start - starts[line - 1] + 1))
    return findings

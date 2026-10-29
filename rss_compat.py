"""Leitor RSS/Atom mínimo, usado quando feedparser não está instalado.
Sem dependência externa. Compatível apenas com os campos usados pelo radar.
"""
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import calendar
import xml.etree.ElementTree as ET


class Entry(dict):
    __getattr__ = dict.get


class Feed:
    def __init__(self, entries):
        self.entries = entries


def _text(el):
    return ''.join(el.itertext()).strip() if el is not None else ''


def _child(el, tag):
    for c in el:
        if c.tag.rsplit('}', 1)[-1] == tag:
            return c
    return None


def _parse_date(value):
    if not value:
        return None
    try:
        d = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (TypeError, ValueError):
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).timetuple()


def parse(content):
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return Feed([])
    entries = []
    for el in root.iter():
        if el.tag.rsplit('}', 1)[-1] not in ('item', 'entry'):
            continue
        link = _child(el, 'link')
        href = link.attrib.get('href', '') if link is not None else ''
        title = _text(_child(el, 'title'))
        raw = next((c for name in ('description', 'summary', 'content', 'encoded')
                    if (c := _child(el, name)) is not None), None)
        summary = _text(raw)
        raw_date = (_text(_child(el, 'published')) or _text(_child(el, 'pubDate'))
                    or _text(_child(el, 'updated')))
        e = Entry(title=title, link=href or _text(link), summary=summary)
        stamp = _parse_date(raw_date)
        if stamp:
            e['published_parsed'] = stamp
        entries.append(e)
    return Feed(entries)

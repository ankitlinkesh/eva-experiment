"""Natural-language rule creation (Phase 54).

The parser is the security-relevant part: it stands up durable rules that fire
unattended, so it must be deterministic, must refuse what it does not understand
(rather than guess), and must never swallow an ordinary request.
"""

from __future__ import annotations

import pytest

from eva.proactivity.models import DAILY, FILE_CHANGE, INTERVAL
from eva.proactivity.nl_rules import ParsedRule, parse_rule_request
from eva.proactivity.store import ProactivityStore


# -- daily ------------------------------------------------------------------

def test_every_morning_defaults_to_eight():
    r = parse_rule_request("remind me every morning to summarize my news")
    assert r is not None
    assert r.kind == DAILY
    assert r.spec == {"at": "08:00"}
    assert r.request == "summarize my news"


def test_named_time_with_explicit_clock_wins():
    r = parse_rule_request("every morning at 6:30 check the weather")
    assert r.spec == {"at": "06:30"}
    assert r.request == "check the weather"


def test_trigger_at_the_end_parses_the_same():
    a = parse_rule_request("every morning summarize my news")
    b = parse_rule_request("summarize my news every morning")
    assert a is not None and b is not None
    assert a.kind == b.kind == DAILY
    assert a.request == b.request == "summarize my news"


def test_evening_and_night_map_sensibly():
    assert parse_rule_request("every evening log my hours").spec == {"at": "18:00"}
    assert parse_rule_request("every night back up my notes").spec == {"at": "21:00"}


def test_every_day_at_explicit_time():
    r = parse_rule_request("every day at 09:15 open my email")
    assert r.kind == DAILY and r.spec == {"at": "09:15"}
    assert r.request == "open my email"


def test_pm_meridiem():
    r = parse_rule_request("every day at 5pm remind me to stand up")
    assert r.spec == {"at": "17:00"}
    assert "stand up" in r.request


# -- interval ---------------------------------------------------------------

def test_every_n_minutes():
    r = parse_rule_request("every 30 minutes check the build status")
    assert r.kind == INTERVAL
    assert r.spec == {"seconds": 1800}
    assert r.request == "check the build status"


def test_interval_paces_itself_no_cooldown_but_capped_budget():
    r = parse_rule_request("every 2 hours summarize my inbox")
    assert r.spec == {"seconds": 7200}
    assert r.cooldown_seconds == 0
    assert r.max_fires_per_day == 96


def test_interval_has_a_floor():
    r = parse_rule_request("every 1 second ping me")
    assert r.spec["seconds"] >= 5


# -- file change ------------------------------------------------------------

def test_when_file_changes():
    r = parse_rule_request(r"when C:\notes\todo.txt changes tell me what changed")
    assert r.kind == FILE_CHANGE
    assert r.spec == {"path": r"C:\notes\todo.txt"}
    assert "tell me" in r.request


def test_whenever_path_is_modified():
    r = parse_rule_request("whenever report.csv is modified summarize it")
    assert r.kind == FILE_CHANGE
    assert r.spec == {"path": "report.csv"}
    assert r.request == "summarize it"


# -- refusal / non-swallowing ----------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "what's the weather today",
        "open chrome",
        "summarize my news",           # an action with NO schedule
        "remind me about the meeting",  # 'remind' but no cadence
        "",
        "every good boy does fine",     # 'every' but no unit/time/day
    ],
)
def test_non_schedules_return_none(text):
    assert parse_rule_request(text) is None


def test_a_recognised_schedule_with_empty_action_is_none():
    # "every morning" with nothing to do is not a usable rule.
    assert parse_rule_request("every morning") is None


def test_parse_is_deterministic():
    text = "every morning at 7 summarize my news"
    first = parse_rule_request(text)
    for _ in range(5):
        assert parse_rule_request(text) == first


# -- it actually persists ---------------------------------------------------

def test_parsed_rule_round_trips_through_the_store(tmp_path):
    store = ProactivityStore(tmp_path / "rules.sqlite3")
    parsed = parse_rule_request("every morning at 8:30 summarize my news")
    assert isinstance(parsed, ParsedRule)
    rule = store.add_rule(**parsed.as_add_rule_kwargs())
    assert rule is not None
    assert rule.kind == DAILY
    assert rule.spec == {"at": "08:30"}
    assert rule.request == "summarize my news"
    assert store.get_rule(rule.id) is not None


def test_interval_budget_survives_the_store_ceiling(tmp_path):
    store = ProactivityStore(tmp_path / "rules.sqlite3")
    parsed = parse_rule_request("every 10 minutes check the build")
    rule = store.add_rule(**parsed.as_add_rule_kwargs())
    assert rule.cooldown_seconds == 0
    assert rule.max_fires_per_day == 96

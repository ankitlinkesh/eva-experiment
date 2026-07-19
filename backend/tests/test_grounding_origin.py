"""Browser origin binding, the identity half of the phishing gap (Phase 67).

Grounding matches LABELS, not origin: a hostile page with a field literally
named "Email" gets ``@vault:email`` filled into it regardless of which site it
is actually on. This module is the piece that makes the SITE itself checkable:
Chrome/Edge expose their address bar as an Edit control in the same
accessibility tree grounding already walks, whose ValuePattern holds the
current page's URL -- so the domain is readable from the tree grounding
already has, without ever invoking ``chrome_copy_current_url`` (which steals
focus and clobbers the clipboard).

Tested here as pure functions against fabricated trees, exactly like the rest
of this module (see test_grounding.py) -- no real desktop.
"""

from __future__ import annotations

from eva.screen import grounding
from eva.screen.grounding import Origin, RawElement, is_browser_window, read_origin


def _bar(value: str, *, name: str = "Address and search bar") -> RawElement:
    return RawElement(name=name, role="Edit", left=0, top=0, width=800, height=30, value=value)


def _field(name: str, **kwargs) -> RawElement:
    kwargs.setdefault("role", "Edit")
    kwargs.setdefault("left", 50)
    kwargs.setdefault("top", 100)
    kwargs.setdefault("width", 80)
    kwargs.setdefault("height", 20)
    return RawElement(name=name, **kwargs)


# -- RawElement.value: backward compatibility --------------------------------


def test_raw_element_value_defaults_to_empty_string():
    # Positional construction exactly as it existed before Phase 67 (8
    # positional/keyword args, no `value`) must keep working unchanged.
    el = RawElement("Submit", "button", 100, 200, 80, 30)
    assert el.value == ""


def test_raw_element_value_can_be_set():
    el = RawElement(name="bar", role="Edit", left=0, top=0, width=10, height=10, value="https://x.example")
    assert el.value == "https://x.example"


# -- is_browser_window: detected by the omnibox's PRESENCE, not its value ----


def test_is_browser_window_true_when_address_bar_present():
    elements = [_bar("https://mybank.com/login"), _field("Email")]
    assert is_browser_window(elements) is True


def test_is_browser_window_true_even_with_empty_omnibox_value():
    # A blank new-tab page: the control exists, but has no value yet. This is
    # still a browser -- just one whose origin cannot currently be read.
    elements = [_bar(""), _field("Email")]
    assert is_browser_window(elements) is True


def test_is_browser_window_false_for_a_native_app():
    elements = [_field("Email"), _field("Password", top=200)]
    assert is_browser_window(elements) is False


def test_is_browser_window_label_match_is_case_and_space_insensitive():
    elements = [_bar("https://mybank.com", name="  ADDRESS   and Search Bar  ")]
    assert is_browser_window(elements) is True


# -- read_origin: domain extraction from the omnibox's displayed text --------


def test_read_origin_parses_a_full_url():
    origin = read_origin([_bar("https://mybank.com/login?x=1")])
    assert origin == Origin(domain="mybank.com", raw_value="https://mybank.com/login?x=1")


def test_read_origin_handles_scheme_less_omnibox_text():
    # The omnibox routinely hides the scheme -- "mybank.com/accounts" is what
    # a user actually sees, not "https://mybank.com/accounts".
    origin = read_origin([_bar("mybank.com/accounts")])
    assert origin is not None and origin.domain == "mybank.com"


def test_read_origin_strips_a_port():
    origin = read_origin([_bar("https://mybank.com:8443/login")])
    assert origin is not None and origin.domain == "mybank.com"


def test_read_origin_none_when_no_address_bar():
    assert read_origin([_field("Email")]) is None


def test_read_origin_none_when_omnibox_value_is_empty():
    assert read_origin([_bar("")]) is None


def test_read_origin_none_when_grounding_off(monkeypatch):
    monkeypatch.delenv("EVA_GUI_GROUNDING_ENABLED", raising=False)
    monkeypatch.setattr(grounding, "_default_provider", lambda: [_bar("https://mybank.com")])
    # No explicit `elements` -> read_origin enumerates via the flag-gated path.
    assert read_origin() is None
    assert is_browser_window() is False


def test_read_origin_domain_is_lowercased():
    origin = read_origin([_bar("HTTPS://MyBank.COM/Login")])
    assert origin is not None and origin.domain == "mybank.com"

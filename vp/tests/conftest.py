"""Test setup: disable UI pacing so output is instant and deterministic."""
from vp import ui

ui.set_pace(False)

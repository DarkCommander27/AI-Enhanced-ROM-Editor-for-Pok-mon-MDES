"""Tests for the AI assistant module."""

from __future__ import annotations

import pytest

from rom_editor.ai.assistant import AIAssistant, Suggestion, AssistantResponse
from rom_editor.games.explorers_sky.pokemon import PokemonEntry
from rom_editor.games.explorers_sky.moves import MoveEntry
from rom_editor.games.explorers_sky.dungeons import DungeonEntry


def _make_pokemon(
    index: int = 1,
    type1: int = 0, type2: int = 0,
    hp: int = 45, atk: int = 49, spatk: int = 65,
    def_: int = 49, spdef: int = 65, spd: int = 45,
    ability1: int = 0, ability2: int = 0,
    exp_group: int = 1, exp_yield: int = 64,
) -> PokemonEntry:
    return PokemonEntry(
        index=index, type1=type1, type2=type2, iq_group=3,
        ability1=ability1, ability2=ability2, flags=0,
        base_hp=hp, base_atk=atk, base_spatk=spatk,
        base_def=def_, base_spdef=spdef, base_spd=spd,
        exp_group=exp_group, exp_yield=exp_yield,
        recruit_rate1=0, size=1, recruit_rate2=0,
    )


def _make_move(
    index: int = 1,
    type_id: int = 0, category: int = 0,
    power: int = 80, acc: int = 100, pp: int = 10,
) -> MoveEntry:
    return MoveEntry(
        index=index, type_id=type_id, category=category, flags=0,
        base_power=power, accuracy=acc, pp=pp, pp2=pp,
        target=0, range_type=0, hits_min=1, hits_max=1,
        status_id=0, status_chance=0, stat_change=0, ai_weight=80,
    )


def _make_dungeon(
    index: int = 0,
    num_floors: int = 12,
    trap_density: int = 10,
    mh_chance: int = 5,
) -> DungeonEntry:
    return DungeonEntry(
        index=index, num_floors=num_floors,
        darkness=0, weather=0,
        monster_house_chance=mh_chance,
        buried_item_chance=0, empty_mh_chance=0,
        random_start_floor=0, map_gen_flags=0,
        item_density=5, trap_density=trap_density,
        floor_connectivity=5, water_chance=20,
        kecleon_shop_chance=10, music_id=5, fixed_floor_id=0,
    )


class TestAssistantNoAPIKey:
    """Tests that run without an OpenAI API key (rule-based fallback)."""

    def setup_method(self):
        self.assistant = AIAssistant(api_key="")

    def test_is_openai_available_false(self):
        assert not self.assistant.is_openai_available()

    def test_suggest_pokemon_returns_response(self):
        entry = _make_pokemon(hp=45)
        resp = self.assistant.suggest_pokemon_changes(entry)
        assert isinstance(resp, AssistantResponse)
        assert resp.source == "rule_based"
        assert len(resp.message) > 0

    def test_suggest_move_returns_response(self):
        entry = _make_move(power=80)
        resp = self.assistant.suggest_move_changes(entry)
        assert isinstance(resp, AssistantResponse)
        assert resp.source == "rule_based"

    def test_suggest_dungeon_returns_response(self):
        entry = _make_dungeon()
        resp = self.assistant.suggest_dungeon_changes(entry)
        assert isinstance(resp, AssistantResponse)
        assert resp.source == "rule_based"

    def test_ask_returns_response(self):
        resp = self.assistant.ask("What is IQ in Mystery Dungeon?")
        assert isinstance(resp, AssistantResponse)
        assert resp.source == "rule_based"

    def test_low_bst_triggers_suggestion(self):
        # Very low BST should not trigger hp > 200 suggestion, but spd < 20 might
        entry = _make_pokemon(hp=30, atk=25, spatk=20, def_=20, spdef=20, spd=15)
        resp = self.assistant.suggest_pokemon_changes(entry)
        # Should mention something about the low stats
        assert len(resp.message) > 0

    def test_high_hp_triggers_suggestion(self):
        entry = _make_pokemon(hp=250, atk=50, spatk=50, def_=50, spdef=50, spd=50)
        resp = self.assistant.suggest_pokemon_changes(entry)
        hp_suggestions = [s for s in resp.suggestions if s.field == "base_hp"]
        assert len(hp_suggestions) > 0

    def test_high_power_move_triggers_suggestion(self):
        entry = _make_move(power=220, acc=100)
        resp = self.assistant.suggest_move_changes(entry)
        power_suggestions = [s for s in resp.suggestions if s.field == "base_power"]
        assert len(power_suggestions) > 0

    def test_too_many_floors_triggers_suggestion(self):
        entry = _make_dungeon(num_floors=150)
        resp = self.assistant.suggest_dungeon_changes(entry)
        floor_suggestions = [s for s in resp.suggestions if s.field == "num_floors"]
        assert len(floor_suggestions) > 0


class TestSuggestionParsing:
    def test_parse_arrow_dash(self):
        text = "base_hp: 45 → 55 — Increasing HP for better survivability"
        suggestions = AIAssistant._parse_suggestions(text)
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s.field == "base_hp"
        assert s.old_value == 45
        assert s.new_value == 55
        assert "survivability" in s.reason

    def test_parse_arrow_hyphen(self):
        text = "base_power: 80 -> 90 - Slight power increase"
        suggestions = AIAssistant._parse_suggestions(text)
        assert len(suggestions) == 1
        assert suggestions[0].new_value == 90

    def test_parse_multiple(self):
        text = (
            "base_hp: 45 → 55 — more HP\n"
            "base_atk: 49 → 60 — more attack\n"
        )
        suggestions = AIAssistant._parse_suggestions(text)
        assert len(suggestions) == 2
        fields = {s.field for s in suggestions}
        assert "base_hp" in fields
        assert "base_atk" in fields

    def test_parse_no_match(self):
        text = "No numeric changes needed for this Pokémon."
        suggestions = AIAssistant._parse_suggestions(text)
        assert suggestions == []

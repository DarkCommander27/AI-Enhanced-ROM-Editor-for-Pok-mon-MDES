"""AI assistant for ROM editing suggestions.

This module provides an AI-assisted interface that can:
1. Suggest stat changes and balance adjustments for Pokémon.
2. Suggest move modifications (power, accuracy, PP) for better balance.
3. Suggest dungeon difficulty parameters.
4. Answer questions about game mechanics.

The assistant uses OpenAI's API when a valid API key is configured
(via the ``OPENAI_API_KEY`` environment variable or passed directly).
When no API key is available it falls back to a built-in rule-based system
that provides sensible suggestions without any external dependencies.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Suggestion:
    """A single AI suggestion."""

    field: str        # e.g. "base_hp", "base_power"
    old_value: int | str
    new_value: int | str
    reason: str


@dataclass
class AssistantResponse:
    """The AI assistant's response to a query."""

    message: str
    suggestions: list[Suggestion]
    source: str  # "openai" | "rule_based"


class AIAssistant:
    """AI-powered assistant for ROM editing.

    Usage::

        assistant = AIAssistant()   # will use env var OPENAI_API_KEY
        response = assistant.suggest_pokemon_changes(entry)
        for s in response.suggestions:
            print(s.field, s.old_value, "→", s.new_value, "–", s.reason)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_openai_available(self) -> bool:
        """Return True if an OpenAI API key is configured."""
        return bool(self._api_key)

    def suggest_pokemon_changes(self, entry) -> AssistantResponse:
        """Suggest balance improvements for *entry* (a PokemonEntry)."""
        prompt = self._build_pokemon_prompt(entry)
        return self._query(prompt, context="pokemon", entry=entry)

    def suggest_move_changes(self, entry) -> AssistantResponse:
        """Suggest balance improvements for *entry* (a MoveEntry)."""
        prompt = self._build_move_prompt(entry)
        return self._query(prompt, context="move", entry=entry)

    def suggest_dungeon_changes(self, entry) -> AssistantResponse:
        """Suggest parameter tweaks for *entry* (a DungeonEntry)."""
        prompt = self._build_dungeon_prompt(entry)
        return self._query(prompt, context="dungeon", entry=entry)

    def ask(self, question: str) -> AssistantResponse:
        """Ask a free-form question about game mechanics or ROM editing."""
        return self._query(question, context="general")

    # ------------------------------------------------------------------
    # Internal – prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_pokemon_prompt(entry) -> str:
        return (
            f"I am editing Pokémon Mystery Dungeon: Explorers of Sky.\n"
            f"Pokémon: {entry.name} (#{entry.index})\n"
            f"Type: {entry.type1_name}/{entry.type2_name}\n"
            f"Base stats: HP={entry.base_hp}, ATK={entry.base_atk}, "
            f"SP.ATK={entry.base_spatk}, DEF={entry.base_def}, "
            f"SP.DEF={entry.base_spdef}, SPD={entry.base_spd} (BST={entry.bst})\n"
            f"Abilities: {entry.ability1_name} / {entry.ability2_name}\n"
            f"EXP Group: {entry.exp_group_name}\n"
            f"\n"
            f"Please analyse this Pokémon's stats for balance in a Mystery Dungeon "
            f"context and suggest specific numeric changes if any are needed. "
            f"Format each suggestion as: FIELD: old_value → new_value — reason\n"
            f"Fields to consider: base_hp, base_atk, base_spatk, base_def, "
            f"base_spdef, base_spd"
        )

    @staticmethod
    def _build_move_prompt(entry) -> str:
        return (
            f"I am editing Pokémon Mystery Dungeon: Explorers of Sky.\n"
            f"Move: {entry.name} (#{entry.index})\n"
            f"Type: {entry.type_name}, Category: {entry.category_name}\n"
            f"Power: {entry.base_power}, Accuracy: {entry.accuracy}, PP: {entry.pp}\n"
            f"Range: {entry.range_type}, Target: {entry.target}\n"
            f"\n"
            f"Please analyse this move for balance in a Mystery Dungeon context "
            f"and suggest specific numeric changes if any are needed. "
            f"Format each suggestion as: FIELD: old_value → new_value — reason\n"
            f"Fields to consider: base_power, accuracy, pp"
        )

    @staticmethod
    def _build_dungeon_prompt(entry) -> str:
        return (
            f"I am editing Pokémon Mystery Dungeon: Explorers of Sky.\n"
            f"Dungeon: {entry.name} (#{entry.index})\n"
            f"Floors: {entry.num_floors}, Darkness: {entry.darkness_name}, "
            f"Weather: {entry.weather_name}\n"
            f"Item density: {entry.item_density}, Trap density: {entry.trap_density}\n"
            f"Monster House chance: {entry.monster_house_chance}%, "
            f"Kecleon shop chance: {entry.kecleon_shop_chance}%\n"
            f"\n"
            f"Please analyse these dungeon parameters for balance and difficulty "
            f"and suggest specific numeric changes if any are needed. "
            f"Format each suggestion as: FIELD: old_value → new_value — reason\n"
            f"Fields: num_floors, item_density, trap_density, "
            f"monster_house_chance, kecleon_shop_chance, water_chance"
        )

    # ------------------------------------------------------------------
    # Internal – query dispatch
    # ------------------------------------------------------------------

    def _query(
        self, prompt: str, context: str, entry=None
    ) -> AssistantResponse:
        if self.is_openai_available():
            try:
                return self._query_openai(prompt, context)
            except Exception as exc:
                # Fall back to rule-based if OpenAI fails
                fallback = self._rule_based(context, entry)
                fallback.message = (
                    f"(OpenAI unavailable: {exc})\n\n" + fallback.message
                )
                return fallback
        return self._rule_based(context, entry)

    def _query_openai(self, prompt: str, context: str) -> AssistantResponse:
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError("openai package not installed") from exc

        client = openai.OpenAI(api_key=self._api_key)
        system_msg = (
            "You are an expert on Pokémon Mystery Dungeon: Explorers of Sky ROM hacking. "
            "You help users balance and modify game data. "
            "Be concise and specific when suggesting numeric changes."
        )
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.7,
        )
        raw_text = response.choices[0].message.content or ""
        suggestions = self._parse_suggestions(raw_text)
        return AssistantResponse(
            message=raw_text,
            suggestions=suggestions,
            source="openai",
        )

    def _rule_based(self, context: str, entry=None) -> AssistantResponse:
        """Simple rule-based suggestion engine (no API required)."""
        if context == "pokemon" and entry is not None:
            return self._rule_based_pokemon(entry)
        if context == "move" and entry is not None:
            return self._rule_based_move(entry)
        if context == "dungeon" and entry is not None:
            return self._rule_based_dungeon(entry)
        return AssistantResponse(
            message=(
                "No OpenAI API key is configured.  Set the OPENAI_API_KEY "
                "environment variable to enable AI-powered suggestions.\n\n"
                "You can still edit all values manually using the editor."
            ),
            suggestions=[],
            source="rule_based",
        )

    # ------------------------------------------------------------------
    # Rule-based helpers
    # ------------------------------------------------------------------

    def _rule_based_pokemon(self, entry) -> AssistantResponse:
        suggestions: list[Suggestion] = []
        lines: list[str] = [
            f"Rule-based analysis for {entry.name} (#{entry.index}):",
            f"  Type: {entry.type1_name}/{entry.type2_name}",
            f"  BST: {entry.bst}",
            "",
        ]

        # Check BST against expected ranges
        if entry.bst < 300:
            lines.append(
                "⚠ BST is very low (<300).  "
                "Basic Pokémon typically have 250–350 BST in Mystery Dungeon."
            )
        elif entry.bst > 600:
            lines.append(
                "⚠ BST is very high (>600).  "
                "Only legendary Pokémon should exceed 550–600."
            )
        else:
            lines.append("✓ BST is within a typical range.")

        # Stat-specific checks
        if entry.base_hp > 200:
            suggestions.append(Suggestion("base_hp", entry.base_hp, 200,
                                          "HP above 200 is unusual outside legendaries"))
        if entry.base_spd < 20:
            suggestions.append(Suggestion("base_spd", entry.base_spd, 30,
                                          "Very low Speed makes the Pokémon unusable"))
        if entry.base_atk > 150:
            suggestions.append(Suggestion("base_atk", entry.base_atk, 130,
                                          "ATK above 130 tends to one-shot everything"))

        if not suggestions:
            lines.append("No specific stat changes suggested.")
        else:
            lines.append("Suggested changes:")
            for s in suggestions:
                lines.append(f"  • {s.field}: {s.old_value} → {s.new_value} — {s.reason}")

        return AssistantResponse(
            message="\n".join(lines),
            suggestions=suggestions,
            source="rule_based",
        )

    def _rule_based_move(self, entry) -> AssistantResponse:
        suggestions: list[Suggestion] = []
        lines: list[str] = [
            f"Rule-based analysis for {entry.name} (#{entry.index}):",
            f"  Type: {entry.type_name}, Category: {entry.category_name}",
            f"  Power: {entry.base_power}, Accuracy: {entry.accuracy}, PP: {entry.pp}",
            "",
        ]

        if entry.base_power > 120 and entry.accuracy > 95:
            suggestions.append(Suggestion(
                "accuracy", entry.accuracy, 90,
                "High-power moves (>120) with near-perfect accuracy are too strong"
            ))
        if entry.pp < 3 and entry.base_power > 0:
            suggestions.append(Suggestion(
                "pp", entry.pp, 5,
                "Moves with very low PP (< 3) are frustrating to use"
            ))
        if entry.base_power > 200:
            suggestions.append(Suggestion(
                "base_power", entry.base_power, 150,
                "Power above 200 is unbalanced in Mystery Dungeon"
            ))

        if not suggestions:
            lines.append("No specific move changes suggested.")
        else:
            lines.append("Suggested changes:")
            for s in suggestions:
                lines.append(f"  • {s.field}: {s.old_value} → {s.new_value} — {s.reason}")

        return AssistantResponse(
            message="\n".join(lines),
            suggestions=suggestions,
            source="rule_based",
        )

    def _rule_based_dungeon(self, entry) -> AssistantResponse:
        suggestions: list[Suggestion] = []
        lines: list[str] = [
            f"Rule-based analysis for {entry.name} (#{entry.index}):",
            f"  Floors: {entry.num_floors}, Darkness: {entry.darkness_name}",
            f"  Weather: {entry.weather_name}",
            f"  Traps: {entry.trap_density}%, MH: {entry.monster_house_chance}%",
            "",
        ]

        if entry.num_floors > 99:
            suggestions.append(Suggestion(
                "num_floors", entry.num_floors, 99,
                "EoS supports a maximum of 99 floors per dungeon"
            ))
        if entry.trap_density > 60:
            suggestions.append(Suggestion(
                "trap_density", entry.trap_density, 45,
                "Trap density above 60 makes exploration very frustrating"
            ))
        if entry.monster_house_chance > 30:
            suggestions.append(Suggestion(
                "monster_house_chance", entry.monster_house_chance, 20,
                "Monster House chance above 30% makes early floors extremely difficult"
            ))

        if not suggestions:
            lines.append("No specific dungeon changes suggested.")
        else:
            lines.append("Suggested changes:")
            for s in suggestions:
                lines.append(f"  • {s.field}: {s.old_value} → {s.new_value} — {s.reason}")

        return AssistantResponse(
            message="\n".join(lines),
            suggestions=suggestions,
            source="rule_based",
        )

    # ------------------------------------------------------------------
    # Suggestion parser (for OpenAI responses)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_suggestions(text: str) -> list[Suggestion]:
        """Extract structured suggestions from a free-text AI response.

        Looks for patterns like:
          FIELD: old_value → new_value — reason
          FIELD: old_value -> new_value - reason
        """
        suggestions: list[Suggestion] = []
        # Match "field: old → new — reason" with flexible separators
        pattern = re.compile(
            r"(\w+)\s*:\s*(\d+)\s*(?:→|->)\s*(\d+)\s*(?:—|-)\s*(.+)",
            re.IGNORECASE,
        )
        for line in text.splitlines():
            m = pattern.search(line)
            if m:
                field, old_val, new_val, reason = m.groups()
                suggestions.append(Suggestion(
                    field=field.lower(),
                    old_value=int(old_val),
                    new_value=int(new_val),
                    reason=reason.strip(),
                ))
        return suggestions

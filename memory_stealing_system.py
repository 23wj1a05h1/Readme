"""
Shadow Echo: The Memory Thief
Core Memory Stealing System
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MemoryType(Enum):
    COMBAT = "combat"
    STEALTH = "stealth"
    WISDOM = "wisdom"
    SPEED = "speed"
    PERCEPTION = "perception"


class Ability(Enum):
    SHADOW_STRIKE = "shadow_strike"      # combat + stealth
    SWIFT_MIND = "swift_mind"            # speed + wisdom
    EAGLE_EYE = "eagle_eye"              # perception + wisdom
    PHANTOM_DASH = "phantom_dash"        # speed + stealth
    BATTLE_INSIGHT = "battle_insight"    # combat + perception


# Maps a frozenset of two MemoryTypes to the unlocked Ability
COMBINATION_TABLE: dict[frozenset, Ability] = {
    frozenset({MemoryType.COMBAT, MemoryType.STEALTH}): Ability.SHADOW_STRIKE,
    frozenset({MemoryType.SPEED, MemoryType.WISDOM}): Ability.SWIFT_MIND,
    frozenset({MemoryType.PERCEPTION, MemoryType.WISDOM}): Ability.EAGLE_EYE,
    frozenset({MemoryType.SPEED, MemoryType.STEALTH}): Ability.PHANTOM_DASH,
    frozenset({MemoryType.COMBAT, MemoryType.PERCEPTION}): Ability.BATTLE_INSIGHT,
}


@dataclass
class Memory:
    """A single memory fragment that can be stolen, held, or combined."""

    memory_type: MemoryType
    power: int  # 1–10; higher power = harder to steal, stronger when combined
    owner_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not (1 <= self.power <= 10):
            raise ValueError(f"Memory power must be between 1 and 10, got {self.power}")


@dataclass
class Player:
    """Represents a player in Shadow Echo."""

    player_id: str
    stealth: int  # 1–10; affects steal success chance
    resistance: int  # 1–10; defends against steal attempts
    memories: list[Memory] = field(default_factory=list)
    abilities: list[Ability] = field(default_factory=list)

    def __post_init__(self) -> None:
        for stat_name, stat_val in (("stealth", self.stealth), ("resistance", self.resistance)):
            if not (1 <= stat_val <= 10):
                raise ValueError(f"Player {stat_name} must be between 1 and 10, got {stat_val}")

    def has_memory_type(self, memory_type: MemoryType) -> bool:
        return any(m.memory_type == memory_type for m in self.memories)

    def get_memory_by_type(self, memory_type: MemoryType) -> Optional[Memory]:
        for memory in self.memories:
            if memory.memory_type == memory_type:
                return memory
        return None

    def add_memory(self, memory: Memory) -> None:
        memory.owner_id = self.player_id
        self.memories.append(memory)

    def remove_memory(self, memory: Memory) -> bool:
        if memory in self.memories:
            self.memories.remove(memory)
            return True
        return False

    def grant_ability(self, ability: Ability) -> None:
        if ability not in self.abilities:
            self.abilities.append(ability)


@dataclass
class StealResult:
    """Outcome of a steal attempt."""

    success: bool
    stolen_memory: Optional[Memory]
    attacker_id: str
    target_id: str
    message: str


@dataclass
class CombineResult:
    """Outcome of combining two memories."""

    success: bool
    ability_unlocked: Optional[Ability]
    player_id: str
    memories_consumed: list[Memory]
    message: str


class MemoryStealingSystem:
    """
    Core system managing memory theft and combination mechanics.

    Steal chance formula:
        base_chance = attacker.stealth / (attacker.stealth + target.resistance)
        adjusted for memory power: higher power reduces success probability
    """

    BASE_STEAL_CHANCE_SCALE = 10  # denominator normaliser

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Steal mechanic
    # ------------------------------------------------------------------

    def steal_memory(
        self,
        attacker: Player,
        target: Player,
        memory_type: MemoryType,
    ) -> StealResult:
        """
        Attempt to steal a memory of *memory_type* from *target*.

        Returns a StealResult describing success or failure.
        """
        target_memory = target.get_memory_by_type(memory_type)
        if target_memory is None:
            return StealResult(
                success=False,
                stolen_memory=None,
                attacker_id=attacker.player_id,
                target_id=target.player_id,
                message=f"Target {target.player_id} has no {memory_type.value} memory to steal.",
            )

        success_chance = self._calculate_steal_chance(attacker, target, target_memory)
        roll = self._rng.random()

        if roll <= success_chance:
            target.remove_memory(target_memory)
            attacker.add_memory(target_memory)
            return StealResult(
                success=True,
                stolen_memory=target_memory,
                attacker_id=attacker.player_id,
                target_id=target.player_id,
                message=(
                    f"{attacker.player_id} successfully stole a {memory_type.value} "
                    f"memory (power {target_memory.power}) from {target.player_id}."
                ),
            )

        return StealResult(
            success=False,
            stolen_memory=None,
            attacker_id=attacker.player_id,
            target_id=target.player_id,
            message=(
                f"{attacker.player_id} failed to steal {target.player_id}'s "
                f"{memory_type.value} memory."
            ),
        )

    def _calculate_steal_chance(
        self, attacker: Player, target: Player, memory: Memory
    ) -> float:
        """
        Compute probability [0, 1] of a successful steal.

        Higher attacker stealth increases chance;
        higher target resistance and memory power decrease it.
        """
        effective_resistance = target.resistance + memory.power / self.BASE_STEAL_CHANCE_SCALE
        chance = attacker.stealth / (attacker.stealth + effective_resistance)
        return max(0.0, min(1.0, chance))

    # ------------------------------------------------------------------
    # Combine mechanic
    # ------------------------------------------------------------------

    def combine_memories(
        self,
        player: Player,
        memory_type_a: MemoryType,
        memory_type_b: MemoryType,
    ) -> CombineResult:
        """
        Combine two of *player*'s memories to unlock an ability.

        Both memory fragments are consumed on success.
        Returns a CombineResult describing the outcome.
        """
        if memory_type_a == memory_type_b:
            return CombineResult(
                success=False,
                ability_unlocked=None,
                player_id=player.player_id,
                memories_consumed=[],
                message="Cannot combine two memories of the same type.",
            )

        mem_a = player.get_memory_by_type(memory_type_a)
        mem_b = player.get_memory_by_type(memory_type_b)

        if mem_a is None or mem_b is None:
            missing = memory_type_a if mem_a is None else memory_type_b
            return CombineResult(
                success=False,
                ability_unlocked=None,
                player_id=player.player_id,
                memories_consumed=[],
                message=f"Player {player.player_id} lacks a {missing.value} memory to combine.",
            )

        ability = COMBINATION_TABLE.get(frozenset({memory_type_a, memory_type_b}))
        if ability is None:
            return CombineResult(
                success=False,
                ability_unlocked=None,
                player_id=player.player_id,
                memories_consumed=[],
                message=(
                    f"No ability found for combining {memory_type_a.value} "
                    f"and {memory_type_b.value}."
                ),
            )

        player.remove_memory(mem_a)
        player.remove_memory(mem_b)
        player.grant_ability(ability)

        return CombineResult(
            success=True,
            ability_unlocked=ability,
            player_id=player.player_id,
            memories_consumed=[mem_a, mem_b],
            message=(
                f"{player.player_id} combined {memory_type_a.value} and "
                f"{memory_type_b.value} memories to unlock {ability.value}!"
            ),
        )

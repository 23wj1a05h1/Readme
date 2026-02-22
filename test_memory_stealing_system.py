"""
Tests for Shadow Echo: The Memory Thief — Memory Stealing System
"""

import random
import unittest

from memory_stealing_system import (
    Ability,
    CombineResult,
    Memory,
    MemoryStealingSystem,
    MemoryType,
    Player,
    StealResult,
)


def _make_player(
    player_id: str = "p1",
    stealth: int = 5,
    resistance: int = 5,
    memories: list[Memory] | None = None,
) -> Player:
    player = Player(player_id=player_id, stealth=stealth, resistance=resistance)
    for mem in memories or []:
        player.add_memory(mem)
    return player


class TestMemory(unittest.TestCase):
    def test_valid_memory(self) -> None:
        mem = Memory(MemoryType.COMBAT, power=7)
        self.assertEqual(mem.memory_type, MemoryType.COMBAT)
        self.assertEqual(mem.power, 7)

    def test_power_out_of_range_raises(self) -> None:
        with self.assertRaises(ValueError):
            Memory(MemoryType.STEALTH, power=0)
        with self.assertRaises(ValueError):
            Memory(MemoryType.STEALTH, power=11)


class TestPlayer(unittest.TestCase):
    def test_stat_out_of_range_raises(self) -> None:
        with self.assertRaises(ValueError):
            Player("p", stealth=0, resistance=5)
        with self.assertRaises(ValueError):
            Player("p", stealth=5, resistance=11)

    def test_add_and_remove_memory(self) -> None:
        player = _make_player()
        mem = Memory(MemoryType.WISDOM, power=3)
        player.add_memory(mem)
        self.assertTrue(player.has_memory_type(MemoryType.WISDOM))
        removed = player.remove_memory(mem)
        self.assertTrue(removed)
        self.assertFalse(player.has_memory_type(MemoryType.WISDOM))

    def test_remove_nonexistent_memory_returns_false(self) -> None:
        player = _make_player()
        mem = Memory(MemoryType.SPEED, power=2)
        self.assertFalse(player.remove_memory(mem))

    def test_grant_ability_no_duplicates(self) -> None:
        player = _make_player()
        player.grant_ability(Ability.EAGLE_EYE)
        player.grant_ability(Ability.EAGLE_EYE)
        self.assertEqual(player.abilities.count(Ability.EAGLE_EYE), 1)

    def test_get_memory_by_type_returns_none_when_absent(self) -> None:
        player = _make_player()
        self.assertIsNone(player.get_memory_by_type(MemoryType.COMBAT))


class TestStealMemory(unittest.TestCase):
    def setUp(self) -> None:
        # Use a seeded RNG for deterministic tests
        self.rng = random.Random(42)
        self.system = MemoryStealingSystem(rng=self.rng)

    def test_steal_succeeds_with_guaranteed_roll(self) -> None:
        """Force the roll to 0.0 so the steal always succeeds."""
        rng = random.Random()
        rng.random = lambda: 0.0  # type: ignore[method-assign]
        system = MemoryStealingSystem(rng=rng)

        target_mem = Memory(MemoryType.COMBAT, power=1)
        attacker = _make_player("attacker", stealth=10, resistance=1)
        target = _make_player("target", stealth=1, resistance=1, memories=[target_mem])

        result = system.steal_memory(attacker, target, MemoryType.COMBAT)

        self.assertIsInstance(result, StealResult)
        self.assertTrue(result.success)
        self.assertEqual(result.stolen_memory, target_mem)
        self.assertIn(target_mem, attacker.memories)
        self.assertNotIn(target_mem, target.memories)
        self.assertEqual(target_mem.owner_id, "attacker")

    def test_steal_fails_with_guaranteed_miss_roll(self) -> None:
        """Force the roll to 1.0 so the steal always fails."""
        rng = random.Random()
        rng.random = lambda: 1.0  # type: ignore[method-assign]
        system = MemoryStealingSystem(rng=rng)

        target_mem = Memory(MemoryType.STEALTH, power=5)
        attacker = _make_player("attacker", stealth=5, resistance=5)
        target = _make_player("target", stealth=5, resistance=5, memories=[target_mem])

        result = system.steal_memory(attacker, target, MemoryType.STEALTH)

        self.assertFalse(result.success)
        self.assertIsNone(result.stolen_memory)
        self.assertIn(target_mem, target.memories)
        self.assertNotIn(target_mem, attacker.memories)

    def test_steal_target_lacks_memory_type(self) -> None:
        attacker = _make_player("attacker")
        target = _make_player("target")

        result = self.system.steal_memory(attacker, target, MemoryType.WISDOM)

        self.assertFalse(result.success)
        self.assertIsNone(result.stolen_memory)
        self.assertIn("no", result.message.lower())

    def test_steal_result_fields(self) -> None:
        rng = random.Random()
        rng.random = lambda: 0.0  # type: ignore[method-assign]
        system = MemoryStealingSystem(rng=rng)

        attacker = _make_player("alice", stealth=8, resistance=2)
        target_mem = Memory(MemoryType.SPEED, power=3)
        target = _make_player("bob", stealth=2, resistance=2, memories=[target_mem])

        result = system.steal_memory(attacker, target, MemoryType.SPEED)

        self.assertEqual(result.attacker_id, "alice")
        self.assertEqual(result.target_id, "bob")
        self.assertTrue(result.success)


class TestCalculateStealChance(unittest.TestCase):
    def setUp(self) -> None:
        self.system = MemoryStealingSystem()

    def test_high_stealth_gives_high_chance(self) -> None:
        attacker = _make_player(stealth=10, resistance=1)
        target = _make_player(stealth=1, resistance=1)
        mem = Memory(MemoryType.COMBAT, power=1)
        chance = self.system._calculate_steal_chance(attacker, target, mem)
        self.assertGreater(chance, 0.7)

    def test_high_resistance_reduces_chance(self) -> None:
        attacker = _make_player(stealth=5, resistance=1)
        target_low = _make_player(stealth=1, resistance=1)
        target_high = _make_player(stealth=1, resistance=10)
        mem = Memory(MemoryType.COMBAT, power=1)
        chance_low = self.system._calculate_steal_chance(attacker, target_low, mem)
        chance_high = self.system._calculate_steal_chance(attacker, target_high, mem)
        self.assertGreater(chance_low, chance_high)

    def test_high_power_memory_reduces_chance(self) -> None:
        attacker = _make_player(stealth=5, resistance=1)
        target = _make_player(stealth=1, resistance=5)
        mem_low = Memory(MemoryType.WISDOM, power=1)
        mem_high = Memory(MemoryType.WISDOM, power=10)
        chance_low = self.system._calculate_steal_chance(attacker, target, mem_low)
        chance_high = self.system._calculate_steal_chance(attacker, target, mem_high)
        self.assertGreater(chance_low, chance_high)

    def test_chance_clamped_between_0_and_1(self) -> None:
        attacker = _make_player(stealth=1, resistance=1)
        target = _make_player(stealth=1, resistance=10)
        mem = Memory(MemoryType.SPEED, power=10)
        chance = self.system._calculate_steal_chance(attacker, target, mem)
        self.assertGreaterEqual(chance, 0.0)
        self.assertLessEqual(chance, 1.0)


class TestCombineMemories(unittest.TestCase):
    def setUp(self) -> None:
        self.system = MemoryStealingSystem()

    def test_combine_unlocks_ability(self) -> None:
        player = _make_player(
            "player",
            memories=[
                Memory(MemoryType.COMBAT, power=5),
                Memory(MemoryType.STEALTH, power=5),
            ],
        )

        result = self.system.combine_memories(player, MemoryType.COMBAT, MemoryType.STEALTH)

        self.assertIsInstance(result, CombineResult)
        self.assertTrue(result.success)
        self.assertEqual(result.ability_unlocked, Ability.SHADOW_STRIKE)
        self.assertIn(Ability.SHADOW_STRIKE, player.abilities)
        # Memories consumed
        self.assertEqual(len(player.memories), 0)
        self.assertEqual(len(result.memories_consumed), 2)

    def test_combine_order_independent(self) -> None:
        """Combining A+B should give same ability as B+A."""
        player = _make_player(
            memories=[
                Memory(MemoryType.SPEED, power=4),
                Memory(MemoryType.WISDOM, power=4),
            ]
        )
        result = self.system.combine_memories(player, MemoryType.WISDOM, MemoryType.SPEED)
        self.assertTrue(result.success)
        self.assertEqual(result.ability_unlocked, Ability.SWIFT_MIND)

    def test_combine_fails_same_type(self) -> None:
        player = _make_player(
            memories=[
                Memory(MemoryType.COMBAT, power=3),
                Memory(MemoryType.COMBAT, power=6),
            ]
        )
        result = self.system.combine_memories(player, MemoryType.COMBAT, MemoryType.COMBAT)
        self.assertFalse(result.success)
        self.assertIsNone(result.ability_unlocked)
        self.assertEqual(len(player.memories), 2)

    def test_combine_fails_missing_memory(self) -> None:
        player = _make_player(memories=[Memory(MemoryType.PERCEPTION, power=2)])
        result = self.system.combine_memories(
            player, MemoryType.PERCEPTION, MemoryType.WISDOM
        )
        self.assertFalse(result.success)
        self.assertIsNone(result.ability_unlocked)
        # Memory not consumed
        self.assertEqual(len(player.memories), 1)

    def test_combine_fails_unknown_combination(self) -> None:
        """COMBAT + SPEED has no entry in the combination table."""
        player = _make_player(
            memories=[
                Memory(MemoryType.COMBAT, power=5),
                Memory(MemoryType.SPEED, power=5),
            ]
        )
        result = self.system.combine_memories(player, MemoryType.COMBAT, MemoryType.SPEED)
        self.assertFalse(result.success)
        self.assertIsNone(result.ability_unlocked)
        self.assertEqual(len(player.memories), 2)

    def test_combine_ability_not_duplicated(self) -> None:
        player = _make_player(
            memories=[
                Memory(MemoryType.COMBAT, power=5),
                Memory(MemoryType.STEALTH, power=5),
            ]
        )
        player.grant_ability(Ability.SHADOW_STRIKE)  # pre-grant

        self.system.combine_memories(player, MemoryType.COMBAT, MemoryType.STEALTH)
        # Still only one copy
        self.assertEqual(player.abilities.count(Ability.SHADOW_STRIKE), 1)

    def test_all_valid_combinations(self) -> None:
        """Every entry in the combination table should produce the expected ability."""
        from memory_stealing_system import COMBINATION_TABLE

        for type_pair, expected_ability in COMBINATION_TABLE.items():
            types = list(type_pair)
            player = _make_player(
                memories=[
                    Memory(types[0], power=5),
                    Memory(types[1], power=5),
                ]
            )
            result = self.system.combine_memories(player, types[0], types[1])
            self.assertTrue(result.success, f"Expected success for {types}")
            self.assertEqual(result.ability_unlocked, expected_ability)


class TestEndToEndScenario(unittest.TestCase):
    """Integration-style test: steal then combine to unlock an ability."""

    def test_steal_then_combine(self) -> None:
        rng = random.Random()
        rng.random = lambda: 0.0  # type: ignore[method-assign]
        system = MemoryStealingSystem(rng=rng)

        # Alice has a combat memory; Bob has a stealth memory
        alice = _make_player("alice", stealth=8, resistance=3,
                              memories=[Memory(MemoryType.COMBAT, power=4)])
        bob = _make_player("bob", stealth=3, resistance=2,
                           memories=[Memory(MemoryType.STEALTH, power=3)])

        # Alice steals Bob's stealth memory
        steal_result = system.steal_memory(alice, bob, MemoryType.STEALTH)
        self.assertTrue(steal_result.success)
        self.assertTrue(alice.has_memory_type(MemoryType.STEALTH))

        # Alice combines combat + stealth to unlock Shadow Strike
        combine_result = system.combine_memories(
            alice, MemoryType.COMBAT, MemoryType.STEALTH
        )
        self.assertTrue(combine_result.success)
        self.assertEqual(combine_result.ability_unlocked, Ability.SHADOW_STRIKE)
        self.assertIn(Ability.SHADOW_STRIKE, alice.abilities)
        self.assertEqual(len(alice.memories), 0)


if __name__ == "__main__":
    unittest.main()

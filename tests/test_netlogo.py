"""Tests for the NetLogo port: hierarchy, structures, mechanics and qualitative properties."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from gcm.netlogo import GarbageCanABM, NetLogoComponents, NetLogoParameters, Structure
from gcm.netlogo.agents import Opportunity, Participant, PatchAgents, PatchColor, Problem, Solution
from gcm.netlogo.hierarchy import hierarchy_divide, hierarchy_levels, level_of
from gcm.netlogo.parameters import behavior_space_experiments
from gcm.netlogo.structures import DecisionStructureRule


# ---------------------------------------------------------------------------------- hierarchy
def test_hierarchy_divide_examples_from_documentation():
    # 100 opportunities, span 2 → 7 levels, mid level 3, divide = 1 + 2 + 4 = 7
    assert hierarchy_levels(100, 2) == 7
    assert hierarchy_divide(100, 2) == 7
    # span 1 degenerates to a chain: 100 levels, divide = 50
    assert hierarchy_divide(100, 1) == 50
    # span 3: levels 1,3,9,27,81 → total 121 ≥ 100 at 5 levels, mid 2 → divide 1 + 3 = 4
    assert hierarchy_levels(100, 3) == 5 and hierarchy_divide(100, 3) == 4
    assert (
        level_of(0, 2) == 1 and level_of(1, 2) == 2 and level_of(2, 2) == 2 and level_of(3, 2) == 3
    )


# ---------------------------------------------------------------------------------- setup
def test_setup_assigns_who_numbers_in_breed_order():
    p = NetLogoParameters(
        seed=3,
        number_of_opportunities=5,
        number_of_participants=4,
        number_of_solutions=3,
        number_of_problems=2,
    )
    m = GarbageCanABM(p)
    assert [o.who for o in m.opportunities] == [0, 1, 2, 3, 4]
    assert [a.who for a in m.participants] == [5, 6, 7, 8]
    assert [s.who for s in m.solutions] == [9, 10, 11]
    assert [pr.who for pr in m.problems] == [12, 13]
    assert all(0 <= a.ability < 10 for a in m.participants)
    assert sum(len(h.all()) for h in m.here.values()) == 14


def test_seed_reproducibility():
    p = NetLogoParameters(seed=42)
    r1 = GarbageCanABM(p).run(300).as_dict()
    r2 = GarbageCanABM(p).run(300).as_dict()
    assert r1 == r2


# ---------------------------------------------------------------------------------- structures
def _tiny_model(structure: Structure) -> GarbageCanABM:
    p = NetLogoParameters(seed=0, number_of_opportunities=100).with_structures(structure)
    return GarbageCanABM(p)


def test_competent_hierarchy_bars_low_ability_from_important_opportunities():
    m = _tiny_model(Structure.COMPETENT_HIERARCHY)
    rule = DecisionStructureRule(Structure.COMPETENT_HIERARCHY)
    important = Opportunity(who=0, x=0, y=0)  # who 0 <= divide 7
    unimportant = Opportunity(who=50, x=0, y=0)
    low = Participant(who=200, x=0, y=0, ability=2.0)
    high = Participant(who=201, x=0, y=0, ability=8.0)
    assert not rule.participant_may_enter(low, PatchAgents(opportunities=[important]), m)
    assert rule.participant_may_enter(low, PatchAgents(opportunities=[unimportant]), m)
    assert rule.participant_may_enter(high, PatchAgents(opportunities=[important]), m)
    assert not rule.participant_may_enter(high, PatchAgents(opportunities=[unimportant]), m)
    # and the mirror image for opportunities
    assert not rule.opportunity_may_enter(important, PatchAgents(participants=[low]), m)
    assert rule.opportunity_may_enter(important, PatchAgents(participants=[high]), m)
    assert not rule.opportunity_may_enter(unimportant, PatchAgents(participants=[high]), m)


def test_incompetent_hierarchy_is_the_mirror_image():
    m = _tiny_model(Structure.INCOMPETENT_HIERARCHY)
    rule = DecisionStructureRule(Structure.INCOMPETENT_HIERARCHY)
    important = Opportunity(who=0, x=0, y=0)
    low = Participant(who=200, x=0, y=0, ability=2.0)
    high = Participant(who=201, x=0, y=0, ability=8.0)
    assert rule.participant_may_enter(low, PatchAgents(opportunities=[important]), m)
    assert not rule.participant_may_enter(high, PatchAgents(opportunities=[important]), m)


def test_organized_anarchy_never_constrains():
    m = _tiny_model(Structure.ORGANIZED_ANARCHY)
    assert not m.hierarchy_active and m.hierarchy_divide == -1
    o = Opportunity(who=0, x=0, y=0)
    target = PatchAgents(
        participants=[Participant(who=1, x=0, y=0, ability=0.1)],
        solutions=[Solution(who=2, x=0, y=0, efficiency=0.01)],
        problems=[Problem(who=3, x=0, y=0, difficulty=9.9)],
    )
    assert m.opportunity_can_move(o, target)


# ---------------------------------------------------------------------------------- mechanics
def _place(m: GarbageCanABM, agent, x: int, y: int) -> None:
    m._move_to(agent, x, y)


def test_oversight_and_resolution_and_block_on_one_patch():
    p = NetLogoParameters(
        seed=1,
        number_of_opportunities=2,
        number_of_participants=2,
        number_of_solutions=2,
        number_of_problems=2,
        postpone=False,
        buckpass=False,
    ).with_structures(Structure.ORGANIZED_ANARCHY)
    m = GarbageCanABM(p)
    # scatter everything far apart, then build the situations by hand
    for i, a in enumerate([*m.opportunities, *m.participants, *m.solutions, *m.problems]):
        _place(m, a, i * 5, 40)
    o, a, s, pr = m.opportunities[0], m.participants[0], m.solutions[0], m.problems[0]
    a.ability, s.efficiency, pr.difficulty = 4.0, 0.5, 3.0
    _place(m, o, 1, 1)
    _place(m, a, 1, 1)
    _place(m, s, 1, 1)
    m._decision_making()
    assert m.num_oversights == 1 and m.color[m._index(1, 1)] is PatchColor.SKY
    _place(m, pr, 1, 1)  # 4 × 0.5 = 2 < 3 → blocked
    m.ticks += 1
    m._decision_making()
    assert m.num_resolutions == 0
    assert m.color[m._index(1, 1)] is PatchColor.WHITE and m.white_since[m._index(1, 1)] == m.ticks
    assert a.blocked and o.blocked and s.blocked and pr.blocked
    a.ability = 7.0  # 7 × 0.5 = 3.5 ≥ 3 → resolution after a block
    m.ticks += 1
    m._decision_making()
    assert m.num_resolutions == 1 and m.num_blocked_resolutions == 1
    assert not (a.blocked or o.blocked or s.blocked or pr.blocked)
    assert m.color[m._index(1, 1)] is PatchColor.LIME


def test_postponement_couples_most_difficult_problem_to_latest_opportunity():
    p = NetLogoParameters(
        seed=2,
        number_of_opportunities=2,
        number_of_participants=1,
        number_of_solutions=1,
        number_of_problems=2,
        postpone=True,
        buckpass=False,
    ).with_structures(Structure.ORGANIZED_ANARCHY)
    m = GarbageCanABM(p)
    for i, a in enumerate([*m.opportunities, *m.participants, *m.solutions, *m.problems]):
        _place(m, a, i * 5, 40)
    o1, o2 = m.opportunities
    a, s = m.participants[0], m.solutions[0]
    p1, p2 = m.problems
    a.ability, s.efficiency, p1.difficulty, p2.difficulty = 1.0, 1.0, 5.0, 9.0
    for ag in (o1, a, s, p1, p2):
        _place(m, ag, 2, 2)
    m.ticks = 1
    m._decision_making()  # blocked at tick 1
    assert m.color[m._index(2, 2)] is PatchColor.WHITE
    # a second opportunity arrives during tick 1's move phase
    _place(m, o2, 2, 2)
    o2.last_movement = 1
    m.ticks = 2
    m._decision_making()
    assert m.num_postponements == 1
    assert o2.charged and o2.with_problem is p2 and p2.postponed and p2.to_opportunity is o2
    assert (o2.x, o2.y) == (p2.x, p2.y) and (o2.x, o2.y) != (2, 2)
    assert not o2.blocked and not p2.blocked and o1.blocked and p1.blocked
    # the pair then moves together
    m._move()
    assert (o2.x, o2.y) == (p2.x, p2.y)
    assert m.color.get(m._index(o2.x, o2.y)) is PatchColor.BROWN


def test_flying_pairs_move_about_e_minus_1_patches_per_tick():
    """The ``ask patches [ask -here …]`` idiom makes charged opportunities move ≈ e − 1 ≈ 1.72
    patches per tick on average (they are re-asked when they land on a not-yet-visited patch)."""
    p = NetLogoParameters(
        seed=7,
        number_of_participants=60,
        number_of_opportunities=200,
        number_of_solutions=60,
        number_of_problems=200,
        max_ability=3.0,
        postpone=True,
        buckpass=False,
    ).with_structures(Structure.ORGANIZED_ANARCHY)
    m = GarbageCanABM(p, record_events=False)
    m.run(3000)
    assert m.stats_flying_opportunity_ticks > 500, "not enough postponements to measure"
    rate = m.stats_flying_opportunity_moves / m.stats_flying_opportunity_ticks
    assert abs(rate - (math.e - 1)) < 0.12


def test_free_spot_is_black_and_empty():
    m = GarbageCanABM(NetLogoParameters(seed=5))
    for _ in range(50):
        x, y = m._free_spot()
        idx = m._index(x, y)
        assert idx not in m.here and idx not in m.color


# ---------------------------------------------------------------------------------- properties
@pytest.mark.slow
def test_qualitative_properties_of_the_netlogo_model():
    """The four properties listed under 'Things to notice' in the .nlogox info tab (short runs,
    several seeds, so only the robust orderings are asserted)."""

    def share(structure, postpone, buckpass, seeds=(0, 1, 2), ticks=2500):
        res, ov = 0, 0
        for s in seeds:
            p = NetLogoParameters(seed=s, postpone=postpone, buckpass=buckpass).with_structures(
                structure
            )
            r = GarbageCanABM(p, record_events=False).run(ticks)
            res += r.num_resolutions
            ov += r.num_oversights
        return res / (res + ov), ov

    anarchy, _ = share(Structure.ORGANIZED_ANARCHY, False, False)
    anarchy_flights, _ = share(Structure.ORGANIZED_ANARCHY, True, True)
    competent, _ = share(Structure.COMPETENT_HIERARCHY, False, False)
    incompetent, _ = share(Structure.INCOMPETENT_HIERARCHY, False, False)
    assert anarchy < 0.5 and competent < 0.5  # 1. most decisions are made by oversight
    assert anarchy_flights > anarchy  # 2. flights raise the proportion of resolutions
    assert anarchy > competent  # 3. organized anarchies out-resolve hierarchies
    assert incompetent >= competent  # 4. incompetent hierarchies are at least as efficient


def test_behavior_space_experiments_are_the_twelve_from_the_file():
    exps = behavior_space_experiments()
    assert len(exps) == 12
    assert (
        exps["Organized Anarchy"].postpone is False and exps["Organized Anarchy"].buckpass is False
    )
    assert exps["Competent Hierarchy P+BP"].postpone and exps["Competent Hierarchy P+BP"].buckpass
    assert exps["Incompetent Hierarchy BP"].access_structure is Structure.INCOMPETENT_HIERARCHY
    assert all(e.stop_at == 50_000 for e in exps.values())


# ---------------------------------------------------------------------------------- extension seams
def test_custom_components_are_used():
    class NoResolution:
        name = "never"

        def resolves(self, here, model):
            return False

    p = NetLogoParameters(seed=3, postpone=False, buckpass=False).with_structures(
        Structure.ORGANIZED_ANARCHY
    )
    comps = NetLogoComponents.classic(p)
    comps.resolution_rule = NoResolution()
    r = GarbageCanABM(p, components=comps, record_events=False).run(500)
    assert r.num_resolutions == 0 and r.num_oversights > 0

    class Closed:
        """A decision structure under which nobody may ever join an opportunity."""

        name = "closed"

        def participant_may_enter(self, participant, target, model):
            return not target.opportunities

        def opportunity_may_enter(self, opportunity, target, model):
            return not target.participants

    comps2 = NetLogoComponents.classic(p)
    comps2.decision_structure = Closed()
    m = GarbageCanABM(replace(p, seed=11), components=comps2, record_events=False)
    # participants and opportunities may start on the same patch; after the first move phase
    # no new meetings can form, so decisions stay at their initial count
    m.go()
    first = m.num_oversights + m.num_resolutions
    m.run(300)
    assert m.num_oversights + m.num_resolutions == first

"""Contextual organizational structures: an LLM-based representation of who may enter what.

The rule-based ports encode the decision structure as a fixed 0/1 relation between participants
and choice opportunities (a matrix in :mod:`gcm.fortran`, a movement rule in :mod:`gcm.netlogo`).
This subpackage replaces exactly that component by a *contextual* one: an organization is
described in natural language, language models are asked repeatedly whether a participant is
permitted to take part in an opportunity, and the answers are aggregated into a probability
matrix and a binary structure. The structure is exported to a file and loaded by the simulations
through the existing Protocols, so a simulation never calls a language model.

The pipeline, module by module:

==========================  ====================================================================
:mod:`.scenario`            scenario descriptions as YAML data files
:mod:`.representation`      how a scenario becomes text (prose, role list, statute)
:mod:`.prompts`             system and user templates, expected JSON answer, leak guard
:mod:`.connectors`          one small interface to Ollama, OpenAI-compatible APIs, Gemini, Mock
:mod:`.cache`, :mod:`.runlog`  disk cache keyed by the full request; raw responses as JSONL
:mod:`.experiment`          factors, call planning, the runner
:mod:`.aggregate`           yes shares, Wilson intervals, binarization, agreement, distances
:mod:`.structure_io`        the exported structure file
:mod:`.fortran_adapter`     ``DecisionStructure.matrix(state)`` backed by an exported structure
:mod:`.netlogo_adapter`     ``*_may_enter`` permissions backed by a role × type structure
:mod:`.metrics`, :mod:`.compare`  per-level metrics, paired runs, tests and effect sizes
==========================  ====================================================================

Terminology. "Organized anarchy" in the texts of the thesis is the organization type of Cohen,
March & Olsen (1972), such as a university. In the NetLogo code the same words name the setting
without restrictions (``Structure.ORGANIZED_ANARCHY``). This subpackage never uses the term for
its own objects: the unrestricted matrix is called *unsegmented*, as in the 1972 paper.
"""

from gcm.contextual.references import reference_matrices, reference_matrix
from gcm.contextual.scenario import Scenario, load_scenario_file, load_scenarios

__all__ = [
    "Scenario",
    "load_scenario_file",
    "load_scenarios",
    "reference_matrices",
    "reference_matrix",
]

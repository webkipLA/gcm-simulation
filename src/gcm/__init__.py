"""Garbage Can Model of Organizational Choice: Python re-implementations.

Two independent, faithful ports live in this package:

* :mod:`gcm.fortran`: the original FORTRAN simulation ("version five") printed in the
  appendix of Cohen, March & Olsen (1972), *A Garbage Can Model of Organizational Choice*,
  Administrative Science Quarterly 17(1): 1–25.
* :mod:`gcm.netlogo`: the agent-based reconstruction by Fioretti & Lomi (2008, 2010), ported
  from Guido Fioretti's most recent NetLogo source (``GarbageCan_simplified17.nlogox``,
  NetLogo 7.0.4).

Both ports expose their behavioural assumptions (organizational structures, allocation rules,
resolution rule, flight selection) as small, swappable components, see
:mod:`gcm.fortran.interfaces` and :mod:`gcm.netlogo.interfaces`. Only rule-based
implementations are provided here; these seams are the intended insertion points for
LLM-agent substitutes in later work.
"""

from gcm.common import DecisionStyle

__all__ = ["DecisionStyle"]
__version__ = "0.1.0"

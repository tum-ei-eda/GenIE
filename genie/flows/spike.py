"""Spike equivalents of the normal and extended ISS evaluation flows."""
from .flow import GenIEFlow
from .default import DefaultGenIEFlow
from .evaluation import ISSEvaluationFlow
from genie.steps import Spike


@GenIEFlow.factory.register()
class SpikeGenIEFlow(DefaultGenIEFlow):
    Substitutions = {
        "Setup.SetupETISS": None,
        "ISAAC.RetargetISS": Spike.RetargetSpike,
    }


@GenIEFlow.factory.register()
class SpikeEvaluationFlow(ISSEvaluationFlow):
    Substitutions = SpikeGenIEFlow.Substitutions

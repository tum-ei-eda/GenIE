"""Register an example custom flow and run the regular GenIE CLI.

Usage: python examples/demo_script.py --help
"""
from genie.flows import GenIEFlow, ISSEvaluationFlow


@GenIEFlow.factory.register()
class ExampleGenIEFlow(ISSEvaluationFlow):
    """Customize Steps or Substitutions here for a new experiment."""
    pass


if __name__ == "__main__":
    # Import after registration: the CLI builds flow choices at import time.
    from genie.__main__ import cli
    cli()

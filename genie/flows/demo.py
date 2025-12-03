from .flow import GenIEFlow
from .default import DefaultGenIEFlow


@GenIEFlow.factory.register()
class Demo(DefaultGenIEFlow):
    pass

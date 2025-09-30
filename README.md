# GenIE
Code for NorCAS Paper: GenIE: Reuse-Oriented Generation of Domain-Specific Instruction Extensions

## Information on open-source release

The full code (including automation and synthesis scripts) will be mage availabel later this year.

Some parts of the implementation are already available via: https://github.com/tum-ei-eda/isaac-toolkit

## Planned features

Support for:
- 64-bit application cores (multi-issue pipelines)
- custom memory & branch instructions
- more simulators (i.e. Spike/riscv-isa-sim) and compilers (i.e. RISCV-GCC)
- alternative retargeting/synthesis tools
- different extension interfaces (i.e. OpenHWGroup CV-X-IF)

## Disclaimer

The HLS tool used in the paper is currently not available at this point in time. We are working on the integration of alternative HLS solutions and extension interfaces.

## Acknowledgment

<img src="./BMBF_gefoerdert_2017_en.jpg" alt="drawing" height="75" align="left" >

This research is partially funded by the German Federal Ministry of Education and Research (BMBF) within
the projects [Scale4Edge](https://www.edacentrum.de/scale4edge/) (grant number 16ME0465) and [MANNHEIM-FlexKI](https://www.edacentrum.de/projekte/MANNHEIM-FlexKI) (grant number 01IS22086L).

# Code Framework

### Goals

- Split sensor logic into modules
- Schedule module reads at appropriate, synchronized intervals
- Standardize the format in which data is logged
- Catch errors such that if one module fails, the others can continue to run

### Implementation

- `lib.py` organizes towards the goals above
- `base.py` is a class meant to be extended by each module
- `modules/[id].py` contains implementation of the logic for a specific sensor
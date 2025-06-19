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

### Storage

Data is sent over WiFi and saved to an SD card. When saving to SD, it will use the JSONL file format. When saving to web, it will POST a JSON entry to the server URL configured, followed by `/sync/{device_id}?expid={experiment_id}`, with the Bearer authentication header set to the API key configured.
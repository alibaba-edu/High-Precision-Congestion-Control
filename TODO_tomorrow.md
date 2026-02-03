
# TODO For Tomorrow

## 1. Summary of Completed Work (Context for Agent)
The following major tasks have been completed:
- **Waf Build System Migration (Python 3)**:
    - Ported `waf` 1.7.11 and `wscript` files from Python 2 to Python 3.12.
    - Patched `waflib/Context.py` to fix `AttributeError: srcnode/bldnode` and pickling issues by initializing them in `__init__` and fixing class scope.
    - Patched `waflib/Utils.py`, `waflib/Node.py` (fixed `stopIteration`), and `wutils.py` (fixed `TypeError` in environment variable handling).
    - **Status**: The project now builds and runs using `waf` (or `waf_bypass.py`) with Python 3.

- **Dynamic Pulling Rate Implementation**:
    - Added `RX_PULL_RATE_SCHEDULE` configuration to support changing receiver pulling rates over time.
    - Implemented `PullRateEvent` logic in `rdma-hw.cc` and `rdma-hw.h`.
    - Verified with `config_dynamic_pull.txt` (see `walkthrough.md` for results).

- **Instantaneous Queue Depth Logging**:
    - Modified `HandleAckHp` in `src/point-to-point/model/rdma-hw.cc` to log queue depth from INT headers.
    - Output file: `queue_depth.csv`.
    - Plotting script: `results/scripts/plot_queue_depth.py`.

## 2. Outstanding Issues
- **Fix Instantaneous Queue Plot**:
    - **Problem**: The current `instantaneous_queue_depth.png` is reported as "not meaningful".
    - **Investigation Needed**:
        - **Topology Verified**: `topology_two_senders.txt` contains a single switch (Node 3), so seeing only `Hop 0` in `queue_depth.csv` is CORRECT.
        - meaningfulness: The values (~20KB peak) are real queue depth data. The "not meaningful" issue is likely due to the scatter plot visualization (dots) or scale.
        - **Action**: Modify `plot_queue_depth.py` to use line plots (`plt.step` or `plt.plot`) instead of scatter, or improve axis labeling/scaling. Verify if correct INT fields are used.
    - **Action**: Fix the logging or the plotting script to produce a meaningful visualization of switch queue buildup.

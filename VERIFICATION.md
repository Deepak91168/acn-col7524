# Assignment 3 verification

Verified against all pages of `a3/Assignment3.pdf`, including the submission rules.
The final submission opens directly to `p1/`, `p2/`, `p3/`, `Report.pdf` and `README.md`.

## Structure

- `p1/`: unchanged reactive/proactive controllers, original `p1_topo.py`, its runner and results.
- `p2/`: static shortest-delay controller, original `p3_topo.py`, its runner and results.
- `p3/`: independent congestion-aware controller, original `p3_topo.py`, its runner and results.
- `Report.pdf`: design, assumptions, diagrams, selected controller logs, before/after rules,
  ping/receiver results and run commands.

The Python requirements and bundled third-party Ryu wheel are under `p1/` and
install one environment for all parts. Full instructions are in the report and
`README.md`. Parts 2 and 3 have no imports from another part.

The report generator and saved-evidence checker are repository maintenance tools
under `tools/`, outside the submission ZIP. Examiner materials remain in `a3/`.

## Validation procedure

1. Packaged and extracted the refactored sources into an isolated directory.
2. Created a new Python virtual environment there and installed the documented
   `setuptools`, wheel and `p1/requirements.txt` dependencies. `pip check` passed.
3. Ran all three part runners, covering six experiments, with system Python and
   Mininet and the new environment's Ryu controller. After preserving the original
   topology filenames, reran the complete set with the final imports and paths.
4. Compared all networking Python sources in the isolated copy with the submission.
5. Checked connectivity, selected routes, switch rules, utilization and receiver
   throughput using `python3 tools/verify.py`.
6. Regenerated the report from the final logs; rendered and visually checked every
   page. Verified black Arial text and embedded Arial fonts.
7. Rebuilt the final ZIP and checked integrity, top-level structure and byte-for-byte
   agreement with submitted files. Temporary environments, images and caches are excluded.

## Requirements checked

| Requirement | Evidence |
| --- | --- |
| Python 3, Mininet, OpenFlow 1.3, compatible Ryu/OVS and consistent controller port | Six actual Linux experiments; port 6633 in all runners/topologies. |
| Part 1 reactive and proactive rule installation | Existing controllers preserved byte-for-byte; initial/final switch tables and Ryu logs retained. |
| Part 1 connectivity and suitable comparison | Zero-loss pingAll and h1-h5 pings; Packet-In counts and warmed-up RTT in report. |
| Part 1 trade-off | Initial controller work versus advance rules/knowledge explained; first-packet delay is not claimed to have been measured. |
| Part 2 graph, host attachment points and valid metric | Fixed graph/MAC/port maps; additive delay costs; shortest-path computation and OpenFlow rules on the selected switches. |
| Part 2 reverse connectivity | All-pairs pings plus forward/reverse PATH entries. |
| Part 2 changed-cost test | DELAY12=40 changes only a controller cost; h1-h3 route switches from s2 to s4. |
| Part 2 route and performance evidence | Actual before/after tables, packet counters, forward/reverse logs and measured ping RTTs. |
| Part 3 statistics and threshold | One-second port-statistics differences divided by capacity; utilization over 0.70 adds a 100 ms penalty. |
| Part 3 updated routing for later traffic | Later h1-h3 pair uses s4 under load; active h1-h2 rule remains on s1-s2. Five-second idle expiration permits later decisions. |
| Part 3 congestion scenario and static comparison | Same background/foreground UDP workload in both modes; path/utilization logs and receiver intervals retained. |
| Part 3 decision and limitation | Penalty calculation, sampling delay, queue/counter interpretation and host-pair granularity explained. |
| Required topology files | Examiner filenames and content retained, byte-for-byte. No topology changes. |
| Self-contained source and setup | Controllers, topology files, runners, configuration and logs under the three part folders. No external local source tree needed. |
| Report format | Black-and-white diagrams, embedded Arial, actual selected logs and measurements. Setup prose shortened; dependency details remain in README.md. |
| Required archive name | `2025CSY7616 2025MCS2096 A3.zip`. |
| Two-member group | Deepak 2025CSY7616 and Pratik 2025MCS2096. |

Results are single-run demonstrations, not statistical benchmarks. Fixed host
locations and host-pair/EtherType rule granularity are explicit assumptions.

Git branch: `main`. Remote: https://github.com/Deepak91168/acn-col7524.
The course upload and final Submit button remain user actions. This verification
covers technical requirements, not external plagiarism-check outcomes or marks.

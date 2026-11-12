# Assignment 3 verification

Verified on 12 November 2026 against all three pages of `a3/Assignment3.pdf`.
All technical assignment requirements passed in the tested Linux environment.
The report contains the observations and assumptions needed to explain the work.

## What was rerun

A new Python 3.12 virtual environment was created under the ignored `tmp/reverify/`
directory. The documented installation commands installed the bundled Ryu wheel
and requirements without using the earlier environment or external Ryu source.
`pip check` passed. All six Mininet cases ran in an isolated source copy with that
new controller environment. The submitted controllers, topologies and experiment
driver are byte-for-byte identical to the networking sources used in that run.
The final ZIP was extracted separately, its contents compared with the source,
and its saved experiment evidence checked using `experiments/verify.py`.

## Requirement-by-requirement check

| Requirement | Result and evidence |
| --- | --- |
| Linux, Python 3, Mininet, Open vSwitch and OpenFlow 1.3 | PASS. Python 3.12.3, OVS 3.3.9, Ryu 4.34, iperf 2.1.9; six actual Mininet runs. |
| Consistent controller address and port | PASS. Both topologies use 127.0.0.1:6633; the driver starts Ryu on 6633. |
| Part 1 reactive installation | PASS. Existing controller learns MAC ports, handles table misses and installs rules on demand. Initial and final flow tables saved. |
| Part 1 proactive installation | PASS. Ten unicast rules and two broadcast rules already exist across the two switches before host tests. No controller-output rule. |
| Part 1 communication | PASS. Both all-pairs tests and h1-h5 ten-packet ping tests have zero loss. |
| Part 1 suitable comparison | PASS. 101 reactive forwarding Packet-In log entries versus zero for proactive in this run. The workload includes all-pairs warm-up and ten pings. |
| Part 1 trade-off explanation | PASS. Report page 1 explains initial controller work, advance knowledge and unnecessary installed rules. Warmed-up RTT is not presented as first-packet delay. |
| Part 2 topology with alternative routes | PASS. Unchanged four-switch supplied ring; s1-s2-s3 and s1-s4-s3 are alternatives. |
| Part 2 graph and host attachments | PASS. Fixed graph, link port map and MAC/port-1 host mapping, documented on report page 2. Dynamic discovery is not claimed. |
| Part 2 metric and path computation | PASS. Additive delay costs; NetworkX shortest path; OpenFlow rules installed at all switches on the chosen route. |
| Part 2 bidirectional communication | PASS. All-pairs ping and explicit h1-h3 pings; logs show the forward and reverse routes. |
| Part 2 changed link cost | PASS. DELAY12=40 changes a controller cost, as allowed by the assignment. The physical topology stays unchanged. Route changes from s1-s2-s3 to s1-s4-s3. |
| Part 2 route evidence and performance | PASS. Selected-path logs, final switch rules and counters; mean RTT 61.037 ms versus 71.010 ms. |
| Part 3 changing utilization | PASS. One-second port-statistics requests, byte-counter differences and known capacities. The larger directional estimate is used per undirected link. |
| Part 3 congestion rule | PASS. Utilization above 0.70 adds a 100 ms routing-cost penalty. Observed estimate at adaptive decision: 0.97. |
| Part 3 later flow uses updated state | PASS. After warm-up rules expire, the later h1-h3 pair changes from its initial s2 route to s4. The active h1-h2 rule stays on s1-s2. Rules expire after five idle seconds. |
| Part 3 actual congestion scenario | PASS. h1-h2 UDP load uses -b 1.8M on the 2 Mbps link; h1-h3 UDP is offered at -b 600K. Both modes use the same workload. |
| Part 3 comparison to static | PASS. Static path s1-s2-s3, adaptive path s1-s4-s3. Mean first-seven-second receiver rates: 0.480 versus 0.617 Mbps. |
| Part 3 explanation and limitation | PASS. Report page 3 explains the penalty and documents sampling, counter/queue interpretation, no hysteresis, host-pair granularity and no active-flow rerouting. |
| Required source and topology files | PASS. All used topology/controller/configuration/experiment files are inside code-a3 in the ZIP. Topologies match examiner files byte-for-byte. Part 1 code matches the baseline Git commit. |
| Report PDF | PASS. Five pages, three diagrams, selected actual logs, flow-table counters, performance tables, assumptions and run commands. Visually checked all pages. |
| Report style requested in follow-up | PASS. Black and white. Actual text font specifications are Arial in black; Arial regular, bold and italic are embedded. All measurements come from logs. |
| Self-contained extracted submission | PASS in tested environment. Bundled third-party Ryu wheel; other Python dependencies installed by pip. No references to an external local source tree are required. Mininet/OVS/iperf are OS prerequisites, as specified by the assignment. |
| Correct archive name and integrity | PASS. `2025CSY7616 2025MCS2096 A3.zip`; ZIP integrity test and byte comparison after extraction pass. Virtual environments, caches and Git history are excluded. |
| Names and group size | PASS. Deepak 2025CSY7616 and Pratik 2025MCS2096, two members. |

## Corrections made during review

- Report values now come from saved results; the old reactive count of 103 is not hard-coded.
- Every flow-table dump labels its switch.
- Failed switch connection or all-pairs connectivity checks now stop the driver.
- Controller mode/cost environment variables are cleared between experiment cases.
- Background processes are tracked and stopped individually; no global iperf kill.
- Background and foreground receiver logs are retained.
- Removed the empty Part 3 placeholder. The implementation is the shared controller
  in `p2/routing.py`, run with `CONGESTION=1`.
- Added `experiments/verify.py` to check connectivity, forward/reverse path choices,
  output rules, utilization threshold, retained background rule and receiver rates.
- Rewrote the report in plain language with black-and-white vector diagrams,
  embedded Arial and selected evidence from this rerun.

## Scope and remaining user actions

These are single-run demonstration results, not statistical benchmarks. Host
locations are fixed; routing rules distinguish a MAC pair and EtherType, not
individual transport sessions. These assumptions are explicit in the report.

Git is initialized locally on branch `main`. No GitHub remote is configured and
nothing has been pushed. The course upload and final Submit button remain user
actions; neither is part of this local verification. This review verifies the
technical requirements, not external plagiarism-check outcomes or marks.

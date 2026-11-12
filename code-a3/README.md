# Assignment 3: Software-Defined Networking

Deepak — 2025CSY7616  
Pratik — 2025MCS2096

## Files

```text
p1/                  Reactive and proactive forwarding
  reactive.py
  proactive.py
  p1_topo.py         Original two-switch topology
  run.py             Runs both Part 1 experiments
  requirements.txt   Python dependencies for all three parts
  vendor/            Compatible Ryu wheel
  results/           Controller logs, flow tables and ping results
p2/                  Static shortest-delay routing
  routing.py
  p3_topo.py         Original four-switch ring
  run.py             Runs normal and changed-cost experiments
  results/
p3/                  Congestion-aware routing
  routing.py
  p3_topo.py         Original four-switch ring
  run.py             Runs static and congestion-aware comparisons
  results/           Also includes UDP client/server and receiver logs
Report.pdf
README.md
```

The supplied topology files are unchanged. Parts 2 and 3 have separate controllers.
All commands below run from this directory, beside `p1/`, `p2/` and `p3/`.
If you cloned the GitHub repository, first run `cd code-a3`.

## 1. One-time setup

Use Linux with Mininet and Open vSwitch. The tested environment used Python
3.12.3, Open vSwitch 3.3.9, Ryu 4.34 and iperf 2.1.9.

```sh
sudo apt update
sudo apt install mininet openvswitch-switch iperf python3-venv
python3 -m venv .venv
.venv/bin/pip install setuptools==67.6.1 wheel
.venv/bin/pip install -r p1/requirements.txt
sudo systemctl start openvswitch-switch
```

The virtual environment is shared by all parts. No activation is needed when
using the commands here. Ryu runs from `.venv`; Mininet runs with system Python
and `sudo`. All topologies connect to `127.0.0.1:6633`.

The bundled Ryu wheel is third-party Apache-2.0 software with the existing
`ALREADY_HANDLED` adjustment for eventlet. `pip` installs its other dependencies.

## 2. Run the saved experiments automatically

Stop any manually started controller and Mininet session first. Run each command
separately and wait for it to finish before starting the next.

```sh
# Part 1: reactive, then proactive
sudo python3 p1/run.py "$PWD/.venv/bin/ryu-manager"

# Part 2: normal costs, then DELAY12=40
sudo python3 p2/run.py "$PWD/.venv/bin/ryu-manager"

# Part 3: static routing, then congestion-aware routing
sudo python3 p3/run.py "$PWD/.venv/bin/ryu-manager"
```

Each script starts and stops its controller/network and replaces the logs in its
own `results/` folder. Expect each script to take roughly a minute or two. A
failed switch connection or all-pairs connectivity check stops the script.

| Part | Main result files |
| --- | --- |
| 1 | `p1/results/p1-reactive.txt`, `p1-proactive.txt`, and their `*-controller.log` files |
| 2 | `p2/results/p2-base.txt`, `p2-changed.txt`, and their `*-controller.log` files |
| 3 | `p3/results/p3-static.txt`, `p3-adaptive.txt`, controller logs and `*-receiver.log` files |

The `.txt` files contain before/after flow tables and ping output. Part 3 also
saves background UDP logs. The existing PDF records the submitted run; rerunning
experiments updates the logs, not the PDF automatically.

## 3. Part 1 interactively

Open two terminals in this same directory.

**Terminal 1 — reactive controller:**

```sh
.venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p1/reactive.py
```

**Terminal 2 — topology:**

```sh
sudo python3 p1/p1_topo.py
```

At the `mininet>` prompt, inspect the initial tables before sending test traffic:

```text
sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s2
pingall
h1 ping -c 10 10.0.0.5
sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s2
exit
```

Stop Ryu in Terminal 1 with `Ctrl+C`. Repeat with the proactive controller:

```sh
.venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p1/proactive.py
```

Start the same topology again in Terminal 2 and repeat the Mininet commands.
Reactive forwarding starts with a table-miss rule and learns unicast rules.
Proactive forwarding already has destination rules before the ping tests.

## 4. Part 2 interactively

**Terminal 1 — normal delay costs:**

```sh
.venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p2/routing.py
```

**Terminal 2 — ring topology:**

```sh
sudo python3 p2/p3_topo.py
```

At the Mininet prompt:

```text
pingall
h1 ping -c 10 10.0.0.3
sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s2
sh ovs-ofctl -O OpenFlow13 dump-flows s3
sh ovs-ofctl -O OpenFlow13 dump-flows s4
exit
```

Ryu should log `PATH 1 -> 3: [1, 2, 3]`. Its total cost is 30 ms, compared with
35 ms through s4.

Stop Ryu, then restart it with a changed s1-s2 cost:

```sh
DELAY12=40 .venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p2/routing.py
```

Start the topology again and repeat the test. The expected path is `[1, 4, 3]`:
35 ms through s4 versus 50 ms through s2. This changes the controller cost only;
the physical topology stays unchanged.

## 5. Part 3 interactively

The automatic runner is the easiest way to repeat the exact reported comparison.
For a manual test, use the following workload once in each mode, restarting both
Ryu and Mininet between modes.

**Terminal 1 — static comparison:**

```sh
CONGESTION=0 .venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p3/routing.py
```

**Terminal 2 — topology:**

```sh
sudo python3 p3/p3_topo.py
```

At the Mininet prompt, enter these commands in order. `sh sleep 6` allows the
warm-up forwarding rules to expire; the later five-second wait allows utilization
measurements to update while background traffic is running.

```text
pingall
sh sleep 6
h2 iperf -s -u -p 5001 > /tmp/a3-manual-background-server.log 2>&1 &
h1 iperf -c 10.0.0.2 -u -b 1.8M -t 24 -p 5001 > /tmp/a3-manual-background-client.log 2>&1 &
sh sleep 5
h1 ping -c 5 -i 0.2 10.0.0.3
h3 iperf -s -u -i 1 -p 5002 > /tmp/a3-manual-receiver.log 2>&1 &
h1 iperf -c 10.0.0.3 -u -b 600K -t 8 -p 5002
h3 cat /tmp/a3-manual-receiver.log
sh ovs-ofctl -O OpenFlow13 dump-flows s1
exit
```

Stop Ryu. Restart it in congestion-aware mode, start the topology again, and run
the same Mininet workload:

```sh
.venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p3/routing.py
```

Congestion-aware routing is the default in Part 3. Ryu samples port statistics
every second and adds a 100 ms cost penalty when estimated utilization exceeds
70%. Under this workload, the later h1-h3 traffic should use `[1, 4, 3]` instead
of the static `[1, 2, 3]` route. Existing active rules are not rerouted; rules
expire after five idle seconds. Rules distinguish a MAC pair and EtherType,
so the UDP traffic reuses the route selected for the preceding h1-h3 ping.

Compare receiver interval rates, not just the client's offered rate. Under load,
the final UDP acknowledgement can time out even while the server receives data.
Manual `/tmp/a3-manual-*.log` files are overwritten when the workload is repeated;
copy them elsewhere first if you want to retain both runs.

## 6. Stop and clean up

In Mininet, enter `exit`. In the controller terminal, press `Ctrl+C`.
After an interrupted run, use:

```sh
sudo mn -c
```

If the controller cannot bind port 6633, check for another controller:

```sh
sudo ss -ltnp 'sport = :6633'
```

Stop the old controller before retrying. If an interactive run cannot reach the
switches, check that Ryu is running, the topology uses port 6633, and Open vSwitch
is active:

```sh
sudo systemctl status openvswitch-switch
```

The fixed host MAC addresses and port maps assume the supplied topology files;
keep `autoSetMacs=True` when rerunning them.

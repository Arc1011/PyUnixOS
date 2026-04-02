# PyUnixOS

A single-file Unix-like „kernel” and interactive shell for the **ESP32 WROOM**, written entirely in MicroPython.

No `uasyncio`. No frameworks. Just Python generators, a round-robin scheduler, a virtual filesystem, and a shell that feels like the real thing.

```
rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
...
  Starting kernel subsystems...

  Mounting LittleFS root filesystem              [  OK  ]
  Loading scheduler (round-robin, preempt)       [  OK  ]
  Starting shell daemon (kshd)                   [  OK  ]

  KernelOS booted successfully.  [Power-on reset]

esp32 login: root  (autologin)

root@esp32:/# _
```

---

## Features

### Shell
- Interactive REPL with `root@esp32:/path#` prompt
- Command history — up/down arrow navigation, `!n` re-execution
- Tab completion for all built-in commands
- Pipe support: `cat /proc/cpuinfo | grep MHz | less`
- Variable expansion (`$HOME`, `$USER`, etc.)
- Aliases — built-in and user-defined

### Virtual Filesystem
| Path | Description |
|------|-------------|
| `/proc/cpuinfo` | Real CPU info from `machine.freq()` and `unique_id()` |
| `/proc/meminfo` | Live RAM stats from `gc` |
| `/proc/uptime` | Seconds since boot |
| `/proc/mounts` | Mounted filesystems including SD card detection |
| `/proc/stat` | Scheduler process stats |
| `/proc/loadavg` | Calculated from running/total process ratio |
| `/etc/passwd` | System users |
| `/etc/os-release` | OS identity with real build ID |
| `/etc/motd` | Live RAM and flash stats at login |
| `/dev/null` `/dev/zero` `/dev/random` | Standard devices |
| `/sys/devices/cpu/freq` | Live CPU frequency |
| `/bin/<cmd>` | Virtual executables for every built-in |

Real directories on LittleFS: `/root`, `/var/log`, `/tmp`  
`/var/log/syslog` — persists across reboots, logs boot and kernel panics.

### Scheduler
- Generator-based cooperative round-robin — `yield N` sleeps for N milliseconds
- Real PID table, process states (R/S/Z)
- `ps`, `kill`, `spawn`, `watch`
- Kernel panic recovery loop — auto-restarts without flashing

### Hardware Commands
| Command | Description |
|---------|-------------|
| `gpio read/write/mode <pin>` | Digital I/O |
| `adc <pin>` | 12-bit ADC read with mV conversion (GPIO 32–39) |
| `pwm <pin> <freq> <duty>` | PWM on any output pin |
| `i2cscan [sda] [scl]` | I2C bus scan like `i2cdetect` |
| `temp` | Internal ESP32 temperature sensor |

### Network
| Command | Description |
|---------|-------------|
| `wifi connect <ssid> <pw>` | Connect to WiFi |
| `wifi status/scan/disconnect/up/down` | WiFi management |
| `ntp` | Sync RTC via pool.ntp.org |
| `wget <url> [-O file\|-]` | HTTP/HTTPS download with progress bar |

### Editor
- `vi <file>` — line-oriented editor, type freely, `:wq` save+quit, `:q` quit, `:p` print, `:d N` delete line

### Other
- `neofetch` — ASCII logo with real hardware stats
- `less`/`more` — scrollable pager with keyboard navigation
- `dmesg` — kernel ring buffer with real timestamps and hardware values
- `free` — RAM and Flash usage from real `gc` and `statvfs()`
- `hwinfo` — full hardware report, refreshable at runtime
- `gc` — explicit garbage collection with honest before/after reporting
- `lsmod` — probes hardware modules instead of hardcoding them
- `exit-debug` — drops to native MicroPython REPL without reflashing

---

## Requirements

| | |
|-|-|
| Board | ESP32 WROOM-32 (or any ESP32 with ≥4MB flash) |
| Firmware | MicroPython ≥ 1.20 (tested on v1.27.0) |
| Flash | One file: `main.py` or pre-compiled `main.mpy` |
| RAM | ~320kB free recommended (standard ESP32 heap) |

---

## Quick start

See [QUICKSTART.md](QUICKSTART.md) for full installation instructions.

```bash
# Clone
git clone https://github.com/Arc1011/PyUnixOS
cd kernelos

# Pre-compile (recommended — avoids MemoryError on large files)
git clone https://github.com/micropython/micropython
git -C micropython checkout v1.27.0
make -C micropython/mpy-cross
./micropython/mpy-cross/build/mpy-cross main.py

# Flash
mpremote connect /dev/ttyUSB0 fs cp main.mpy :main.mpy + reset
```

---

## Architecture

```
main.py
├── Colors / output helpers
├── Scrollback buffer + pager (less/more)
├── Boot sequence
├── Scheduler          — generator-based, TICK_MS = 5ms
│   └── Process        — pid, state (R/S/Z), wake_ms
├── Virtual Filesystem — VIRTUAL_FILES + VIRTUAL_LS + real LittleFS
├── Shell state        — history, env, aliases, cron
├── Parser             — tokenizer, pipe splitter, $VAR expansion
├── Commands           — ~50 built-ins
├── Dispatch           — pipe execution, !n history, tab completion
├── proc_repl          — generator: non-blocking stdin, arrow keys, Tab
├── proc_cron          — generator: fires scheduled commands
├── proc_heartbeat     — generator: blinks GPIO2
└── Main loop          — boot → spawn processes → run_forever()
```

Every process is a Python generator. `yield N` yields control for N milliseconds. No threads, no `uasyncio`, no event loops — just `next()` in a loop.

---

## License

BSD 3-Clause. See [LICENSE](LICENSE).

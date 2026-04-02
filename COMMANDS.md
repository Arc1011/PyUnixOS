# Command Reference

## Filesystem

| Command | Description |
|---------|-------------|
| `ls [-la] [path]` | List directory. `-l` long format, `-a` show hidden |
| `cat <file>` | Print file contents |
| `pwd` | Print working directory |
| `cd [dir]` | Change directory. No argument → `/root` |
| `mkdir <dir>` | Create directory |
| `rm <file>` | Remove file |
| `touch <file>` | Create empty file |
| `write <file> <text>` | Write text to file (overwrites) |
| `append <file> <text>` | Append text to file |
| `head [-N] <file>` | First N lines (default 10) |
| `tail [-N] <file>` | Last N lines (default 10) |
| `df` | Disk usage (RAM + Flash via `statvfs`) |
| `wc <file>` | Line / word / byte count |

## Text tools

| Command | Description |
|---------|-------------|
| `grep <pattern> [file]` | Search for pattern. Works with pipe |
| `tee <file>` | Write pipe input to file and stdout |
| `less [file]` | Scrollable pager. No argument = scrollback buffer |
| `more [file]` | Alias for `less` |
| `scroll [N]` | Print last N lines of scrollback (default 40) |

**Pager keys:** arrows / `j` `k` scroll line, `f` `b` / Space scroll page, `g` `G` top/bottom, `q` quit.

## Process management

| Command | Description |
|---------|-------------|
| `ps` | List all processes with PID, state, VSZ, time |
| `kill <pid\|name>` | Send SIGKILL to process |
| `spawn <name> [ticks] [ms]` | Start a demo background process |
| `watch <ms> <cmd>` | Re-run command every N ms (like `top`) |

**Process states:** `R` running, `S` sleeping, `Z` zombie (finished)

## System

| Command | Description |
|---------|-------------|
| `uname [-a]` | OS and hardware info |
| `uptime` | System uptime and load average |
| `date` | Current date/time from RTC |
| `dmesg` | Kernel ring buffer (opens in pager) |
| `free` | RAM and Flash usage |
| `temp` | Internal ESP32 CPU temperature |
| `hwinfo` | Full hardware report (refreshes from hardware) |
| `refresh-hw` | Re-probe hardware and update cached info |
| `neofetch` | ASCII logo + system summary |
| `reboot` | Restart the ESP32 |
| `halt` | Halt the system |
| `shutdown` | Alias for `reboot` |

## Users

| Command | Description |
|---------|-------------|
| `who` | Current logged-in user |
| `w` | Who is logged in and what they are doing |
| `last` | Login history |
| `su [user]` | Switch user (root only) |
| `wall <message>` | Broadcast message to all users |

## Hardware

| Command | Usage |
|---------|-------|
| `gpio read <pin>` | Read digital pin value (0 or 1) |
| `gpio write <pin> <0\|1>` | Set digital output |
| `gpio mode <pin> <in\|out\|pu>` | Configure pin mode (`pu` = pull-up input) |
| `gpio list` | Show available GPIO ranges |
| `adc <pin>` | Read ADC — GPIO 32–39, returns raw + mV |
| `pwm <pin> <freq_hz> <duty>` | PWM output. duty 0–1023 |
| `i2cscan [sda] [scl]` | Scan I2C bus (default SDA=21 SCL=22) |

## Network

| Command | Description |
|---------|-------------|
| `wifi status` | Show interface status and IP |
| `wifi scan` | Scan for nearby networks |
| `wifi connect <ssid> <pw>` | Connect to WiFi |
| `wifi disconnect` | Disconnect |
| `wifi up` / `wifi down` | Enable / disable radio |
| `ntp` | Sync time via pool.ntp.org (requires WiFi) |
| `wget <url> [-O file\|-]` | Download file. `-O -` prints to stdout |

**wget examples:**
```bash
wget http://wttr.in/London?format=3 -O -
wget https://raw.githubusercontent.com/user/repo/main/file.py
wget http://example.com/data.json -O /root/data.json
```

## Scheduler / cron

| Command | Description |
|---------|-------------|
| `cron add <ms> <cmd>` | Run `cmd` every N milliseconds |
| `cron list` | Show scheduled jobs |
| `cron del <id>` | Remove job by ID |
| `crontab` | Alias for `cron list` |
| `crontab -r` | Remove all jobs |

## Modules / hardware info

| Command | Description |
|---------|-------------|
| `lsmod` | List kernel modules (probes hardware) |
| `lspci` | List hardware devices |
| `lsblk` | List block devices with sizes |
| `modprobe <mod>` | Attempt to load kernel module |

## Editor

| Command | Description |
|---------|-------------|
| `vi <file>` | Open file for editing |

**vi commands** (type on a line by itself, then Enter):

| Command | Action |
|---------|--------|
| `:wq` | Save and quit |
| `:q` | Quit without saving |
| `:w` | Save without quitting |
| `:p` | Print file with line numbers |
| `:d N` | Delete line N |
| `:help` | Show command list |

## Shell

| Command | Description |
|---------|-------------|
| `echo [-n] <text>` | Print text. `-n` suppresses newline |
| `env` | Show all environment variables |
| `export KEY=value` | Set environment variable |
| `alias [name=cmd]` | Show or define alias |
| `unalias <name>` | Remove alias |
| `history [N]` | Show last N commands (default 10) |
| `which <cmd>` | Show path of command (`/bin/<cmd>`) |
| `gc` | Run garbage collector, report freed memory |
| `help` | List all commands |
| `clear` | Clear terminal screen |
| `exit-debug` | Drop to MicroPython REPL |

## Built-in aliases

| Alias | Expands to |
|-------|-----------|
| `ll` | `ls -la` |
| `la` | `ls -a` |
| `..` | `cd ..` |
| `mem` | `cat /proc/meminfo` |
| `cpu` | `cat /proc/cpuinfo` |
| `top` | `watch ps 2000` |
| `ifconfig` | `wifi status` |
| `dir` | `ls` |
| `type` | `which` |

## Pipe

Commands can be chained with `|`:

```bash
cat /proc/cpuinfo | grep MHz
cat /proc/meminfo | less
ls -la /etc | grep passwd
wifi scan | grep MyNetwork
```

## History

```bash
history         # show last 10
history 50      # show last 50
!3              # re-run command #3
```

Arrow keys ↑↓ navigate history in the prompt.

## Virtual paths

These paths exist but are generated on-the-fly from real hardware:

```
/proc/cpuinfo     /proc/meminfo     /proc/uptime
/proc/version     /proc/mounts      /proc/stat
/proc/loadavg     /proc/self/status
/etc/passwd       /etc/hostname     /etc/os-release  /etc/motd
/dev/null         /dev/zero         /dev/random      /dev/urandom
/sys/devices/cpu/freq
/sys/kernel/mm/free
/sys/kernel/flash/size
/sys/kernel/uptime_ms
/bin/<any-command>
```

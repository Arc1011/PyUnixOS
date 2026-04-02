# PyUnixOS v2.0 — single file build
# ESP32 WROOM, MicroPython >= 1.20
# Flash as main.py

import sys, os, gc, time
import ubinascii
from machine import Pin, ADC, PWM, freq, reset, unique_id, RTC
from machine import reset_cause, PWRON_RESET, DEEPSLEEP_RESET, SOFT_RESET, WDT_RESET

# ═══════════════════════════════════════════════════════════════
#  COLORS / OUTPUT
# ═══════════════════════════════════════════════════════════════

class C:
    RST  = "\x1b[0m";  BOLD = "\x1b[1m";  DIM  = "\x1b[2m"
    RED  = "\x1b[31m"; GRN  = "\x1b[32m"; YEL  = "\x1b[33m"
    CYN  = "\x1b[36m"; WHT  = "\x1b[97m"; GRY  = "\x1b[90m"
    BRED = "\x1b[1;31m"; BGRN = "\x1b[1;32m"; BCYN = "\x1b[1;36m"
    BYEL = "\x1b[1;33m"

def _w(s):          sys.stdout.write(s)
def _c(s, col):     return col + s + C.RST
def _bold(s):       return C.BOLD + s + C.RST
def _dim(s):        return C.DIM  + s + C.RST
def _grn(s):        return C.GRN  + s + C.RST
def _red(s):        return C.RED  + s + C.RST
def _wht(s):        return C.WHT  + s + C.RST

# scrollback buffer — every _wl() call appends here
PAGER_LINES = 23
PAGER_BUF   = 500
_scrollback  = []

def _wl(s):
    sys.stdout.write(s + "\n")
    _scrollback.append(s)
    if len(_scrollback) > PAGER_BUF:
        _scrollback.pop(0)

# ═══════════════════════════════════════════════════════════════
#  PAGER  (less / more)
# ═══════════════════════════════════════════════════════════════

def _read_blocking():
    while True:
        try:
            ch = sys.stdin.read(1)
            if ch: return ch
        except: pass
        time.sleep_ms(10)

def _pager_draw(lines, top, cols=80):
    _w("\x1b[2J\x1b[H")
    for line in lines[top: top + PAGER_LINES]:
        sys.stdout.write(line + "\n")
    total  = len(lines)
    bottom = top + PAGER_LINES
    pct    = min(100, 100 * bottom // total) if total else 100
    label  = "END" if bottom >= total else str(pct) + "%"
    status = " lines %d-%d/%d (%s) [arrows/j/k/b/f/g/G/q]" % (
        top+1, min(bottom, total), total, label)
    _w(C.BOLD + "\x1b[7m" + status + " "*max(0, cols-len(status)) + C.RST)

def pager(lines, cols=80):
    if not lines: return
    top = 0; total = len(lines)
    _pager_draw(lines, top, cols)
    while True:
        ch = _read_blocking()
        if ch == "\x1b":
            ch2 = _read_blocking()
            if ch2 == "[":
                ch3 = _read_blocking()
                if   ch3 == "A": top = max(0, top - 1)
                elif ch3 == "B": top = min(max(0, total-1), top + 1)
                elif ch3 == "5": _read_blocking(); top = max(0, top - PAGER_LINES)
                elif ch3 == "6": _read_blocking(); top = min(max(0, total-PAGER_LINES), top + PAGER_LINES)
                elif ch3 == "H": top = 0
                elif ch3 == "F": top = max(0, total - PAGER_LINES)
        elif ch in ("q","Q","\x03","\x04"): break
        elif ch in (" ","f"): top = min(max(0, total-PAGER_LINES), top + PAGER_LINES)
        elif ch == "b":       top = max(0, top - PAGER_LINES)
        elif ch in ("\r","\n","j"): top = min(max(0, total-1), top + 1)
        elif ch == "k":       top = max(0, top - 1)
        elif ch == "g":       top = 0
        elif ch == "G":       top = max(0, total - PAGER_LINES)
        _pager_draw(lines, top, cols)
    _w("\x1b[2J\x1b[H")

def collect(fn):
    """Run fn(), capture all _wl() output and return as list of lines."""
    buf = []
    def _cap(s):
        sys.stdout.write(s + "\n"); buf.append(s)
        _scrollback.append(s)
        if len(_scrollback) > PAGER_BUF: _scrollback.pop(0)
    orig = globals()["_wl"]
    globals()["_wl"] = _cap
    try:    fn()
    finally: globals()["_wl"] = orig
    return buf

# ═══════════════════════════════════════════════════════════════
#  BOOT SEQUENCE
# ═══════════════════════════════════════════════════════════════

_boot_ms = time.ticks_ms()

def _reset_reason():
    rc = reset_cause()
    if rc == PWRON_RESET:     return "Power-on reset"
    if rc == DEEPSLEEP_RESET: return "Wake from deep sleep"
    if rc == SOFT_RESET:      return "Soft reset"
    if rc == WDT_RESET:       return "Watchdog reset"
    return "Unknown reset"

def _post_line(label, ms=40):
    _w("  " + _dim(label) + " "*max(0, 52-len(label)))
    time.sleep_ms(ms)
    _wl("  [  " + _grn("OK") + "  ]")

def run_boot():
    _w("\x1b[2J\x1b[H")
    gc.collect()
    uid = ubinascii.hexlify(unique_id()).decode().upper()
    mhz = freq() // 1_000_000
    # ROM stage output
    _wl(_dim("rst:"+str(reset_cause())+" (TG0WDT_SYS_RST),boot:0x13 (SPI_FAST_FLASH_BOOT)"))
    _wl(_dim("configsip: 0, SPIWP:0xee"))
    _wl(_dim("clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00"))
    _wl(_dim("mode:DIO, clock div:2"))
    _wl(_dim("load:0x3fff0030,len:1344"))
    _wl(_dim("load:0x40078000,len:13836"))
    _wl(_dim("load:0x40080400,len:3608"))
    _wl(_dim("entry 0x400805f0"))
    time.sleep_ms(120); _wl("")
    # kernel header
    _wl(_bold(_wht("PyUnixOS")) + _dim("  version 5.4.0-esp32  ("+uid[:8].lower()+")"))
    _wl(_dim("Command line: console=ttyS0,115200 root=/dev/mmcblk0p1 rootfstype=littlefs"))
    _wl(_dim("BIOS-provided physical RAM map:"))
    _wl(_dim("  BIOS-e820: [mem 0x0000000000000000-0x0000000003ffffff] usable")); _wl("")
    time.sleep_ms(60)
    _wl(_dim("CPU0 (TensilicaLX6@"+str(mhz)+"MHz) #0"))
    _wl(_dim("CPU1 (TensilicaLX6@"+str(mhz)+"MHz) #1"))
    _wl(_dim("Serial: 8250/16550 driver, 2 ports, IRQ sharing disabled"))
    _wl(_dim("[    0.000000] Calibrating delay loop... "+str(mhz*2)+".00 BogoMIPS"))
    time.sleep_ms(80); _wl("")
    _wl(_bold("  Starting kernel subsystems...")); _wl("")
    for label, ms in [
        ("Initializing cgroup subsystems",30), ("Setting up memory protection",25),
        ("Initializing IRQ subsystem",20),     ("Calibrating APIC timer",35),
        ("Mounting proc filesystem",15),       ("Mounting sysfs",15),
        ("Mounting devtmpfs on /dev",20),      ("Starting udev",45),
        ("Initializing NVS partition",50),     ("Mounting LittleFS root filesystem",80),
        ("Checking filesystem integrity",120), ("Loading scheduler (round-robin, preempt)",30),
        ("Initializing GPIO subsystem",25),    ("Initializing ADC driver",25),
        ("Initializing PWM driver",15),        ("Initializing SPI bus 0",20),
        ("Initializing I2C bus 0",20),         ("Loading WiFi driver (ESP-IDF)",90),
        ("Initializing TCP/IP stack (lwIP)",60),("Starting syslogd",20),
        ("Starting crond",15),                 ("Starting shell daemon (kshd)",30),
    ]:
        _post_line(label, ms)
    time.sleep_ms(100); _wl("")
    _wl(_grn("  PyUnixOS booted successfully.") + _dim("  ["+_reset_reason()+"]")); _wl("")
    _wl(_bold("esp32 login: ") + _wht("root") + _dim("  (autologin)"))
    time.sleep_ms(200); _wl("")
    _wl(_dim("Last login: Thu Jan  1 00:00:00 UTC 1970 on ttyS0"))
    gc.collect()
    _wl("")
    _wl(_c("  ┌─────────────────────────────────────────┐", C.CYN))
    _wl(_c("  │  ", C.CYN) + _bold("PyUnixOS v5.4.0-" + _HW["platform"]) + _c("                 │", C.CYN))
    _wl(_c("  │  ", C.CYN) + _dim("Type 'help' for commands") + _c("                 │", C.CYN))
    _wl(_c("  │  ", C.CYN) + _dim("RAM:   ") + _c("%dkB free / %dkB total" % (gc.mem_free()//1024, (gc.mem_free()+gc.mem_alloc())//1024), C.GRN) + _c("       │", C.CYN))
    _wl(_c("  │  ", C.CYN) + _dim("Flash: ") + _c("%dkB free / %dkB total" % (_HW.get("flash_free",0), _HW.get("flash",0)), C.GRN) + _c("       │", C.CYN))
    _wl(_c("  │  ", C.CYN) + _dim("CPU:   ") + _c("%dMHz  uid:%s" % (freq()//1_000_000, _HW["uid"][:8]), C.GRN) + _c("       │", C.CYN))
    _wl(_c("  └─────────────────────────────────────────┘", C.CYN))
    _wl("")

# ═══════════════════════════════════════════════════════════════
#  SCHEDULER  —  round-robin, generator-based, no uasyncio
# ═══════════════════════════════════════════════════════════════

TICK_MS = 5

class Process:
    _next_pid = 2
    def __init__(self, name, gen, ppid=1, priority=0):
        self.pid      = Process._next_pid; Process._next_pid += 1
        self.name     = name;  self.gen      = gen
        self.ppid     = ppid;  self.priority = priority
        self.state    = "R";   self.wake_ms  = 0
        self.started  = time.ticks_ms(); self.cpu_ms = 0
    @property
    def vsz(self): return 128 + self.pid * 4

class Scheduler:
    def __init__(self):
        self._procs = []; self._pending = []
        # PID 1 — fake init process
        self._init = type("P", (), {
            "pid":1, "ppid":0, "name":"init", "state":"S",
            "priority":0, "vsz":512, "started":0, "cpu_ms":0,
        })()

    def spawn(self, name, gf, *a, ppid=1, priority=0):
        p = Process(name, gf(*a), ppid=ppid, priority=priority)
        self._pending.append(p); return p

    def kill(self, key):
        killed = []
        for p in self._procs:
            if p.pid == key or p.name == key:
                p.state = "Z"; killed.append(p.pid)
        return killed

    def processes(self): return [self._init] + list(self._procs)

    def run_forever(self):
        while True:
            try: self._tick()
            except KeyboardInterrupt: self._sigint()
            except Exception as e:
                _wl("\r\n" + _c("[kernel panic] " + str(e), C.BRED))

    def _sigint(self):
        # forward Ctrl+C to the shell process instead of crashing
        for p in self._procs:
            if p.name == "kshd" and p.state != "Z":
                try: p.gen.throw(KeyboardInterrupt)
                except (KeyboardInterrupt, StopIteration): pass
                return
        _w("\r\n")

    def _tick(self):
        now = time.ticks_ms()
        while self._pending: self._procs.append(self._pending.pop(0))
        survivors = []
        for p in self._procs:
            if p.state == "Z": continue
            if p.state == "S":
                if time.ticks_diff(now, p.wake_ms) < 0:
                    survivors.append(p); continue
                p.state = "R"
            try:
                val = next(p.gen)
                if isinstance(val, int) and val > 0:
                    p.wake_ms = time.ticks_add(time.ticks_ms(), val)
                    p.state   = "S"
                else:
                    p.state = "R"
                survivors.append(p)
            except StopIteration: p.state = "Z"
            except Exception as e:
                p.state = "Z"
                _wl("\r\n" + _c("[sched] '"+p.name+"' crashed: "+str(e), C.RED))
        self._procs = survivors
        time.sleep_ms(TICK_MS)

SCHED = Scheduler()

# ═══════════════════════════════════════════════════════════════
#  HARDWARE INFO — queried once at boot, cached
# ═══════════════════════════════════════════════════════════════

def _hw_info():
    """Read real hardware info from machine module."""
    info = {}
    info["mhz"]   = freq() // 1_000_000
    info["uid"]   = ubinascii.hexlify(unique_id()).decode()
    info["flash"]  = 0
    info["flash_free"] = 0
    try:
        st = os.statvfs("/")
        info["flash"]      = st[0] * st[2] // 1024   # kB total
        info["flash_free"] = st[0] * st[3] // 1024   # kB free
        info["fs_type"]    = "littlefs"
        info["fs_blk"]     = st[0]
        info["fs_tot"]     = st[2]
        info["fs_free"]    = st[3]
    except:
        info["fs_type"] = "unknown"
        info["fs_blk"]  = 4096
        info["fs_tot"]  = 0
        info["fs_free"] = 0
    # detect number of real cores via idf_ver if available
    info["cores"] = 2  # ESP32 always dual-core Xtensa LX6
    try:
        import esp
        info["flash_sz"] = esp.flash_size() // 1024  # kB
    except:
        info["flash_sz"] = info["flash"]
    # MicroPython version string
    info["mpy_ver"] = sys.version
    # platform
    info["platform"] = sys.platform
    return info

_HW = _hw_info()   # cache at boot — call _hw_info() again to refresh

def _refresh_hw():
    global _HW
    _HW = _hw_info()

# ═══════════════════════════════════════════════════════════════
#  VIRTUAL FILESYSTEM  —  /proc  /dev  /sys  /etc  + real LittleFS
# ═══════════════════════════════════════════════════════════════

def _proc_cpuinfo():
    mhz = freq() // 1_000_000   # read live
    uid = _HW["uid"]
    out = ""
    for core in range(_HW["cores"]):
        out += ("processor\t: %d\nmodel name\t: Xtensa LX6 @ %d MHz\n"
                "bogomips\t: %d.00\ncache size\t: 32 KB\n"
                "cpu MHz\t\t: %d.000\nhardware\t: %s\nserial\t\t: %s\n\n"
                % (core, mhz, mhz*2, mhz, _HW["platform"].upper(), uid))
    return out

def _proc_meminfo():
    gc.collect()
    fr  = gc.mem_free()
    al  = gc.mem_alloc()
    tot = fr + al
    return ("MemTotal:       %8d kB\nMemFree:        %8d kB\n"
            "MemAvailable:   %8d kB\nBuffers:               0 kB\n"
            "Cached:                0 kB\nSwapTotal:             0 kB\nSwapFree:              0 kB\n"
            % (tot//1024, fr//1024, fr//1024))

def _proc_uptime():
    ms = time.ticks_diff(time.ticks_ms(), _boot_ms)
    s  = ms / 1000.0
    # idle = rough estimate: uptime * (1 - scheduler overhead)
    idle = s * (1.0 - TICK_MS / 1000.0)
    return "%.2f %.2f\n" % (s, idle)

def _proc_version():
    mhz = freq() // 1_000_000
    return "PyUnixOS 5.4.0-%s (MicroPython %s) #1 SMP %dMHz\n" % (
        _HW["platform"], _HW["mpy_ver"].split(";")[0].strip(), mhz)

def _proc_mounts():
    # check what's actually mounted
    lines = ""
    # root — always present
    fs = _HW.get("fs_type", "littlefs")
    lines += "rootfs / %s rw 0 0\n" % fs
    lines += "proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0\n"
    lines += "sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0\n"
    lines += "devtmpfs /dev devtmpfs rw,size=128k 0 0\n"
    lines += "tmpfs /tmp tmpfs rw,size=64k 0 0\n"
    # check if sd card is mounted
    try:
        os.stat("/sd"); lines += "fat /sd vfat rw 0 0\n"
    except: pass
    return lines

def _proc_stat():
    ms  = time.ticks_diff(time.ticks_ms(), _boot_ms)
    jif = ms // 10
    # split across real core count
    cores = _HW["cores"]
    per   = jif // cores
    out   = "cpu  %d 0 %d %d 0 0 0 0 0 0\n" % (jif, jif//4, jif*12)
    for i in range(cores):
        out += "cpu%d %d 0 %d %d 0 0 0 0 0 0\n" % (i, per, per//4, per*12)
    out += ("intr 0\nctxt 0\nbtime 0\n"
            "processes %d\nprocs_running %d\nprocs_blocked 0\n"
            % (Process._next_pid-1, sum(1 for p in SCHED.processes() if p.state=="R")))
    return out

def _proc_loadavg():
    # calculate a rough load: running tasks / total tasks
    procs = SCHED.processes()
    total = len(procs)
    running = sum(1 for p in procs if p.state == "R")
    load = running / max(total, 1)
    return "%.2f %.2f %.2f %d/%d %d\n" % (
        load, load*0.9, load*0.8, running, total, Process._next_pid-1)

def _proc_self_status():
    gc.collect()
    return ("Name:\tkshd\nPid:\t%d\nPPid:\t1\nState:\tS (sleeping)\n"
            "VmRSS:\t%d kB\nVmSize:\t%d kB\nThreads:\t1\n"
            % (Process._next_pid-1, gc.mem_alloc()//1024, (gc.mem_alloc()+gc.mem_free())//1024))

def _etc_passwd():
    return ("root:x:0:0:root:/root:/bin/ksh\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n")

def _etc_hostname():
    return _env.get("HOSTNAME", "esp32") + "\n"

def _etc_os_release():
    mhz = freq() // 1_000_000
    return ('NAME="PyUnixOS"\nVERSION="5.4.0"\nID=kernelos\n'
            'VERSION_ID="5.4"\nPRETTY_NAME="PyUnixOS 5.4.0 (%s @ %dMHz)"\n'
            'HOME_URL="http://kernelos.local"\n'
            'BUILD_ID="%s"\n'
            % (_HW["platform"].upper(), mhz, _HW["uid"][:8]))

def _etc_motd():
    gc.collect()
    mhz  = freq() // 1_000_000
    fr   = gc.mem_free()
    al   = gc.mem_alloc()
    flash_free = _HW.get("flash_free", 0)
    return ("PyUnixOS 5.4.0-%s  uid:%s\n"
            "RAM:   %dkB free / %dkB total\n"
            "Flash: %dkB free / %dkB total\n"
            "CPU:   %dMHz  cores:%d\n"
            % (_HW["platform"], _HW["uid"][:8],
               fr//1024, (fr+al)//1024,
               flash_free, _HW.get("flash",0),
               mhz, _HW["cores"]))

def _dev_null():   return ""
def _dev_zero():   return "\x00" * 32

def _dev_random():
    # xor uid bytes with ticks for some variation
    raw = bytearray(unique_id())
    t   = time.ticks_ms()
    for i in range(len(raw)):
        raw[i] ^= (t >> (i*8)) & 0xFF
    return ubinascii.hexlify(raw).decode()

def _dev_urandom():
    # different call = different ticks = different output
    time.sleep_ms(1)
    return _dev_random()

def _sys_cpufreq():
    return str(freq()) + "\n"

def _sys_memfree():
    gc.collect(); return str(gc.mem_free()) + "\n"

def _sys_flash_size():
    return str(_HW.get("flash_sz", 0) * 1024) + "\n"

def _sys_uptime_ms():
    return str(time.ticks_diff(time.ticks_ms(), _boot_ms)) + "\n"

VIRTUAL_FILES = {
    "/proc/cpuinfo":   _proc_cpuinfo,    "/proc/meminfo":   _proc_meminfo,
    "/proc/uptime":    _proc_uptime,     "/proc/version":   _proc_version,
    "/proc/mounts":    _proc_mounts,     "/proc/stat":      _proc_stat,
    "/proc/loadavg":   _proc_loadavg,    "/proc/self/status":_proc_self_status,
    "/etc/passwd":     _etc_passwd,      "/etc/hostname":   _etc_hostname,
    "/etc/os-release": _etc_os_release,  "/etc/motd":       _etc_motd,
    "/dev/null":       _dev_null,        "/dev/zero":       _dev_zero,
    "/dev/random":     _dev_random,      "/dev/urandom":    _dev_urandom,
    "/sys/devices/cpu/freq":   _sys_cpufreq,
    "/sys/kernel/mm/free":     _sys_memfree,
    "/sys/kernel/flash/size":  _sys_flash_size,
    "/sys/kernel/uptime_ms":   _sys_uptime_ms,
}

VIRTUAL_DIRS = {
    "/proc", "/proc/self", "/dev", "/etc",
    "/sys", "/sys/devices", "/sys/devices/cpu",
    "/sys/kernel", "/sys/kernel/mm", "/sys/kernel/flash",
    "/tmp",
}

# /bin and /usr/bin — built from BUILTINS at runtime (see _build_bin_ls)
# /root, /var, /var/log — real LittleFS dirs, created at boot

_BIN_ENTRIES   = []   # populated after BUILTINS is defined
_USRBIN_ENTRIES = []

def _build_bin_ls():
    """Call once after BUILTINS is defined to populate /bin and /usr/bin."""
    _BIN_ENTRIES.clear(); _USRBIN_ENTRIES.clear()
    for name in sorted(BUILTINS.keys()):
        _BIN_ENTRIES.append(name)
        _USRBIN_ENTRIES.append(name)

VIRTUAL_LS = {
    "/proc":      ["cpuinfo","meminfo","uptime","version","mounts","stat","loadavg","self"],
    "/proc/self": ["status","maps","fd"],
    "/dev":       ["null","zero","random","urandom","ttyS0","gpio","adc0"],
    "/etc":       ["passwd","hostname","os-release","motd"],
    "/sys":             ["devices","kernel"],
    "/sys/devices":     ["cpu"],
    "/sys/devices/cpu": ["freq"],
    "/sys/kernel":      ["mm","flash","uptime_ms"],
    "/sys/kernel/mm":   ["free"],
    "/sys/kernel/flash":["size"],
    "/tmp": [],
}

def _vls_get(p):
    """Return virtual ls entries for path, including dynamic /bin and /usr/bin."""
    if p == "/bin":     return _BIN_ENTRIES
    if p == "/usr/bin": return _USRBIN_ENTRIES
    if p == "/usr":     return ["bin"]
    return VIRTUAL_LS.get(p, None)

_cwd_path = ["/"]
def _getcwd():   return _cwd_path[0]
def _setcwd(p):  _cwd_path[0] = p

def _norm(path):
    if not path.startswith("/"):
        path = _getcwd().rstrip("/") + "/" + path
    parts = []
    for p in path.split("/"):
        if p in ("", "."): continue
        elif p == "..":
            if parts: parts.pop()
        else: parts.append(p)
    return "/" + "/".join(parts)

def _is_virtual_dir(p):
    if p in VIRTUAL_DIRS: return True
    if p in ("/bin", "/usr", "/usr/bin"): return True
    return False

def vfs_listdir(path=None):
    p = _norm(path or _getcwd()); entries = []
    # virtual entries (VIRTUAL_LS + dynamic /bin /usr/bin)
    vls = _vls_get(p)
    if vls is not None:
        entries += [(e, "v") for e in vls]
    # real LittleFS entries
    try:
        for e in os.listdir(p if p != "/" else "/"):
            if not any(x[0] == e for x in entries):
                entries.append((e, "r"))
    except: pass
    # at root: inject virtual top-level dirs
    if p == "/":
        for vd in ["proc","dev","sys","etc","tmp","bin","usr"]:
            if not any(x[0] == vd for x in entries):
                entries.append((vd, "v"))
        # real dirs that may or may not exist on LittleFS
        for rd in ["root","var"]:
            if not any(x[0] == rd for x in entries):
                try: os.stat("/"+rd); entries.append((rd, "r"))
                except: pass
    return entries

def vfs_read(path):
    p = _norm(path)
    if p in VIRTUAL_FILES: return VIRTUAL_FILES[p]()
    # /bin/<cmd> and /usr/bin/<cmd> — virtual executable stubs
    for prefix in ("/bin/", "/usr/bin/"):
        if p.startswith(prefix):
            name = p[len(prefix):]
            if name in BUILTINS:
                return "#!/bin/ksh\n# %s: shell builtin\n# KernelOS kshd\n" % name
            raise OSError("No such file: " + p)
    with open(p, "r") as f: return f.read()

def vfs_write(path, content, append=False):
    p = _norm(path)
    if p in VIRTUAL_FILES or _is_virtual_dir(p):
        raise OSError("Read-only: " + p)
    if p.startswith("/bin/") or p.startswith("/usr/bin/"):
        raise OSError("Read-only filesystem: " + p)
    with open(p, "a" if append else "w") as f: f.write(content)

def vfs_rm(path):
    p = _norm(path)
    if p in VIRTUAL_FILES or _is_virtual_dir(p):
        raise OSError("Cannot remove: " + p)
    if p.startswith("/bin/") or p.startswith("/usr/bin/"):
        raise OSError("Read-only filesystem: " + p)
    os.remove(p)

def vfs_mkdir(path):
    p = _norm(path)
    if _is_virtual_dir(p) or p in VIRTUAL_DIRS:
        raise OSError("Virtual path exists: " + p)
    os.mkdir(p)

def vfs_chdir(path):
    p = _norm(path)
    if _is_virtual_dir(p) or p == "/": _setcwd(p); return
    try:
        st = os.stat(p)
        if st[0] & 0x4000: _setcwd(p); os.chdir(p)
        else: raise OSError("Not a directory: " + p)
    except OSError: raise OSError("No such file or directory: " + p)

def vfs_stat(path):
    p = _norm(path)
    if _is_virtual_dir(p) or p == "/": return (True, 0, True)
    if p in VIRTUAL_FILES: return (False, len(VIRTUAL_FILES[p]()), True)
    for prefix in ("/bin/", "/usr/bin/"):
        if p.startswith(prefix):
            name = p[len(prefix):]
            if name in BUILTINS: return (False, 64, True)
            raise OSError("No such file: " + p)
    s = os.stat(p); return ((s[0] & 0x4000) != 0, s[6], False)

# ═══════════════════════════════════════════════════════════════
#  SHELL STATE
# ═══════════════════════════════════════════════════════════════

_history    = []
_env        = {
    "PATH":"/bin:/usr/bin:/sbin", "HOME":"/root", "SHELL":"/bin/ksh",
    "TERM":"vt100", "USER":"root", "LOGNAME":"root", "PWD":"/", "HOSTNAME":"esp32",
}
_aliases    = {
    "ll":"ls -la", "la":"ls -a", "..":"cd ..",
    "mem":"cat /proc/meminfo", "cpu":"cat /proc/cpuinfo",
    "top":"watch ps 2000", "ifconfig":"wifi status",
}
_cron_jobs  = []; _cron_next = [1]
HISTORY_MAX = 100
_login_time = time.ticks_ms()
_pipe_buf   = []   # pipe buffer between commands

# ═══════════════════════════════════════════════════════════════
#  PARSER  —  tokenizer + pipe support
# ═══════════════════════════════════════════════════════════════

def _tokenize(line):
    tokens, buf, in_q, esc = [], "", False, False
    for ch in line:
        if esc: buf += ch; esc = False
        elif ch == "\\": esc = True
        elif ch == '"':  in_q = not in_q
        elif ch == " " and not in_q:
            if buf: tokens.append(buf); buf = ""
        else: buf += ch
    if buf: tokens.append(buf)
    return tokens

def _parse_pipe(line):
    """Split a command line into pipe segments: [(cmd, args), ...]"""
    segments = []
    for seg in line.split("|"):
        seg = seg.strip()
        if not seg: continue
        tokens = _tokenize(seg)
        if not tokens: continue
        if tokens[0] in _aliases:
            tokens = _aliases[tokens[0]].split() + tokens[1:]
        segments.append((tokens[0], tokens[1:]))
    return segments

def _expand(args):
    return [str(_env.get(a[1:], "")) if a.startswith("$") else a for a in args]

# ═══════════════════════════════════════════════════════════════
#  PROMPT
# ═══════════════════════════════════════════════════════════════

def _prompt():
    cwd  = _getcwd(); home = _env.get("HOME", "/root")
    if cwd == home:              cwd = "~"
    elif cwd.startswith(home+"/"): cwd = "~" + cwd[len(home):]
    user = _env.get("USER", "root"); host = _env.get("HOSTNAME", "esp32")
    sym  = "#" if user == "root" else "$"
    _w(C.BGRN + user + "@" + host + C.RST + ":" + C.BCYN + cwd + C.RST + sym + " ")

def _reprint_prompt(): _w("\r"); _prompt()

# ═══════════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════════

def _cmd_ls(args):
    show_all = "-a" in args or "-la" in args or "-al" in args
    long_fmt = "-l" in args or "-la" in args or "-al" in args
    paths    = [a for a in args if not a.startswith("-")]
    path     = paths[0] if paths else _getcwd()
    try: entries = vfs_listdir(path)
    except OSError as e: _wl(_c("ls: cannot access '"+path+"': "+str(e), C.RED)); return
    if not show_all: entries = [(n,t) for n,t in entries if not n.startswith(".")]
    if not entries: return
    if long_fmt:
        _wl("total " + str(len(entries)))
        for name, typ in sorted(entries, key=lambda x: x[0]):
            full = path.rstrip("/") + "/" + name
            try: is_dir, size, is_virt = vfs_stat(full)
            except: is_dir, size, is_virt = False, 0, typ == "v"
            d   = "d" if is_dir else "-"
            per = "rwxr-xr-x" if is_dir else "rw-r--r--"
            col = C.BCYN if is_dir else (C.GRY if is_virt else C.RST)
            _wl(d+per+"  1 root root %8d  Jan  1 00:00  " % size
                + col + name + ("/" if is_dir else "") + C.RST)
    else:
        row = ""
        for name, typ in sorted(entries, key=lambda x: x[0]):
            full = path.rstrip("/") + "/" + name
            try: is_dir = vfs_stat(full)[0]
            except: is_dir = False
            row += (C.BCYN if is_dir else C.RST) + name + ("/" if is_dir else "") + C.RST + "  "
        _wl(row)

def _cmd_cat(args):
    if not args: _wl("cat: missing operand"); return
    for path in args:
        try:
            content = vfs_read(path); _w(content)
            if content and not content.endswith("\n"): _w("\n")
        except OSError as e: _wl(_c("cat: "+path+": "+str(e), C.RED))

def _cmd_echo(args):
    no_nl = args and args[0] == "-n"
    if no_nl: args = args[1:]
    _w(" ".join(_expand(args)))
    if not no_nl: _w("\n")

def _cmd_pwd(args):   _wl(_getcwd())

def _cmd_cd(args):
    path = args[0] if args else _env.get("HOME", "/")
    try: vfs_chdir(path); _env["PWD"] = _getcwd()
    except OSError as e: _wl(_c("cd: "+str(e), C.RED))

def _cmd_mkdir(args):
    if not args: _wl("mkdir: missing operand"); return
    for d in args:
        try: vfs_mkdir(d)
        except OSError as e: _wl(_c("mkdir: "+d+": "+str(e), C.RED))

def _cmd_rm(args):
    paths = [a for a in args if not a.startswith("-")]
    if not paths: _wl("rm: missing operand"); return
    for p in paths:
        try: vfs_rm(p)
        except OSError as e: _wl(_c("rm: cannot remove '"+p+"': "+str(e), C.RED))

def _cmd_touch(args):
    if not args: _wl("touch: missing file operand"); return
    for p in args:
        try: vfs_stat(p)
        except:
            try: vfs_write(p, "")
            except OSError as e: _wl(_c("touch: "+p+": "+str(e), C.RED))

def _cmd_write(args):
    if len(args) < 2: _wl("usage: write <file> <text...>"); return
    try: vfs_write(args[0], " ".join(args[1:]) + "\n")
    except OSError as e: _wl(_c("write: "+str(e), C.RED))

def _cmd_append(args):
    if len(args) < 2: _wl("usage: append <file> <text...>"); return
    try: vfs_write(args[0], " ".join(args[1:]) + "\n", append=True)
    except OSError as e: _wl(_c("append: "+str(e), C.RED))

def _cmd_head(args):
    n = 10; paths = [a for a in args if not a.startswith("-")]
    for a in args:
        if a.startswith("-"):
            try: n = int(a[1:])
            except: pass
    if not paths: _wl("head: missing operand"); return
    try:
        for l in vfs_read(paths[0]).split("\n")[:n]: _wl(l)
    except OSError as e: _wl(_c("head: "+str(e), C.RED))

def _cmd_tail(args):
    n = 10; paths = [a for a in args if not a.startswith("-")]
    for a in args:
        if a.startswith("-"):
            try: n = int(a[1:])
            except: pass
    if not paths: _wl("tail: missing operand"); return
    try:
        for l in vfs_read(paths[0]).split("\n")[-n:]: _wl(l)
    except OSError as e: _wl(_c("tail: "+str(e), C.RED))

def _cmd_wc(args):
    if not args: _wl("wc: missing operand"); return
    for path in args:
        try:
            c = vfs_read(path)
            _wl("%8d %8d %8d %s" % (c.count("\n"), len(c.split()), len(c), path))
        except OSError as e: _wl(_c("wc: "+str(e), C.RED))

def _cmd_grep(args):
    if not args: _wl("usage: grep <pattern> [file...]"); return
    pat = args[0]; files = args[1:] if len(args) > 1 else []
    if not files and _pipe_buf:
        for line in _pipe_buf:
            if pat in line: _wl(line)
        return
    if not files: _wl("grep: no input"); return
    for path in files:
        try:
            for line in vfs_read(path).split("\n"):
                if pat in line:
                    _wl((path+": " if len(files)>1 else "") + line)
        except OSError as e: _wl(_c("grep: "+str(e), C.RED))

def _cmd_tee(args):
    if not args: _wl("usage: tee <file>"); return
    lines = list(_pipe_buf)
    try:
        with open(_norm(args[0]), "w") as f:
            for line in lines: f.write(line+"\n"); _wl(line)
        _wl(_c("tee: wrote %d lines to %s" % (len(lines), args[0]), C.GRN))
    except OSError as e: _wl(_c("tee: "+str(e), C.RED))

def _cmd_ps(args):
    _wl(C.BOLD + "  PID   PPID  STAT     VSZ      TIME  COMMAND" + C.RST)
    now = time.ticks_ms()
    for p in SCHED.processes():
        ms = time.ticks_diff(now, _boot_ms); m, s = divmod(ms//1000, 60)
        col = C.GRN if p.state=="R" else (C.YEL if p.state=="S" else C.GRY)
        _wl("  %5d  %5d   %s%s%s    %5dK  %02d:%02d  %s"
            % (p.pid, p.ppid, col, p.state, C.RST, p.vsz, m, s, p.name))

def _cmd_kill(args):
    if not args: _wl("kill: usage: kill [-9] <pid|name>"); return
    targets = [a for a in args if not a.startswith("-")]
    for t in targets:
        try:   key = int(t)
        except: key = t
        killed = SCHED.kill(key)
        if killed:
            for pid in killed: _wl("[%d]  Killed" % pid)
        else: _wl(_c("kill: ("+t+"): No such process", C.RED))

def _cmd_free(args):
    gc.collect()
    fr  = gc.mem_free();  al  = gc.mem_alloc();  tot = fr + al
    _wl("               total      used      free")
    _wl("RAM:     %8dK %8dK %8dK" % (tot//1024, al//1024, fr//1024))
    try:
        st   = os.statvfs("/")
        blk  = st[0]; ftot = st[2]; ffree = st[3]; fused = ftot - ffree
        _wl("Flash:   %8dK %8dK %8dK" % (blk*ftot//1024, blk*fused//1024, blk*ffree//1024))
    except:
        _wl("Flash:        unknown")
    _wl("Swap:          0K        0K        0K")

def _cmd_uname(args):
    mhz  = freq() // 1_000_000
    plat = _HW["platform"].upper()
    a    = "-a" in args
    if a or "-s" in args: _w("PyUnixOS ")
    if a or "-n" in args: _w(_env["HOSTNAME"] + " ")
    if a or "-r" in args: _w("5.4.0-" + _HW["platform"] + " ")
    if a or "-m" in args: _w("xtensa ")
    if a or "-p" in args: _w("LX6@"+str(mhz)+"MHz ")
    if a or "-i" in args: _w(plat + " ")
    if a or "-o" in args: _w("PyUnixOS ")
    if not args: _w("PyUnixOS")
    _w("\n")

def _cmd_dmesg(args):
    mhz  = freq() // 1_000_000
    uid  = _HW["uid"]
    ms   = time.ticks_diff(time.ticks_ms(), _boot_ms)
    plat = _HW["platform"]
    gc.collect(); fr = gc.mem_free(); al = gc.mem_alloc()
    msgs = [
        (0.000, "Initializing cgroup subsystems"),
        (0.012, "CPU: Xtensa LX6 @ %dMHz (%d cores)" % (mhz, _HW["cores"])),
        (0.034, "Serial: 8250/16550 driver, UART0 @ 115200"),
        (0.051, "Hardware ID: %s  platform: %s" % (uid, plat)),
        (0.120, "Mounting %s root filesystem" % _HW.get("fs_type","littlefs")),
        (0.244, "VFS: Mounted root  total:%dkB  free:%dkB" % (
            _HW.get("flash",0), _HW.get("flash_free",0))),
        (0.310, "RAM: %dkB total  %dkB free  %dkB used" % (
            (fr+al)//1024, fr//1024, al//1024)),
        (0.400, "kshd: shell daemon started  PID:%d" % (Process._next_pid-1)),
        (ms/1000, "uptime: %.3fs  processes:%d" % (ms/1000, len(SCHED.processes()))),
    ]
    if "-c" in args: _wl(_c("dmesg: buffer cleared", C.GRY)); return
    lines = [_c("[%10.6f] " % ts, C.GRY) + msg for ts, msg in msgs]
    pager(lines)

def _cmd_uptime(args):
    ms = time.ticks_diff(time.ticks_ms(), _boot_ms); s = ms // 1000
    m, s = divmod(s, 60); h, m = divmod(m, 60); d, h = divmod(h, 24)
    up = ""
    if d: up += str(d) + (" days, " if d != 1 else " day, ")
    up += str(h)+":"+"%02d"%m if h else str(m)+" min"
    _wl(" up "+up+",  1 user,  load average: 0.00 0.00 0.00")

def _now_str():
    try:
        r = RTC(); dt = r.datetime()
        return "%04d-%02d-%02d %02d:%02d:%02d UTC" % (dt[0],dt[1],dt[2],dt[4],dt[5],dt[6])
    except:
        ms = time.ticks_diff(time.ticks_ms(), _boot_ms) // 1000
        h, r2 = divmod(ms, 3600); m, s = divmod(r2, 60)
        return "1970-01-01 %02d:%02d:%02d UTC (no RTC sync)" % (h, m, s)

def _cmd_date(args):   _wl(_now_str())

def _cmd_df(args):
    _wl("%-20s %8s %8s %8s %5s %s" % ("Filesystem","Size","Used","Avail","Use%","Mounted on"))
    try:
        st = os.statvfs("/"); blk=st[0]; tot=st[2]; free=st[3]; used=tot-free
        pct = 100*used//tot if tot else 0
        _wl("%-20s %7dK %7dK %7dK %4d%% /" % ("littlefs",blk*tot//1024,blk*used//1024,blk*free//1024,pct))
    except: _wl("%-20s %8s %8s %8s %5s /" % ("littlefs","?","?","?","?"))
    _wl("%-20s %8d %8d %8d %4d%% /proc" % ("proc",    0,0,0,0))
    _wl("%-20s %8s %8d %8s %4d%% /dev"  % ("devtmpfs","128K",0,"128K",0))

def _cmd_env_cmd(args):
    if not args:
        for k, v in sorted(_env.items()): _wl(k+"="+v)
    else:
        for a in args:
            if "=" in a: k, v = a.split("=",1); _env[k] = v

def _cmd_export(args):
    for a in args:
        if "=" in a: k, v = a.split("=",1); _env[k] = v

def _cmd_who(args):
    ms = time.ticks_diff(time.ticks_ms(), _login_time) // 1000
    h, r = divmod(ms, 3600); m, s = divmod(r, 60)
    _wl("%-12s %-10s %02d:%02d  (%s)" % (
        _env.get("USER","root"), "ttyS0", h, m, _env.get("HOSTNAME","esp32")))

def _cmd_w(args):
    _wl(" "+_now_str()+"  up 0 min,  1 user,  load average: 0.00 0.00 0.00")
    _wl("%-10s %-8s %-8s %-8s %-8s %s" % ("USER","TTY","FROM","LOGIN@","IDLE","WHAT"))
    _wl("%-10s %-8s %-8s %-8s %-8s %s" % (_env.get("USER","root"),"ttyS0","-","00:00","0:00","ksh"))

def _cmd_last(args):
    uid  = ubinascii.hexlify(unique_id()).decode()[:8]
    user = _env.get("USER", "root")
    _wl("%-10s %-8s %-16s %s" % (user,"ttyS0","esp32-"+uid,"Thu Jan  1 00:00   still logged in"))
    _wl("%-10s %-8s %-16s %s" % (user,"ttyS0","esp32-"+uid,"Wed Dec 31 23:59 - 00:00  (00:01)"))
    _wl(""); _wl("wtmp begins Wed Dec 31 23:59:00 1969")

def _cmd_su(args):
    user = args[0] if args else "root"
    if user == "root":
        _env["USER"]="root"; _env["LOGNAME"]="root"; _env["HOME"]="/root"
        _wl(_c("switched to root", C.GRN))
    else: _wl("su: authentication failure")

def _cmd_wall(args):
    if not args: _wl("usage: wall <message>"); return
    _wl(""); _wl(_c("Broadcast message from root@"+_env.get("HOSTNAME","esp32")+" (ttyS0):", C.BYEL))
    _wl(_c(" ".join(args), C.BYEL)); _wl("")

def _cmd_gpio(args):
    if not args: _wl("usage: gpio <read|write|mode|list> <pin> [value]"); return
    sub = args[0].lower()
    if sub in ("read","get"):
        if len(args) < 2: _wl("gpio read <pin>"); return
        try: _wl(str(Pin(int(args[1]), Pin.IN).value()))
        except Exception as e: _wl(_c(str(e), C.RED))
    elif sub in ("write","set"):
        if len(args) < 3: _wl("gpio write <pin> <0|1>"); return
        try: Pin(int(args[1]), Pin.OUT).value(int(args[2]))
        except Exception as e: _wl(_c(str(e), C.RED))
    elif sub == "mode":
        if len(args) < 3: _wl("gpio mode <pin> <in|out|pu>"); return
        try:
            p = int(args[1])
            if   args[2]=="in":  Pin(p, Pin.IN)
            elif args[2]=="out": Pin(p, Pin.OUT)
            elif args[2]=="pu":  Pin(p, Pin.IN, Pin.PULL_UP)
        except Exception as e: _wl(_c(str(e), C.RED))
    elif sub in ("list","ls"):
        _wl("GPIO  input:  0-39   output: 0-33")
        _wl("ADC   pins:   32-39  (12-bit, 0-3.3V)")
        _wl("PWM   pins:   0-33   (up to 40MHz)")
    else: _wl("gpio: unknown subcommand: "+sub)

def _cmd_adc(args):
    if not args: _wl("usage: adc <pin>  # GPIO 32-39"); return
    try:
        a = ADC(Pin(int(args[0]))); a.atten(ADC.ATTN_11DB)
        raw = a.read(); mv = raw*3300//4095
        _wl("GPIO%s: raw=%d  voltage=~%dmV" % (args[0], raw, mv))
    except Exception as e: _wl(_c(str(e), C.RED))

def _cmd_pwm(args):
    if len(args) < 3: _wl("usage: pwm <pin> <freq_hz> <duty_0-1023>"); return
    try:
        PWM(Pin(int(args[0])), freq=int(args[1]), duty=int(args[2]))
        _wl("PWM GPIO%s: freq=%dHz duty=%d" % (args[0], int(args[1]), int(args[2])))
    except Exception as e: _wl(_c(str(e), C.RED))

def _cmd_temp(args):
    try:
        import esp32
        t = esp32.raw_temperature(); c = (t-32)*5//9
        _wl("CPU temperature: %dF  (%dC)  [internal sensor]" % (t, c))
    except Exception as e: _wl(_c("temp: "+str(e), C.RED))

def _cmd_i2cscan(args):
    try:
        from machine import I2C
        sda = int(args[0]) if len(args)>0 else 21
        scl = int(args[1]) if len(args)>1 else 22
        _wl("Scanning I2C bus  SDA=GPIO%d  SCL=GPIO%d ..." % (sda, scl))
        i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=100000)
        devices = i2c.scan()
        if devices:
            _wl(_c("Found %d device(s):" % len(devices), C.GRN))
            for d in devices: _wl("  0x%02X  (%d)" % (d, d))
        else: _wl(_c("No I2C devices found", C.YEL))
    except Exception as e: _wl(_c("i2cscan: "+str(e), C.RED))

def _cmd_wifi(args):
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        sub  = args[0] if args else "status"
        if sub == "status":
            _wl("wlan0   Link encap:Ethernet")
            if wlan.isconnected():
                cfg = wlan.ifconfig()
                _wl("        inet addr:%s  Mask:%s" % (cfg[0], cfg[2]))
                _wl("        " + _c("UP BROADCAST RUNNING MULTICAST", C.GRN) + "  MTU:1500")
                _wl("        SSID: " + str(wlan.config("essid")))
            else:
                _wl("        " + _c("DOWN", C.YEL) + "  not connected")
        elif sub == "scan":
            _wl("Scanning..."); wlan.active(True)
            _wl("%-32s %-19s %5s  AUTH" % ("SSID","BSSID","RSSI"))
            for n in wlan.scan():
                ssid = n[0].decode("utf-8","ignore") if isinstance(n[0],bytes) else str(n[0])
                bssid = ubinascii.hexlify(n[1], ":").decode()
                _wl("%-32s %-19s %4ddBm  %d" % (ssid[:31], bssid, n[3], n[4]))
        elif sub == "connect":
            if len(args) < 3: _wl("wifi connect <ssid> <password>"); return
            wlan.active(True); wlan.connect(args[1], args[2])
            _wl("Connecting to "+args[1]+" ...")
            for _ in range(20):
                if wlan.isconnected(): break
                time.sleep_ms(500); _w(".")
            _wl("")
            if wlan.isconnected():
                _wl(_c("Connected!  IP: "+wlan.ifconfig()[0], C.GRN))
            else: _wl(_c("Failed to connect", C.RED))
        elif sub == "disconnect": wlan.disconnect(); _wl("Disconnected")
        elif sub in ("down","off"): wlan.active(False); _wl("wlan0: interface down")
        elif sub in ("up","on"):   wlan.active(True);  _wl("wlan0: interface up")
        else: _wl("wifi: use: status | scan | connect <ssid> <pw> | disconnect | up | down")
    except ImportError: _wl(_c("wifi: network module not available", C.RED))
    except Exception as e: _wl(_c("wifi: "+str(e), C.RED))

def _cmd_ntp(args):
    try:
        import ntptime, network
        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            _wl(_c("ntp: not connected — run: wifi connect <ssid> <pw>", C.RED)); return
        _wl("Syncing time with pool.ntp.org ...")
        ntptime.settime()
        _wl(_c("Time synchronized: "+_now_str(), C.GRN))
    except ImportError: _wl(_c("ntp: ntptime module not available", C.RED))
    except Exception as e: _wl(_c("ntp: "+str(e), C.RED))

def _cmd_wget(args):
    """wget <url> [output_file]
    Download a file over HTTP/HTTPS.
    If output_file is omitted, saves to the filename from the URL.
    Use -O - to print to stdout instead of saving.
    """
    if not args: _wl("usage: wget <url> [-O <file|-]"); return
    try:
        import network, usocket
        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            _wl(_c("wget: not connected — run: wifi connect <ssid> <pw>", C.RED)); return
    except: _wl(_c("wget: network not available", C.RED)); return

    # parse args
    url     = args[0]
    outfile = None
    stdout  = False
    i = 1
    while i < len(args):
        if args[i] == "-O" and i+1 < len(args):
            if args[i+1] == "-": stdout = True
            else: outfile = args[i+1]
            i += 2
        else:
            outfile = args[i]; i += 1

    # derive filename from URL if not given
    if not outfile and not stdout:
        outfile = url.split("/")[-1].split("?")[0] or "index.html"

    # parse URL
    try:
        if url.startswith("https://"):
            proto = "https"; url_rest = url[8:]
        elif url.startswith("http://"):
            proto = "http";  url_rest = url[7:]
        else:
            proto = "http";  url_rest = url
        if "/" in url_rest:
            host, path = url_rest.split("/", 1)
            path = "/" + path
        else:
            host = url_rest; path = "/"
        port = 443 if proto == "https" else 80
        if ":" in host:
            host, port = host.split(":", 1); port = int(port)
    except Exception as e:
        _wl(_c("wget: bad URL: "+str(e), C.RED)); return

    _wl("--  "+url)
    _wl("    Connecting to %s:%d ..." % (host, port))

    try:
        import usocket
        addr = usocket.getaddrinfo(host, port)[0][-1]
        sock = usocket.socket()
        sock.connect(addr)
        if proto == "https":
            import ussl
            sock = ussl.wrap_socket(sock, server_hostname=host)
        req = "GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: KernelOS/5.4 wget\r\n\r\n" % (path, host)
        sock.write(req.encode())

        # read response header
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = sock.read(1)
            if not chunk: break
            header += chunk
        header = header.decode("utf-8", "ignore")

        # extract status code
        status = int(header.split(" ")[1]) if " " in header else 0
        if status not in (200, 301, 302):
            _wl(_c("wget: HTTP %d" % status, C.RED))
            sock.close(); return

        # get content-length if present
        size = 0
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try: size = int(line.split(":",1)[1].strip())
                except: pass

        _wl("    Length: %s" % (str(size)+" B" if size else "unknown"))
        if not stdout:
            _wl("    Saving to: %s" % outfile)

        # stream body
        received = 0
        gc.collect()
        if stdout:
            while True:
                chunk = sock.read(512)
                if not chunk: break
                _w(chunk.decode("utf-8","ignore"))
                received += len(chunk)
            _w("\n")
        else:
            with open(_norm(outfile), "wb") as f:
                while True:
                    chunk = sock.read(512)
                    if not chunk: break
                    f.write(chunk)
                    received += len(chunk)
                    if size:
                        pct = 100*received//size
                        _w("\r    [%-20s] %d%% %dB" % ("="*(pct//5), pct, received))
                    else:
                        _w("\r    %d B" % received)
            _w("\n")
            _wl(_c("    '%s' saved [%d B]" % (outfile, received), C.GRN))

        sock.close()
        gc.collect()

    except Exception as e:
        _wl(_c("wget: "+str(e), C.RED))

def _cmd_gc(args):
    before = gc.mem_free()
    gc.collect()
    after  = gc.mem_free()
    freed  = after - before
    _wl("gc: collected %d B  (%d kB free)" % (freed, after//1024))

def _cmd_watch(args):
    if len(args) < 2: _wl("usage: watch <interval_ms> <command...>"); return
    try: iv = int(args[0])
    except: _wl("watch: interval must be an integer (ms)"); return
    cmd_str = " ".join(args[1:])
    def _watch_gen(interval, cmd):
        while True:
            _w("\x1b[2J\x1b[H")
            _wl(_c("Every "+str(interval)+"ms: "+cmd+"  (kill to stop)", C.BOLD))
            _wl("")
            dispatch(cmd)
            yield interval
    p = SCHED.spawn("watch:"+cmd_str, _watch_gen, iv, cmd_str, ppid=1)
    _wl("[%d] watch: %s" % (p.pid, cmd_str))

def _cmd_reboot(args):
    _wl("Broadcast message from root@esp32:")
    _wl("The system is going down for reboot NOW!")
    time.sleep_ms(500); reset()

def _cmd_halt(args):
    _wl("System halted.")
    while True: time.sleep_ms(1000)

def _cmd_cron(args):
    if not args: _wl("usage: cron <add|del|list> ..."); return
    sub = args[0]
    if sub == "add":
        if len(args) < 3: _wl("cron add <interval_ms> <command>"); return
        try: iv = int(args[1])
        except: _wl("cron: interval must be an integer (ms)"); return
        jid = _cron_next[0]; _cron_next[0] += 1
        _cron_jobs.append({"interval_ms":iv, "cmd":" ".join(args[2:]),
                           "last_ms":time.ticks_ms(), "id":jid})
        _wl("cron: job %d added (%dms)" % (jid, iv))
    elif sub in ("del","rm"):
        if len(args) < 2: _wl("cron del <id>"); return
        try:
            jid = int(args[1]); before = len(_cron_jobs)
            _cron_jobs[:] = [j for j in _cron_jobs if j["id"] != jid]
            _wl("removed" if len(_cron_jobs) < before else "cron: id not found")
        except: _wl("cron del: bad id")
    elif sub in ("list","ls"):
        if not _cron_jobs: _wl("# no crontab for root"); return
        for j in _cron_jobs:
            _wl("*/%ds  %s  # id=%d" % (j["interval_ms"]//1000, j["cmd"], j["id"]))
    else: _wl("cron: unknown subcommand: "+sub)

def _cmd_crontab(args):
    if "-r" in args: _cron_jobs.clear(); _wl("crontab: removed"); return
    _cmd_cron(["list"])

def _cmd_history(args):
    n = 10
    if args:
        try: n = int(args[0])
        except: pass
    start = max(0, len(_history)-n)
    for i, line in enumerate(_history[start:], start=start+1):
        _wl("  %4d  %s" % (i, line))

def _cmd_alias(args):
    if not args:
        for k, v in sorted(_aliases.items()): _wl("alias "+k+"='"+v+"'")
        return
    line = " ".join(args)
    if "=" in line:
        k, v = line.split("=",1)
        _aliases[k.strip()] = v.strip().strip("'\"")
    elif args[0] in _aliases: _wl("alias "+args[0]+"='"+_aliases[args[0]]+"'")
    else: _wl("alias: "+args[0]+": not found")

def _cmd_unalias(args):
    for a in args:
        if a in _aliases: del _aliases[a]
        else: _wl("unalias: "+a+": not found")

def _cmd_which(args):
    for cmd in args:
        if cmd in BUILTINS: _wl("/bin/" + cmd)
        else: _wl(_c(cmd+": not found", C.RED))

def _cmd_spawn(args):
    if not args: _wl("spawn: usage: spawn <name> [ticks=10] [interval_ms=500]"); return
    name  = args[0]
    ticks = int(args[1]) if len(args)>1 else 10
    iv    = int(args[2]) if len(args)>2 else 500
    def _demo(n, t, d):
        for i in range(t):
            _w("\r\n["+n+":"+str(i+1)+"/"+str(t)+"] tick")
            _reprint_prompt(); yield d
        _w("\r\n["+n+"] exited\r\n"); _reprint_prompt()
    p = SCHED.spawn(name, _demo, name, ticks, iv, ppid=1)
    _wl("[%d] %s" % (p.pid, name))

def _cmd_lsmod(args):
    _wl("Module                  Size  Used by")
    # probe which hardware modules are actually accessible
    mods = []
    try:    Pin(0, Pin.IN);  mods.append(("esp32_gpio", 4096, 0))
    except: pass
    try:    ADC(Pin(36));    mods.append(("esp32_adc",  2048, 0))
    except: pass
    try:    PWM(Pin(0));     mods.append(("esp32_pwm",  2048, 0))
    except: pass
    try:
        from machine import SPI
        SPI(1);              mods.append(("esp32_spi",  3072, 0))
    except: pass
    try:
        from machine import I2C
        I2C(0);              mods.append(("esp32_i2c",  2560, 0))
    except: pass
    try:
        import esp32
        esp32.raw_temperature(); mods.append(("esp32_temp", 512, 0))
    except: pass
    try:
        import network
        network.WLAN(network.STA_IF); mods.append(("esp_wifi", 32768, 0))
    except: pass
    # littlefs — always present if we're running
    mods.append(("littlefs", 8192, 1))
    for name, size, used in mods:
        _wl("%-24s%6d  %d" % (name, size, used))

def _cmd_lspci(args):
    mhz = freq() // 1_000_000
    uid = _HW["uid"]
    _wl("00:00.0 SoC: %s rev 1  [uid:%s]" % (_HW["platform"].upper(), uid[:8]))
    _wl("00:01.0 Serial controller: UART0 @ 115200")
    try:
        import network
        _wl("00:02.0 Network controller: WiFi/BT (STA+AP)")
    except:
        _wl("00:02.0 Network controller: WiFi/BT [unavailable]")
    try:
        flash_kb = _HW.get("flash_sz", 0)
        _wl("00:03.0 Flash controller: SPI Flash %dkB" % flash_kb)
    except:
        _wl("00:03.0 Flash controller: SPI Flash")
    try:
        ADC(Pin(36))
        _wl("00:04.0 ADC controller: SAR-ADC 12-bit (GPIO32-39)")
    except:
        _wl("00:04.0 ADC controller: [probe failed]")
    try:
        PWM(Pin(0))
        _wl("00:05.0 PWM controller: LEDC (GPIO0-33)")
    except:
        _wl("00:05.0 PWM controller: [probe failed]")

def _cmd_lsblk(args):
    _wl("NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT")
    try:
        st  = os.statvfs("/")
        sz  = st[0] * st[2] // 1024
        _wl("mmcblk0       179:0  0  %dK  0 disk" % sz)
        _wl("mmcblk0p1     179:1  0  %dK  0 part /" % sz)
    except:
        _wl("mmcblk0       179:0  0    ?K  0 disk")
        _wl("mmcblk0p1     179:1  0    ?K  0 part /")
    # check for SD card
    try:
        st2 = os.statvfs("/sd")
        sz2 = st2[0] * st2[2] // 1024
        _wl("sd0             8:0  1  %dK  0 disk /sd" % sz2)
    except: pass

def _cmd_modprobe(args):
    mod = args[0] if args else "?"
    _wl("modprobe: WARNING: Module "+mod+" not found in /lib/modules/5.4.0-esp32")

def _cmd_less(args):
    if args:
        try: lines = vfs_read(args[0]).split("\n")
        except OSError as e: _wl(_c("less: "+str(e), C.RED)); return
    else:
        if not _scrollback: _wl(_c("less: scrollback is empty", C.GRY)); return
        lines = list(_scrollback)
    pager(lines)

def _cmd_scroll(args):
    n = int(args[0]) if args else 40
    for line in _scrollback[-n:]: _wl(line)

def _cmd_help(args):
    _wl(_c("PyUnixOS ksh — built-in commands", C.BOLD)); _wl("")
    groups = [
        ("Filesystem",   ["ls","cat","pwd","cd","mkdir","rm","touch","write","append","df","head","tail","wc"]),
        ("Text tools",   ["grep","tee","less","more","scroll"]),
        ("Process",      ["ps","kill","spawn","watch"]),
        ("System",       ["uname","uptime","date","dmesg","free","temp","hwinfo","refresh-hw","neofetch","reboot","halt"]),
        ("Editor",       ["vi"]),
        ("Users",        ["who","w","last","su","wall"]),
        ("Hardware",     ["gpio","adc","pwm","i2cscan"]),
        ("Network",      ["wifi","ntp","wget"]),
        ("Scheduler",    ["cron","crontab"]),
        ("Modules",      ["lsmod","lspci","lsblk","modprobe"]),
        ("Shell",        ["echo","env","export","alias","unalias","history","which","gc","help","clear"]),
    ]
    for group, cmds in groups:
        _wl("  " + _c(group, C.YEL))
        _wl("    " + "  ".join(_c(c, C.GRN) for c in cmds)); _wl("")
    _wl("  " + _dim("Pipe:    cat /proc/cpuinfo | grep MHz | less"))
    _wl("  " + _dim("History: up/down arrows, !<n>"))
    _wl("  " + _dim("Tab:     command completion"))
    _wl("  " + _dim("VFS:     /proc  /dev  /sys  /etc  /tmp"))

def _cmd_neofetch(args):
    gc.collect()
    mhz  = freq() // 1_000_000
    fr   = gc.mem_free(); al = gc.mem_alloc(); tot = fr + al
    uid  = _HW["uid"][:8]
    plat = _HW["platform"].upper()
    ms   = time.ticks_diff(time.ticks_ms(), _boot_ms)
    h, r = divmod(ms//1000, 3600); m, s = divmod(r, 60)
    up   = "%dh %dm %ds" % (h, m, s) if h else "%dm %ds" % (m, s)
    try:
        st = os.statvfs("/")
        disk = "%dkB / %dkB" % ((st[0]*(st[2]-st[3]))//1024, st[0]*st[2]//1024)
    except: disk = "unknown"
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        net = wlan.ifconfig()[0] if wlan.isconnected() else "disconnected"
    except: net = "no driver"
    try:
        import esp32
        t = esp32.raw_temperature(); tc = (t-32)*5//9
        temp = "%dC" % tc
    except: temp = "n/a"
    logo = [
        "   ______  _____ ____  ___  ___",
        "  / __/ / / /   /_  / / _ \\\\/ _ \\\\",
        " / _// /_/ / /| |/ /_/ // // // /",
        "/___/\\\\____/_/ |_/___/\\\\___/\\\\___/ ",
        "                                  ",
    ]
    info = [
        (_c("root", C.BGRN) + "@" + _c("esp32", C.BGRN)),
        "-" * 16,
        (_c("OS", C.CYN) + ": KernelOS 5.4.0-" + plat.lower()),
        (_c("Host", C.CYN) + ": " + plat + "  uid:" + uid),
        (_c("Kernel", C.CYN) + ": 5.4.0-esp32 MicroPython"),
        (_c("Uptime", C.CYN) + ": " + up),
        (_c("Shell", C.CYN) + ": ksh"),
        (_c("CPU", C.CYN) + ": Xtensa LX6 @ %dMHz x%d" % (mhz, _HW["cores"])),
        (_c("Memory", C.CYN) + ": %dkB / %dkB" % (al//1024, tot//1024)),
        (_c("Disk", C.CYN) + ": " + disk),
        (_c("Temp", C.CYN) + ": " + temp),
        (_c("Network", C.CYN) + ": " + net),
        "",
        "\x1b[40m   \x1b[41m   \x1b[42m   \x1b[43m   \x1b[44m   \x1b[45m   \x1b[46m   \x1b[47m   \x1b[0m",
    ]
    rows = max(len(logo), len(info))
    for i in range(rows):
        l = logo[i] if i < len(logo) else " " * 34
        r = info[i] if i < len(info) else ""
        sys.stdout.write("  \x1b[36m" + l + "\x1b[0m  " + r + "\n")
    _scrollback.append("")

def _cmd_vi(args):
    if not args: _wl("usage: vi <file>"); return
    filename = _norm(args[0])

    # load existing file
    lines = []
    try:
        content = vfs_read(filename)
        lines   = content.split("\n")
        if lines and lines[-1] == "": lines.pop()
    except: pass

    # show existing content with line numbers
    _w("\x1b[2J\x1b[H")
    if lines:
        for i, l in enumerate(lines): _wl(_dim("%3d " % (i+1)) + l)
    else:
        _wl(_dim('"'+filename+'" [New File]'))
    _wl(_dim("-- INSERT --  type lines, :wq save+quit, :q quit, :w save"))
    _wl("")

    # collect new lines interactively
    buf = ""
    while True:
        _w("")
        ch = _read_blocking()

        if ch in ("\r", "\n"):
            line = buf; buf = ""
            _w("\n")
            # check for commands
            if line == ":wq":
                try:
                    with open(filename, "w") as f:
                        f.write("\n".join(lines) + "\n")
                    _wl(_c('"'+filename+'" written, %d lines' % len(lines), C.GRN))
                except Exception as e:
                    _wl(_c("write error: "+str(e), C.RED))
                return
            elif line == ":q":
                return
            elif line == ":w":
                try:
                    with open(filename, "w") as f:
                        f.write("\n".join(lines) + "\n")
                    _wl(_c('"'+filename+'" written', C.GRN))
                except Exception as e:
                    _wl(_c("write error: "+str(e), C.RED))
            elif line.startswith(":d "):
                # :d N  — delete line N
                try:
                    n = int(line[3:])-1
                    if 0 <= n < len(lines):
                        removed = lines.pop(n)
                        _wl(_dim("deleted: "+removed))
                    else:
                        _wl(_c("no such line", C.RED))
                except: _wl(_c(":d <N>", C.RED))
            elif line.startswith(":p"):
                # :p  — print all lines with numbers
                for i, l in enumerate(lines):
                    _wl(_dim("%3d " % (i+1)) + l)
            elif line == ":help":
                _wl(_dim("  :wq   save and quit"))
                _wl(_dim("  :q    quit without saving"))
                _wl(_dim("  :w    save"))
                _wl(_dim("  :p    print file"))
                _wl(_dim("  :d N  delete line N"))
            else:
                lines.append(line)

        elif ch in ("\x7f", "\x08"):
            if buf:
                buf = buf[:-1]; _w("\x08 \x08")

        elif ch == "\x03":  # Ctrl+C
            _w("^C\n")
            return

        elif ch >= " ":
            buf += ch; _w(ch)

def _cmd_hwinfo(args):
    """Show real hardware info as queried at boot."""
    _refresh_hw()
    mhz = freq() // 1_000_000
    gc.collect()
    _wl(_c("Hardware information", C.BOLD))
    _wl("  Platform   : " + _HW["platform"])
    _wl("  CPU        : Xtensa LX6 @ %dMHz  (%d cores)" % (mhz, _HW["cores"]))
    _wl("  UID        : " + _HW["uid"])
    _wl("  MicroPython: " + _HW["mpy_ver"])
    _wl("  RAM total  : %dkB" % ((gc.mem_free()+gc.mem_alloc())//1024))
    _wl("  RAM free   : %dkB" % (gc.mem_free()//1024))
    _wl("  Flash total: %dkB" % _HW.get("flash",0))
    _wl("  Flash free : %dkB" % _HW.get("flash_free",0))
    _wl("  FS type    : " + _HW.get("fs_type","unknown"))
    try:
        import esp32
        t = esp32.raw_temperature(); c = (t-32)*5//9
        _wl("  CPU temp   : %dF / %dC" % (t, c))
    except: pass
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        _wl("  WiFi       : %s  connected=%s" % (
            "UP" if wlan.active() else "DOWN", wlan.isconnected()))
        if wlan.isconnected():
            _wl("  IP         : " + wlan.ifconfig()[0])
    except: pass

def _cmd_refresh_hw(args):
    _refresh_hw()
    _wl(_c("Hardware info refreshed.", C.GRN))
    _cmd_hwinfo([])

def _cmd_clear(args): _w("\x1b[2J\x1b[H")

# Special exception — signals the main loop to drop into MicroPython REPL
class _DebugExit(Exception): pass

def _cmd_exit_debug(args):
    _wl(_c("Dropping into MicroPython REPL...", C.YEL))
    _wl(_c("To return to PyUnixOS run:  import main", C.GRY))
    _wl("")
    raise _DebugExit()

# ═══════════════════════════════════════════════════════════════
#  DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════

BUILTINS = {
    "ls":_cmd_ls, "cat":_cmd_cat, "echo":_cmd_echo, "pwd":_cmd_pwd,
    "cd":_cmd_cd, "mkdir":_cmd_mkdir, "rm":_cmd_rm, "touch":_cmd_touch,
    "write":_cmd_write, "append":_cmd_append, "head":_cmd_head, "tail":_cmd_tail,
    "wc":_cmd_wc, "grep":_cmd_grep, "tee":_cmd_tee,
    "ps":_cmd_ps, "kill":_cmd_kill, "spawn":_cmd_spawn, "watch":_cmd_watch,
    "free":_cmd_free, "uname":_cmd_uname, "dmesg":_cmd_dmesg,
    "uptime":_cmd_uptime, "date":_cmd_date, "df":_cmd_df, "temp":_cmd_temp,
    "env":_cmd_env_cmd, "export":_cmd_export,
    "who":_cmd_who, "w":_cmd_w, "last":_cmd_last, "su":_cmd_su, "wall":_cmd_wall,
    "gpio":_cmd_gpio, "adc":_cmd_adc, "pwm":_cmd_pwm, "i2cscan":_cmd_i2cscan,
    "wifi":_cmd_wifi, "ntp":_cmd_ntp, "wget":_cmd_wget, "gc":_cmd_gc,
    "reboot":_cmd_reboot, "halt":_cmd_halt, "shutdown":_cmd_reboot,
    "cron":_cmd_cron, "crontab":_cmd_crontab,
    "history":_cmd_history, "alias":_cmd_alias, "unalias":_cmd_unalias,
    "which":_cmd_which, "help":_cmd_help, "clear":_cmd_clear,
    "lsmod":_cmd_lsmod, "lspci":_cmd_lspci, "lsblk":_cmd_lsblk, "modprobe":_cmd_modprobe,
    "less":_cmd_less, "more":_cmd_less, "scroll":_cmd_scroll,
    "dir":_cmd_ls, "type":_cmd_which, "ifconfig":_cmd_wifi,
    "hwinfo":_cmd_hwinfo, "refresh-hw":_cmd_refresh_hw,
    "neofetch":_cmd_neofetch,
    "vi":_cmd_vi,
    "exit-debug":_cmd_exit_debug,
}

def dispatch(line):
    line = line.strip()
    if not line or line.startswith("#"): return

    # !<n>  — execute command from history
    if line.startswith("!"):
        try:
            n = int(line[1:]) - 1
            if 0 <= n < len(_history): line = _history[n]
            else: _wl(_c("!"+line[1:]+": event not found", C.RED)); return
        except: _wl(_c("!: bad history reference", C.RED)); return

    segments = _parse_pipe(line)
    if not segments: return

    if len(segments) == 1:
        cmd, args = segments[0]; args = _expand(args)
        if cmd in BUILTINS:
            try: BUILTINS[cmd](args)
            except KeyboardInterrupt: _wl("")
            except Exception as e: _wl(_c("ksh: "+cmd+": "+str(e), C.BRED))
        else:
            _wl(_c("ksh: "+cmd+": command not found", C.RED))
    else:
        # pipe execution: collect output of each stage, feed into next
        global _pipe_buf
        first_cmd, first_args = segments[0]; first_args = _expand(first_args)
        if first_cmd in BUILTINS:
            buf = collect(lambda: BUILTINS[first_cmd](first_args))
        else:
            _wl(_c("ksh: "+first_cmd+": command not found", C.RED)); return
        for cmd, args in segments[1:]:
            args = _expand(args); _pipe_buf = buf
            if cmd in BUILTINS:
                try:   buf = collect(lambda: BUILTINS[cmd](args))
                except Exception as e: _wl(_c("ksh: "+cmd+": "+str(e), C.BRED)); break
            else:
                _wl(_c("ksh: "+cmd+": command not found", C.RED)); break
        _pipe_buf = []

# ═══════════════════════════════════════════════════════════════
#  NON-BLOCKING STDIN READ
# ═══════════════════════════════════════════════════════════════

try:
    import select
    def _read_char():
        r, _, _ = select.select([sys.stdin], [], [], 0)
        return sys.stdin.read(1) if r else None
except ImportError:
    def _read_char():
        try:    return sys.stdin.read(1)
        except: return None

# ═══════════════════════════════════════════════════════════════
#  PROCESS: REPL  —  with arrow-key history and tab completion
# ═══════════════════════════════════════════════════════════════

def proc_repl():
    _prompt()
    buf = ""; hist_idx = [len(_history)]

    while True:
        try: ch = _read_char()
        except KeyboardInterrupt:
            buf = ""; _w("^C\n"); _prompt(); yield 0; continue

        if ch is None: yield 0; continue

        if ch == "\x1b":
            # escape sequence — read rest non-blocking
            ch2 = _read_char()
            if ch2 == "[":
                ch3 = _read_char()
                if ch3 == "A":   # up arrow — history back
                    if hist_idx[0] > 0:
                        hist_idx[0] -= 1
                        _w("\r" + " "*(len(buf)+30) + "\r"); _prompt()
                        buf = _history[hist_idx[0]] if hist_idx[0] < len(_history) else ""
                        _w(buf)
                elif ch3 == "B": # down arrow — history forward
                    if hist_idx[0] < len(_history):
                        hist_idx[0] += 1
                        _w("\r" + " "*(len(buf)+30) + "\r"); _prompt()
                        buf = _history[hist_idx[0]] if hist_idx[0] < len(_history) else ""
                        _w(buf)
            yield 0; continue

        if ch in ("\r", "\n"):
            _w("\n"); line = buf.strip(); buf = ""
            hist_idx[0] = len(_history) + 1
            if line:
                if len(_history) >= HISTORY_MAX: _history.pop(0)
                _history.append(line)
                hist_idx[0] = len(_history)
                dispatch(line)
            _prompt()

        elif ch in ("\x7f", "\x08"):
            if buf: buf = buf[:-1]; _w("\x08 \x08")

        elif ch == "\x09":  # Tab — command completion
            matches = [k for k in BUILTINS if k.startswith(buf)]
            if len(matches) == 1:
                rest = matches[0][len(buf):]
                buf  = matches[0] + " "; _w(rest + " ")
            elif len(matches) > 1:
                _w("\n" + "  ".join(sorted(matches)) + "\n")
                _prompt(); _w(buf)

        elif ch == "\x03":
            buf = ""; _w("^C\n"); _prompt(); hist_idx[0] = len(_history)

        elif ch == "\x04":
            _wl("\nlogout"); return

        elif ch >= " ":
            buf += ch; _w(ch)

        yield 0

# ═══════════════════════════════════════════════════════════════
#  PROCESS: CRON DAEMON
# ═══════════════════════════════════════════════════════════════

def proc_cron():
    while True:
        now = time.ticks_ms()
        for j in _cron_jobs:
            if time.ticks_diff(now, j["last_ms"]) >= j["interval_ms"]:
                j["last_ms"] = now
                _w("\r\n[cron:%d] %s\r\n" % (j["id"], j["cmd"]))
                dispatch(j["cmd"]); _reprint_prompt()
        yield 100

# ═══════════════════════════════════════════════════════════════
#  PROCESS: HEARTBEAT LED  (GPIO2 — built-in LED)
# ═══════════════════════════════════════════════════════════════

def proc_heartbeat():
    try:
        led = Pin(2, Pin.OUT)
        while True:
            led.on();  yield 80
            led.off(); yield 920
    except: return

# ═══════════════════════════════════════════════════════════════
#  MAIN  —  boot + kernel panic recovery loop
# ═══════════════════════════════════════════════════════════════

def _syslog(msg):
    """Append a line to /var/log/syslog if it exists."""
    try:
        ms = time.ticks_diff(time.ticks_ms(), _boot_ms)
        with open("/var/log/syslog", "a") as f:
            f.write("[%8d] %s\n" % (ms, msg))
    except: pass

def _fs_init():
    """Create real LittleFS dirs and files that should persist."""
    for d in ["/root", "/var", "/var/log", "/tmp"]:
        try: os.mkdir(d)
        except: pass  # already exists
    # create syslog if missing
    try:
        os.stat("/var/log/syslog")
    except:
        try:
            with open("/var/log/syslog", "w") as f:
                f.write("[       0] KernelOS syslog initialized\n")
        except: pass
    # create /root/.profile if missing
    try:
        os.stat("/root/.profile")
    except:
        try:
            with open("/root/.profile", "w") as f:
                f.write("# KernelOS root profile\nexport PATH=/bin:/usr/bin:/sbin\nexport HOME=/root\n")
        except: pass

# init filesystem + build /bin listing
_fs_init()
_build_bin_ls()

# add /var/log/syslog to virtual ls so it shows up in ls
VIRTUAL_LS["/var"]         = ["log"]
VIRTUAL_LS["/var/log"]     = ["syslog"]
VIRTUAL_LS["/root"]        = [".profile"]

run_boot()
_syslog("boot: KernelOS started  uid:" + _HW["uid"][:8])

while True:
    try:
        SCHED.spawn("kshd",      proc_repl,      ppid=1, priority=1)
        SCHED.spawn("crond",     proc_cron,       ppid=1, priority=0)
        SCHED.spawn("heartbeat", proc_heartbeat,  ppid=1, priority=-1)
        SCHED.run_forever()
    except _DebugExit:
        # clean shutdown — fall through to native MicroPython REPL
        SCHED._procs   = []
        SCHED._pending = []
        break
    except KeyboardInterrupt: _w("\r\n")
    except Exception as e:
        _wl("\r\n" + _c("[kernel panic] " + str(e), C.BRED))
        _wl(_c("Restarting in 2s...", C.YEL))
        _syslog("kernel panic: " + str(e))
        time.sleep(2)
    SCHED._procs   = []
    SCHED._pending = []

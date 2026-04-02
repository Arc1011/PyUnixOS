# Quickstart

## 1. Get MicroPython on your ESP32

If your board is blank or running something else (Arduino, ESP-IDF), flash MicroPython first.

```bash
pip install esptool

# Erase flash
esptool.py --port /dev/ttyUSB0 erase_flash

# Download firmware from https://micropython.org/download/ESP32_GENERIC/
# Then flash it:
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-v1.27.0.bin
```

**Already have MicroPython?** Skip to step 3.  
Check by connecting and looking for `>>>`:
```bash
mpremote connect /dev/ttyUSB0
```

---

## 2. Install tools

```bash
pip install mpremote
```

On Arch Linux:
```bash
sudo pacman -S python-pip
pip install mpremote
```

---

## 3. Get the code

```bash
git clone https://github.com/Arc1011/PyUnixOS
cd PyUnixOS
```

---

## 4. Pre-compile (strongly recommended)

PyUnixOS is a large single file. MicroPython compiles Python to bytecode in RAM at import time — on a stock ESP32 this can trigger a `MemoryError`. Pre-compiling with `mpy-cross` eliminates this.

**Build mpy-cross** (version must match your MicroPython firmware):

```bash
git clone https://github.com/micropython/micropython
git -C micropython checkout v1.27.0
make -C micropython/mpy-cross
```

**Compile:**
```bash
./micropython/mpy-cross/build/mpy-cross main.py
# produces main.mpy
```

---

## 5. Flash PyUnixOS

Remove any old version first, then upload:

```bash
# If upgrading from a previous .py version:
mpremote connect /dev/ttyUSB0 fs rm :main.py

# Upload compiled binary and reboot:
mpremote connect /dev/ttyUSB0 fs cp main.mpy :main.mpy + reset
```

---

## 6. Connect to the terminal

```bash
# Linux / macOS
screen /dev/ttyUSB0 115200
# or
mpremote connect /dev/ttyUSB0

# Windows — use PuTTY
# Serial → COM3 → Speed: 115200 → Open
```

To exit `screen`: **Ctrl+A**, then **K**, then **Y**.

You should see the boot sequence followed by:
```
root@esp32:/# _
```

---

## 7. First steps

```bash
# Show all commands
help

# System info
neofetch
hwinfo

# Explore the virtual filesystem
ls /
cat /proc/cpuinfo
cat /etc/motd
ls /bin

# Hardware
gpio write 2 1      # turn on built-in LED
gpio write 2 0      # turn off
adc 36              # read ADC on GPIO36
temp                # internal temperature

# Connect to WiFi
wifi connect MyNetwork MyPassword
wifi status
ntp                 # sync time

# Download a file
wget http://wttr.in/Warsaw?format=3 -O -

# Edit a file
vi /root/notes.txt
# type freely, Enter for new line
# :wq to save and quit

# Background process
spawn blinker 10 500    # blinks every 500ms, 10 times
ps                      # see it running
kill blinker            # stop it

# Drop to MicroPython REPL for debugging
exit-debug
# to come back:
>>> import main
```

---

## Troubleshooting

**`MemoryError` on boot**  
Pre-compile with `mpy-cross` as described in step 4.

**Nothing shows after connecting**  
The board may have already booted before you connected. Press the **EN** (reset) button on the board, or send a hard reset:
```bash
mpremote connect /dev/ttyUSB0 reset
```

**`Ctrl+C` kills the whole shell**  
This is fixed in KernelOS — `Ctrl+C` sends `^C` to the shell buffer, not the scheduler. If you still see this, make sure you're running the latest version.

**`wifi connect` hangs**  
The connection attempt times out after 10 seconds. Double-check SSID and password. The SSID is case-sensitive. If your SSID contains spaces, wrap it in quotes:
```bash
wifi connect "My Network" password123
```

**`wget` fails on HTTPS**  
Make sure your MicroPython build includes `ussl`. Most generic ESP32 builds do. If not, use HTTP where possible.

**`vi` — how do I quit without saving?**  
Type `:q` and press Enter.

**Port is `/dev/ttyUSB0` on Linux, `COM3` on Windows**  
Check Device Manager on Windows, or `ls /dev/tty*` on Linux after plugging in the board.

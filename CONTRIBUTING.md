# Contributing

Contributions are welcome. PyUnixOS is a single-file project by design — keep that in mind when adding features.

## Ground rules

- **One file.** Everything lives in `main.py`. No external dependencies beyond the MicroPython standard library and `machine`.
- **No `uasyncio`.** The scheduler is generator-based on purpose. New background tasks should be generator functions that `yield N` (sleep N ms) or `yield 0` (busy-yield).
- **No f-strings with quotes inside `{}`** — MicroPython's parser rejects them. Use `%` formatting or concatenation instead.
- **RAM budget.** The ESP32 WROOM has ~320kB heap. Keep new features lean. Avoid allocating large buffers. Run `gc` and `free` to sanity-check after changes.
- **Test on hardware.** The simulator in the README is illustrative. Real testing means flashing to an actual ESP32.

## Adding a command

1. Write a function `_cmd_yourname(args)` — `args` is a list of strings.
2. Add it to the `BUILTINS` dict.
3. Add it to the relevant group in `_cmd_help`.
4. `_build_bin_ls()` will automatically pick it up for `/bin`.

```python
def _cmd_hello(args):
    name = args[0] if args else "world"
    _wl("Hello, " + name + "!")

BUILTINS["hello"] = _cmd_hello
```

## Adding a virtual file

Add an entry to `VIRTUAL_FILES` (a callable that returns a string) and optionally to `VIRTUAL_LS` for the parent directory:

```python
def _my_virtual_file():
    return "some dynamic content\n"

VIRTUAL_FILES["/proc/myfile"] = _my_virtual_file
VIRTUAL_LS["/proc"].append("myfile")
```

## Adding a background process

Write a generator function and spawn it after `_build_bin_ls()` in the boot section:

```python
def proc_myservice():
    while True:
        # do something
        yield 1000   # sleep 1 second

SCHED.spawn("myservice", proc_myservice, ppid=1, priority=0)
```

## Style

- Short lines. This runs on a microcontroller — clarity over cleverness.
- Error messages follow the Unix convention: `command: reason`.
- Use `_wl()` for output (feeds scrollback). Use `_w()` for raw writes (prompt, pager drawing).
- Avoid `print()` — it bypasses the scrollback buffer.

## Pull request checklist

- [ ] Syntax check: `python3 -c "import ast; ast.parse(open('main.py').read())"`
- [ ] No f-strings with quotes inside `{}`: `grep -n "f['\"].*{['\"]" main.py`
- [ ] Tested on real ESP32 hardware (or at minimum via `mpy-cross` compilation check)
- [ ] `mpy-cross main.py` succeeds without errors
- [ ] Help text updated in `_cmd_help`
- [ ] `COMMANDS.md` updated if new commands added

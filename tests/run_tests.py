#!/usr/bin/env python3
"""Check the Wireshark dissectors against the captures in tests/captures.

Each capture is dissected by tshark with the dissectors of this repository and a fresh
configuration. The Info column and expert messages of the Minecraft frames must match
tests/expected/<capture>.txt, and frames with only TCP data must not get Lua errors.

Usage:
  python tests/run_tests.py             # compare with the expected output
  python tests/run_tests.py --update    # write the expected output after a wanted change
  python tests/run_tests.py --tshark /usr/bin/tshark

On Linux and macOS, Wireshark always loads Lua plugins from ~/.local/lib/wireshark/plugins:
the dissectors are copied there only with --install (done in CI), check that it's fine first.
"""

import argparse
import difflib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAPTURES = ROOT / "tests" / "captures"
EXPECTED = ROOT / "tests" / "expected"
MINIMUM_VERSION = (4, 4)


def find_tshark():
    found = shutil.which("tshark")
    if found is not None:
        return found
    for candidate in (r"C:\Program Files\Wireshark\tshark.exe", "/Applications/Wireshark.app/Contents/MacOS/tshark"):
        if pathlib.Path(candidate).exists():
            return candidate
    sys.exit("tshark not found, use --tshark <path>")


def run(tshark, env, *args):
    result = subprocess.run([tshark, *args], capture_output=True, env=env)
    return result.returncode, result.stdout.decode("utf-8", "replace"), result.stderr.decode("utf-8", "replace")


def lua_plugins_folder(tshark, env):
    _, out, _ = run(tshark, env, "-G", "folders")
    for line in out.splitlines():
        name, _, value = line.partition(":")
        if name.strip() == "Personal Lua Plugins":
            return pathlib.Path(value.strip())
    sys.exit("Can't find the personal Lua plugins folder in tshark -G folders")


def install_dissectors(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for script in ("sniffcraft.lua", "minecraft.lua"):
        shutil.copy2(ROOT / "wireshark" / script, folder / script)
    shutil.rmtree(folder / "minecraft_mcdata", ignore_errors=True)
    shutil.copytree(ROOT / "wireshark" / "minecraft_mcdata", folder / "minecraft_mcdata")


def dissect(tshark, env, capture):
    """Info column and expert messages of the Minecraft frames, one line per frame"""
    code, out, err = run(tshark, env, "-r", str(capture), "-Y", "minecraft || sniffcraft", "-T", "fields",
                         "-E", "separator=\t", "-E", "occurrence=a", "-E", "aggregator=|",
                         "-e", "frame.number", "-e", "_ws.col.info", "-e", "_ws.expert.message")
    if code != 0:
        raise RuntimeError(err.strip())
    return [line.rstrip("\r") for line in out.splitlines()]


def lua_errors(tshark, env, capture):
    code, out, err = run(tshark, env, "-r", str(capture), "-Y", "_ws.lua.error", "-T", "fields", "-e", "frame.number",
                         "-e", "_ws.lua.error")
    if code != 0:
        raise RuntimeError(err.strip())
    return [line for line in out.splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tshark", default=None)
    parser.add_argument("--update", action="store_true", help="write the expected output")
    parser.add_argument("--install", action="store_true",
                        help="allow copying the dissectors to the personal Lua plugins folder when it's outside of the test configuration")
    args = parser.parse_args()
    tshark = args.tshark or find_tshark()
    # The Info column has arrows, which Windows consoles may not be able to show
    sys.stdout.reconfigure(errors="replace")

    with tempfile.TemporaryDirectory(prefix="sniffcraft-tests-") as config:
        # Fresh configuration, the user's preferences (ports, protocol...) don't change the result
        env = dict(os.environ, WIRESHARK_CONFIG_DIR=config)
        _, version, _ = run(tshark, env, "--version")
        print(version.splitlines()[0] if version else "unknown tshark")
        numbers = version.split()[2].split(".") if len(version.split()) > 2 else []
        if tuple(int(n) for n in numbers[:2] if n.isdigit()) < MINIMUM_VERSION:
            sys.exit("The dissectors need Wireshark %d.%d or newer" % MINIMUM_VERSION)

        plugins = lua_plugins_folder(tshark, env)
        if pathlib.Path(config) not in plugins.parents and not args.install:
            sys.exit("Wireshark loads Lua plugins from %s, run again with --install to copy the dissectors there" % plugins)
        install_dissectors(plugins)
        _, loaded, _ = run(tshark, env, "-G", "plugins")
        for script in ("sniffcraft.lua", "minecraft.lua"):
            if script not in loaded:
                sys.exit("%s is not loaded by tshark" % script)

        failures = 0
        EXPECTED.mkdir(exist_ok=True)
        for capture in sorted(CAPTURES.glob("*.pcapng")):
            expected_file = EXPECTED / (capture.stem + ".txt")
            try:
                lines = dissect(tshark, env, capture)
                errors = lua_errors(tshark, env, capture)
            except RuntimeError as e:
                print("FAIL %s: tshark error: %s" % (capture.name, e))
                failures += 1
                continue
            if errors:
                print("FAIL %s: Lua errors\n  %s" % (capture.name, "\n  ".join(errors[:10])))
                failures += 1
                continue
            if not lines:
                print("FAIL %s: no Minecraft packet" % capture.name)
                failures += 1
                continue
            if args.update:
                expected_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
                print("updated %s (%d frames)" % (expected_file.name, len(lines)))
                continue
            if not expected_file.exists():
                print("FAIL %s: no expected output, run with --update" % capture.name)
                failures += 1
                continue
            expected = expected_file.read_text(encoding="utf-8").splitlines()
            if lines != expected:
                print("FAIL %s:" % capture.name)
                diff = list(difflib.unified_diff(expected, lines, "expected", "actual", lineterm="", n=0))
                print("\n".join(diff[:40]) + ("\n  ..." if len(diff) > 40 else ""))
                failures += 1
            else:
                print("ok   %s (%d frames)" % (capture.name, len(lines)))

    if failures:
        sys.exit("%d capture(s) failed" % failures)


if __name__ == "__main__":
    main()

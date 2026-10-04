#!/bin/sh
# Install SniffCraft as a Wireshark capture interface (extcap), the Minecraft dissectors and the
# Minecraft configuration profile, for the current user (Linux and macOS).
#
# Usage: ./install.sh [--exe <sniffcraft>] [--versions <dir>] [--lib-dir <dir>] [--config-dir <dir>]
#   --exe         sniffcraft executable, defaults to sniffcraft next to this script or in ../bin
#   --versions    folder with the builds for other Minecraft versions (sniffcraft-<version>),
#                 defaults to sniffcraft_versions next to this script or ../dist/sniffcraft_versions
#   --lib-dir     personal Wireshark plugins and extcap parent folder, defaults to ~/.local/lib/wireshark
#   --config-dir  personal Wireshark configuration folder, defaults to ~/.config/wireshark
#
# The folders Wireshark uses are listed in Help > About Wireshark > Folders, the Flatpak version
# for example uses ~/.var/app/org.wireshark.Wireshark instead.

set -e

here=$(cd "$(dirname "$0")" && pwd)
exe=""
versions=""
lib_dir="$HOME/.local/lib/wireshark"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/wireshark"

while [ $# -gt 0 ]; do
    case "$1" in
        --exe) exe="$2"; shift 2 ;;
        --versions) versions="$2"; shift 2 ;;
        --lib-dir) lib_dir="$2"; shift 2 ;;
        --config-dir) config_dir="$2"; shift 2 ;;
        -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$exe" ]; then
    for candidate in "$here/sniffcraft" "$here/../bin/sniffcraft"; do
        if [ -f "$candidate" ]; then exe="$candidate"; break; fi
    done
fi
if [ -z "$versions" ]; then
    for candidate in "$here/sniffcraft_versions" "$here/../dist/sniffcraft_versions"; do
        if [ -d "$candidate" ]; then versions="$candidate"; break; fi
    done
fi

extcap_dir="$lib_dir/extcap"
plugins_dir="$lib_dir/plugins"
mkdir -p "$extcap_dir" "$plugins_dir"

if [ -n "$exe" ] && [ -f "$exe" ]; then
    cp "$exe" "$extcap_dir/sniffcraft"
    chmod +x "$extcap_dir/sniffcraft"
    echo "Capture interface: $extcap_dir/sniffcraft"
else
    echo "Warning: sniffcraft not found, only the dissectors are installed (use --exe <path>)" >&2
fi

if [ -n "$versions" ] && [ -d "$versions" ]; then
    # Replaced as a whole so removed versions don't stay in the version list
    rm -rf "$extcap_dir/sniffcraft_versions"
    mkdir -p "$extcap_dir/sniffcraft_versions"
    count=0
    for build in "$versions"/sniffcraft-*; do
        [ -f "$build" ] || continue
        cp "$build" "$extcap_dir/sniffcraft_versions/"
        chmod +x "$extcap_dir/sniffcraft_versions/$(basename "$build")"
        count=$((count + 1))
    done
    echo "Other Minecraft versions: $count builds in $extcap_dir/sniffcraft_versions"
fi

for script in sniffcraft.lua minecraft.lua; do
    cp "$here/$script" "$plugins_dir/"
    echo "Dissector: $plugins_dir/$script"
done

if [ -d "$here/minecraft_mcdata" ]; then
    rm -rf "$plugins_dir/minecraft_mcdata"
    cp -R "$here/minecraft_mcdata" "$plugins_dir/"
    echo "Protocol definitions: $plugins_dir/minecraft_mcdata"
fi

if [ -d "$here/profiles/Minecraft" ]; then
    target="$config_dir/profiles/Minecraft"
    mkdir -p "$target"
    for file in "$here/profiles/Minecraft"/*; do
        name=$(basename "$file")
        # Wireshark saves the capture options (server address...) in the profile preferences, keep them
        if [ "$name" = "preferences" ] && [ -f "$target/$name" ]; then
            continue
        fi
        cp "$file" "$target/$name"
    done
    echo "Minecraft profile: $target (Edit > Configuration Profiles)"
fi

echo "Done, restart Wireshark to load the changes."

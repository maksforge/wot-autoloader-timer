# Autoloader Shell Timer

A World of Tanks mod that shows the load time of **every shell** in an autoreloader magazine (Italian tanks and any other gun with the `autoreload` mechanic), not just the one that's loading now.

```
1/4   4.5   16.2   26.7   35.5
```

- **1/4**: shells in the magazine now.
- **Each number**: seconds until that shell is ready, counted from now. The amber one is loading now.
- When the magazine is full it shows **3/3** in green, then each shell's own load time at your current reload speed in grey, fastest first, for example `3/3   10.8   11.7   13.5`.

The times always use your current reload speed. They're recalculated every 0.1 s from the reload time the server sends for the shell being loaded, so a damaged ammo rack, stun, or a crew member knocked out changes them right away. The rest of the magazine is predicted from the gun's per-shell reload table at that same speed.

## Reload quick command

When you use the game's reload quick command in an autoreloader, the game still sends its usual line, for example "Ready to fire! Shells in the magazine: 1 item(s).". The mod then adds one team chat line with the magazine status:

```
Magazine 1/4, full in 35 s
Magazine 0/4, first shell 9 s, full in 35 s
```

Nothing is added when the magazine is already full. Turn it off with `reloadChatLine`.

## Install

1. Install [GUIFlash](https://github.com/CH4MPi/GUIFlash) (`gambiter.guiflash_*.wotmod`). Most modpacks include it.
2. Copy `maksforge.autoloader_timer_<version>.wotmod` into `World_of_Tanks/mods/<game version>/`.

## Settings

The first battle writes `mods/configs/autoloader_timer/config.json`:

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Turns the mod off without uninstalling it |
| `x`, `y` | `0`, `60` | Offset from the crosshair, which the line follows across arcade, sniper and arty views |
| `fontSize` | `14` | Text size |
| `hideWhenFull` | `false` | Hide the panel while the magazine is full |
| `reloadChatLine` | `true` | Add the magazine status line to the reload quick command |
| `colors` | | Hex colours for the count, a full magazine, the loading shell, the queued shells and the per-shell times |

To move the panel, hold Ctrl to show the cursor and drag it. The new position is saved.

## Build

Needs Python 2.7, the game's script runtime (for example `pyenv install 2.7.18`).

```sh
./build.sh                                   # dist/maksforge.autoloader_timer_<version>.wotmod
python2.7 tests/test_schedule.py
python2.7 tests/test_mod_smoke.py
```

## How it works

`gun.autoreload.reloadTime` holds one base time per magazine slot. The first entry is the shell that fills the magazine, and the last is the shell loaded into an empty one. Each frame, the mod reads the shell loading now from the game's `AmmoController`. It takes the remaining time from the server, works out your reload factor from that shell's base time, and adds the scaled time of each shell after it.

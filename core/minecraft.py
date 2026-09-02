"""Minecraft command center for J.A.R.V.I.S.

Safe, local-first Minecraft helpers: planners, calculators, command generation,
and automation recipes. It does not bypass anti-cheat or automate online
multiplayer accounts. Generated commands are shown to the user for review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from math import ceil, sqrt
from typing import Iterable

FEATURES = [
    "inventory planner", "crafting calculator", "smelting calculator", "fuel calculator",
    "building material calculator", "block palette planner", "blueprint planner", "layer planner",
    "coordinate waypoint manager", "distance calculator", "nether coordinate converter", "portal planner",
    "overworld route planner", "mining route planner", "strip-mining planner", "branch-mining planner",
    "ore checklist", "ancient-city checklist", "bastion checklist", "fortress checklist",
    "stronghold checklist", "end-prep checklist", "dragon-prep checklist", "elytra checklist",
    "beacon planner", "enchantment planner", "anvil cost helper", "villager trade planner",
    "villager hall planner", "breeding planner", "crop-farm planner", "tree-farm planner",
    "mob-farm planner", "iron-farm planner", "raid-farm planner", "sugar-cane planner",
    "bamboo planner", "kelp planner", "honey planner", "wool-farm planner", "storage planner",
    "item-sorting plan", "shulker packing planner", "ender-chest checklist", "redstone component planner",
    "redstone clock planner", "hopper throughput helper", "minecart route planner", "rail calculator",
    "command generator", "fill command generator", "clone command generator", "summon command generator",
    "teleport command generator", "give command generator", "time/weather command helper", "gamerule helper",
    "scoreboard design helper", "datapack function planner", "resource-pack checklist", "modpack checklist",
    "server maintenance checklist", "backup checklist", "world-reset checklist", "performance checklist",
    "seed notes", "biome notes", "death-location tracker", "session checklist", "achievement planner",
]

@dataclass(frozen=True)
class Waypoint:
    name: str
    x: int
    y: int
    z: int
    dimension: str = "overworld"


def feature_count() -> int:
    return len(FEATURES)


def distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def nether_to_overworld(x: int, z: int) -> tuple[int, int]:
    return x * 8, z * 8


def overworld_to_nether(x: int, z: int) -> tuple[int, int]:
    return round(x / 8), round(z / 8)


def blocks_for_box(width: int, height: int, length: int, hollow: bool = False) -> int:
    if min(width, height, length) < 1:
        raise ValueError("dimensions must be positive")
    if not hollow:
        return width * height * length
    if min(width, height, length) < 2:
        return width * height * length
    return width * height * length - max(width - 2, 0) * max(height - 2, 0) * max(length - 2, 0)


def stacks(items: int, stack_size: int = 64) -> tuple[int, int]:
    if items < 0 or stack_size <= 0:
        raise ValueError("items must be non-negative and stack size positive")
    return items // stack_size, items % stack_size


def crafting_batches(total_items: int, output_per_craft: int) -> int:
    if total_items < 0 or output_per_craft <= 0:
        raise ValueError("invalid crafting values")
    return ceil(total_items / output_per_craft)


def fuel_items(smelt_count: int, items_per_fuel: int = 8) -> int:
    if smelt_count < 0 or items_per_fuel <= 0:
        raise ValueError("invalid smelting values")
    return ceil(smelt_count / items_per_fuel)


def command_fill(pos1: tuple[int, int, int], pos2: tuple[int, int, int], block: str, replace: str | None = None) -> str:
    if not re.fullmatch(r"[a-z0-9_.:-]+", block):
        raise ValueError("invalid block id")
    x1, y1, z1 = pos1
    x2, y2, z2 = pos2
    if replace:
        if not re.fullmatch(r"[a-z0-9_.:-]+", replace):
            raise ValueError("invalid replacement block id")
        return f"/fill {x1} {y1} {z1} {x2} {y2} {z2} {block} replace {replace}"
    return f"/fill {x1} {y1} {z1} {x2} {y2} {z2} {block}"


def command_tp(x: int, y: int, z: int) -> str:
    return f"/tp @s {x} {y} {z}"


def command_time(value: str) -> str:
    if not re.fullmatch(r"(?:day|night|noon|midnight|[0-9]+)", value):
        raise ValueError("invalid time value")
    return f"/time set {value}"


def build_checklist(project: str, materials: Iterable[str]) -> str:
    lines = [f"Minecraft project: {project}", "", "Materials / tasks:"]
    lines.extend(f"- [ ] {m}" for m in materials if str(m).strip())
    return "\n".join(lines)


def parse_request(text: str) -> str | None:
    t = text.strip().lower()
    m = re.search(r"distance\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(?:to|and)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", t)
    if m:
        nums = list(map(int, m.groups()))
        return f"3D distance: {distance(tuple(nums[:3]), tuple(nums[3:])):.2f} blocks."
    m = re.search(r"(nether|overworld)\s+(?:coords?|coordinates?)\s+(-?\d+)\s+(-?\d+)", t)
    if m:
        dimension, x, z = m.group(1), int(m.group(2)), int(m.group(3))
        if dimension == "nether":
            ox, oz = nether_to_overworld(x, z)
            return f"Overworld portal target: X {ox}, Z {oz}."
        nx, nz = overworld_to_nether(x, z)
        return f"Nether portal target: X {nx}, Z {nz}."
    m = re.search(r"(?:box|cube)\s+(\d+)\s*[x×]\s*(\d+)\s*[x×]\s*(\d+)", t)
    if m:
        w, h, l = map(int, m.groups())
        n = blocks_for_box(w, h, l); s, r = stacks(n)
        return f"Solid {w}×{h}×{l} box: {n:,} blocks = {s} full stacks + {r}."
    m = re.search(r"stacks?\s+(\d+)", t)
    if m:
        n = int(m.group(1)); s, r = stacks(n)
        return f"{n:,} items = {s} full stacks + {r}."
    return None

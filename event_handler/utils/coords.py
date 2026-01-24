from typing import Tuple, Optional
import string
from math import sqrt

GRID_DIAMETER = 146.28571428571428
OIL_HELI_MAX_DISTANCE = GRID_DIAMETER * 4

def convert_coordinates_to_grid(coords: Tuple[int, int], map_size: int) -> Tuple[str, int]:
    grids = list(string.ascii_uppercase)
    grids.extend(a+b for a in string.ascii_uppercase for b in string.ascii_uppercase)

    return grids[int(coords[0] // GRID_DIAMETER)], int ((map_size - coords[1]) // GRID_DIAMETER)

def convert_coordinates_to_map_side(coords: Tuple[int, int], map_size: int) -> str:
    x = coords[0]
    y = coords[1]

    row = None
    col = None

    if x < 0:
        col = "Left"
    if   0 <= x <= map_size:
        col = ""
    if x > map_size:
        col = "Right"

    if y < 0:
        row = "Bottom"
    if 0 <= y <= map_size:
        row = ""
    if y > map_size:
        row = "Top"


    return (" ".join([row, col]).strip() if row or col else "")

def is_in_harbor(coords: Tuple[int, int], harbor_coords: Tuple[int, int]) -> bool:
    dx = coords[0] - harbor_coords[0]
    dy = coords[1] - harbor_coords[1]
    return sqrt(dx*dx + dy*dy) <= GRID_DIAMETER

def find_nearest_harbor_cords(coords: Tuple[int, int], monuments: dict) -> Tuple[int, int]:
    nearest_dist = 100000
    harbor_x = 0
    harbor_y = 0

    for token, monument_list in monuments.items():
        if "harbor" not in token:
            continue

        for m in monument_list:
            dx = coords[0] - m.x
            dy = coords[1] - m.y
            d = sqrt(dx*dx + dy*dy)
            if d < nearest_dist:
                nearest_dist = d
                harbor_x = m.x
                harbor_y = m.y

    return (harbor_x, harbor_y)

def find_nearest_rad_town(coords: Tuple[int, int], monuments: dict) -> Optional[str]:
    MAX_RADIUS = 2*GRID_DIAMETER
    nearest_dist = 100000
    nearest_rt = None

    for token, monument_list in monuments.items():
        for m in monument_list:
            dx = coords[0] - m.x
            dy = coords[1] - m.y
            d = sqrt(dx*dx + dy*dy)
            if d < nearest_dist and d < MAX_RADIUS:
                nearest_dist = d
                nearest_rt = token

    return nearest_rt

'large_oil_rig'
'oil_rig_small'

def get_oil_info(coords: Tuple[int, int], monuments: dict) -> Tuple[bool, Optional[str]]:
    for token, monument_list in monuments.items():
        if "oil_rig" not in token:
            continue

        for m in monument_list:
            dx = coords[0] - m.x
            dy = coords[1] - m.y
            d = sqrt(dx*dx + dy*dy)
            if d < OIL_HELI_MAX_DISTANCE:
                return (True, "Large" if token == 'large_oil_rig' else 'Small')
    
    return (False, None)


            
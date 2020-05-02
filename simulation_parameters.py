RED_MOVEMENT_SPEED = 0.8
BLUE_MOVEMENT_SPEED = 0.8

COHERENCE_FACTOR = 0.025
SEPARATION_FACTOR = 0.2
MATCH_FACTOR = 0.05
ENEMY_POSITION_FACTOR = 0.03
WANT_HEALING = 1.0

BASIC_MORALE = 8.0
BASIC_DAMAGE = 3.0
BASIC_HP = 100.0
BASIC_ATTACK_RANGE = 2.0
HEALING_RANGE = 3.0
GUARDING_RANGE = 4.0
VISION_RANGE = 50
SUCCESS_CHANCE = 6
FLOCKING_RADIUS = 5
SEPARATION_DISTANCE = 1.5

ALLIES_MORALE_WEIGHT = 0.2

# morale under which soldiers flee from the battlefield
TO_FLEE_THRESHOLD = 2.0

def kill_morale_modifier(has_killed: bool) -> float:
    if has_killed:
        return 1.5
    return 0

def damage_inflicted_morale_modifier(damage_inflicted: float) -> float:
    return damage_inflicted

def damage_received_morale_modifier(damage_received_recently: float, initial_hp: float) -> float:
    return max((damage_received_recently.__pow__(2) / initial_hp, damage_received_recently))
from typing import Dict

from ps2_analysis.enums import DamageLocation
from ps2_census.enums import (
    Faction,
    FireModeType,
    ItemCategory,
    PlayerState,
    ProjectileFlightType,
    ResistType,
    TargetType,
)

faction_resolver: Dict[Faction, str] = {
    Faction.NONE: "No faction",
    Faction.VANU_SOVEREIGNTY: "Vanu Sovereignty",
    Faction.NEW_CONGLOMERATE: "New Conglomerate",
    Faction.TERRAN_REPUBLIC: "Terran Republic",
    Faction.NS_OPERATIVES: "NS Operatives",
}
fire_mode_type_resolver: Dict[FireModeType, str] = {
    FireModeType.PROJECTILE: "Hip fire",
    FireModeType.IRON_SIGHT: "ADS",
    FireModeType.MELEE: "Melee",
    FireModeType.TRIGGER_ITEM_ABILITY: "Item ability",
    FireModeType.THROWN: "Throw",
}
item_category_resolver: Dict[ItemCategory, str] = {
    ItemCategory.ROCKET_LAUNCHER: "Rocket launcher",
    ItemCategory.EXPLOSIVE: "Explosive",
    ItemCategory.GRENADE: "Grenade",
    ItemCategory.KNIFE: "Knife",
    ItemCategory.PISTOL: "Pistol",
    ItemCategory.SHOTGUN: "Shotgun",
    ItemCategory.SMG: "SMG",
    ItemCategory.LMG: "LMG",
    ItemCategory.ASSAULT_RIFLE: "Assault rifle",
    ItemCategory.CARBINE: "Carbine",
    ItemCategory.SNIPER_RIFLE: "Sniper rifle",
    ItemCategory.SCOUT_RIFLE: "Scout rifle",
    ItemCategory.HEAVY_WEAPON: "Heavy weapon",
    ItemCategory.BATTLE_RIFLE: "Battle rifle",
    ItemCategory.CROSSBOW: "Crossbow",
    ItemCategory.HYBRID_RIFLE: "Hybrid rifle",
    ItemCategory.AERIAL_COMBAT_WEAPON: "Aerial combat weapon",
    ItemCategory.VEHICLE_WEAPONS: "Vehicle weapon",
    ItemCategory.FLASH_PRIMARY_WEAPON: "Flash primary",
    ItemCategory.GALAXY_LEFT_WEAPON: "Galaxy left",
    ItemCategory.GALAXY_TAIL_WEAPON: "Galazy tail",
    ItemCategory.GALAXY_RIGHT_WEAPON: "Galaxy right",
    ItemCategory.GALAXY_TOP_WEAPON: "Galaxy top",
    ItemCategory.HARASSER_TOP_GUNNER: "Harasser top",
    ItemCategory.LIBERATOR_BELLY_WEAPON: "Liberator belly",
    ItemCategory.LIBERATOR_NOSE_CANNON: "Liberator nose",
    ItemCategory.LIBERATOR_TAIL_WEAPON: "Liberator tail",
    ItemCategory.LIGHTNING_PRIMARY_WEAPON: "Lightning",
    ItemCategory.MAGRIDER_GUNNER_WEAPON: "Magrider gunner",
    ItemCategory.MAGRIDER_PRIMARY_WEAPON: "Magrider primary",
    ItemCategory.MOSQUITO_NOSE_CANNON: "Mosquito nose",
    ItemCategory.MOSQUITO_WING_MOUNT: "Mosquito wing",
    ItemCategory.PROWLER_GUNNER_WEAPON: "Prowler gunner",
    ItemCategory.PROWLER_PRIMARY_WEAPON: "Prowler primary",
    ItemCategory.REAVER_NOSE_CANNON: "Reaver nose",
    ItemCategory.REAVER_WING_MOUNT: "Reaver wing",
    ItemCategory.SCYTHE_NOSE_CANNON: "Scythe nose",
    ItemCategory.SCYTHE_WING_MOUNT: "Scythe wing",
    ItemCategory.SUNDERER_FRONT_GUNNER: "Sunderer front",
    ItemCategory.SUNDERER_REAR_GUNNER: "Sunderer rear",
    ItemCategory.VANGUARD_GUNNER_WEAPON: "Vanguard gunner",
    ItemCategory.VANGUARD_PRIMARY_WEAPON: "Vanguard primary",
    ItemCategory.VALKYRIE_NOSE_GUNNER: "Valkyrie nose",
    ItemCategory.ANT_TOP_TURRET: "Ant top",
    ItemCategory.BASTION_POINT_DEFENSE: "Bastion point defense",
    ItemCategory.BASTION_BOMBARD: "Bastion bombard",
    ItemCategory.BASTION_WEAPON_SYSTEM: "Bastion weapon system",
    ItemCategory.COLOSSUS_PRIMARY_WEAPON: "Colossus primary",
    ItemCategory.COLOSSUS_FRONT_RIGHT_WEAPON: "Colossus front right",
    ItemCategory.COLOSSUS_FRONT_LEFT_WEAPON: "Colossus front left",
    ItemCategory.COLOSSUS_REAR_RIGHT_WEAPON: "Colossus rear right",
    ItemCategory.COLOSSUS_REAR_LEFT_WEAPON: "Colossus rear left",
    ItemCategory.AA_MAX_RIGHT: "MAX AA right",
    ItemCategory.AA_MAX_LEFT: "MAX AA left",
    ItemCategory.AV_MAX_RIGHT: "MAX AV right",
    ItemCategory.AV_MAX_LEFT: "MAX AV left",
    ItemCategory.AI_MAX_RIGHT: "MAX AI right",
    ItemCategory.AI_MAX_LEFT: "MAX AI left",
}
projectile_flight_type_resolver: Dict[ProjectileFlightType, str] = {
    ProjectileFlightType.BALLISTIC: "Ballistic",
    ProjectileFlightType.TRUE_BALLISTIC: "True ballistic",
    ProjectileFlightType.DYNAMIC: "Dynamic",
    ProjectileFlightType.PROXIMITY_DETONATE: "Proximity detonate",
}
damage_location_resolver: Dict[DamageLocation, str] = {
    DamageLocation.HEAD: "Head",
    DamageLocation.TORSO: "Body",
    DamageLocation.LEGS: "Legs",
}
player_state_resolver: Dict[PlayerState, str] = {
    PlayerState.STANDING: "Standing",
    PlayerState.CROUCHING: "Crouching",
    PlayerState.RUNNING: "Running",
    PlayerState.SPRINTING: "Sprinting",
    PlayerState.FALLING_LONG: "Falling long",
    PlayerState.CROUCH_WALKING: "Crouch walking",
    PlayerState.FALLING_SHORT: "Falling short",
    PlayerState.JUMPING: "Jumping",
}
resist_type_resolver: Dict[ResistType, str] = {
    ResistType.NONE: "None",
    ResistType.MELEE: "Melee",
    ResistType.SMALL_ARM: "Small arm",
    ResistType.HEAVY_MACHINE_GUN: "Heavy machine gun",
    ResistType.HEAVY_ANTI_ARMOR: "Heavy anti armor",
    ResistType.EXPLOSIVE: "Explosive",
    ResistType.TANK_SHELL: "Tank shell",
    ResistType.AIRCRAFT_MACHINE_GUN: "Aircraft machine gun",
    ResistType.ANTI_VEHICLE_MINE: "Anti-vehicle mine",
    ResistType.FLAK_EXPLOSIVE_BLAST: "Flak explosive blast",
    ResistType.ANTI_AIRCRAFT_MACHINE_GUN: "Anti aircraft machine gun",
    ResistType.AIR_TO_GROUND_WARHEAD: "Air to ground warhead",
    ResistType.ARMOR_PIERCING_CHAIN_GUN: "Armor-piercing chain gun",
    ResistType.DEFAULT_ROCKET_LAUNCHER: "Rocket launcher",
    ResistType.ANTI_MATERIEL_RIFLE: "Anti-materiel rifle",
    ResistType.WHALE_HUNTER: "Whale hunter",
    ResistType.CORE_EXPLOSION: "Core explosion",
}
target_type_resolver: Dict[TargetType, str] = {
    TargetType.SELF: "Self",
    TargetType.ANY: "Any",
    TargetType.ENEMY: "Enemy",
    TargetType.ALLY: "Ally",
}
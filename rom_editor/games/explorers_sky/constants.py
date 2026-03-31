"""Game constants for Pokémon Mystery Dungeon: Explorers of Sky (US).

Offsets and sizes documented by the community at:
https://projectpokemon.org/home/forums/topic/62264-pmd-explorers-of-sky-data-research/
https://github.com/SkyTemple/skytemple

Game codes:
  US: YOTE  EU: YOTJ  JP: YOTK
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Game code identifiers
# ---------------------------------------------------------------------------
GAME_CODES = {"YOTE", "YOTJ", "YOTK"}

# ---------------------------------------------------------------------------
# NARC file paths within the ROM
# ---------------------------------------------------------------------------

# Pokémon base stats (MD format: magic "MD", ~130 bytes per entry)
POKEMON_DATA_NARC = "/BALANCE/MONSTER.MD"

# Move data (one entry per move)
MOVE_DATA_NARC = "/BALANCE/WAZA_P.BIN"

# Move learnset data (one entry per Pokémon)
MOVE_LEARNSET_NARC = "/BALANCE/WAZA_P2.BIN"

# Dungeon data files
DUNGEON_DATA_NARC = "/DUNGEON/DUNGEON.BIN"

# Portrait sprites (kaomado container, one block per Pokémon × emotion)
PORTRAIT_DATA = "/FONT/KAOMADO.KAO"

# Portrait emotion names (indices 0–39; 40 total slots in kaomado)
EMOTION_NAMES: list[str] = [
    "Normal", "Happy", "Pain", "Angry", "Worried", "Sad",
    "Crying", "Shouting", "Teary-Eyed", "Determined", "Scared",
    "Joyous", "Inspired", "Surprised", "Dizzy", "Special",
] + [f"Emotion {i}" for i in range(16, 40)]

# ---------------------------------------------------------------------------
# Pokémon names (National Dex order, index 0 = ???/empty, 1 = Bulbasaur, …)
# Includes the 493 Gen-I–IV Pokémon plus the EoS-exclusive special forms.
# ---------------------------------------------------------------------------
POKEMON_NAMES: list[str] = [
    "???",           # 0
    "Bulbasaur", "Ivysaur", "Venusaur",
    "Charmander", "Charmeleon", "Charizard",
    "Squirtle", "Wartortle", "Blastoise",
    "Caterpie", "Metapod", "Butterfree",       # 10-12
    "Weedle", "Kakuna", "Beedrill",
    "Pidgey", "Pidgeotto", "Pidgeot",
    "Rattata", "Raticate",                       # 19-20
    "Spearow", "Fearow",
    "Ekans", "Arbok",
    "Pikachu", "Raichu",
    "Sandshrew", "Sandslash",
    "Nidoran♀", "Nidorina", "Nidoqueen",        # 29-31
    "Nidoran♂", "Nidorino", "Nidoking",
    "Clefairy", "Clefable",
    "Vulpix", "Ninetales",
    "Jigglypuff", "Wigglytuff",                  # 39-40
    "Zubat", "Golbat",
    "Oddish", "Gloom", "Vileplume",
    "Paras", "Parasect",
    "Venonat", "Venomoth",
    "Diglett", "Dugtrio",                        # 50-51
    "Meowth", "Persian",
    "Psyduck", "Golduck",
    "Mankey", "Primeape",
    "Growlithe", "Arcanine",
    "Poliwag", "Poliwhirl", "Poliwrath",         # 60-62
    "Abra", "Kadabra", "Alakazam",
    "Machop", "Machoke", "Machamp",
    "Bellsprout", "Weepinbell", "Victreebel",
    "Tentacool", "Tentacruel",                   # 72-73
    "Geodude", "Graveler", "Golem",
    "Ponyta", "Rapidash",
    "Slowpoke", "Slowbro",
    "Magnemite", "Magneton",                     # 81-82
    "Farfetch'd",
    "Doduo", "Dodrio",
    "Seel", "Dewgong",
    "Grimer", "Muk",
    "Shellder", "Cloyster",                      # 90-91
    "Gastly", "Haunter", "Gengar",
    "Onix",
    "Drowzee", "Hypno",
    "Krabby", "Kingler",
    "Voltorb", "Electrode",                      # 100-101
    "Exeggcute", "Exeggutor",
    "Cubone", "Marowak",
    "Hitmonlee", "Hitmonchan",
    "Lickitung",
    "Koffing", "Weezing",                        # 109-110
    "Rhyhorn", "Rhydon",
    "Chansey",
    "Tangela",
    "Kangaskhan",
    "Horsea", "Seadra",
    "Goldeen", "Seaking",                        # 118-119
    "Staryu", "Starmie",
    "Mr. Mime",
    "Scyther",
    "Jynx",
    "Electabuzz",
    "Magmar",
    "Pinsir",                                    # 127
    "Tauros",
    "Magikarp", "Gyarados",                      # 129-130
    "Lapras",
    "Ditto",
    "Eevee", "Vaporeon", "Jolteon", "Flareon",  # 133-136
    "Porygon",
    "Omanyte", "Omastar",                        # 138-139
    "Kabuto", "Kabutops",
    "Aerodactyl",
    "Snorlax",
    "Articuno", "Zapdos", "Moltres",            # 144-146
    "Dratini", "Dragonair", "Dragonite",        # 147-149
    "Mewtwo",                                    # 150
    "Mew",                                       # 151
    "Chikorita", "Bayleef", "Meganium",         # 152-154
    "Cyndaquil", "Quilava", "Typhlosion",       # 155-157
    "Totodile", "Croconaw", "Feraligatr",       # 158-160
    "Sentret", "Furret",
    "Hoothoot", "Noctowl",
    "Ledyba", "Ledian",
    "Spinarak", "Ariados",                       # 167-168
    "Crobat",                                    # 169
    "Chinchou", "Lanturn",
    "Pichu",
    "Cleffa",
    "Igglybuff",
    "Togepi", "Togetic",                         # 175-176
    "Natu", "Xatu",
    "Mareep", "Flaaffy", "Ampharos",            # 179-181
    "Bellossom",
    "Marill", "Azumarill",
    "Sudowoodo",
    "Politoed",
    "Hoppip", "Skiploom", "Jumpluff",           # 187-189
    "Aipom",
    "Sunkern", "Sunflora",
    "Yanma",
    "Wooper", "Quagsire",
    "Espeon", "Umbreon",                         # 196-197
    "Murkrow",
    "Slowking",
    "Misdreavus",
    "Unown",                                     # 201
    "Wobbuffet",
    "Girafarig",
    "Pineco", "Forretress",
    "Dunsparce",
    "Gligar",
    "Steelix",                                   # 208
    "Snubbull", "Granbull",
    "Qwilfish",
    "Scizor",
    "Shuckle",
    "Heracross",
    "Sneasel",                                   # 215
    "Teddiursa", "Ursaring",
    "Slugma", "Magcargo",
    "Swinub", "Piloswine",
    "Corsola",
    "Remoraid", "Octillery",                     # 223-224
    "Delibird",
    "Mantine",
    "Skarmory",
    "Houndour", "Houndoom",
    "Kingdra",
    "Phanpy", "Donphan",                         # 231-232
    "Porygon2",
    "Stantler",
    "Smeargle",
    "Tyrogue",
    "Hitmontop",
    "Smoochum",
    "Elekid",                                    # 239
    "Magby",
    "Miltank",
    "Blissey",
    "Raikou", "Entei", "Suicune",               # 243-245
    "Larvitar", "Pupitar", "Tyranitar",         # 246-248
    "Lugia",                                     # 249
    "Ho-oh",                                     # 250
    "Celebi",                                    # 251
    # Gen-III (252–386) — abbreviated for readability
    "Treecko", "Grovyle", "Sceptile",
    "Torchic", "Combusken", "Blaziken",
    "Mudkip", "Marshtomp", "Swampert",
    "Poochyena", "Mightyena",
    "Zigzagoon", "Linoone",
    "Wurmple", "Silcoon", "Beautifly", "Cascoon", "Dustox",
    "Lotad", "Lombre", "Ludicolo",
    "Seedot", "Nuzleaf", "Shiftry",
    "Taillow", "Swellow",
    "Wingull", "Pelipper",
    "Ralts", "Kirlia", "Gardevoir",
    "Surskit", "Masquerain",
    "Shroomish", "Breloom",
    "Slakoth", "Vigoroth", "Slaking",
    "Nincada", "Ninjask", "Shedinja",
    "Whismur", "Loudred", "Exploud",
    "Makuhita", "Hariyama",
    "Azurill",
    "Nosepass",
    "Skitty", "Delcatty",
    "Sableye",
    "Mawile",
    "Aron", "Lairon", "Aggron",
    "Meditite", "Medicham",
    "Electrike", "Manectric",
    "Plusle", "Minun",
    "Volbeat", "Illumise",
    "Roselia",
    "Gulpin", "Swalot",
    "Carvanha", "Sharpedo",
    "Wailmer", "Wailord",
    "Numel", "Camerupt",
    "Torkoal",
    "Spoink", "Grumpig",
    "Spinda",
    "Trapinch", "Vibrava", "Flygon",
    "Cacnea", "Cacturne",
    "Swablu", "Altaria",
    "Zangoose",
    "Seviper",
    "Lunatone", "Solrock",
    "Barboach", "Whiscash",
    "Corphish", "Crawdaunt",
    "Baltoy", "Claydol",
    "Lileep", "Cradily",
    "Anorith", "Armaldo",
    "Feebas", "Milotic",
    "Castform",
    "Kecleon",
    "Shuppet", "Banette",
    "Duskull", "Dusclops",
    "Tropius",
    "Chimecho",
    "Absol",
    "Wynaut",
    "Snorunt", "Glalie",
    "Spheal", "Sealeo", "Walrein",
    "Clamperl", "Huntail", "Gorebyss",
    "Relicanth",
    "Luvdisc",
    "Bagon", "Shelgon", "Salamence",
    "Beldum", "Metang", "Metagross",
    "Regirock", "Regice", "Registeel",
    "Latias", "Latios",
    "Kyogre", "Groudon", "Rayquaza",
    "Jirachi",
    "Deoxys",                                    # 386
    # Gen-IV (387–493)
    "Turtwig", "Grotle", "Torterra",
    "Chimchar", "Monferno", "Infernape",
    "Piplup", "Prinplup", "Empoleon",
    "Starly", "Staravia", "Staraptor",
    "Bidoof", "Bibarel",
    "Kricketot", "Kricketune",
    "Shinx", "Luxio", "Luxray",
    "Budew", "Roserade",
    "Cranidos", "Rampardos",
    "Shieldon", "Bastiodon",
    "Burmy", "Wormadam", "Mothim",
    "Combee", "Vespiquen",
    "Pachirisu",
    "Buizel", "Floatzel",
    "Cherubi", "Cherrim",
    "Shellos", "Gastrodon",
    "Ambipom",
    "Drifloon", "Drifblim",
    "Buneary", "Lopunny",
    "Mismagius",
    "Honchkrow",
    "Glameow", "Purugly",
    "Chingling",
    "Stunky", "Skuntank",
    "Bronzor", "Bronzong",
    "Bonsly",
    "Mime Jr.",
    "Happiny",
    "Chatot",
    "Spiritomb",
    "Gible", "Gabite", "Garchomp",
    "Munchlax",
    "Riolu", "Lucario",
    "Hippopotas", "Hippowdon",
    "Skorupi", "Drapion",
    "Croagunk", "Toxicroak",
    "Carnivine",
    "Finneon", "Lumineon",
    "Mantyke",
    "Snover", "Abomasnow",
    "Weavile",
    "Magnezone",
    "Lickilicky",
    "Rhyperior",
    "Tangrowth",
    "Electivire",
    "Magmortar",
    "Togekiss",
    "Yanmega",
    "Leafeon", "Glaceon",
    "Gliscor",
    "Mamoswine",
    "Porygon-Z",
    "Gallade",
    "Probopass",
    "Dusknoir",
    "Froslass",
    "Rotom",
    "Uxie", "Mesprit", "Azelf",
    "Dialga", "Palkia",
    "Heatran",
    "Regigigas",
    "Giratina",
    "Cresselia",
    "Phione", "Manaphy",
    "Darkrai",
    "Shaymin",
    "Arceus",                                    # 493
]

# ---------------------------------------------------------------------------
# Type names (EoS type IDs 0–17 match Gen-IV types)
# ---------------------------------------------------------------------------
TYPE_NAMES: list[str] = [
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic",
    "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "???",
]

# ---------------------------------------------------------------------------
# Ability names (EoS ability IDs)
# ---------------------------------------------------------------------------
ABILITY_NAMES: list[str] = [
    "None",
    "Stench", "Drizzle", "Speed Boost", "Battle Armor", "Sturdy",
    "Damp", "Limber", "Sand Veil", "Static", "Volt Absorb",
    "Water Absorb", "Oblivious", "Cloud Nine", "Compound Eyes",
    "Insomnia", "Color Change", "Immunity", "Flash Fire", "Shield Dust",
    "Own Tempo", "Suction Cups", "Intimidate", "Shadow Tag", "Rough Skin",
    "Wonder Guard", "Levitate", "Effect Spore", "Synchronize",
    "Clear Body", "Natural Cure", "Lightningrod", "Serene Grace",
    "Swift Swim", "Chlorophyll", "Illuminate", "Trace", "Huge Power",
    "Poison Point", "Inner Focus", "Magma Armor", "Water Veil",
    "Magnet Pull", "Soundproof", "Rain Dish", "Sand Stream", "Pressure",
    "Thick Fat", "Early Bird", "Flame Body", "Run Away", "Keen Eye",
    "Hyper Cutter", "Pickup", "Truant", "Hustle", "Cute Charm",
    "Plus", "Minus", "Forecast", "Sticky Hold", "Shed Skin",
    "Guts", "Marvel Scale", "Liquid Ooze", "Overgrow", "Blaze",
    "Torrent", "Swarm", "Rock Head", "Drought", "Arena Trap",
    "Vital Spirit", "White Smoke", "Pure Power", "Shell Armor",
    "Air Lock", "Tangled Feet", "Motor Drive", "Rivalry", "Steadfast",
    "Snow Cloak", "Gluttony", "Anger Point", "Unburden", "Heatproof",
    "Simple", "Dry Skin", "Download", "Iron Fist", "Poison Heal",
    "Adaptability", "Skill Link", "Hydration", "Solar Power", "Quick Feet",
    "Normalize", "Sniper", "Magic Guard", "No Guard", "Stall",
    "Technician", "Leaf Guard", "Klutz", "Mold Breaker", "Super Luck",
    "Aftermath", "Anticipation", "Forewarn", "Unaware", "Tinted Lens",
    "Filter", "Slow Start", "Scrappy", "Storm Drain", "Ice Body",
    "Solid Rock", "Snow Warning", "Honey Gather", "Frisk", "Reckless",
    "Multitype", "Flower Gift", "Bad Dreams",
]

# ---------------------------------------------------------------------------
# Move category names
# ---------------------------------------------------------------------------
MOVE_CATEGORIES: list[str] = ["Physical", "Special", "Status"]

# ---------------------------------------------------------------------------
# Move names (move IDs 0–467 for EoS US)
# ---------------------------------------------------------------------------
MOVE_NAMES: list[str] = [
    "None",             # 0
    "Pound", "Karate Chop", "Double Slap", "Comet Punch", "Mega Punch",
    "Pay Day", "Fire Punch", "Ice Punch", "Thunder Punch", "Scratch",
    "Vice Grip", "Guillotine", "Razor Wind", "Swords Dance", "Cut",
    "Gust", "Wing Attack", "Whirlwind", "Fly", "Bind",
    "Slam", "Vine Whip", "Stomp", "Double Kick", "Mega Kick",
    "Jump Kick", "Rolling Kick", "Sand Attack", "Headbutt", "Horn Attack",
    "Fury Attack", "Horn Drill", "Tackle", "Body Slam", "Wrap",
    "Take Down", "Thrash", "Double-Edge", "Tail Whip", "Poison Sting",
    "Twineedle", "Pin Missile", "Leer", "Bite", "Growl",
    "Roar", "Sing", "Supersonic", "Sonic Boom", "Disable",
    "Acid", "Ember", "Flamethrower", "Mist", "Water Gun",
    "Hydro Pump", "Surf", "Ice Beam", "Blizzard", "Psybeam",
    "Bubblebeam", "Aurora Beam", "Hyper Beam", "Peck", "Drill Peck",
    "Submission", "Low Kick", "Counter", "Seismic Toss", "Strength",
    "Absorb", "Mega Drain", "Leech Seed", "Growth", "Razor Leaf",
    "Solar Beam", "Poison Powder", "Stun Spore", "Sleep Powder",
    "Petal Dance", "String Shot", "Dragon Rage", "Fire Spin", "Thunder Wave",
    "Clamp", "Swift", "Skull Bash", "Spike Cannon", "Constrict",
    "Amnesia", "Kinesis", "Soft-Boiled", "High Jump Kick", "Glare",
    "Dream Eater", "Poison Gas", "Barrage", "Leech Life", "Lovely Kiss",
    "Sky Attack", "Transform", "Bubble", "Dizzy Punch", "Spore",
    "Flash", "Psywave", "Splash", "Acid Armor", "Crabhammer",
    "Explosion", "Fury Swipes", "Bonemerang", "Rest", "Rock Slide",
    "Hyper Fang", "Sharpen", "Conversion", "Tri Attack", "Super Fang",
    "Slash", "Substitute", "Struggle", "Sketch", "Triple Kick",
    "Thief", "Spider Web", "Mind Reader", "Nightmare", "Flame Wheel",
    "Snore", "Curse", "Flail", "Conversion 2", "Aeroblast",
    "Cotton Spore", "Reversal", "Spite", "Powder Snow", "Protect",
    "Mach Punch", "Scary Face", "Feint Attack", "Sweet Kiss", "Belly Drum",
    "Sludge Bomb", "Mud-Slap", "Octazooka", "Spikes", "Zap Cannon",
    "Foresight", "Destiny Bond", "Perish Song", "Icy Wind", "Detect",
    "Bone Rush", "Lock-On", "Outrage", "Sandstorm", "Giga Drain",
    "Endure", "Charm", "Rollout", "False Swipe", "Swagger",
    "Milk Drink", "Spark", "Fury Cutter", "Steel Wing", "Mean Look",
    "Attract", "Sleep Talk", "Heal Bell", "Return", "Present",
    "Frustration", "Safeguard", "Pain Split", "Sacred Fire", "Magnitude",
    "DynamicPunch", "Megahorn", "DragonBreath", "Baton Pass", "Encore",
    "Pursuit", "Rapid Spin", "Sweet Scent", "Iron Tail", "Metal Claw",
    "Vital Throw", "Morning Sun", "Synthesis", "Moonlight", "Hidden Power",
    "Cross Chop", "Twister", "Rain Dance", "Sunny Day", "Crunch",
    "Mirror Coat", "Psych Up", "Extreme Speed", "Ancient Power",
    "Shadow Ball", "Future Sight", "Rock Smash", "Whirlpool", "Beat Up",
    "Fake Out", "Uproar", "Stockpile", "Spit Up", "Swallow",
    "Heat Wave", "Hail", "Torment", "Flatter", "Will-O-Wisp",
    "Memento", "Facade", "Focus Punch", "Smelling Salts", "Follow Me",
    "Nature Power", "Charge", "Taunt", "Helping Hand", "Trick",
    "Role Play", "Wish", "Assist", "Ingrain", "Superpower",
    "Magic Coat", "Recycle", "Revenge", "Brick Break", "Yawn",
    "Knock Off", "Endeavor", "Eruption", "Skill Swap", "Imprison",
    "Refresh", "Grudge", "Snatch", "Secret Power", "Dive",
    "Arm Thrust", "Camouflage", "Tail Glow", "Luster Purge", "Mist Ball",
    "Feather Dance", "Teeter Dance", "Blaze Kick", "Mud Sport",
    "Ice Ball", "Needle Arm", "Slack Off", "Hyper Voice", "Poison Fang",
    "Crush Claw", "Blast Burn", "Hydro Cannon", "Meteor Mash",
    "Astonish", "Weather Ball", "Aromatherapy", "Fake Tears", "Air Cutter",
    "Overheat", "Odor Sleuth", "Rock Tomb", "Silver Wind", "Metal Sound",
    "GrassWhistle", "Tickle", "Cosmic Power", "Water Spout", "Signal Beam",
    "Shadow Punch", "Extrasensory", "Sky Uppercut", "Sand Tomb",
    "Sheer Cold", "Muddy Water", "Bullet Seed", "Aerial Ace",
    "Icicle Spear", "Iron Defense", "Block", "Howl", "Dragon Claw",
    "Frenzy Plant", "Bulk Up", "Bounce", "Mud Shot", "Poison Tail",
    "Covet", "Volt Tackle", "Magical Leaf", "Water Sport", "Calm Mind",
    "Leaf Blade", "Dragon Dance", "Rock Blast", "Shock Wave", "Water Pulse",
    "Doom Desire", "Psycho Boost",
    # Gen-IV moves (337+)
    "Feint", "Pluck", "Tailwind", "Acupressure", "Metal Burst",
    "U-turn", "Close Combat", "Payback", "Assurance", "Embargo",
    "Fling", "Psycho Shift", "Trump Card", "Heal Block", "Wring Out",
    "Power Trick", "Gastro Acid", "Lucky Chant", "Me First", "Copycat",
    "Power Swap", "Guard Swap", "Punishment", "Last Resort", "Worry Seed",
    "Sucker Punch", "Toxic Spikes", "Heart Swap", "Aqua Ring",
    "Magnet Rise", "Flare Blitz", "Force Palm", "Aura Sphere",
    "Rock Polish", "Poison Jab", "Dark Pulse", "Night Slash",
    "Aqua Tail", "Seed Bomb", "Air Slash", "X-Scissor", "Bug Buzz",
    "Dragon Pulse", "Dragon Rush", "Power Gem", "Drain Punch",
    "Vacuum Wave", "Focus Blast", "Energy Ball", "Brave Bird",
    "Earth Power", "Switcheroo", "Giga Impact", "Nasty Plot",
    "Bullet Punch", "Avalanche", "Ice Shard", "Shadow Claw",
    "Thunder Fang", "Ice Fang", "Fire Fang", "Shadow Sneak",
    "Mud Bomb", "Psycho Cut", "Zen Headbutt", "Mirror Shot",
    "Flash Cannon", "Rock Climb", "Defog", "Trick Room", "Draco Meteor",
    "Discharge", "Lava Plume", "Leaf Storm", "Power Whip",
    "Rock Wrecker", "Cross Poison", "Gunk Shot", "Iron Head",
    "Magnet Bomb", "Stone Edge", "Captivate", "Stealth Rock",
    "Grass Knot", "Chatter", "Judgment", "Bug Bite", "Charge Beam",
    "Wood Hammer", "Aqua Jet", "Attack Order", "Defend Order",
    "Heal Order", "Head Smash", "Double Hit", "Roar of Time",
    "Spacial Rend", "Lunar Dance", "Crush Grip", "Magma Storm",
    "Dark Void", "Seed Flare", "Ominous Wind", "Shadow Force",
]

# ---------------------------------------------------------------------------
# Dungeon names (EoS US; 0-based index matches the dungeon ID)
# ---------------------------------------------------------------------------
DUNGEON_NAMES: list[str] = [
    "Temporal Tower", "Spacial Rift",
    "Dark Crater",
    "Concealed Ruins",
    "Marine Resort",
    "Bottomless Sea",
    "Shimmer Desert",
    "Mt. Avalanche",
    "Giant Volcano",
    "World Abyss",
    "Sky Stairway",
    "Mystery Jungle",
    "Serenity River",
    "Landslide Cave",
    "Lush Prairie",
    "Tiny Meadow",
    "Murky Forest",
    "Eastern Cave",
    "Fortune Ravine",
    "Spring Cave",
    "Southern Jungle",
    "Boulder Quarry",
    "Right Cave Path",
    "Left Cave Path",
    "Limestone Cavern",
    "Bad Cave",
    "Aegis Cave",
    "Mt. Horn",
    "Forest Path",
    "Foggy Forest",
    "Steam Cave",
    "Amp Plains",
    "Northern Desert",
    "Quicksand Cave",
    "Crystal Cave",
    "Crystal Crossing",
    "Chasm Cave",
    "Dark Hill",
    "Sealed Ruin",
    "Dusk Forest",
    "Treeshroud Forest",
    "Brine Cave",
    "Hidden Highland",
    "Temporal Tower (lower)",
    "Mystifying Forest",
    "Sky Peak",
    "Blizzard Island",
    "Craggy Coast",
    "Mt. Mistral",
    "Shimmer Hill",
    "Lost Wilderness",
    "Midnight Forest",
    "Zero Isle North",
    "Zero Isle East",
    "Zero Isle West",
    "Zero Isle South",
    "Zero Isle Center",
    "Final Maze",
    "Purity Forest",
    "Destiny Tower",
    "Oblivion Forest",
    "Treacherous Waters",
    "Southeastern Islands",
    "Inferno Cave",
    "Star Cave",
    "Maze Cave",
    "Oran Forest",
    "Lake Afar",
    "Happy Outlook",
    "Mt. Travail",
    "The Nightmare",
    "Spacial Cliffs",
    "Dark Ice Mountain",
    "Icicle Forest",
    "Vast Ice Mountain",
    "Southern Bittercold",
    "Bittercold (inner)",
    "Sky Tower Summit",
    "Unknown Dungeon",
]

# ---------------------------------------------------------------------------
# IQ Group names
# ---------------------------------------------------------------------------
IQ_GROUP_NAMES: list[str] = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I",
]

# ---------------------------------------------------------------------------
# EXP group names
# ---------------------------------------------------------------------------
EXP_GROUP_NAMES: list[str] = [
    "Slow", "Medium Slow", "Medium Fast", "Fast",
]

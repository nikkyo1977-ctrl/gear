"""
Configurazioni preset per uso rapido e demo.
"""

PRESETS = {
    "-- Seleziona preset --": None,

    # Ingranaggi dritti
    "Spur m2 z20 (standard)": {
        "gear_type": "spur",
        "params": {"m": "2.0", "z": "20", "b": "20.0", "alpha": "20.0", "x": "0.0"},
        "pair": {"z2": "40", "x2": "0.0"},
        "strength": {"material": "C45 bonificato", "P_kW": "5.0", "n_rpm": "1500", "KA": "1.25"},
    },
    "Spur m3 z17 (pignone riduttore)": {
        "gear_type": "spur",
        "params": {"m": "3.0", "z": "17", "b": "30.0", "alpha": "20.0", "x": "0.3"},
        "pair": {"z2": "51", "x2": "0.0"},
        "strength": {"material": "16MnCr5 cementato", "P_kW": "15.0", "n_rpm": "1000", "KA": "1.5"},
    },

    # Ingranaggi elicoidali
    "Helical mn2 z20 β15°": {
        "gear_type": "helical",
        "params": {"m": "2.0", "z": "20", "b": "25.0", "beta": "15.0"},
        "pair": {"z2": "60", "x2": "0.0"},
        "strength": {"material": "42CrMo4 bonificato", "P_kW": "10.0", "n_rpm": "1450", "KA": "1.25"},
    },
    "Helical mn2.5 z24 β20°": {
        "gear_type": "helical",
        "params": {"m": "2.5", "z": "24", "b": "30.0", "beta": "20.0"},
        "pair": {"z2": "72", "x2": "0.0"},
        "strength": {"material": "C45 bonificato", "P_kW": "7.5", "n_rpm": "960", "KA": "1.25"},
    },

    # Cremagliera
    "Rack m3 20 denti": {
        "gear_type": "rack",
        "params": {"m": "3.0", "z": "20", "b": "25.0", "alpha": "20.0"},
        "pair": {},
        "strength": {},
    },

    # Vite senza fine
    "Worm mx2 q10 z1": {
        "gear_type": "worm",
        "params": {"mx": "2.0", "z1": "1", "q": "10.0", "length": "60.0"},
        "pair": {},
        "strength": {},
    },
}


def list_presets() -> list:
    """Ritorna la lista dei nomi dei preset disponibili."""
    return list(PRESETS.keys())


def get_preset(name: str) -> dict:
    """Ritorna il preset richiesto o None se è il placeholder."""
    return PRESETS.get(name)

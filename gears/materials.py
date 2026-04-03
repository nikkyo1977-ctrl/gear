"""
Database materiali per ingranaggi.
Valori di riferimento da ISO 6336 e letteratura tecnica.
"""

MATERIAL_DB = {
    "C45 bonificato": {
        "nome": "Acciaio C45 bonificato",
        "E": 206000,       # MPa - modulo di Young
        "nu": 0.3,         # coefficiente di Poisson
        "HB": 220,         # durezza Brinell
        "sigma_b": 700,    # MPa - resistenza a trazione
        "sigma_Flim": 230, # MPa - limite a flessione ISO 6336 qualità MQ
        "sigma_Hlim": 550, # MPa - limite Hertz ISO 6336 qualità MQ
        "rho": 7850,       # kg/m³ - densità
    },
    "16MnCr5 cementato": {
        "nome": "Acciaio 16MnCr5 cementato e temperato",
        "E": 206000,
        "nu": 0.3,
        "HB": 650,         # HV equivalente per cementati (strato cementato ~60 HRC)
        "sigma_b": 1100,
        "sigma_Flim": 430, # MPa - qualità MQ cementato
        "sigma_Hlim": 1500,
        "rho": 7850,
    },
    "42CrMo4 bonificato": {
        "nome": "Acciaio 42CrMo4 bonificato",
        "E": 206000,
        "nu": 0.3,
        "HB": 280,
        "sigma_b": 1000,
        "sigma_Flim": 290, # MPa - qualità MQ
        "sigma_Hlim": 650,
        "rho": 7850,
    },
    "GG25 ghisa grigia": {
        "nome": "Ghisa grigia GG25",
        "E": 100000,
        "nu": 0.26,
        "HB": 180,
        "sigma_b": 250,
        "sigma_Flim": 85,  # MPa - qualità MQ ghisa
        "sigma_Hlim": 350,
        "rho": 7200,
    },
    "CuSn12 bronzo": {
        "nome": "Bronzo allo stagno CuSn12 (ruote elicoidali)",
        "E": 88000,
        "nu": 0.35,
        "HB": 120,
        "sigma_b": 350,
        "sigma_Flim": 70,  # MPa - ruote elicoidali in bronzo
        "sigma_Hlim": 220,
        "rho": 8800,
    },
}


def get_material(name: str) -> dict:
    """Ritorna il dizionario del materiale richiesto. Lancia KeyError se non trovato."""
    return MATERIAL_DB[name]


def list_materials() -> list:
    """Ritorna la lista dei nomi dei materiali disponibili."""
    return list(MATERIAL_DB.keys())

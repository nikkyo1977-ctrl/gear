"""
Salvataggio e caricamento progetti in formato JSON.
"""

import json


def save_project(filepath: str, state: dict) -> None:
    """
    Salva lo stato del progetto corrente in un file JSON.

    Parametri:
        filepath : percorso del file di destinazione (es. 'mio_progetto.gear.json')
        state    : dict con lo stato dell'applicazione (gear_type, params, pair, strength)
    """
    data = {"version": 1}
    data.update(state)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_project(filepath: str) -> dict:
    """
    Carica un progetto da file JSON.

    Ritorna il dict dello stato, compatibile con GearApp.set_state().
    Lancia ValueError se il file non è un progetto valido.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if data.get('version') != 1:
        raise ValueError(f"Versione file non supportata: {data.get('version')}")
    return data

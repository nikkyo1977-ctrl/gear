# gearcalc

Libreria Python di calcolo ingranaggi, priva di dipendenze CAD e pensata per essere esposta
come tool del server MCP `CATIA_V5_MCP`. Il modello 3D si genera in CATIA (via pycatia) a
partire dai punti di profilo prodotti da questa libreria.

## Stato

| Fase | Contenuto | Stato |
|---|---|---|
| 1 | Struttura del pacchetto, modello dati pydantic, geometria cilindrica esterna, test, CI | ✅ |
| 2 | Geometria completa ISO 21771: dentatura interna, trocoide di piede, ripartizione x (DIN 3992), W_k / M_d, tolleranze di spessore (DIN 3967) | ⏳ |
| 4 | Ruote in polimero VDI 2736; vite-ruota ISO/TS 14521 – DIN 3996 | ⏳ (prioritaria) |
| 3 | Acciaio ISO 6336:2019 tramite [python-gearbox](https://github.com/efirvida/python-gearbox) | ⏳ |
| 5 | Tolleranze ISO 1328-1:2013, report | ⏳ |
| 6 | Integrazione in `CATIA_V5_MCP` | ⏳ |

## Installazione

```bash
pip install -e ".[dev]"
```

## Esempio

```python
from gearcalc import CylindricalGear, GearPair, pair_geometry, gear_profile

pair = GearPair(
    gear1=CylindricalGear(z=17, m_n=1.0, b=8.0, beta=12.0, x=0.35),
    gear2=CylindricalGear(z=52, m_n=1.0, b=8.0, beta=-12.0, x=-0.1),
)
geo = pair_geometry(pair)
print(geo.a_w, geo.alpha_wt, geo.epsilon_alpha, geo.warnings)

pts = gear_profile(geo.gear1, thickness_reduction=0.05)  # array (N, 2) in mm
print(geo.model_dump_json(indent=2))  # output pronto per MCP
```

## Convenzioni

- mm, gradi, N, N·m; nomi dei campi = simboli ISO 21771 (`m_n`, `alpha_wt`, `d_a`, ...).
- `beta` con segno (>0 elica destra); coppia esterna: `beta2 = -beta1`.
- Modelli immutabili: per una variante ricostruire il modello (`Model.model_validate(m.model_dump() | {...})`), così i nuovi valori vengono validati.

## Sviluppo

```bash
pytest
ruff check .
mypy src
```

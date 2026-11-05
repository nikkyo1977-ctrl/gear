# gearcalc

Libreria Python di calcolo ingranaggi, priva di dipendenze CAD e pensata per essere esposta
come tool del server MCP `CATIA_V5_MCP`. Il modello 3D si genera in CATIA (via pycatia) a
partire dai punti di profilo prodotti da questa libreria.

## Stato

| Fase | Contenuto | Stato |
|---|---|---|
| 1 | Struttura del pacchetto, modello dati pydantic, geometria cilindrica esterna, test, CI | ✅ |
| 2 | Geometria ISO 21771 completa: dentature interne, profilo generato da creatore (trocoide, sottosquadro), d_Ff / d_Nf, strisciamenti specifici, ripartizione di x, W_k / M_d, gioco | ✅ |
| 4a | Ruote in polimero VDI 2736-2: temperature, piede, fianco, usura a secco, deformazione | ✅ |
| 4b | Vite-ruota ISO/TS 14521 – DIN 3996 | ⏳ (prioritaria) |
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

# quote di controllo con scostamenti di spessore (mm)
from gearcalc import ThicknessAllowances, tooth_measurement

tm = tooth_measurement(geo.gear1, ThicknessAllowances(A_sne=-0.02, A_sni=-0.05))
print(tm.k, tm.W_k_max, tm.W_k_min, tm.D_M, tm.M_d_max, tm.M_d_min)
```

## Verifica ruote in plastica (VDI 2736)

```python
from gearcalc.rating import (
    Lubrication,
    Material,
    OperatingConditions,
    Polymer,
    VDI2736Input,
    rate_vdi2736,
)

res = rate_vdi2736(
    VDI2736Input(
        pair=pair,
        material1=Material(polymer=Polymer.STEEL),
        material2=Material(polymer=Polymer.POM),
        lubrication=Lubrication.GREASE,  # es. Klüber Isoflex Topas L32 → μ = 0.09
        operating=OperatingConditions(T_1=0.15, n_1=3000, life_hours=500, theta_0=60),
    )
)
print(res.gear2.theta_flank, res.gear2.S_F, res.warnings)
```

Dati dei materiali: curve di resistenza, attrito, scambio termico e usura da VDI 2736-2;
moduli elastici **indicativi** (sostituibili con `Material(E_23=..., dE_dT=...)`). Dove la norma
non dà curve (PBT al piede, POM al fianco) si può fornire `sigma_FlimN` / `sigma_HlimN`.

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

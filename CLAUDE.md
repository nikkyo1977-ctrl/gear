# gearcalc — note di progetto

Libreria di calcolo ingranaggi **senza dipendenze CAD**, destinata a essere importata dal
server MCP `nikkyo1977-ctrl/CATIA_V5_MCP` (dipendenza pinnata su tag). Il solido 3D si
costruisce in CATIA via pycatia dai punti di `gear_profile`; qui non c'è codice CAD né GUI
(la vecchia GUI PySide6 e i modelli build123d sono stati rimossi in fase 1: sono nella
storia git, commit 538f5fc).

## Decisioni prese
- Priorità applicative: **ruote in polimero (VDI 2736)** e **vite-ruota (ISO/TS 14521,
  DIN 3996)** → attuatori automotive.
- Acciaio: ISO 6336:2019 delegato a `python-gearbox` (MIT), pinnato su commit in
  `pyproject.toml`, dietro un adapter nostro (fase 3).
- Validazione finale contro KISSsoft (casi forniti dall'utente).
- Riferimenti consultati, non copiare codice: `mjesus18/PEC_VDI2736` (nessuna licenza),
  `cfernandesFEUP/GEARpie` (MIT, VDI 2736; bug nel confronto materiali `== ('STEEL' or ...)`).

## Convenzioni
- Python ≥ 3.11, tipizzazione stretta (`mypy --strict`), ruff, pytest; deve girare su Windows.
- Input/output = modelli pydantic frozen in `models.py`, serializzabili JSON (contratto MCP).
- Unità: mm, gradi, N, N·m. Nomi = simboli ISO 21771 (`m_n`, `alpha_wt`, `d_a`, `s_an`...).
- `beta` con segno; coppia esterna `beta2 = -beta1`. `x` riferito sempre a `m_n`.
- Ogni formula: norma e paragrafo nella docstring, ipotesi e limiti espliciti.
- Avvisi progettuali come stringhe in `warnings` (non eccezioni); eccezioni solo per
  geometria non realizzabile (`GeometryError`).
- Ogni nuova verifica va accompagnata da un test di confronto con una fonte indipendente
  (python-gearbox, esempi della norma, KISSsoft).

## Roadmap
1. ✅ struttura, modello dati, geometria cilindrica esterna, profilo 2D, CI
2. ✅ geometria ISO 21771: interne (convenzione con segno: z, d, a_w < 0), profilo esterno come
   inviluppo esatto del creatore (trocoide + sottosquadro, verificato contro evolvente analitica e
   d_Ff ISO), d_Nf, strisciamenti specifici, ripartizione x (uguale / strisciamenti bilanciati),
   W_k, M_d (sfera ideale), gioco da scostamenti di spessore e interasse.
   Aperti: tabelle DIN 3967 (scostamenti oggi in input), raccordo delle interne (coltello
   stozzatore) e verifica completa di interferenza trocoidale nelle interne (ora regola z2−z1≥10).
4. (anticipata) VDI 2736 polimeri; vite-ruota ISO/TS 14521
3. adapter ISO 6336 → python-gearbox
5. ISO 1328-1:2013, report
6. tool MCP in CATIA_V5_MCP

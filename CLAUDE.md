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
4a. ✅ VDI 2736-2 (src/gearcalc/rating): temperature θ_Fuß/θ_Fla, piede (Y_Fa/Y_Sa con carico in
   testa da geometria reale, σ_FG = Y_ST·σ_FlimN), fianco, usura a secco, deformazione.
   Materiali standard POM/PA66/PBT/acciaio; E(θ) indicativi. Lubrificazioni: secco o grasso
   (Isoflex Topas L32 trattato come grasso VDI, μ = 0.09). Mancano: coppie interne, carico di
   picco (σ_S), dati fornitori.
4b. ✅ vite-ruota (geometry/worm.py, rating/worm_plastic.py): geometria ZA/ZN/ZI/ZK, ruota
   virtuale del piano medio per il piede, rendimento/forze esatti, autobloccaggio, usura Archard
   coerente con VDI 2736. Temperatura = adattamento VDI 2736-2 con P_V e v_g: SOVRASTIMA
   (es. 240 °C), va sostituita con VDI 2736-3 o tarata su prove; theta_wheel per imporla.
   Mancano: VDI 2736-3, ruota in bronzo ISO/TS 14521, profilo vite per CATIA.
3. adapter ISO 6336 → python-gearbox
5. ISO 1328-1:2013, report
6. ◐ tool MCP in CATIA_V5_MCP (branch claude/dazzling-faraday-r6nr9o, dipendenza bloccata su
   commit di gear): gear_pair_calc, gear_measurement, gear_backlash, gear_plastic_rating,
   worm_gear_calc, worm_gear_plastic_rating, gear_profile_points, catia_create_spur_gear
   (schizzo da gear_outline + Pad, controllo volume). Da fare: prova live su R34, elicoidali,
   vite e ruota a vite in CATIA. Aggiornando gearcalc, aggiornare lo SHA in CATIA_V5_MCP.

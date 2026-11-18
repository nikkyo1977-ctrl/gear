# Ricoprimento attivo e pressione al fianco

Riscontro sulla copia VDI 2736 Blatt 3:2014-05. Il §3.2.1 (PDF 11 e 13) prescrive i cerchi di forma pertinenti in presenza di modifiche di testa. A1 (PDF 21–24) assegna sia i diametri di testa sia il ricoprimento. Le figure dell'esempio mostrano il riduttore in assieme. Mancano le due quote di forma attive.

## Ricostruzione A1

Con le quote di testa della vite e della ruota, le due lunghezze di contatto normale valgono 7,755584 e 4,025126 mm. Il passo normale di base è 5,133818 mm. La (11) dà 2,294727; il valore assegnato di 2,130 richiede una lunghezza complessiva inferiore di 0,845679 mm. Anche variando indipendentemente i diametri e gli angoli di base di mezza unità dell'ultima cifra stampata e ammettendo ±0,05 mm sul modulo e ±0,5° sulla pressione, il risultato rimane fra 2,222 e 2,372.

Due inversioni della (12) illustrano perché l'origine fisica non è identificabile. Mantenendo la testa della ruota a 53,865 mm si ottiene un diametro attivo della vite di 18,080900 mm. Mantenendo la vite a 18,632 mm si ottiene invece 53,188327 mm sulla ruota. Entrambe le coppie restituiscono 2,130. Sono soluzioni matematiche. Per attribuire lo scarto a una modifica reale servono il disegno delle teste o le lunghezze attive originali. Rimane possibile un'incongruenza nei dati dell'allegato.

## Uso in gearcalc

Il gruppo opzionale `Blatt3Input.flank` richiede attrito di esercizio, moduli elastici in MPa e coefficienti di Poisson alle condizioni di contatto. L'output `result.flank` espone la forza normale nominale, le curvature, gli intermedi delle equazioni (22)–(34), i semiassi e la pressione in MPa. Con `sigma_HP` fornita e documentata, `flank_ok` confronta direttamente pressione e limite. In sua assenza l'esito resta indeterminato.

Il default `epsilon_source="geometry"` usa i diametri attivi forniti, con ripiego sui diametri di testa. Per ripercorrere un esempio con ricoprimento assegnato, scegliere esplicitamente `epsilon_source="reference"` e fornire `geometry.epsilon_n_reference`. Il risultato conserva fonte e valore usato. La scelta riguarda soltanto il fianco. A parità di geometria i semiassi restano uguali e la pressione varia come l'inverso della radice del ricoprimento.

| Esempio | Ricoprimento geometrico / assegnato | Pressione geometrica / con valore assegnato [MPa] | Pressione stampata [MPa] |
|---|---:|---:|---:|
| A1 | 2,294727 / 2,130 | 99,2921 / 103,0601 | 102,33 |
| A2 | 2,267539 / 2,268 | 38,9109 / 38,9069 | 39,10 |

Con il ricoprimento assegnato si ritrova il ricalcolo indipendente a precisione piena della KB GEARS. Le differenze con le pressioni stampate dipendono principalmente dall'uso di intermedi arrotondati nei semiassi. In A1 anche il fattore di ricoprimento stampato (0,686) differisce dal ricalcolo (0,685189). Le verifiche usano proprietà dei materiali assegnate negli esempi. I due casi verificano la pressione calcolata; la durata e l'ammissibile del materiale reale richiedono dati propri.

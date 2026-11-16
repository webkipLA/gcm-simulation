# FORTRAN-Vergleiche mit Arithmetik `ibm360` gegenüber `exact`

Quelle: die Tabellen dieses Ordners und von `data/analysis`. Anteile gepoolt über 108 Situationen. Bei den Tests heißt "Richtung gleich", dass die mittlere gepaarte Differenz dasselbe Vorzeichen hat, und "Signifikanz gleich", dass p (Holm) in beiden Rechnungen auf derselben Seite von 0,05 liegt.

## Referenzszenarien

| condition                    |   resolution exact |   resolution ibm360 |   flight exact |   flight ibm360 |   KX exact |   KX ibm360 |   Differenz Resolution |
|:-----------------------------|-------------------:|--------------------:|---------------:|----------------:|-----------:|------------:|-----------------------:|
| D_unsegmented                |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |
| D_hierarchical               |              0.373 |               0.366 |          0.383 |           0.392 |     64.843 |      63.944 |                 -0.006 |
| D_specialized                |              0.16  |               0.16  |          0.595 |           0.595 |     16.935 |      16.917 |                  0     |
| gemini hier T0.7             |              0.373 |               0.366 |          0.383 |           0.392 |     64.843 |      63.944 |                 -0.006 |
| qwen3:4b hier T0             |              0.325 |               0.325 |          0.406 |           0.403 |     54.491 |      54.37  |                  0     |
| qwen3:4b hier T0.7           |              0.248 |               0.243 |          0.502 |           0.504 |     38.602 |      38.537 |                 -0.005 |
| qwen3:4b hier T0.7 (Ziehung) |              0.289 |               0.284 |          0.441 |           0.45  |     49.796 |      49.88  |                 -0.005 |

Tests: 24, Richtung gleich in 24, Signifikanz gleich in 24.

Kein Test ändert Richtung oder Signifikanz.

## Hochschulszenario

| condition                     |   resolution exact |   resolution ibm360 |   flight exact |   flight ibm360 |   KX exact |   KX ibm360 |   Differenz Resolution |
|:------------------------------|-------------------:|--------------------:|---------------:|----------------:|-----------:|------------:|-----------------------:|
| D_unsegmented                 |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |
| D_hierarchical                |              0.373 |               0.366 |          0.383 |           0.392 |     64.843 |      63.944 |                 -0.006 |
| D_specialized                 |              0.16  |               0.16  |          0.595 |           0.595 |     16.935 |      16.917 |                  0     |
| Hochschule stark (Schwelle)   |              0.35  |               0.361 |          0.423 |           0.415 |     59.843 |      60.565 |                  0.011 |
| Hochschule stark (Ziehung)    |              0.32  |               0.32  |          0.434 |           0.438 |     59.333 |      59.815 |                 -0     |
| Hochschule mittel (Schwelle)  |              0.206 |               0.206 |          0.59  |           0.59  |     29.593 |      29.519 |                  0     |
| Hochschule mittel (Ziehung)   |              0.212 |               0.208 |          0.566 |           0.565 |     31.639 |      31.611 |                 -0.004 |
| Hochschule schwach (Schwelle) |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |

Tests: 32, Richtung gleich in 32, Signifikanz gleich in 30.

Tests mit anderem Ergebnis:

| condition                   | reference      | Kennzahl                     |   difference exact |   difference ibm360 |   p_holm exact |   p_holm ibm360 | Richtung gleich   | Signifikanz gleich   |
|:----------------------------|:---------------|:-----------------------------|-------------------:|--------------------:|---------------:|----------------:|:------------------|:---------------------|
| Hochschule stark (Schwelle) | D_hierarchical | Anteil Resolution            |            -0.0319 |             -0.0153 |         0.0082 |          0.0765 | True              | False                |
| Hochschule stark (Schwelle) | D_hierarchical | Anteil Flight oder Oversight |             0.0319 |              0.0153 |         0.0082 |          0.0765 | True              | False                |

## Hochschulszenario, weitere Bedingungen

| condition                          |   resolution exact |   resolution ibm360 |   flight exact |   flight ibm360 |   KX exact |   KX ibm360 |   Differenz Resolution |
|:-----------------------------------|-------------------:|--------------------:|---------------:|----------------:|-----------:|------------:|-----------------------:|
| D_unsegmented                      |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |
| D_hierarchical                     |              0.373 |               0.366 |          0.383 |           0.392 |     64.843 |      63.944 |                 -0.006 |
| D_specialized                      |              0.16  |               0.16  |          0.595 |           0.595 |     16.935 |      16.917 |                  0     |
| Hochschule stark (Schwelle)        |              0.35  |               0.361 |          0.423 |           0.415 |     59.843 |      60.565 |                  0.011 |
| Hochschule mittel (Schwelle)       |              0.206 |               0.206 |          0.59  |           0.59  |     29.593 |      29.519 |                  0     |
| Hochschule schwach (Schwelle)      |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |
| ohne Teilnahmeaussage stark        |              0.199 |               0.198 |          0.597 |           0.598 |     34.778 |      34.806 |                 -0.001 |
| ohne Teilnahmeaussage mittel       |              0.143 |               0.141 |          0.672 |           0.673 |     15.778 |      15.833 |                 -0.001 |
| ohne Teilnahmeaussage schwach      |              0.176 |               0.176 |          0.612 |           0.612 |     19.306 |      19.278 |                  0     |
| Hauptmodell, Denkstufe low stark   |              0.366 |               0.362 |          0.389 |           0.395 |     67.435 |      67.259 |                 -0.003 |
| Hauptmodell, Denkstufe low mittel  |              0.159 |               0.158 |          0.649 |           0.65  |     25.509 |      25.722 |                 -0.001 |
| Hauptmodell, Denkstufe low schwach |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |
| gemini-4-argon stark               |              0.429 |               0.432 |          0.32  |           0.317 |     81     |      81.139 |                  0.002 |
| gemini-4-argon mittel              |              0.175 |               0.175 |          0.595 |           0.595 |     19.806 |      19.806 |                  0     |
| gemini-4-argon schwach             |              0.66  |               0.689 |          0.167 |           0.131 |    122.222 |     122.593 |                  0.029 |

Tests: 104, Richtung gleich in 104, Signifikanz gleich in 96.

Tests mit anderem Ergebnis:

| condition                         | reference                   | Kennzahl                     |   difference exact |   difference ibm360 |   p_holm exact |   p_holm ibm360 | Richtung gleich   | Signifikanz gleich   |
|:----------------------------------|:----------------------------|:-----------------------------|-------------------:|--------------------:|---------------:|----------------:|:------------------|:---------------------|
| ohne Teilnahmeaussage schwach     | D_unsegmented               | Entscheidungsdauer KY        |            20.6204 |             10.3704 |         0.0001 |          0.2019 | True              | False                |
| Hauptmodell, Denkstufe low stark  | D_hierarchical              | Problemaktivität KT          |            13.3981 |             13.0278 |         0.0455 |          0.0689 | True              | False                |
| Hauptmodell, Denkstufe low stark  | Hochschule stark (Schwelle) | Anteil Resolution            |             0.0169 |              0.003  |         0.0321 |          0.2129 | True              | False                |
| Hauptmodell, Denkstufe low stark  | Hochschule stark (Schwelle) | Anteil Flight oder Oversight |            -0.0169 |             -0.003  |         0.0354 |          0.2243 | True              | False                |
| Hauptmodell, Denkstufe low mittel | D_specialized               | Problemaktivität KT          |            -5.6481 |             -5.6111 |         0.0473 |          0.058  | True              | False                |
| gemini-4-argon stark              | D_hierarchical              | Anteil Resolution            |             0.0481 |              0.0573 |         0.1198 |          0.0344 | True              | False                |
| gemini-4-argon stark              | D_hierarchical              | Anteil Flight oder Oversight |            -0.0481 |             -0.0573 |         0.1191 |          0.0324 | True              | False                |
| gemini-4-argon stark              | D_hierarchical              | Ungelöste Probleme KW        |            -1.1296 |             -1.4167 |         0.1107 |          0.0255 | True              | False                |

# Docking report

reference: `GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx`, 269 published values

## FORTRAN port, arithmetic `exact` (2 s, 324 runs)

pooled styles: {'by_resolution': 1201, 'by_oversight': 634, 'by_flight': 1066} of 2901 choices made

docking status: {'identisch im Rahmen der Rundung': 47, 'innerhalb Toleranz': 33, 'Abweichung': 21}

### Deviations

| id                                             | fundstelle    |   publiziert |     port |   abweichung |
|:-----------------------------------------------|:--------------|-------------:|---------:|-------------:|
| CMO_T1_leicht_unsegmentiert                    | Tab. 1, S. 9  |         0.38 |   0.4302 |       0.0502 |
| CMO_T1_leicht_hierarchisch                     | Tab. 1, S. 9  |         0.61 |   0.497  |      -0.113  |
| CMO_T1_mittel_hierarchisch                     | Tab. 1, S. 9  |         0.27 |   0.3274 |       0.0574 |
| CMO_T1_schwer_spezialisiert                    | Tab. 1, S. 9  |         0.5  |   0.5634 |       0.0634 |
| CMO_T1_alle_unsegmentiert                      | Tab. 1, S. 9  |         0.26 |   0.2908 |       0.0308 |
| CMO_T1_alle_spezialisiert                      | Tab. 1, S. 9  |         0.58 |   0.6126 |       0.0326 |
| CMO_T3_hoch_frueh                              | Tab. 3, S. 10 |         0.46 |   0.5222 |       0.0622 |
| CMO_T4_niedrig_frueh                           | Tab. 4, S. 11 |         0.54 |   0.5071 |      -0.0329 |
| CMO_T5_1112_anteil_resolution                  | Tab. 5, S. 17 |         0.38 |   0.575  |       0.195  |
| CMO_T5_1112_problemaktivitaet_KT               | Tab. 5, S. 17 |       210    | 182.75   |     -27.25   |
| CMO_T5_1112_problemlatenz_KU                   | Tab. 5, S. 17 |        25    |  17      |      -8      |
| CMO_T5_1112_aktivitaet_entscheidungstraeger_KX | Tab. 5, S. 17 |        66    |  74.25   |       8.25   |
| CMO_T5_1112_entscheidungszeit_KY               | Tab. 5, S. 17 |        31    |  35.5    |       4.5    |
| CMO_T5_1111_anteil_resolution                  | Tab. 5, S. 17 |         0.31 |   0.35   |       0.04   |
| CMO_T5_1111_problemaktivitaet_KT               | Tab. 5, S. 17 |       200    | 184.75   |     -15.25   |
| CMO_T5_1111_problemlatenz_KU                   | Tab. 5, S. 17 |        30    |  25.5    |      -4.5    |
| CMO_T5_1111_aktivitaet_entscheidungstraeger_KX | Tab. 5, S. 17 |        58    |  65.5    |       7.5    |
| CMO_T5_1002_anteil_resolution                  | Tab. 5, S. 17 |         0    |   0.0556 |       0.0556 |
| CMO_T5_1002_problemaktivitaet_KT               | Tab. 5, S. 17 |       310    | 291      |     -19      |
| CMO_T5_1002_aktivitaet_entscheidungstraeger_KX | Tab. 5, S. 17 |        90    |  95      |       5      |
| CMO_T5_1002_entscheidungszeit_KY               | Tab. 5, S. 17 |        20    |  26.5    |       6.5    |

### Properties

|   nr | verdict       | evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----:|:--------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|    1 | bestätigt     | cells >= 0.5: [('light', 'all'), ('light', 'hierarchical'), ('light', 'specialized'), ('moderate', 'specialized'), ('heavy', 'specialized'), ('all', 'specialized')]                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|    2 | bestätigt     | means by load {'problem_persistence': [114.3, 200.2, 208.8], 'dm_velocity': [61.0, 66.0, 76.9], 'choice_persistence': [19.5, 34.1, 46.1]}; flight/oversight [0.473, 0.677, 0.617]; unsegmented access x specialized decision: {'choice_persistence': {'heavy': 20.0, 'light': 31.83, 'moderate': 20.0}, 'by_resolution': {'heavy': 0.0, 'light': 0.0, 'moderate': 0.0}}                                                                                                                                                                                                                                                                           |
|    3 | nicht geprüft | verbal in the paper; not operationalised here (see FL 2008 déjà-vu indicators)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|    4 | bestätigt     | by access {'unsegmented': {'problem_persistence': 242.2, 'problem_latency': 0.0, 'choice_persistence': 30.1}, 'hierarchical': {'problem_persistence': 201.2, 'problem_latency': 26.3, 'choice_persistence': 28.2}, 'specialized': {'problem_persistence': 80.0, 'problem_latency': 142.7, 'choice_persistence': 41.5}}; by decision {'unsegmented': {'problem_persistence': 108.7, 'problem_latency': 63.4, 'choice_persistence': 24.6}, 'hierarchical': {'problem_persistence': 167.5, 'problem_latency': 61.2, 'choice_persistence': 30.1}, 'specialized': {'problem_persistence': 247.2, 'problem_latency': 44.4, 'choice_persistence': 45.1}} |
|    5 | bestätigt     | mean KY access x decision: {'hierarchical': {'hierarchical': 26.9, 'specialized': 39.0, 'unsegmented': 24.3}, 'specialized': {'hierarchical': 39.2, 'specialized': 72.1, 'unsegmented': 23.9}, 'unsegmented': {'hierarchical': 18.4, 'specialized': 13.2, 'unsegmented': 42.2}}                                                                                                                                                                                                                                                                                                                                                                   |
|    6 | bestätigt     | Tab. 3 port: {('hoch', 'früh (erste 10)'): 0.522, ('hoch', 'spät (letzte 10)'): 0.467, ('niedrig', 'früh (erste 10)'): 0.498, ('niedrig', 'spät (letzte 10)'): 0.269}                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|    7 | bestätigt     | Tab. 4 port: {('hoch', 'früh (erste 5)'): 0.862, ('hoch', 'spät (letzte 5)'): 0.642, ('niedrig', 'früh (erste 5)'): 0.507, ('niedrig', 'spät (letzte 5)'): 0.603}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|    8 | bestätigt     | choice failures by importance: {'oberste 3': 0.135, 'mittlere 4': 0.053, 'unterste 3': 0.115}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |


## FORTRAN port, arithmetic `exact`, initial requirement 0 (1 s, 324 runs)

pooled styles: {'by_resolution': 1215, 'by_oversight': 479, 'by_flight': 1204} of 2898 choices made

docking status: {'Abweichung': 43, 'identisch im Rahmen der Rundung': 31, 'innerhalb Toleranz': 27}

### Deviations

| id                                               | fundstelle    |   publiziert |     port |   abweichung |
|:-------------------------------------------------|:--------------|-------------:|---------:|-------------:|
| CMO_T1_leicht_unsegmentiert                      | Tab. 1, S. 9  |         0.38 |   0.5058 |       0.1258 |
| CMO_T1_leicht_hierarchisch                       | Tab. 1, S. 9  |         0.61 |   0.4971 |      -0.1129 |
| CMO_T1_mittel_alle                               | Tab. 1, S. 9  |         0.3  |   0.4433 |       0.1433 |
| CMO_T1_mittel_unsegmentiert                      | Tab. 1, S. 9  |         0.04 |   0.4107 |       0.3707 |
| CMO_T1_mittel_hierarchisch                       | Tab. 1, S. 9  |         0.27 |   0.3263 |       0.0563 |
| CMO_T1_schwer_alle                               | Tab. 1, S. 9  |         0.36 |   0.2431 |      -0.1169 |
| CMO_T1_schwer_unsegmentiert                      | Tab. 1, S. 9  |         0.35 |   0      |      -0.35   |
| CMO_T1_schwer_spezialisiert                      | Tab. 1, S. 9  |         0.5  |   0.5618 |       0.0618 |
| CMO_T1_alle_unsegmentiert                        | Tab. 1, S. 9  |         0.26 |   0.3108 |       0.0508 |
| CMO_T1_alle_spezialisiert                        | Tab. 1, S. 9  |         0.58 |   0.6126 |       0.0326 |
| CMO_T2_leicht_problemaktivitaet_KT               | Tab. 2, S. 10 |       114.9  | 108.574  |      -6.3259 |
| CMO_T2_leicht_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        19.5  |  18.3241 |      -1.1759 |
| CMO_T2_mittel_problemaktivitaet_KT               | Tab. 2, S. 10 |       204.3  | 191.361  |     -12.9389 |
| CMO_T2_mittel_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        63.8  |  78.2222 |      14.4222 |
| CMO_T2_mittel_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        32.9  |  42.5926 |       9.6926 |
| CMO_T2_mittel_anteil_flight_oversight            | Tab. 2, S. 10 |         0.7  |   0.5567 |      -0.1433 |
| CMO_T2_schwer_problemaktivitaet_KT               | Tab. 2, S. 10 |       211.1  | 224.204  |      13.1037 |
| CMO_T2_schwer_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        76.6  |  65.7222 |     -10.8778 |
| CMO_T2_schwer_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        46.1  |  36.4815 |      -9.6185 |
| CMO_T2_schwer_anteil_flight_oversight            | Tab. 2, S. 10 |         0.64 |   0.7569 |       0.1169 |
| CMO_T4_hoch_frueh                                | Tab. 4, S. 11 |         0.86 |   0.8081 |      -0.0519 |
| CMO_T4_niedrig_frueh                             | Tab. 4, S. 11 |         0.54 |   0.501  |      -0.039  |
| CMO_T5_1110_anteil_resolution                    | Tab. 5, S. 17 |         0.21 |   0.3056 |       0.0956 |
| CMO_T5_1110_problemaktivitaet_KT                 | Tab. 5, S. 17 |       210    | 197.75   |     -12.25   |
| CMO_T5_1110_problemlatenz_KU                     | Tab. 5, S. 17 |        23    |  33.5    |      10.5    |
| CMO_T5_1110_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        58    |  64.5    |       6.5    |
| CMO_T5_0111_problemaktivitaet_KT                 | Tab. 5, S. 17 |        57    |  60.75   |       3.75   |
| CMO_T5_0111_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        66    |  70.5    |       4.5    |
| CMO_T5_1112_anteil_resolution                    | Tab. 5, S. 17 |         0.38 |   0.475  |       0.095  |
| CMO_T5_1112_problemaktivitaet_KT                 | Tab. 5, S. 17 |       210    | 170.25   |     -39.75   |
| CMO_T5_1112_problemlatenz_KU                     | Tab. 5, S. 17 |        25    |  34.75   |       9.75   |
| CMO_T5_2112_anteil_resolution                    | Tab. 5, S. 17 |         0.24 |   0.1515 |      -0.0885 |
| CMO_T5_2112_problemaktivitaet_KT                 | Tab. 5, S. 17 |       248    | 267.5    |      19.5    |
| CMO_T5_2112_problemlatenz_KU                     | Tab. 5, S. 17 |        32    |  19.5    |     -12.5    |
| CMO_T5_2112_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        55    |  59.5    |       4.5    |
| CMO_T5_1111_problemlatenz_KU                     | Tab. 5, S. 17 |        30    |  34      |       4      |
| CMO_T5_1002_anteil_resolution                    | Tab. 5, S. 17 |         0    |   1      |       1      |
| CMO_T5_1002_problemaktivitaet_KT                 | Tab. 5, S. 17 |       310    | 198      |    -112      |
| CMO_T5_1002_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        90    | 190      |     100      |
| CMO_T5_1002_entscheidungszeit_KY                 | Tab. 5, S. 17 |        20    | 100      |      80      |
| CMO_T5_1211_problemaktivitaet_KT                 | Tab. 5, S. 17 |        78    |  82.75   |       4.75   |
| CMO_T5_1211_entscheidungszeit_KY                 | Tab. 5, S. 17 |        39    |  42      |       3      |
| CMO_Text_mittel_nicht_getroffen                  | Text, S. 9    |         1    |   1.0556 |       0.0556 |

### Properties

|   nr | verdict       | evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----:|:--------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|    1 | bestätigt     | cells >= 0.5: [('light', 'all'), ('light', 'unsegmented'), ('light', 'hierarchical'), ('light', 'specialized'), ('moderate', 'specialized'), ('heavy', 'specialized'), ('all', 'specialized')]                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|    2 | teilweise     | means by load {'problem_persistence': [108.6, 191.4, 224.2], 'dm_velocity': [62.0, 78.2, 65.7], 'choice_persistence': [18.3, 42.6, 36.5]}; flight/oversight [0.448, 0.557, 0.757]; unsegmented access x specialized decision: {'choice_persistence': {'heavy': 20.0, 'light': 20.0, 'moderate': 20.0}, 'by_resolution': {'heavy': 0.0, 'light': 0.0, 'moderate': 0.0}}                                                                                                                                                                                                                                                                            |
|    3 | nicht geprüft | verbal in the paper; not operationalised here (see FL 2008 déjà-vu indicators)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|    4 | bestätigt     | by access {'unsegmented': {'problem_persistence': 237.9, 'problem_latency': 0.0, 'choice_persistence': 26.8}, 'hierarchical': {'problem_persistence': 204.5, 'problem_latency': 25.9, 'choice_persistence': 28.2}, 'specialized': {'problem_persistence': 81.8, 'problem_latency': 142.3, 'choice_persistence': 42.4}}; by decision {'unsegmented': {'problem_persistence': 112.4, 'problem_latency': 63.4, 'choice_persistence': 24.7}, 'hierarchical': {'problem_persistence': 163.6, 'problem_latency': 60.8, 'choice_persistence': 29.3}, 'specialized': {'problem_persistence': 248.1, 'problem_latency': 44.0, 'choice_persistence': 43.4}} |
|    5 | bestätigt     | mean KY access x decision: {'hierarchical': {'hierarchical': 27.9, 'specialized': 39.8, 'unsegmented': 20.3}, 'specialized': {'hierarchical': 38.2, 'specialized': 72.1, 'unsegmented': 20.0}, 'unsegmented': {'hierarchical': 18.7, 'specialized': 15.3, 'unsegmented': 40.0}}                                                                                                                                                                                                                                                                                                                                                                   |
|    6 | bestätigt     | Tab. 3 port: {('hoch', 'früh (erste 10)'): 0.481, ('hoch', 'spät (letzte 10)'): 0.45, ('niedrig', 'früh (erste 10)'): 0.478, ('niedrig', 'spät (letzte 10)'): 0.25}                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|    7 | bestätigt     | Tab. 4 port: {('hoch', 'früh (erste 5)'): 0.808, ('hoch', 'spät (letzte 5)'): 0.645, ('niedrig', 'früh (erste 5)'): 0.501, ('niedrig', 'spät (letzte 5)'): 0.598}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|    8 | bestätigt     | choice failures by importance: {'oberste 3': 0.15, 'mittlere 4': 0.04, 'unterste 3': 0.122}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |


## FORTRAN port, arithmetic `exact`, initial requirement 1.0 (1 s, 324 runs)

pooled styles: {'by_resolution': 1325, 'by_oversight': 605, 'by_flight': 983} of 2913 choices made

docking status: {'identisch im Rahmen der Rundung': 42, 'Abweichung': 30, 'innerhalb Toleranz': 29}

### Deviations

| id                                               | fundstelle    |   publiziert |     port |   abweichung |
|:-------------------------------------------------|:--------------|-------------:|---------:|-------------:|
| CMO_T1_leicht_unsegmentiert                      | Tab. 1, S. 9  |         0.38 |   0.4561 |       0.0761 |
| CMO_T1_leicht_hierarchisch                       | Tab. 1, S. 9  |         0.61 |   0.4912 |      -0.1188 |
| CMO_T1_mittel_alle                               | Tab. 1, S. 9  |         0.3  |   0.4368 |       0.1368 |
| CMO_T1_mittel_unsegmentiert                      | Tab. 1, S. 9  |         0.04 |   0.4048 |       0.3648 |
| CMO_T1_mittel_hierarchisch                       | Tab. 1, S. 9  |         0.27 |   0.3166 |       0.0466 |
| CMO_T1_schwer_unsegmentiert                      | Tab. 1, S. 9  |         0.35 |   0.381  |       0.031  |
| CMO_T1_schwer_spezialisiert                      | Tab. 1, S. 9  |         0.5  |   0.5634 |       0.0634 |
| CMO_T1_alle_alle                                 | Tab. 1, S. 9  |         0.4  |   0.4549 |       0.0549 |
| CMO_T1_alle_unsegmentiert                        | Tab. 1, S. 9  |         0.26 |   0.4142 |       0.1542 |
| CMO_T1_alle_spezialisiert                        | Tab. 1, S. 9  |         0.58 |   0.6126 |       0.0326 |
| CMO_T2_mittel_problemaktivitaet_KT               | Tab. 2, S. 10 |       204.3  | 191.352  |     -12.9481 |
| CMO_T2_mittel_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        63.8  |  78.1111 |      14.3111 |
| CMO_T2_mittel_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        32.9  |  42.6019 |       9.7019 |
| CMO_T2_mittel_anteil_flight_oversight            | Tab. 2, S. 10 |         0.7  |   0.5632 |      -0.1368 |
| CMO_T3_hoch_frueh                                | Tab. 3, S. 10 |         0.46 |   0.5167 |       0.0567 |
| CMO_T4_niedrig_frueh                             | Tab. 4, S. 11 |         0.54 |   0.4878 |      -0.0522 |
| CMO_T5_1110_anteil_resolution                    | Tab. 5, S. 17 |         0.21 |   0.2432 |       0.0332 |
| CMO_T5_1110_problemlatenz_KU                     | Tab. 5, S. 17 |        23    |  30      |       7      |
| CMO_T5_1110_entscheidungszeit_KY                 | Tab. 5, S. 17 |        34    |  31.25   |      -2.75   |
| CMO_T5_1112_anteil_resolution                    | Tab. 5, S. 17 |         0.38 |   0.45   |       0.07   |
| CMO_T5_1112_problemlatenz_KU                     | Tab. 5, S. 17 |        25    |  17      |      -8      |
| CMO_T5_1111_anteil_resolution                    | Tab. 5, S. 17 |         0.31 |   0.35   |       0.04   |
| CMO_T5_1111_problemaktivitaet_KT                 | Tab. 5, S. 17 |       200    | 184.75   |     -15.25   |
| CMO_T5_1111_problemlatenz_KU                     | Tab. 5, S. 17 |        30    |  25.5    |      -4.5    |
| CMO_T5_1111_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        58    |  65.5    |       7.5    |
| CMO_T5_1002_anteil_resolution                    | Tab. 5, S. 17 |         0    |   1      |       1      |
| CMO_T5_1002_problemaktivitaet_KT                 | Tab. 5, S. 17 |       310    | 198      |    -112      |
| CMO_T5_1002_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        90    | 190      |     100      |
| CMO_T5_1002_entscheidungszeit_KY                 | Tab. 5, S. 17 |        20    | 100      |      80      |
| CMO_Text_mittel_ungeloest                        | Text, S. 9    |        12.3  |  11.4136 |      -0.8864 |

### Properties

|   nr | verdict       | evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----:|:--------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|    1 | abweichend    | cells >= 0.5: [('light', 'all'), ('light', 'specialized'), ('moderate', 'specialized'), ('heavy', 'specialized'), ('all', 'specialized')]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|    2 | teilweise     | means by load {'problem_persistence': [111.9, 191.4, 208.2], 'dm_velocity': [61.2, 78.1, 76.9], 'choice_persistence': [19.2, 42.6, 46.1]}; flight/oversight [0.466, 0.563, 0.614]; unsegmented access x specialized decision: {'choice_persistence': {'heavy': 20.0, 'light': 27.67, 'moderate': 20.0}, 'by_resolution': {'heavy': 0.0, 'light': 0.0, 'moderate': 0.0}}                                                                                                                                                                                                                                                                           |
|    3 | nicht geprüft | verbal in the paper; not operationalised here (see FL 2008 déjà-vu indicators)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|    4 | bestätigt     | by access {'unsegmented': {'problem_persistence': 227.6, 'problem_latency': 0.0, 'choice_persistence': 37.9}, 'hierarchical': {'problem_persistence': 202.2, 'problem_latency': 26.7, 'choice_persistence': 27.7}, 'specialized': {'problem_persistence': 81.6, 'problem_latency': 142.7, 'choice_persistence': 42.3}}; by decision {'unsegmented': {'problem_persistence': 100.2, 'problem_latency': 63.4, 'choice_persistence': 33.5}, 'hierarchical': {'problem_persistence': 164.0, 'problem_latency': 61.5, 'choice_persistence': 29.9}, 'specialized': {'problem_persistence': 247.2, 'problem_latency': 44.5, 'choice_persistence': 44.4}} |
|    5 | bestätigt     | mean KY access x decision: {'hierarchical': {'hierarchical': 26.0, 'specialized': 39.3, 'unsegmented': 24.4}, 'specialized': {'hierarchical': 38.5, 'specialized': 72.1, 'unsegmented': 22.6}, 'unsegmented': {'hierarchical': 18.6, 'specialized': 15.3, 'unsegmented': 66.7}}                                                                                                                                                                                                                                                                                                                                                                   |
|    6 | bestätigt     | Tab. 3 port: {('hoch', 'früh (erste 10)'): 0.517, ('hoch', 'spät (letzte 10)'): 0.463, ('niedrig', 'früh (erste 10)'): 0.5, ('niedrig', 'spät (letzte 10)'): 0.256}                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|    7 | bestätigt     | Tab. 4 port: {('hoch', 'früh (erste 5)'): 0.854, ('hoch', 'spät (letzte 5)'): 0.65, ('niedrig', 'früh (erste 5)'): 0.488, ('niedrig', 'spät (letzte 5)'): 0.598}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|    8 | bestätigt     | choice failures by importance: {'oberste 3': 0.135, 'mittlere 4': 0.051, 'unterste 3': 0.117}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |


## Comparison of the FORTRAN configurations (first: `exact`)

| configuration   |   identisch im Rahmen der Rundung |   innerhalb Toleranz |   Abweichung |   situations differing from the first |   resolution |   oversight |   flight |   choices made |
|:----------------|----------------------------------:|---------------------:|-------------:|--------------------------------------:|-------------:|------------:|---------:|---------------:|
| exact           |                                47 |                   33 |           21 |                                     0 |       0.414  |      0.2185 |   0.3675 |           2901 |
| exact__xerc0    |                                31 |                   27 |           43 |                                   178 |       0.4193 |      0.1653 |   0.4155 |           2898 |
| exact__xerc1.0  |                                42 |                   29 |           30 |                                    74 |       0.4549 |      0.2077 |   0.3375 |           2913 |

### Published values whose status is not the same in every configuration (54)

| id                                               | fundstelle    |   publiziert |   port exact |   port exact__xerc0 |   port exact__xerc1.0 | status exact                    | status exact__xerc0             | status exact__xerc1.0           |
|:-------------------------------------------------|:--------------|-------------:|-------------:|--------------------:|----------------------:|:--------------------------------|:--------------------------------|:--------------------------------|
| CMO_T1_leicht_alle                               | Tab. 1, S. 9  |         0.55 |       0.5269 |              0.5523 |                0.5337 | innerhalb Toleranz              | identisch im Rahmen der Rundung | innerhalb Toleranz              |
| CMO_T1_mittel_alle                               | Tab. 1, S. 9  |         0.3  |       0.3233 |              0.4433 |                0.4368 | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T1_mittel_unsegmentiert                      | Tab. 1, S. 9  |         0.04 |       0.0556 |              0.4107 |                0.4048 | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T1_schwer_alle                               | Tab. 1, S. 9  |         0.36 |       0.3834 |              0.2431 |                0.386  | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T1_schwer_unsegmentiert                      | Tab. 1, S. 9  |         0.35 |       0.375  |              0      |                0.381  | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T1_alle_alle                                 | Tab. 1, S. 9  |         0.4  |       0.414  |              0.4193 |                0.4549 | innerhalb Toleranz              | innerhalb Toleranz              | Abweichung                      |
| CMO_T2_leicht_problemaktivitaet_KT               | Tab. 2, S. 10 |       114.9  |     114.343  |            108.574  |              111.889  | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T2_leicht_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        60.9  |      61.0463 |             62.0093 |               61.1944 | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T2_leicht_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        19.5  |      19.537  |             18.3241 |               19.1574 | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_T2_leicht_anteil_flight_oversight            | Tab. 2, S. 10 |         0.45 |       0.4731 |              0.4477 |                0.4663 | innerhalb Toleranz              | identisch im Rahmen der Rundung | innerhalb Toleranz              |
| CMO_T2_mittel_problemaktivitaet_KT               | Tab. 2, S. 10 |       204.3  |     200.222  |            191.361  |              191.352  | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T2_mittel_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        63.8  |      66.0463 |             78.2222 |               78.1111 | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T2_mittel_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        32.9  |      34.1389 |             42.5926 |               42.6019 | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T2_mittel_anteil_flight_oversight            | Tab. 2, S. 10 |         0.7  |       0.6767 |              0.5567 |                0.5632 | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T2_schwer_problemaktivitaet_KT               | Tab. 2, S. 10 |       211.1  |     208.833  |            224.204  |              208.204  | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T2_schwer_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        76.6  |      76.9074 |             65.7222 |               76.8704 | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_T2_schwer_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        46.1  |      46.0926 |             36.4815 |               46.0926 | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_T2_schwer_anteil_flight_oversight            | Tab. 2, S. 10 |         0.64 |       0.6166 |              0.7569 |                0.614  | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T3_hoch_frueh                                | Tab. 3, S. 10 |         0.46 |       0.5222 |              0.4815 |                0.5167 | Abweichung                      | innerhalb Toleranz              | Abweichung                      |
| CMO_T3_niedrig_frueh                             | Tab. 3, S. 10 |         0.48 |       0.4981 |              0.4778 |                0.5    | innerhalb Toleranz              | identisch im Rahmen der Rundung | innerhalb Toleranz              |
| CMO_T3_niedrig_spaet                             | Tab. 3, S. 10 |         0.25 |       0.2685 |              0.25   |                0.2556 | innerhalb Toleranz              | identisch im Rahmen der Rundung | innerhalb Toleranz              |
| CMO_T4_hoch_frueh                                | Tab. 4, S. 11 |         0.86 |       0.8622 |              0.8081 |                0.8538 | identisch im Rahmen der Rundung | Abweichung                      | innerhalb Toleranz              |
| CMO_T4_hoch_spaet                                | Tab. 4, S. 11 |         0.65 |       0.6418 |              0.6452 |                0.6498 | innerhalb Toleranz              | identisch im Rahmen der Rundung | identisch im Rahmen der Rundung |
| CMO_Wahlausfall_oberste_3                        | Text, S. 11   |         0.14 |       0.1352 |              0.15   |                0.1352 | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_Wahlausfall_mittlere_4                       | Text, S. 11   |         0.05 |       0.0528 |              0.0403 |                0.0514 | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_Wahlausfall_unterste_3                       | Text, S. 11   |         0.12 |       0.1148 |              0.1222 |                0.1167 | innerhalb Toleranz              | identisch im Rahmen der Rundung | identisch im Rahmen der Rundung |
| CMO_T5_1110_anteil_resolution                    | Tab. 5, S. 17 |         0.21 |       0.2105 |              0.3056 |                0.2432 | identisch im Rahmen der Rundung | Abweichung                      | Abweichung                      |
| CMO_T5_1110_problemaktivitaet_KT                 | Tab. 5, S. 17 |       210    |     208.25   |            197.75   |              204      | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_1110_problemlatenz_KU                     | Tab. 5, S. 17 |        23    |      22.25   |             33.5    |               30      | innerhalb Toleranz              | Abweichung                      | Abweichung                      |
| CMO_T5_1110_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        58    |      57.5    |             64.5    |               58.75   | identisch im Rahmen der Rundung | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_1110_entscheidungszeit_KY                 | Tab. 5, S. 17 |        34    |      33.75   |             35.25   |               31.25   | identisch im Rahmen der Rundung | innerhalb Toleranz              | Abweichung                      |
| CMO_T5_0111_anteil_resolution                    | Tab. 5, S. 17 |         0.65 |       0.65   |              0.625  |                0.65   | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_0111_problemaktivitaet_KT                 | Tab. 5, S. 17 |        57    |      57      |             60.75   |               57      | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_T5_0111_problemlatenz_KU                     | Tab. 5, S. 17 |        60    |      59.5    |             58      |               59.5    | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_0111_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        66    |      65.5    |             70.5    |               64.5    | identisch im Rahmen der Rundung | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_0111_entscheidungszeit_KY                 | Tab. 5, S. 17 |        14    |      13.75   |             15.25   |               14      | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_1112_problemaktivitaet_KT                 | Tab. 5, S. 17 |       210    |     182.75   |            170.25   |              200.75   | Abweichung                      | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_1112_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        66    |      74.25   |             65.75   |               68.75   | Abweichung                      | identisch im Rahmen der Rundung | innerhalb Toleranz              |
| CMO_T5_1112_entscheidungszeit_KY                 | Tab. 5, S. 17 |        31    |      35.5    |             29.5    |               32.25   | Abweichung                      | innerhalb Toleranz              | innerhalb Toleranz              |
| CMO_T5_2112_anteil_resolution                    | Tab. 5, S. 17 |         0.24 |       0.2353 |              0.1515 |                0.2424 | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_T5_2112_problemaktivitaet_KT                 | Tab. 5, S. 17 |       248    |     246.5    |            267.5    |              246.5    | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_2112_problemlatenz_KU                     | Tab. 5, S. 17 |        32    |      31.25   |             19.5    |               31.25   | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_2112_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        55    |      54.75   |             59.5    |               53.5    | identisch im Rahmen der Rundung | Abweichung                      | innerhalb Toleranz              |
| CMO_T5_2112_entscheidungszeit_KY                 | Tab. 5, S. 17 |        38    |      37.75   |             39      |               37.75   | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_1111_anteil_resolution                    | Tab. 5, S. 17 |         0.31 |       0.35   |              0.3158 |                0.35   | Abweichung                      | innerhalb Toleranz              | Abweichung                      |
| CMO_T5_1111_problemaktivitaet_KT                 | Tab. 5, S. 17 |       200    |     184.75   |            206.75   |              184.75   | Abweichung                      | innerhalb Toleranz              | Abweichung                      |
| CMO_T5_1111_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        58    |      65.5    |             60.5    |               65.5    | Abweichung                      | innerhalb Toleranz              | Abweichung                      |
| CMO_T5_1111_entscheidungszeit_KY                 | Tab. 5, S. 17 |        28    |      27.5    |             29.25   |               27.5    | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_2211_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        73    |      72.5    |             75.25   |               72.5    | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_1211_problemaktivitaet_KT                 | Tab. 5, S. 17 |        78    |      78.5    |             82.75   |               78.5    | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_T5_1211_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        76    |      76.5    |             77.75   |               76.5    | identisch im Rahmen der Rundung | innerhalb Toleranz              | identisch im Rahmen der Rundung |
| CMO_T5_1211_entscheidungszeit_KY                 | Tab. 5, S. 17 |        39    |      39.75   |             42      |               39.75   | innerhalb Toleranz              | Abweichung                      | innerhalb Toleranz              |
| CMO_Text_mittel_nicht_getroffen                  | Text, S. 9    |         1    |       1.0463 |              1.0556 |                1.0093 | identisch im Rahmen der Rundung | Abweichung                      | identisch im Rahmen der Rundung |
| CMO_Text_mittel_ungeloest                        | Text, S. 9    |        12.3  |      12.0093 |             12.1852 |               11.4136 | identisch im Rahmen der Rundung | identisch im Rahmen der Rundung | Abweichung                      |


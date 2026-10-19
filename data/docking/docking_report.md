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


## FORTRAN port, arithmetic `ibm360` (4 s, 324 runs)

pooled styles: {'by_resolution': 1194, 'by_oversight': 631, 'by_flight': 1030} of 2855 choices made

docking status: {'identisch im Rahmen der Rundung': 47, 'Abweichung': 30, 'innerhalb Toleranz': 24}

### Deviations

| id                                               | fundstelle    |   publiziert |     port |   abweichung |
|:-------------------------------------------------|:--------------|-------------:|---------:|-------------:|
| CMO_T1_leicht_unsegmentiert                      | Tab. 1, S. 9  |         0.38 |   0.4302 |       0.0502 |
| CMO_T1_leicht_hierarchisch                       | Tab. 1, S. 9  |         0.61 |   0.4911 |      -0.1189 |
| CMO_T1_mittel_alle                               | Tab. 1, S. 9  |         0.3  |   0.3886 |       0.0886 |
| CMO_T1_mittel_unsegmentiert                      | Tab. 1, S. 9  |         0.04 |   0.2711 |       0.2311 |
| CMO_T1_mittel_hierarchisch                       | Tab. 1, S. 9  |         0.27 |   0.3084 |       0.0384 |
| CMO_T1_schwer_alle                               | Tab. 1, S. 9  |         0.36 |   0.3257 |      -0.0343 |
| CMO_T1_schwer_unsegmentiert                      | Tab. 1, S. 9  |         0.35 |   0.2838 |      -0.0662 |
| CMO_T1_schwer_hierarchisch                       | Tab. 1, S. 9  |         0.23 |   0.1763 |      -0.0537 |
| CMO_T1_schwer_spezialisiert                      | Tab. 1, S. 9  |         0.5  |   0.5517 |       0.0517 |
| CMO_T1_alle_unsegmentiert                        | Tab. 1, S. 9  |         0.26 |   0.3313 |       0.0713 |
| CMO_T1_alle_hierarchisch                         | Tab. 1, S. 9  |         0.37 |   0.3293 |      -0.0407 |
| CMO_T2_mittel_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        63.8  |  73.3426 |       9.5426 |
| CMO_T2_mittel_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        32.9  |  39.7037 |       6.8037 |
| CMO_T2_mittel_anteil_flight_oversight            | Tab. 2, S. 10 |         0.7  |   0.6114 |      -0.0886 |
| CMO_T2_schwer_problemaktivitaet_KT               | Tab. 2, S. 10 |       211.1  | 221.759  |      10.6593 |
| CMO_T2_schwer_aktivitaet_entscheidungstraeger_KX | Tab. 2, S. 10 |        76.6  |  69.287  |      -7.313  |
| CMO_T2_schwer_entscheidungsschwierigkeit_KY      | Tab. 2, S. 10 |        46.1  |  50.8889 |       4.7889 |
| CMO_T2_schwer_anteil_flight_oversight            | Tab. 2, S. 10 |         0.64 |   0.6743 |       0.0343 |
| CMO_T3_hoch_frueh                                | Tab. 3, S. 10 |         0.46 |   0.5074 |       0.0474 |
| CMO_T3_niedrig_frueh                             | Tab. 3, S. 10 |         0.48 |   0.4463 |      -0.0337 |
| CMO_T5_1112_anteil_resolution                    | Tab. 5, S. 17 |         0.38 |   0.575  |       0.195  |
| CMO_T5_1112_problemaktivitaet_KT                 | Tab. 5, S. 17 |       210    | 182.75   |     -27.25   |
| CMO_T5_1112_problemlatenz_KU                     | Tab. 5, S. 17 |        25    |  17      |      -8      |
| CMO_T5_1112_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        66    |  74.25   |       8.25   |
| CMO_T5_1112_entscheidungszeit_KY                 | Tab. 5, S. 17 |        31    |  35.5    |       4.5    |
| CMO_T5_1002_anteil_resolution                    | Tab. 5, S. 17 |         0    |   1      |       1      |
| CMO_T5_1002_problemaktivitaet_KT                 | Tab. 5, S. 17 |       310    | 198      |    -112      |
| CMO_T5_1002_aktivitaet_entscheidungstraeger_KX   | Tab. 5, S. 17 |        90    | 190      |     100      |
| CMO_T5_1002_entscheidungszeit_KY                 | Tab. 5, S. 17 |        20    | 100      |      80      |
| CMO_Text_mittel_nicht_getroffen                  | Text, S. 9    |         1    |   1.1883 |       0.1883 |

### Properties

|   nr | verdict       | evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----:|:--------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|    1 | abweichend    | cells >= 0.5: [('light', 'all'), ('light', 'specialized'), ('moderate', 'specialized'), ('heavy', 'specialized'), ('all', 'specialized')]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|    2 | teilweise     | means by load {'problem_persistence': [114.9, 197.9, 221.8], 'dm_velocity': [60.8, 73.3, 69.3], 'choice_persistence': [19.6, 39.7, 50.9]}; flight/oversight [0.475, 0.611, 0.674]; unsegmented access x specialized decision: {'choice_persistence': {'heavy': 20.0, 'light': 31.83, 'moderate': 20.0}, 'by_resolution': {'heavy': 0.0, 'light': 0.0, 'moderate': 0.0}}                                                                                                                                                                                                                                                                           |
|    3 | nicht geprüft | verbal in the paper; not operationalised here (see FL 2008 déjà-vu indicators)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|    4 | teilweise     | by access {'unsegmented': {'problem_persistence': 242.2, 'problem_latency': 0.0, 'choice_persistence': 37.4}, 'hierarchical': {'problem_persistence': 208.2, 'problem_latency': 24.0, 'choice_persistence': 29.1}, 'specialized': {'problem_persistence': 84.2, 'problem_latency': 142.0, 'choice_persistence': 43.7}}; by decision {'unsegmented': {'problem_persistence': 117.1, 'problem_latency': 60.5, 'choice_persistence': 34.9}, 'hierarchical': {'problem_persistence': 170.0, 'problem_latency': 61.2, 'choice_persistence': 30.1}, 'specialized': {'problem_persistence': 247.4, 'problem_latency': 44.4, 'choice_persistence': 45.1}} |
|    5 | bestätigt     | mean KY access x decision: {'hierarchical': {'hierarchical': 26.9, 'specialized': 39.6, 'unsegmented': 23.7}, 'specialized': {'hierarchical': 39.2, 'specialized': 72.3, 'unsegmented': 23.9}, 'unsegmented': {'hierarchical': 21.2, 'specialized': 19.2, 'unsegmented': 64.4}}                                                                                                                                                                                                                                                                                                                                                                   |
|    6 | bestätigt     | Tab. 3 port: {('hoch', 'früh (erste 10)'): 0.507, ('hoch', 'spät (letzte 10)'): 0.444, ('niedrig', 'früh (erste 10)'): 0.446, ('niedrig', 'spät (letzte 10)'): 0.226}                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|    7 | bestätigt     | Tab. 4 port: {('hoch', 'früh (erste 5)'): 0.865, ('hoch', 'spät (letzte 5)'): 0.657, ('niedrig', 'früh (erste 5)'): 0.544, ('niedrig', 'spät (letzte 5)'): 0.618}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|    8 | bestätigt     | choice failures by importance: {'oberste 3': 0.135, 'mittlere 4': 0.054, 'unterste 3': 0.128}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |


## NetLogo port (50000 ticks, 30 seeds, 7415 s)

| experiment                 |   num_resolutions |   num_oversights |   share_resolutions |   share_resolutions_sd |   n_runs |
|:---------------------------|------------------:|-----------------:|--------------------:|-----------------------:|---------:|
| Organized Anarchy          |            96.3   |         2149.53  |               0.038 |                 0.0114 |       30 |
| Organized Anarchy P        |          1137.03  |         6048.03  |               0.158 |                 0.0134 |       30 |
| Organized Anarchy BP       |           851.933 |         3799.27  |               0.183 |                 0.0075 |       30 |
| Organized Anarchy P+BP     |          1188.27  |         6259.37  |               0.16  |                 0.0061 |       30 |
| Competent Hierarchy        |             4.3   |          383.633 |               0.011 |                 0.0084 |       30 |
| Competent Hierarchy P      |            22     |          966.633 |               0.024 |                 0.0115 |       30 |
| Competent Hierarchy BP     |            41.067 |          473.567 |               0.072 |                 0.0406 |       30 |
| Competent Hierarchy P+BP   |            78.133 |         1614.6   |               0.045 |                 0.0137 |       30 |
| Incompetent Hierarchy      |            24.033 |         1148.03  |               0.019 |                 0.0068 |       30 |
| Incompetent Hierarchy P    |            37.7   |         1601.4   |               0.023 |                 0.0076 |       30 |
| Incompetent Hierarchy BP   |           188.7   |         1093.83  |               0.143 |                 0.038  |       30 |
| Incompetent Hierarchy P+BP |            84.767 |         1704.8   |               0.048 |                 0.0195 |       30 |

### Properties of the current model (info tab)

|   nr | verdict   | property                                                                          | evidence                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----:|:----------|:----------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|    1 | bestätigt | most decisions by oversight (every experiment)                                    | {'Organized Anarchy': 0.0429, 'Organized Anarchy P': 0.1582, 'Organized Anarchy BP': 0.1832, 'Organized Anarchy P+BP': 0.1595, 'Competent Hierarchy': 0.0111, 'Competent Hierarchy P': 0.0223, 'Competent Hierarchy BP': 0.0798, 'Competent Hierarchy P+BP': 0.0462, 'Incompetent Hierarchy': 0.0205, 'Incompetent Hierarchy P': 0.023, 'Incompetent Hierarchy BP': 0.1471, 'Incompetent Hierarchy P+BP': 0.0474} |
|    2 | bestätigt | flights raise the resolution share                                                | {'Organized Anarchy': {'none': 0.0429, ' P': 0.1582, ' BP': 0.1832, ' P+BP': 0.1595}, 'Competent Hierarchy': {'none': 0.0111, ' P': 0.0223, ' BP': 0.0798, ' P+BP': 0.0462}, 'Incompetent Hierarchy': {'none': 0.0205, ' P': 0.023, ' BP': 0.1471, ' P+BP': 0.0474}}                                                                                                                                              |
|    3 | bestätigt | organized anarchy out-resolves both hierarchies (anarchy, competent, incompetent) | {'none': (0.0429, 0.0111, 0.0205), ' P': (0.1582, 0.0223, 0.023), ' BP': (0.1832, 0.0798, 0.1471), ' P+BP': (0.1595, 0.0462, 0.0474)}                                                                                                                                                                                                                                                                             |
|    4 | bestätigt | incompetent hierarchy at least about as efficient as competent (ratio >= 0.9)     | {'none': (0.0429, 0.0111, 0.0205), ' P': (0.1582, 0.0223, 0.023), ' BP': (0.1832, 0.0798, 0.1471), ' P+BP': (0.1595, 0.0462, 0.0474)}                                                                                                                                                                                                                                                                             |

Fioretti & Lomi (2008) values in the workbook: 168 (different model; qualitative comparison only, see sheet FL_Befunde). Oversight dominance (FL Nr. 1) holds for the port: see property 1.

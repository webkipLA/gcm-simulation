# NetLogo transfer check (ranked_50000t_10s)

8 conditions, seeds 0 to 9, 50000 ticks, flights on, availability and access unrestricted, roles onto abilities: ranked.

Chi-square over all conditions (resolutions vs. oversights): chi2 = 6684.0, df = 7, p = 0, V = 0.154

## Means per condition

| condition                             |   share_resolutions |   decisions |   num_resolutions |   num_oversights |   flights |   ave_duration_blocked |   resolution_share_L1 |   resolution_share_L2 |   decisions_L1 |   decisions_L2 |
|:--------------------------------------|--------------------:|------------:|------------------:|-----------------:|----------:|-----------------------:|----------------------:|----------------------:|---------------:|---------------:|
| rule: organized anarchy               |               0.158 |      7464.3 |            1178.8 |           6285.5 |    3923.4 |                 14.035 |                 0.15  |                 0.159 |          588.3 |         6876   |
| rule: competent hierarchy             |               0.067 |      1733.3 |             105.7 |           1627.6 |    1118.9 |                447.793 |                 0.037 |                 0.078 |          260.7 |         1472.6 |
| rule: incompetent hierarchy           |               0.052 |      3024.8 |             159.1 |           2865.7 |     629.2 |                297.035 |                 0.053 |                 0.056 |          125.1 |         2899.7 |
| target: hierarchical 6x5              |               0.184 |      5106.3 |             940.1 |           4166.2 |    3096.2 |                 19.579 |                 0.154 |                 0.185 |           99.2 |         5007.1 |
| target: specialized 6x5               |               0.026 |      1318.7 |              33.7 |           1285   |     519.9 |                473.806 |                 0.02  |                 0.027 |           76.7 |         1242   |
| gemini-3.5-flash-lite: strong_power   |               0.079 |      1417.2 |             105.3 |           1311.9 |     487.7 |                424.415 |                 0.081 |                 0.079 |           64.5 |         1352.7 |
| gemini-3.5-flash-lite: moderate_power |               0.052 |       792.5 |              40   |            752.5 |     251.8 |                962.212 |                 0.12  |                 0.051 |           27   |          765.5 |
| gemini-3.5-flash-lite: weak_power     |               0.158 |      7464.3 |            1178.8 |           6285.5 |    3923.4 |                 14.035 |                 0.15  |                 0.159 |          588.3 |         6876   |

## Styles (pooled)

| condition                             |   num_resolutions |   num_oversights |   num_resolutions_share |   num_oversights_share |
|:--------------------------------------|------------------:|-----------------:|------------------------:|-----------------------:|
| rule: organized anarchy               |             11788 |            62855 |                   0.158 |                  0.842 |
| rule: competent hierarchy             |              1057 |            16276 |                   0.061 |                  0.939 |
| rule: incompetent hierarchy           |              1591 |            28657 |                   0.053 |                  0.947 |
| target: hierarchical 6x5              |              9401 |            41662 |                   0.184 |                  0.816 |
| target: specialized 6x5               |               337 |            12850 |                   0.026 |                  0.974 |
| gemini-3.5-flash-lite: strong_power   |              1053 |            13119 |                   0.074 |                  0.926 |
| gemini-3.5-flash-lite: moderate_power |               400 |             7525 |                   0.05  |                  0.95  |
| gemini-3.5-flash-lite: weak_power     |             11788 |            62855 |                   0.158 |                  0.842 |

## Tests (paired by seed; Wilcoxon; Holm over all rows)

| condition                             | reference                | metric               |      mean |   baseline_mean |   difference |   diff_ci_low |   diff_ci_high |   p_value |   p_holm |
|:--------------------------------------|:-------------------------|:---------------------|----------:|----------------:|-------------:|--------------:|---------------:|----------:|---------:|
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | share_resolutions    |    0.0787 |          0.1579 |      -0.0792 |       -0.0933 |        -0.0653 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | decisions            | 1417.2    |       7464.3    |   -6047.1    |    -6283.55   |     -5784.4    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | num_resolutions      |  105.3    |       1178.8    |   -1073.5    |    -1100.5    |     -1044.8    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | num_oversights       | 1311.9    |       6285.5    |   -4973.6    |    -5204.73   |     -4705.52   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | flights              |  487.7    |       3923.4    |   -3435.7    |    -3588.32   |     -3241.39   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | ave_duration_blocked |  424.415  |         14.0352 |     410.38   |      202.78   |       743.444  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | resolution_share_L1  |    0.0808 |          0.15   |      -0.0692 |       -0.0974 |        -0.0355 |    0.0098 |   0.1855 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | resolution_share_L2  |    0.0786 |          0.1586 |      -0.08   |       -0.0934 |        -0.0665 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | decisions_L1         |   64.5    |        588.3    |    -523.8    |     -542.003  |      -505.697  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | rule: organized anarchy  | decisions_L2         | 1352.7    |       6876      |   -5523.3    |    -5756.62   |     -5256.34   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | share_resolutions    |    0.0787 |          0.1841 |      -0.1054 |       -0.1177 |        -0.0939 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | decisions            | 1417.2    |       5106.3    |   -3689.1    |    -3925.21   |     -3452.99   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | num_resolutions      |  105.3    |        940.1    |    -834.8    |     -861.5    |      -806.587  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | num_oversights       | 1311.9    |       4166.2    |   -2854.3    |    -3094.72   |     -2609.39   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | flights              |  487.7    |       3096.2    |   -2608.5    |    -2738.21   |     -2470.7    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | ave_duration_blocked |  424.415  |         19.5788 |     404.836  |      197.884  |       737.704  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | resolution_share_L1  |    0.0808 |          0.1545 |      -0.0736 |       -0.0987 |        -0.0477 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | resolution_share_L2  |    0.0786 |          0.1847 |      -0.106  |       -0.1184 |        -0.0946 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | decisions_L1         |   64.5    |         99.2    |     -34.7    |      -43.6    |       -24.1    |    0.0039 |   0.1758 |
| gemini-3.5-flash-lite: strong_power   | target: hierarchical 6x5 | decisions_L2         | 1352.7    |       5007.1    |   -3654.4    |    -3885.2    |     -3425.59   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | share_resolutions    |    0.0518 |          0.1579 |      -0.1062 |       -0.1139 |        -0.0989 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | decisions            |  792.5    |       7464.3    |   -6671.8    |    -6785.01   |     -6542.98   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | num_resolutions      |   40      |       1178.8    |   -1138.8    |    -1158      |     -1121.4    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | num_oversights       |  752.5    |       6285.5    |   -5533      |    -5639.01   |     -5411.5    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | flights              |  251.8    |       3923.4    |   -3671.6    |    -3830.92   |     -3505.87   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | ave_duration_blocked |  962.212  |         14.0352 |     948.177  |      694.555  |      1218.09   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | resolution_share_L1  |    0.1202 |          0.15   |      -0.0299 |       -0.0762 |         0.0279 |    0.1602 |   1      |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | resolution_share_L2  |    0.0505 |          0.1586 |      -0.1081 |       -0.1167 |        -0.1001 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | decisions_L1         |   27      |        588.3    |    -561.3    |     -588.3    |      -533.295  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | rule: organized anarchy  | decisions_L2         |  765.5    |       6876      |   -6110.5    |    -6221.41   |     -5986.48   |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | share_resolutions    |    0.0518 |          0.026  |       0.0258 |        0.0122 |         0.0389 |    0.0098 |   0.1855 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | decisions            |  792.5    |       1318.7    |    -526.2    |     -663.2    |      -379.877  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | num_resolutions      |   40      |         33.7    |       6.3    |      -10.3025 |        20.6    |    0.2148 |   1      |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | num_oversights       |  752.5    |       1285      |    -532.5    |     -673.67   |      -383.683  |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | flights              |  251.8    |        519.9    |    -268.1    |     -410.1    |      -125.69   |    0.0137 |   0.2324 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | ave_duration_blocked |  962.212  |        473.806  |     488.406  |       65.8095 |       895.815  |    0.0645 |   0.9023 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | resolution_share_L1  |    0.1202 |          0.0201 |       0.1    |        0.0456 |         0.1642 |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | resolution_share_L2  |    0.0505 |          0.0267 |       0.0238 |        0.0099 |         0.0373 |    0.0137 |   0.2324 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | decisions_L1         |   27      |         76.7    |     -49.7    |      -63.5025 |       -34.8    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: moderate_power | target: specialized 6x5  | decisions_L2         |  765.5    |       1242      |    -476.5    |     -613.905  |      -333.4    |    0.002  |   0.1758 |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | share_resolutions    |    0.1579 |          0.1579 |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | decisions            | 7464.3    |       7464.3    |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | num_resolutions      | 1178.8    |       1178.8    |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | num_oversights       | 6285.5    |       6285.5    |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | flights              | 3923.4    |       3923.4    |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | ave_duration_blocked |   14.0352 |         14.0352 |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | resolution_share_L1  |    0.15   |          0.15   |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | resolution_share_L2  |    0.1586 |          0.1586 |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | decisions_L1         |  588.3    |        588.3    |       0      |        0      |         0      |    1      |   1      |
| gemini-3.5-flash-lite: weak_power     | rule: organized anarchy  | decisions_L2         | 6876      |       6876      |       0      |        0      |         0      |    1      |   1      |
| rule: competent hierarchy             | rule: organized anarchy  | share_resolutions    |    0.0668 |          0.1579 |      -0.0912 |       -0.114  |        -0.0679 |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | decisions            | 1733.3    |       7464.3    |   -5731      |    -6056      |     -5276.66   |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | num_resolutions      |  105.7    |       1178.8    |   -1073.1    |    -1110.11   |     -1032.5    |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | num_oversights       | 1627.6    |       6285.5    |   -4657.9    |    -4986.66   |     -4197.95   |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | flights              | 1118.9    |       3923.4    |   -2804.5    |    -3194.14   |     -2457.28   |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | ave_duration_blocked |  447.793  |         14.0352 |     433.758  |      207.782  |       716.068  |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | resolution_share_L1  |    0.0368 |          0.15   |      -0.1132 |       -0.147  |        -0.0564 |    0.0137 |   0.2324 |
| rule: competent hierarchy             | rule: organized anarchy  | resolution_share_L2  |    0.0784 |          0.1586 |      -0.0802 |       -0.1085 |        -0.0516 |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | decisions_L1         |  260.7    |        588.3    |    -327.6    |     -384.603  |      -281.895  |    0.002  |   0.1758 |
| rule: competent hierarchy             | rule: organized anarchy  | decisions_L2         | 1472.6    |       6876      |   -5403.4    |    -5761.44   |     -4897.27   |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | share_resolutions    |    0.0516 |          0.1579 |      -0.1063 |       -0.1356 |        -0.0661 |    0.0039 |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | decisions            | 3024.8    |       7464.3    |   -4439.5    |    -4912.05   |     -4021.39   |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | num_resolutions      |  159.1    |       1178.8    |   -1019.7    |    -1127.5    |      -849.683  |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | num_oversights       | 2865.7    |       6285.5    |   -3419.8    |    -3854.4    |     -3075.18   |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | flights              |  629.2    |       3923.4    |   -3294.2    |    -3711.94   |     -2725.3    |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | ave_duration_blocked |  297.035  |         14.0352 |     283      |      199.068  |       359.202  |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | resolution_share_L1  |    0.053  |          0.15   |      -0.097  |       -0.1297 |        -0.0567 |    0.0039 |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | resolution_share_L2  |    0.0557 |          0.1586 |      -0.1029 |       -0.1356 |        -0.0605 |    0.0039 |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | decisions_L1         |  125.1    |        588.3    |    -463.2    |     -520.41   |      -399.77   |    0.002  |   0.1758 |
| rule: incompetent hierarchy           | rule: organized anarchy  | decisions_L2         | 2899.7    |       6876      |   -3976.3    |    -4491.01   |     -3531.72   |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | share_resolutions    |    0.1841 |          0.1579 |       0.0261 |        0.0203 |         0.0323 |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | decisions            | 5106.3    |       7464.3    |   -2358      |    -2432.51   |     -2295.69   |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | num_resolutions      |  940.1    |       1178.8    |    -238.7    |     -265.902  |      -212.498  |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | num_oversights       | 4166.2    |       6285.5    |   -2119.3    |    -2210.5    |     -2042.79   |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | flights              | 3096.2    |       3923.4    |    -827.2    |     -960.735  |      -679.362  |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | ave_duration_blocked |   19.5788 |         14.0352 |       5.5436 |        4.1479 |         7.075  |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | resolution_share_L1  |    0.1545 |          0.15   |       0.0044 |       -0.0162 |         0.0257 |    0.625  |   1      |
| target: hierarchical 6x5              | rule: organized anarchy  | resolution_share_L2  |    0.1847 |          0.1586 |       0.026  |        0.0197 |         0.0325 |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | decisions_L1         |   99.2    |        588.3    |    -489.1    |     -510      |      -468.998  |    0.002  |   0.1758 |
| target: hierarchical 6x5              | rule: organized anarchy  | decisions_L2         | 5007.1    |       6876      |   -1868.9    |    -1946.61   |     -1800.1    |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | share_resolutions    |    0.026  |          0.1579 |      -0.132  |       -0.1413 |        -0.1198 |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | decisions            | 1318.7    |       7464.3    |   -6145.6    |    -6285.9    |     -6009.57   |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | num_resolutions      |   33.7    |       1178.8    |   -1145.1    |    -1170.1    |     -1115.69   |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | num_oversights       | 1285      |       6285.5    |   -5000.5    |    -5148.1    |     -4859.14   |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | flights              |  519.9    |       3923.4    |   -3403.5    |    -3640.24   |     -3127.68   |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | ave_duration_blocked |  473.806  |         14.0352 |     459.771  |      224.115  |       707.885  |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | resolution_share_L1  |    0.0201 |          0.15   |      -0.1299 |       -0.1484 |        -0.1068 |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | resolution_share_L2  |    0.0267 |          0.1586 |      -0.132  |       -0.1415 |        -0.1188 |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | decisions_L1         |   76.7    |        588.3    |    -511.6    |     -538.1    |      -488.697  |    0.002  |   0.1758 |
| target: specialized 6x5               | rule: organized anarchy  | decisions_L2         | 1242      |       6876      |   -5634      |    -5775.82   |     -5485.56   |    0.002  |   0.1758 |

### gemini/gemini-3.5-flash-lite: university_roles_strong_power

expected form: hierarchical; invalid answers: 0, failed calls: 0

| | senate | budget_planning | appointment_committee | faculty_council | examination_board | permitted |
|---|---|---|---|---|---|---|
| presidium | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |
| deans | 0.0 | 1.0 | 1.0 | 1.0 | 0.2 | 3 |
| professors | 0.0 | 0.8 | 1.0 | 1.0 | 0.8 | 4 |
| administration | 0.0 | 1.0 | 0.0 | 0.0 | 1.0 | 2 |
| research_staff | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| students | 0.0 | 0.0 | 0.0 | 0.0 | 0.4 | 0 |

Hamming share to the rule-based 6 x 5 forms: unsegmented 0.53, hierarchical 0.27, specialized 0.53
nearest: hierarchical; density 0.47; rows with exactly one body: 0 of 6; bodies nobody may enter: []

### gemini/gemini-3.5-flash-lite: university_roles_moderate_power

expected form: specialized; invalid answers: 0, failed calls: 0

| | senate | budget_planning | appointment_committee | faculty_council | examination_board | permitted |
|---|---|---|---|---|---|---|
| presidium | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| deans | 0.0 | 0.6 | 0.6 | 0.8 | 0.0 | 3 |
| professors | 0.0 | 0.0 | 0.4 | 0.8 | 0.0 | 1 |
| administration | 0.0 | 0.6 | 0.0 | 0.0 | 1.0 | 2 |
| research_staff | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| students | 0.0 | 0.0 | 0.0 | 0.4 | 0.4 | 0 |

Hamming share to the rule-based 6 x 5 forms: unsegmented 0.80, hierarchical 0.53, specialized 0.40
nearest: specialized; density 0.20; rows with exactly one body: 1 of 6; bodies nobody may enter: ['senate']

### gemini/gemini-3.5-flash-lite: university_roles_weak_power

expected form: unsegmented; invalid answers: 0, failed calls: 0

| | senate | budget_planning | appointment_committee | faculty_council | examination_board | permitted |
|---|---|---|---|---|---|---|
| presidium | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |
| deans | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |
| professors | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |
| administration | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |
| research_staff | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |
| students | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 5 |

Hamming share to the rule-based 6 x 5 forms: unsegmented 0.00, hierarchical 0.33, specialized 0.80
nearest: unsegmented; density 1.00; rows with exactly one body: 0 of 6; bodies nobody may enter: []

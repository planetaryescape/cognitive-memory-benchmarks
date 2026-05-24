# Paired LoCoMo architecture-control deltas

Full result: `tuning/runs/locomo-0029/run-00/result.json`

Positive deltas are `Full - Control`.

## overall

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| vector_only | 843 | 0.459 | 0.413 | 0.046 | [0.019, 0.072] | 280/255/308 |
| heuristic_default | 843 | 0.459 | 0.408 | 0.051 | [0.031, 0.072] | 228/169/446 |
| no_reinforcement | 843 | 0.459 | 0.471 | -0.011 | [-0.032, 0.009] | 193/220/430 |
| no_associative_graph | 843 | 0.459 | 0.466 | -0.007 | [-0.029, 0.015] | 211/224/408 |
| no_consolidation_deep_recall | 843 | 0.459 | 0.434 | 0.025 | [0.003, 0.048] | 227/198/418 |
| no_core_promotion | 843 | 0.459 | 0.479 | -0.020 | [-0.042, 0.000] | 200/223/420 |
| no_retention_weighting | 843 | 0.459 | 0.480 | -0.021 | [-0.042, 0.001] | 197/219/427 |

## multi-hop

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| vector_only | 168 | 0.409 | 0.435 | -0.026 | [-0.072, 0.019] | 42/66/60 |
| heuristic_default | 168 | 0.409 | 0.358 | 0.051 | [0.017, 0.086] | 61/41/66 |
| no_reinforcement | 168 | 0.409 | 0.411 | -0.002 | [-0.041, 0.039] | 50/55/63 |
| no_associative_graph | 168 | 0.409 | 0.384 | 0.025 | [-0.023, 0.073] | 61/55/52 |
| no_consolidation_deep_recall | 168 | 0.409 | 0.371 | 0.038 | [-0.004, 0.080] | 52/47/69 |
| no_core_promotion | 168 | 0.409 | 0.436 | -0.027 | [-0.074, 0.019] | 53/58/57 |
| no_retention_weighting | 168 | 0.409 | 0.422 | -0.013 | [-0.058, 0.032] | 51/55/62 |

## temporal

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| vector_only | 158 | 0.538 | 0.183 | 0.354 | [0.282, 0.424] | 95/28/35 |
| heuristic_default | 158 | 0.538 | 0.447 | 0.090 | [0.037, 0.146] | 41/23/94 |
| no_reinforcement | 158 | 0.538 | 0.562 | -0.024 | [-0.062, 0.010] | 20/24/114 |
| no_associative_graph | 158 | 0.538 | 0.562 | -0.024 | [-0.068, 0.018] | 19/28/111 |
| no_consolidation_deep_recall | 158 | 0.538 | 0.495 | 0.043 | [-0.013, 0.097] | 35/24/99 |
| no_core_promotion | 158 | 0.538 | 0.548 | -0.011 | [-0.053, 0.031] | 23/26/109 |
| no_retention_weighting | 158 | 0.538 | 0.568 | -0.030 | [-0.072, 0.009] | 20/26/112 |

## open-domain

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| vector_only | 53 | 0.302 | 0.282 | 0.020 | [-0.058, 0.097] | 13/10/30 |
| heuristic_default | 53 | 0.302 | 0.259 | 0.042 | [-0.017, 0.114] | 7/9/37 |
| no_reinforcement | 53 | 0.302 | 0.321 | -0.019 | [-0.106, 0.066] | 13/12/28 |
| no_associative_graph | 53 | 0.302 | 0.317 | -0.015 | [-0.103, 0.073] | 12/11/30 |
| no_consolidation_deep_recall | 53 | 0.302 | 0.330 | -0.029 | [-0.120, 0.062] | 10/13/30 |
| no_core_promotion | 53 | 0.302 | 0.309 | -0.007 | [-0.079, 0.062] | 12/8/33 |
| no_retention_weighting | 53 | 0.302 | 0.324 | -0.023 | [-0.093, 0.036] | 11/10/32 |

## single-hop

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| vector_only | 464 | 0.469 | 0.499 | -0.030 | [-0.063, 0.004] | 130/151/183 |
| heuristic_default | 464 | 0.469 | 0.430 | 0.039 | [0.010, 0.069] | 119/96/249 |
| no_reinforcement | 464 | 0.469 | 0.479 | -0.010 | [-0.039, 0.020] | 110/129/225 |
| no_associative_graph | 464 | 0.469 | 0.480 | -0.011 | [-0.043, 0.020] | 119/130/215 |
| no_consolidation_deep_recall | 464 | 0.469 | 0.448 | 0.021 | [-0.010, 0.053] | 130/114/220 |
| no_core_promotion | 464 | 0.469 | 0.491 | -0.023 | [-0.052, 0.008] | 112/131/221 |
| no_retention_weighting | 464 | 0.469 | 0.489 | -0.020 | [-0.052, 0.011] | 115/128/221 |


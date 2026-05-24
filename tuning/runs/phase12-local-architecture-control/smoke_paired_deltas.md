# Paired LoCoMo architecture-control deltas

Full result: `tuning/runs/locomo-0014/run-00/result.json`

Positive deltas are `Full - Control`.

## overall

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Vector-only | 152 | 0.528 | 0.514 | 0.014 | [-0.049, 0.081] | 49/53/50 |
| Heuristic default | 152 | 0.528 | 0.448 | 0.080 | [0.039, 0.124] | 48/19/85 |
| No reinforcement | 152 | 0.528 | 0.512 | 0.016 | [-0.011, 0.044] | 31/19/102 |
| No associative graph | 152 | 0.528 | 0.517 | 0.011 | [-0.021, 0.046] | 31/27/94 |
| No consolidation/deep recall | 152 | 0.528 | 0.473 | 0.055 | [0.007, 0.104] | 40/30/82 |
| No core promotion | 152 | 0.528 | 0.511 | 0.017 | [-0.014, 0.052] | 26/27/99 |
| No retention weighting | 152 | 0.528 | 0.526 | 0.002 | [-0.021, 0.027] | 24/28/100 |

## single-hop

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Vector-only | 31 | 0.664 | 0.702 | -0.037 | [-0.129, 0.060] | 8/11/12 |
| Heuristic default | 31 | 0.664 | 0.521 | 0.143 | [0.059, 0.237] | 14/2/15 |
| No reinforcement | 31 | 0.664 | 0.634 | 0.031 | [-0.017, 0.090] | 8/5/18 |
| No associative graph | 31 | 0.664 | 0.643 | 0.021 | [-0.020, 0.078] | 6/4/21 |
| No consolidation/deep recall | 31 | 0.664 | 0.539 | 0.125 | [0.025, 0.239] | 11/4/16 |
| No core promotion | 31 | 0.664 | 0.649 | 0.015 | [-0.043, 0.084] | 6/5/20 |
| No retention weighting | 31 | 0.664 | 0.661 | 0.004 | [-0.040, 0.056] | 5/5/21 |

## multi-hop

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Vector-only | 27 | 0.598 | 0.181 | 0.417 | [0.239, 0.595] | 18/6/3 |
| Heuristic default | 27 | 0.598 | 0.450 | 0.148 | [0.027, 0.288] | 7/2/18 |
| No reinforcement | 27 | 0.598 | 0.572 | 0.025 | [-0.012, 0.072] | 4/2/21 |
| No associative graph | 27 | 0.598 | 0.521 | 0.077 | [0.007, 0.169] | 7/2/18 |
| No consolidation/deep recall | 27 | 0.598 | 0.526 | 0.071 | [-0.024, 0.194] | 4/4/19 |
| No core promotion | 27 | 0.598 | 0.541 | 0.056 | [-0.009, 0.149] | 4/2/21 |
| No retention weighting | 27 | 0.598 | 0.574 | 0.024 | [-0.012, 0.068] | 4/2/21 |

## temporal

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Vector-only | 8 | 0.292 | 0.284 | 0.008 | [-0.227, 0.274] | 4/2/2 |
| Heuristic default | 8 | 0.292 | 0.275 | 0.017 | [-0.100, 0.117] | 3/1/4 |
| No reinforcement | 8 | 0.292 | 0.115 | 0.177 | [0.031, 0.375] | 3/0/5 |
| No associative graph | 8 | 0.292 | 0.250 | 0.042 | [-0.119, 0.208] | 3/2/3 |
| No consolidation/deep recall | 8 | 0.292 | 0.163 | 0.129 | [0.015, 0.296] | 3/0/5 |
| No core promotion | 8 | 0.292 | 0.259 | 0.033 | [0.000, 0.095] | 2/0/6 |
| No retention weighting | 8 | 0.292 | 0.264 | 0.028 | [-0.009, 0.094] | 1/1/6 |

## open-domain

| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Vector-only | 86 | 0.480 | 0.573 | -0.093 | [-0.166, -0.019] | 19/34/33 |
| Heuristic default | 86 | 0.480 | 0.437 | 0.042 | [-0.010, 0.096] | 24/14/48 |
| No reinforcement | 86 | 0.480 | 0.487 | -0.007 | [-0.045, 0.030] | 16/12/58 |
| No associative graph | 86 | 0.480 | 0.495 | -0.016 | [-0.062, 0.031] | 15/19/52 |
| No consolidation/deep recall | 86 | 0.480 | 0.462 | 0.018 | [-0.046, 0.084] | 22/22/42 |
| No core promotion | 86 | 0.480 | 0.475 | 0.005 | [-0.039, 0.055] | 14/20/52 |
| No retention weighting | 86 | 0.480 | 0.487 | -0.008 | [-0.043, 0.029] | 14/20/52 |


# Beware!

When using Aurora, there are a few things to watch out for.

Did you experience an issue that should be listed here, but currently is not?
Please let us know by [opening an issue](https://github.com/microsoft/aurora/issues/new)!

## Sensitivity to Data

Our hope is that Aurora generally produces sensible predictions.
However, there is no guarantee that it will.

If you require optimal performance,
then the data you use needs to be exactly right.
This means that you should use provide
exactly the right variables
at exactly the right pressure levels
from exactly the right source.

(t0-vs-analysis)=
## HRES IFS T0 Versus HRES IFS Analysis

HRES IFS T0 is _not_ the same as HRES IFS analysis.
Crucially, the analysis product includes an additional surface assimilation step.

Specific versions of Aurora require specific versions of HRES IFS:
Aurora 0.25° Fine-Tuned requires IFS HRES T0,
and Aurora 0.1° Fine-Tuned requires IFS HRES analysis.

## Deterministic and Reproducible Output

If you require deterministic and reproducible output,
you should do two things:

1. Set `torch.use_deterministic_algorithms(True)` to make PyTorch operations deterministic.

2. Set `model.eval()` to disable drop-out.
# Spec: Lite-ActionMAE multimodal action benchmark

## Objective

Keep the five existing lightweight baselines unchanged and add a sixth,
`lite_actionmae`, to test whether an ActionMAE-inspired fusion block improves
robustness to partially or fully missing pose/IMU samples while remaining
deployable in the laptop-side LiteRehab inference pipeline. The model is an
engineering benchmark, not a clinical claim or an exact paper reproduction.

## Assumptions

1. `early_fusion` remains the input/feature-level concatenation baseline.
2. `gated_fusion` remains unchanged so previous results stay comparable.
3. `lite_actionmae` replaces the paper's video backbones with the repository's
   CNN-BiGRU encoders; it is therefore a sensor-oriented adaptation.
4. Clean Macro-F1 alone is not the optimization target; robustness, variance,
   latency, and parameter count must be reported together.
5. The current mRI "IMU" features are full-body pose estimates rather than the
   deployed wrist MPU6050's raw six-axis stream, so benchmark weights are not
   directly deployable without aligned device-data retraining.

The model-selection score is fixed before the new run:

- 25% clean Macro-F1;
- 35% mean Macro-F1 over all nonzero missing-modality conditions;
- 20% worst condition Macro-F1;
- 10% cross-seed stability;
- 5% latency efficiency and 5% parameter efficiency.

Efficiency uses fixed deployment budgets rather than dataset-relative min-max
scaling: `max(0, 1 - latency_ms / 1 ms)` and
`max(0, 1 - parameters / 2,000,000)`. This prevents harmless differences among
models that are all comfortably real-time from outweighing robustness.

The score explains the deployment choice, while every raw component remains
visible so readers can reject the weighting and inspect the trade-off directly.

## Literature basis

- Atrey et al., "Multimodal fusion for multimedia analysis: a survey,"
  *Multimedia Systems* 16, 345–379 (2010).
  <https://doi.org/10.1007/s00530-010-0182-0>
- Baltrušaitis et al., "Multimodal Machine Learning: A Survey and Taxonomy,"
  *IEEE TPAMI* 41(2), 423–443 (2019).
  <https://doi.org/10.1109/TPAMI.2018.2798607>
- Ngiam et al., "Multimodal Deep Learning," *ICML* (2011).
  <https://ai.stanford.edu/~jngiam/papers/NgiamKhoslaKimNamLeeNg2011.pdf>
- Woo et al., "Towards Good Practices for Missing Modality Robust Action
  Recognition," *AAAI Conference on Artificial Intelligence* (2023).
  <https://doi.org/10.1609/aaai.v37i3.25378>

## Tech stack

- Python, PyTorch, NumPy, Matplotlib, pytest.
- Existing CNN-BiGRU encoders and benchmark CSV/JSON schema.

## Commands

```powershell
$env:PYTHONPATH = "."
.\.venv-torch\Scripts\python.exe -m pytest -q
.\.venv-torch\Scripts\python.exe benchmark.py run `
  --dataset data\mri_all12.npz `
  --config configs\rtx5060_full12_repeat3.json `
  --holdout-subjects subject17 subject18 subject19 subject20 `
  --output results\all12_full_repeat3_actionmae
.\.venv-torch\Scripts\python.exe benchmark.py figures `
  --results results\all12_full_repeat3_actionmae `
  --output results\all12_full_repeat3_actionmae\figures
```

## Project structure

- `literehab_benchmark/models.py`: model definition.
- `literehab_benchmark/runner.py`: modality masking and robust evaluation.
- `literehab_benchmark/figures.py`: publication figures.
- `configs/rtx5060_full12_repeat3.json`: six-model full-data experiment.
- `tests/`: model, runner, configuration, and figure regression tests.

## Code style

Use small PyTorch modules with explicit availability handling:

```python
present = (availability > 0).to(values.dtype)
encoded = encoder(values * present.unsqueeze(-1))
```

ActionMAE's essential ingredients are retained: random modality-token dropping,
a memory token, positional embeddings, Transformer encoder/decoder blocks, and
equal-weight classification/reconstruction objectives. Fractional availability
informs the sensor adaptation but must not multiply an already corrupted signal
a second time.

## Testing strategy

- Every configured model returns `[batch, classes]` logits and `[batch, 2]` gates.
- `lite_actionmae` must ignore a modality whose availability is zero.
- ActionMAE augmentation must be seeded, preserve shapes, and never remove
  both modalities from a sample.
- Smoke benchmark must write per-seed history/confusion files.
- Figure suite must export non-empty 300-DPI PNG and vector PDF files.

## Boundaries

- Always: retain subject-disjoint evaluation and train-only normalization.
- Ask first: adding external dependencies or changing the official data.
- Never: overwrite old result directories, claim clinical validity, or describe
  the adapted model as an exact GMU reproduction.

## Success criteria

- All tests pass.
- Every model has fewer than two million trainable parameters.
- The six-model full-data run completes for seeds 7/17/27.
- Clean performance, uncertainty, robustness, latency, and parameters are all
  visible in publication figures.
- The report states the correct provenance and adaptation boundary of
  Lite-ActionMAE.

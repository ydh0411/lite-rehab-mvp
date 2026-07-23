# LiteRehab lightweight multimodal benchmark

This folder is deliberately independent from the production dashboard and the
original training scripts.  It provides a small course-project benchmark, not a
full reproduction of every model in the cited papers.

The benchmark compares five compact action-recognition configurations:

1. `imu_cnn`: fast IMU-only baseline.
2. `imu_cnn_bigru`: the current LiteRehab-style IMU temporal model.
3. `pose_cnn_bigru`: RGB-pose-only temporal baseline.
4. `early_fusion`: direct RGB-pose/IMU feature concatenation.
5. `gated_fusion`: reliability-gated late fusion with modality dropout.

Every model is kept below two million trainable parameters.  The default RTX
5060 Laptop preset runs one seed, at most 5,000 training windows, and eight
epochs.  No video decoding, ViTPose training, PoseC3D training, or six-IMU raw
signal reconstruction is performed.

## Data boundary

Use the official precomputed 3D pose features from the NeurIPS 2022 mRI release:

- Paper: <https://proceedings.neurips.cc/paper_files/paper/2022/hash/af9c9c6d2da701da5a0acf91ec217815-Abstract-Datasets_and_Benchmarks.html>
- Official code/data instructions: <https://github.com/SizheAn/mRI/tree/main/action_localization>
- Small precomputed feature archive: `mri_pose_data.zip` linked by the official repository.

The mRI archive stores synchronized pose estimated from RGB and from the full
IMU setup.  Therefore this benchmark demonstrates the value of modalities and
fusion, but it is **not** evidence that one wrist IMU alone matches the original
six-IMU setup.  The final LiteRehab product still uses one wrist IMU.

## Setup

Python 3.11 or 3.12 is recommended.  On the RTX 5060 laptop, install the CUDA
build of PyTorch using the command generated at <https://pytorch.org/get-started/locally/>,
then install the remaining packages:

```bash
cd experiments/lite_benchmark
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm that PyTorch sees the laptop GPU:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

NVIDIA specifies the RTX 5060 Laptop GPU with 8 GB GDDR7 and a configurable
45--100 W GPU power range.  The compact networks fit comfortably in that memory;
the laptop power limit and cooling mainly affect runtime.  As a practical
estimate, the default five-model/one-seed preset should take roughly 10--30
minutes after data preparation, while the optional three-seed preset should take
roughly 30--90 minutes.  These are planning estimates, not measured claims; the
generated manifest and measured per-window latency are the values to report.

## 1. Prepare a small mRI benchmark file

After extracting `mri_pose_data.zip`, point the command at `pose_features/` and
one official protocol JSON.  Selecting two or three upper-limb labels keeps the
figure easy to explain in a presentation.

```bash
PYTHONPATH=. python benchmark.py prepare-mri \
  --features /path/to/mri/pose_features \
  --annotations /path/to/mri/annotations/mri_split1_p1.json \
  --labels left_upper_limb_extension right_upper_limb_extension both_upper_limb_extension \
  --window-size 100 --stride 50 \
  --output data/mri_upper_limb.npz
```

Use the exact action-label strings present in the selected JSON file.  Omit
`--labels` to include all labels, although that makes the benchmark less small.

## 2. Run the default lightweight comparison

```bash
PYTHONPATH=. python benchmark.py run \
  --dataset data/mri_upper_limb.npz \
  --config configs/rtx5060_laptop.json \
  --output results/quick
```

The split is subject-disjoint.  By default the final 20% of subject/video IDs
are held out.  To make the split explicit:

```bash
PYTHONPATH=. python benchmark.py run \
  --dataset data/mri_upper_limb.npz \
  --holdout-subjects subject17 subject18 subject19 subject20 \
  --output results/quick
```

For error bars, use the optional three-seed preset:

```bash
PYTHONPATH=. python benchmark.py run \
  --dataset data/mri_upper_limb.npz \
  --config configs/rtx5060_repeat3.json \
  --output results/repeat3
```

## 3. Generate PPT-ready scientific figures

The plotting code follows the path-based
[`scientific-figure-making`](https://github.com/ChenLiu-1996/figures4papers/tree/main/scientific-figure-making)
conventions: Helvetica/Arial-like typography, strong bar edges, semantic blue
highlighting for the proposed method, print-safe hatching, minimalist spines,
and vector export.

```bash
PYTHONPATH=. python benchmark.py figures \
  --results results/quick \
  --output results/quick/figures
```

Five figures are exported as both PDF and 300-DPI PNG:

- `fig_model_performance`: Accuracy and Macro-F1 grouped bars.
- `fig_efficiency_tradeoff`: Macro-F1 versus inference latency; bubble size is parameter count.
- `fig_robustness`: missing-pose and missing-IMU degradation.
- `fig_confusion_matrix`: row-normalized confusion matrix with sample counts.
- `fig_training_curves`: loss and held-out Macro-F1 over the eight epochs.

Use PNG files in PowerPoint and keep the PDF files for reports or later editing.

## Result interpretation

- Treat this as an engineering benchmark, not a clinical validation.
- Report Macro-F1 and the confusion matrix, not accuracy alone.
- Do not claim that gated fusion is better unless the generated result actually shows it.
- Keep the generated `manifest.json` with the figures; it records the split,
  device, labels, and exact lightweight budget.
- The KIMORE quality-scoring experiment remains a separate optional extension;
  it is not mixed into this action-recognition benchmark because KIMORE has no
  synchronized wrist IMU.

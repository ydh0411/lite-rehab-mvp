import numpy as np

from literehab_benchmark.metrics import classification_metrics, confusion_matrix


def test_metrics_report_macro_f1_without_class_frequency_bias():
    truth = np.asarray([0, 0, 0, 1, 1, 2])
    prediction = np.asarray([0, 0, 1, 1, 1, 1])

    metrics = classification_metrics(truth, prediction, num_classes=3)

    assert metrics["accuracy"] == 4 / 6
    assert metrics["macro_f1"] == np.mean([0.8, 2 / 3, 0.0])
    assert metrics["balanced_accuracy"] == np.mean([2 / 3, 1.0, 0.0])


def test_confusion_matrix_uses_rows_as_actual_classes():
    matrix = confusion_matrix(
        np.asarray([0, 0, 1, 2]), np.asarray([0, 1, 1, 0]), num_classes=3
    )

    np.testing.assert_array_equal(
        matrix,
        np.asarray([
            [1, 1, 0],
            [0, 1, 0],
            [1, 0, 0],
        ]),
    )

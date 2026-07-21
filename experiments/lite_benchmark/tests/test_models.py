import pytest

torch = pytest.importorskip("torch")

from literehab_benchmark.models import MODEL_NAMES, build_model, count_parameters


@pytest.mark.parametrize("model_name", MODEL_NAMES)
def test_every_model_returns_action_logits(model_name):
    model = build_model(model_name, num_classes=3, imu_channels=6, pose_channels=9)
    model.eval()
    imu = torch.randn(2, 6, 32)
    pose = torch.randn(2, 9, 32)
    availability = torch.ones(2, 2)

    with torch.no_grad():
        logits, gates = model(imu, pose, availability)

    assert logits.shape == (2, 3)
    assert gates.shape == (2, 2)
    assert count_parameters(model) < 2_000_000


def test_gated_fusion_ignores_pose_when_pose_is_unavailable():
    torch.manual_seed(3)
    model = build_model("gated_fusion", num_classes=3, imu_channels=6, pose_channels=9)
    model.eval()
    imu = torch.randn(2, 6, 32)
    pose_a = torch.randn(2, 9, 32)
    pose_b = torch.randn(2, 9, 32) * 50
    availability = torch.tensor([[1.0, 0.0], [1.0, 0.0]])

    with torch.no_grad():
        logits_a, gates_a = model(imu, pose_a, availability)
        logits_b, gates_b = model(imu, pose_b, availability)

    torch.testing.assert_close(logits_a, logits_b)
    torch.testing.assert_close(gates_a, gates_b)
    assert torch.all(gates_a[:, 1] == 0)

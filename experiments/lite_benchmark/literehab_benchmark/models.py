from __future__ import annotations

from .config import MODEL_NAMES


def count_parameters(model) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def build_model(
    name: str,
    num_classes: int,
    imu_channels: int,
    pose_channels: int,
):
    import torch
    import torch.nn as nn

    if name not in MODEL_NAMES:
        raise ValueError(f"unknown benchmark model: {name}")
    if num_classes <= 0 or imu_channels <= 0 or pose_channels <= 0:
        raise ValueError("class and channel counts must be positive")

    class CNNEncoder(nn.Module):
        output_dim = 64

        def __init__(self, channels: int) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Conv1d(channels, 24, kernel_size=5, padding=2),
                nn.BatchNorm1d(24),
                nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(24, 48, kernel_size=3, padding=1),
                nn.BatchNorm1d(48),
                nn.ReLU(),
                nn.AdaptiveAvgPool1d(1),
                nn.Flatten(),
                nn.Linear(48, self.output_dim),
                nn.ReLU(),
            )

        def forward(self, values):
            return self.network(values)

    class CNNBiGRUEncoder(nn.Module):
        output_dim = 64

        def __init__(self, channels: int) -> None:
            super().__init__()
            self.convolution = nn.Sequential(
                nn.Conv1d(channels, 24, kernel_size=5, padding=2),
                nn.BatchNorm1d(24),
                nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(24, 48, kernel_size=3, padding=1),
                nn.BatchNorm1d(48),
                nn.ReLU(),
                nn.MaxPool1d(2),
            )
            self.recurrent = nn.GRU(
                input_size=48, hidden_size=32, batch_first=True, bidirectional=True
            )

        def forward(self, values):
            values = self.convolution(values).permute(0, 2, 1)
            values, _ = self.recurrent(values)
            return values.mean(dim=1)

    class SingleModalityModel(nn.Module):
        def __init__(self, modality: str, encoder) -> None:
            super().__init__()
            self.modality = modality
            self.encoder = encoder
            self.classifier = nn.Linear(encoder.output_dim, num_classes)

        def forward(self, imu, pose, availability):
            if self.modality == "imu":
                gate = availability[:, 0:1]
                embedding = self.encoder(imu * gate.unsqueeze(-1))
                gates = torch.cat((gate, torch.zeros_like(gate)), dim=1)
            else:
                gate = availability[:, 1:2]
                embedding = self.encoder(pose * gate.unsqueeze(-1))
                gates = torch.cat((torch.zeros_like(gate), gate), dim=1)
            return self.classifier(embedding), gates

    class EarlyFusionModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = CNNBiGRUEncoder(imu_channels + pose_channels)
            self.classifier = nn.Linear(self.encoder.output_dim, num_classes)

        def forward(self, imu, pose, availability):
            imu = imu * availability[:, 0:1].unsqueeze(-1)
            pose = pose * availability[:, 1:2].unsqueeze(-1)
            embedding = self.encoder(torch.cat((imu, pose), dim=1))
            return self.classifier(embedding), availability

    class GatedFusionModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.imu_encoder = CNNBiGRUEncoder(imu_channels)
            self.pose_encoder = CNNBiGRUEncoder(pose_channels)
            self.gate = nn.Sequential(
                nn.Linear(2 * self.imu_encoder.output_dim + 2, 32),
                nn.ReLU(),
                nn.Linear(32, 2),
                nn.Sigmoid(),
            )
            self.classifier = nn.Sequential(
                nn.Linear(2 * self.imu_encoder.output_dim + 2, 64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, num_classes),
            )

        def forward(self, imu, pose, availability):
            imu_available = availability[:, 0:1]
            pose_available = availability[:, 1:2]
            imu_embedding = self.imu_encoder(imu * imu_available.unsqueeze(-1))
            pose_embedding = self.pose_encoder(pose * pose_available.unsqueeze(-1))
            gate_input = torch.cat((imu_embedding, pose_embedding, availability), dim=1)
            gates = self.gate(gate_input) * availability
            gates = gates / gates.sum(dim=1, keepdim=True).clamp_min(1e-6)
            fused = torch.cat((
                imu_embedding * gates[:, 0:1],
                pose_embedding * gates[:, 1:2],
                availability,
            ), dim=1)
            return self.classifier(fused), gates

    class LiteActionMAEModel(nn.Module):
        """Sensor-oriented adaptation of ActionMAE (Woo et al., AAAI 2023)."""

        def __init__(self) -> None:
            super().__init__()
            hidden_dim = 64
            self.imu_encoder = CNNBiGRUEncoder(imu_channels)
            self.pose_encoder = CNNBiGRUEncoder(pose_channels)
            self.imu_projection = nn.Linear(self.imu_encoder.output_dim, hidden_dim)
            self.pose_projection = nn.Linear(self.pose_encoder.output_dim, hidden_dim)
            self.memory_token = nn.Parameter(torch.zeros(1, 1, hidden_dim))
            self.dummy_tokens = nn.Parameter(torch.zeros(1, 2, hidden_dim))
            self.position = nn.Parameter(torch.zeros(1, 3, hidden_dim))
            self.quality_projection = nn.Linear(1, hidden_dim, bias=False)

            def transformer_block():
                return nn.TransformerEncoderLayer(
                    d_model=hidden_dim,
                    nhead=4,
                    dim_feedforward=128,
                    dropout=0.1,
                    batch_first=True,
                    norm_first=False,
                )

            self.mae_encoder = nn.TransformerEncoder(transformer_block(), num_layers=2)
            self.mae_decoder = nn.TransformerEncoder(transformer_block(), num_layers=2)
            self.fusion = nn.TransformerEncoder(transformer_block(), num_layers=1)
            self.classifier = nn.Sequential(
                nn.LayerNorm(hidden_dim),
                nn.Dropout(0.2),
                nn.Linear(hidden_dim, num_classes),
            )
            nn.init.normal_(self.memory_token, std=0.02)
            nn.init.normal_(self.dummy_tokens, std=0.02)
            nn.init.normal_(self.position, std=0.02)

        def _modality_tokens(self, imu, pose):
            return torch.stack((
                self.imu_projection(self.imu_encoder(imu)),
                self.pose_projection(self.pose_encoder(pose)),
            ), dim=1)

        def forward_with_reconstruction(self, imu, pose, availability):
            targets = self._modality_tokens(imu, pose)
            present = availability > 0
            batch_size = len(imu)
            memory = self.memory_token.expand(batch_size, -1, -1)
            quality = self.quality_projection(availability.unsqueeze(-1))
            observed = targets + self.position[:, 1:] + quality
            encoder_input = torch.cat((memory + self.position[:, :1], observed), dim=1)
            padding_mask = torch.cat((
                torch.zeros((batch_size, 1), dtype=torch.bool, device=imu.device),
                ~present,
            ), dim=1)
            encoded = self.mae_encoder(
                encoder_input, src_key_padding_mask=padding_mask
            )
            modality_latents = torch.where(
                present.unsqueeze(-1),
                encoded[:, 1:],
                self.dummy_tokens.expand(batch_size, -1, -1),
            )
            decoder_input = torch.cat((encoded[:, :1], modality_latents), dim=1)
            decoded = self.mae_decoder(decoder_input + self.position)[:, 1:]
            completed = torch.where(present.unsqueeze(-1), targets, decoded)
            fused = self.fusion(completed + self.position[:, 1:]).mean(dim=1)
            logits = self.classifier(fused)

            missing = ~present
            if missing.any():
                reconstruction_loss = (
                    decoded[missing] - targets.detach()[missing]
                ).square().mean()
            else:
                reconstruction_loss = decoded.sum() * 0.0
            gates = availability * present.to(availability.dtype)
            gates = gates / gates.sum(dim=1, keepdim=True).clamp_min(1e-6)
            return logits, gates, reconstruction_loss

        def forward(self, imu, pose, availability):
            logits, gates, _ = self.forward_with_reconstruction(
                imu, pose, availability
            )
            return logits, gates

    if name == "imu_cnn":
        return SingleModalityModel("imu", CNNEncoder(imu_channels))
    if name == "imu_cnn_bigru":
        return SingleModalityModel("imu", CNNBiGRUEncoder(imu_channels))
    if name == "pose_cnn_bigru":
        return SingleModalityModel("pose", CNNBiGRUEncoder(pose_channels))
    if name == "early_fusion":
        return EarlyFusionModel()
    if name == "gated_fusion":
        return GatedFusionModel()
    return LiteActionMAEModel()

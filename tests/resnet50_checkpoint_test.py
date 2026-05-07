from pathlib import Path

import pytest

from backend import model_paths
from modules.MatAnyone2Module.matanyone2.model.utils import resnet as resnet_module
from scripts import setup_models


def test_resnet50_checkpoint_dir_uses_project_checkpoints_root():
    path = model_paths.get_resnet50_dir()

    assert path == model_paths.get_checkpoints_root() / "resnet50"


def test_setup_models_detects_resnet50_checkpoint(tmp_path, monkeypatch):
    cfg = dict(setup_models.RESNET50_CHECKPOINT)
    cfg["local_dir"] = tmp_path / "checkpoints" / "resnet50"
    monkeypatch.setattr(setup_models, "RESNET50_CHECKPOINT", cfg)

    assert setup_models.is_resnet50_installed() is False

    cfg["local_dir"].mkdir(parents=True)
    (cfg["local_dir"] / cfg["filename"]).write_bytes(b"checkpoint")

    assert setup_models.is_resnet50_installed() is True


def test_resnet50_missing_checkpoint_does_not_use_torch_cache(tmp_path, monkeypatch):
    missing_path = tmp_path / "checkpoints" / "resnet50" / "resnet50-19c8e357.pth"
    monkeypatch.setattr(resnet_module, "_get_resnet50_checkpoint_path", lambda: missing_path)

    def fail_load_url(*args, **kwargs):
        raise AssertionError("model_zoo.load_url should not be called")

    monkeypatch.setattr(resnet_module.model_zoo, "load_url", fail_load_url)

    with pytest.raises(FileNotFoundError, match="ResNet50 pretrained checkpoint not found"):
        resnet_module.resnet50(pretrained=True)


def test_resnet50_loads_pretrained_state_from_local_checkpoint(tmp_path, monkeypatch):
    checkpoint_path = tmp_path / "checkpoints" / "resnet50" / "resnet50-19c8e357.pth"
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(b"placeholder")

    source_model = resnet_module.ResNet(resnet_module.Bottleneck, [3, 4, 6, 3], extra_dim=0)
    source_state = source_model.state_dict()

    monkeypatch.setattr(resnet_module, "_get_resnet50_checkpoint_path", lambda: checkpoint_path)

    def fake_torch_load(path: Path, *, map_location: str):
        assert path == checkpoint_path
        assert map_location == "cpu"
        return source_state

    def fail_load_url(*args, **kwargs):
        raise AssertionError("model_zoo.load_url should not be called")

    monkeypatch.setattr(resnet_module.torch, "load", fake_torch_load)
    monkeypatch.setattr(resnet_module.model_zoo, "load_url", fail_load_url)

    model = resnet_module.resnet50(pretrained=True)

    assert model.conv1.in_channels == 3

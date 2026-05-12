from CorridorKeyModule import backend as ck_backend


def test_checkpoint_discovery_prefers_primary_dir(monkeypatch, tmp_path):
    primary = tmp_path / "checkpoints" / "corridorkey"
    legacy = tmp_path / "CorridorKeyModule" / "checkpoints"
    primary.mkdir(parents=True)
    legacy.mkdir(parents=True)

    primary_ckpt = primary / "CorridorKey_v1.0.pth"
    primary_ckpt.write_bytes(b"primary")
    (legacy / "CorridorKey_v1.0.pth").write_bytes(b"legacy")

    monkeypatch.setattr(ck_backend, "CHECKPOINT_DIR", str(primary))
    monkeypatch.setattr(ck_backend, "LEGACY_CHECKPOINT_DIR", str(legacy))

    assert ck_backend._discover_checkpoint(".pth") == primary_ckpt


def test_checkpoint_discovery_falls_back_to_legacy_dir(monkeypatch, tmp_path):
    primary = tmp_path / "checkpoints" / "corridorkey"
    legacy = tmp_path / "CorridorKeyModule" / "checkpoints"
    primary.mkdir(parents=True)
    legacy.mkdir(parents=True)

    legacy_ckpt = legacy / "CorridorKey_v1.0.pth"
    legacy_ckpt.write_bytes(b"legacy")

    monkeypatch.setattr(ck_backend, "CHECKPOINT_DIR", str(primary))
    monkeypatch.setattr(ck_backend, "LEGACY_CHECKPOINT_DIR", str(legacy))

    assert ck_backend._discover_checkpoint(".pth") == legacy_ckpt

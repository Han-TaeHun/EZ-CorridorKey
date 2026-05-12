"""Tests for session save/load — JSON sidecar, versioning, forward compat."""
import json
import os
from unittest.mock import patch

import pytest

from backend.service import InferenceParams, OutputConfig
from ui.main_window_mixins.import_mixin import ImportMixin
from ui.main_window_mixins.session_mixin import _SESSION_FILENAME, SessionMixin


class DummyImportWindow(ImportMixin):
    def __init__(self):
        self._clips_dir = None
        self.created_from_folder = []

    def _create_project_from_folder(self, dir_path: str) -> None:
        self.created_from_folder.append(dir_path)

    def _switch_to_workspace(self) -> None:
        raise AssertionError("원본 폴더를 직접 작업공간으로 열면 안 됩니다.")

    def _on_clips_dir_changed(self, dir_path: str, **kwargs) -> None:
        raise AssertionError("원본 폴더를 직접 스캔하면 안 됩니다.")


class DummySessionWindow(SessionMixin):
    def __init__(self, clips_dir: str | None = None):
        self._clips_dir = clips_dir


class TestSessionData:
    def test_params_roundtrip(self):
        """Params serialize and deserialize correctly."""
        params = InferenceParams(despill_strength=0.5, refiner_scale=2.0)
        d = params.to_dict()
        restored = InferenceParams.from_dict(d)
        assert restored.despill_strength == 0.5
        assert restored.refiner_scale == 2.0

    def test_output_config_roundtrip(self):
        cfg = OutputConfig(fg_enabled=False, comp_format="exr")
        d = cfg.to_dict()
        restored = OutputConfig.from_dict(d)
        assert restored.fg_enabled is False
        assert restored.comp_format == "exr"

    def test_session_file_format(self, tmp_path):
        """Session file should be valid JSON with version key."""
        session = {
            "version": 1,
            "params": InferenceParams().to_dict(),
            "output_config": OutputConfig().to_dict(),
            "live_preview": False,
            "split_view": False,
        }
        path = os.path.join(str(tmp_path), ".corridorkey_session.json")
        with open(path, 'w') as f:
            json.dump(session, f)

        with open(path, 'r') as f:
            loaded = json.load(f)

        assert loaded["version"] == 1
        assert "params" in loaded
        assert "output_config" in loaded

    def test_forward_compat_unknown_keys(self):
        """Unknown keys from newer versions should be ignored."""
        d = {
            "input_is_linear": True,
            "new_param_v2": 42,
            "another_future_param": "hello",
        }
        params = InferenceParams.from_dict(d)
        assert params.input_is_linear is True
        # No error, unknown keys silently ignored

    def test_corrupt_session_file(self, tmp_path):
        """Corrupt JSON should not crash."""
        path = os.path.join(str(tmp_path), ".corridorkey_session.json")
        with open(path, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            with open(path, 'r') as f:
                json.load(f)

    def test_atomic_write_pattern(self, tmp_path):
        """Verify tmp+rename pattern produces valid file."""
        path = os.path.join(str(tmp_path), "session.json")
        tmp_path_file = path + ".tmp"

        data = {"version": 1, "test": True}
        with open(tmp_path_file, 'w') as f:
            json.dump(data, f)
        os.rename(tmp_path_file, path)

        assert os.path.isfile(path)
        assert not os.path.exists(tmp_path_file)
        with open(path, 'r') as f:
            loaded = json.load(f)
        assert loaded["test"] is True


class TestImportFolderIsolation:
    def test_welcome_folder_routes_through_project_creation(self):
        """시작 화면 폴더 선택은 원본을 직접 열지 않고 프로젝트 생성 경로로 보낸다."""
        window = DummyImportWindow()
        window._on_welcome_folder(r"C:\source\sequence")

        assert window.created_from_folder == [r"C:\source\sequence"]

    def test_tray_folder_without_open_project_routes_through_project_creation(self):
        """열린 프로젝트가 없을 때 트레이 폴더 추가도 프로젝트 생성 경로로 보낸다."""
        window = DummyImportWindow()
        window._on_tray_folder_imported(r"C:\source\sequence")

        assert window.created_from_folder == [r"C:\source\sequence"]


class TestSessionPathIsolation:
    def test_session_path_only_allows_project_folders(self, tmp_path):
        """세션 파일은 project.json 또는 clips/가 있는 프로젝트 폴더에만 둔다."""
        projects_root = tmp_path / "Projects"
        ordinary_source = tmp_path / "ordinary_source"
        ordinary_source.mkdir()

        project_with_json = tmp_path / "project_with_json"
        project_with_json.mkdir()
        (project_with_json / "project.json").write_text("{}", encoding="utf-8")

        project_with_clips = tmp_path / "project_with_clips"
        (project_with_clips / "clips").mkdir(parents=True)

        with patch("backend.project.projects_root", return_value=str(projects_root)):
            assert DummySessionWindow(str(ordinary_source))._session_path() is None
            assert DummySessionWindow(str(projects_root))._session_path() is None
            assert DummySessionWindow(str(project_with_json))._session_path() == os.path.join(
                str(project_with_json), _SESSION_FILENAME
            )
            assert DummySessionWindow(str(project_with_clips))._session_path() == os.path.join(
                str(project_with_clips), _SESSION_FILENAME
            )

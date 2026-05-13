"""Tests for pre-commit hooks configuration."""

import subprocess
from pathlib import Path

import yaml


class TestPreCommitConfig:
    def test_pre_commit_config_exists(self):
        config_path = Path(".pre-commit-config.yaml")
        assert config_path.exists(), ".pre-commit-config.yaml must exist"

    def test_pre_commit_config_is_valid_yaml(self):
        config_path = Path(".pre-commit-config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert "repos" in config
        assert len(config["repos"]) > 0

    def test_pre_commit_config_has_required_hooks(self):
        config_path = Path(".pre-commit-config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        all_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                all_hooks.append(hook.get("id", ""))

        required_hooks = [
            "trailing-whitespace",
            "end-of-file-fixer",
            "check-yaml",
            "check-json",
        ]
        for required in required_hooks:
            assert required in all_hooks, f"Required hook '{required}' not found in config"

    def test_pre_commit_config_repos_are_reachable(self):
        config_path = Path(".pre-commit-config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            repo_url = repo.get("repo", "")
            assert repo_url.startswith("https://"), f"Repo URL must be https: {repo_url}"
            assert "github.com" in repo_url or "gitlab.com" in repo_url, f"Unknown repo: {repo_url}"

    def test_pre_commit_config_utf8_encoding_coverage(self):
        config_path = Path(".pre-commit-config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        all_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                all_hooks.append(hook.get("id", ""))

        json_hooks = [h for h in all_hooks if "json" in h.lower()]
        yaml_hooks = [h for h in all_hooks if "yaml" in h.lower() or "yml" in h.lower()]

        assert len(json_hooks) > 0, "JSON validation hooks must be present (implicit UTF-8 check)"
        assert len(yaml_hooks) > 0, "YAML validation hooks must be present (implicit UTF-8 check)"
        assert "check-json" in all_hooks, "check-json hook must be present for UTF-8 validation of JSON files"
        assert "check-yaml" in all_hooks, "check-yaml hook must be present for UTF-8 validation of YAML files"


class TestPreCommitHooks:
    def test_pre_commit_run_all_files_succeeds(self):
        result = subprocess.run(
            ["pre-commit", "run", "--all-files"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pre-commit run --all-files failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    def test_pre_commit_trailing_whitespace_hook(self, tmp_path):
        file_with_ws = tmp_path / "test_ws.py"
        file_with_ws.write_text("x = 1  \n")

        result = subprocess.run(
            ["pre-commit", "run", "trailing-whitespace", "--files", str(file_with_ws)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "trailing-whitespace hook should fail on trailing whitespace"

    def test_pre_commit_end_of_file_hook(self, tmp_path):
        file_no_newline = tmp_path / "test_no_newline.py"
        file_no_newline.write_text("x = 1")

        result = subprocess.run(
            ["pre-commit", "run", "end-of-file-fixer", "--files", str(file_no_newline)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "end-of-file-fixer hook should fail on file without newline"

    def test_pre_commit_check_yaml_hook(self, tmp_path):
        valid_yaml = tmp_path / "valid.yaml"
        valid_yaml.write_text("key: value\n")

        result = subprocess.run(
            ["pre-commit", "run", "check-yaml", "--files", str(valid_yaml)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"check-yaml hook failed on valid yaml:\n{result.stderr}"

    def test_pre_commit_check_json_hook(self, tmp_path):
        valid_json = tmp_path / "valid.json"
        valid_json.write_text('{"key": "value"}\n')

        result = subprocess.run(
            ["pre-commit", "run", "check-json", "--files", str(valid_json)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"check-json hook failed on valid json:\n{result.stderr}"


class TestPreCommitConfigJsonValidation:
    def test_pre_commit_config_has_json_schemafile_args(self):
        config_path = Path(".pre-commit-config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        json_hooks_with_schema = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                args = hook.get("args", [])
                if any("schemafile" in arg for arg in args):
                    json_hooks_with_schema.append(hook.get("id"))

        assert len(json_hooks_with_schema) > 0, "At least one JSON schema validation hook must be configured"

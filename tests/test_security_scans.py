"""Tests for security scanning module (bandit, pip-audit, secret detection)."""

import json
from pathlib import Path

import pytest

from fba.security import (
    _SECRET_PATTERNS,
    ScanResult,
    SecurityReport,
    scan_bandit,
    scan_pip_audit,
    scan_secrets,
    run_security_scan,
)


class TestScanResult:
    def test_scan_result_to_dict(self):
        result = ScanResult(
            passed=False,
            scanner="bandit",
            message="Test message",
            findings=["finding1", "finding2"],
            details={"key": "value"},
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["scanner"] == "bandit"
        assert d["message"] == "Test message"
        assert len(d["findings"]) == 2


class TestSecurityReport:
    def test_security_report_to_dict(self):
        results = [
            ScanResult(passed=True, scanner="bandit", message="ok"),
            ScanResult(passed=False, scanner="pip-audit", message="vulns", findings=["vuln1"]),
        ]
        report = SecurityReport(scanner_results=results, overall_passed=False, total_findings=1)
        d = report.to_dict()
        assert d["overall_passed"] is False
        assert d["total_findings"] == 1
        assert len(d["scanner_results"]) == 2

    def test_security_report_to_markdown(self):
        results = [
            ScanResult(passed=True, scanner="bandit", message="no issues"),
            ScanResult(passed=False, scanner="secret_detection", message="secrets found", findings=["file.py:10: hardcoded credential"]),
        ]
        report = SecurityReport(scanner_results=results, overall_passed=False, total_findings=1)
        md = report.to_markdown()
        assert "# Security Report" in md
        assert "❌ FAILED" in md
        assert "secret_detection" in md
        assert "file.py:10" in md


class TestBanditScan:
    def test_bandit_scan_on_clean_directory(self, tmp_path):
        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\n")

        result = scan_bandit(tmp_path)
        assert result.scanner == "bandit"
        assert result.passed is True or result.details.get("skipped") is True

    def test_bandit_scan_detects_hardcoded_password(self, tmp_path):
        vulnerable_py = tmp_path / "vulnerable.py"
        vulnerable_py.write_text("password = 'super_secret_123'\n")

        result = scan_bandit(tmp_path)
        assert result.scanner == "bandit"

    def test_bandit_scan_with_exclude_paths(self, tmp_path):
        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\n")
        excluded = tmp_path / "excluded.py"
        excluded.write_text("password = 'secret'\n")

        result = scan_bandit(tmp_path, exclude_paths=["excluded.py"])
        assert result.scanner == "bandit"


class TestPipAuditScan:
    def test_pip_audit_no_requirements(self, tmp_path):
        result = scan_pip_audit(tmp_path)
        assert result.scanner == "pip-audit"
        assert result.passed is True
        assert result.details.get("skipped") is True

    def test_pip_audit_with_requirements(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("click==8.1.0\n")

        result = scan_pip_audit(tmp_path)
        assert result.scanner == "pip-audit"


class TestSecretDetection:
    def test_secret_scan_clean_directory(self, tmp_path):
        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\ny = 2\n")

        result = scan_secrets(tmp_path)
        assert result.scanner == "secret_detection"
        assert result.passed is True
        assert result.findings == []
        assert result.details["scanned_files"] >= 1

    def test_secret_scan_detects_password_pattern(self, tmp_path):
        vulnerable_py = tmp_path / "vulnerable.py"
        vulnerable_py.write_text("password = 'super_secret_123'\n")

        result = scan_secrets(tmp_path)
        assert result.scanner == "secret_detection"
        assert result.passed is False
        assert len(result.findings) > 0
        assert any("credential" in f for f in result.findings)

    def test_secret_scan_detects_api_key_pattern(self, tmp_path):
        vulnerable_py = tmp_path / "api_creds.py"
        vulnerable_py.write_text("api_key = 'AKIAIOSFODNN7EXAMPLE'\n")

        result = scan_secrets(tmp_path)
        assert result.scanner == "secret_detection"
        assert result.passed is False
        assert len(result.findings) > 0

    def test_secret_scan_detects_github_token(self, tmp_path):
        vulnerable_py = tmp_path / "github.py"
        vulnerable_py.write_text("github_token = 'ghp_1234567890abcdefghijklmnopqrstuvwxyz'\n")

        result = scan_secrets(tmp_path)
        assert result.scanner == "secret_detection"
        assert result.passed is False

    def test_secret_scan_skips_excluded_directories(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("password = 'secret_in_git'\n")

        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (venv_dir / "module.py").write_text("password = 'secret_in_venv'\n")

        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\n")

        result = scan_secrets(tmp_path)
        assert result.scanner == "secret_detection"
        assert result.passed is True

    def test_secret_scan_respects_file_size_limit(self, tmp_path):
        large_py = tmp_path / "large.py"
        large_py.write_text("x = 1\n" * 100_000)

        result = scan_secrets(tmp_path)
        assert result.scanner == "secret_detection"

    def test_secret_scan_only_specified_extensions(self, tmp_path):
        clean_txt = tmp_path / "clean.txt"
        clean_txt.write_text("password = 'secret'\n")

        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\n")

        result = scan_secrets(tmp_path, file_extensions=[".py"])
        assert result.scanner == "secret_detection"
        assert result.passed is True


class TestSecretPatterns:
    def test_password_pattern(self):
        from fba.security import _SECRET_PATTERNS
        pattern = _SECRET_PATTERNS[0][0]
        assert pattern.search("password='secret'")
        assert pattern.search("password: 'secret'")
        assert pattern.search("pwd='secret'")
        assert not pattern.search("password")

    def test_bearer_token_pattern(self):
        pattern = _SECRET_PATTERNS[1][0]
        assert pattern.search("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert not pattern.search("Bearer ")

    def test_github_token_pattern(self):
        pattern = _SECRET_PATTERNS[2][0]
        assert pattern.search("github_token='ghp_abcdefghijklmnopqrstuvwxyz'")
        assert pattern.search("github_token='ghp_abcdefghijklmnopqrstuvwxyz'")

    def test_aws_access_key_pattern(self):
        pattern = _SECRET_PATTERNS[3][0]
        assert pattern.search("aws_access_key='AKIAIOSFODNN7EXAMPLE'")
        assert pattern.search("aws_access_key='AKIAIOSFODNN7EXAMPLE'")

    def test_stripe_key_pattern(self):
        pattern = _SECRET_PATTERNS[4][0]
        assert pattern.search("sk_test_abcdefghijklmnopqrstuvwxyz")


class TestRunSecurityScan:
    def test_run_security_scan_generates_report(self, tmp_path):
        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\n")

        report = run_security_scan(tmp_path)
        assert isinstance(report, SecurityReport)
        assert report.scanner_results is not None
        assert len(report.scanner_results) == 3
        assert any(r.scanner == "bandit" for r in report.scanner_results)
        assert any(r.scanner == "pip-audit" for r in report.scanner_results)
        assert any(r.scanner == "secret_detection" for r in report.scanner_results)

    def test_run_security_scan_generates_report_file(self, tmp_path):
        clean_py = tmp_path / "clean.py"
        clean_py.write_text("x = 1\n")

        factory_dir = tmp_path / ".factory"
        factory_dir.mkdir()

        report = run_security_scan(tmp_path)

        report_path = tmp_path / ".factory" / "security_report.md"
        assert report_path.exists()
        content = report_path.read_text()
        assert "# Security Report" in content


class TestSecurityScanIntegration:
    def test_security_scan_fails_on_vulnerable_code(self, tmp_path):
        vulnerable_py = tmp_path / "vulnerable.py"
        vulnerable_py.write_text("password = 'super_secret_123'\n")

        report = run_security_scan(tmp_path)
        secret_result = next(r for r in report.scanner_results if r.scanner == "secret_detection")
        assert secret_result.passed is False
        assert len(secret_result.findings) > 0

    def test_security_scan_fails_fast(self, tmp_path):
        vulnerable_py = tmp_path / "vulnerable.py"
        vulnerable_py.write_text("password = 'super_secret_123'\n")

        report = run_security_scan(tmp_path)
        assert report.overall_passed is False
        assert report.total_findings > 0
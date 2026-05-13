"""Security scanning module for fail-fast gate enforcement.

Integrates:
- bandit: Python security linter
- pip-audit: Vulnerability scanning for Python dependencies
- Secret detection: regex-based detection of hardcoded credentials
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScanResult:
    passed: bool
    scanner: str
    message: str = ""
    findings: list = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "passed": self.passed,
            "scanner": self.scanner,
            "message": self.message,
            "findings": self.findings,
            "details": self.details,
        }


@dataclass
class SecurityReport:
    scanner_results: list = field(default_factory=list)
    overall_passed: bool = True
    total_findings: int = 0

    def to_dict(self):
        return {
            "overall_passed": self.overall_passed,
            "total_findings": self.total_findings,
            "scanner_results": [r.to_dict() for r in self.scanner_results],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Security Report",
            "",
            f"**Overall Status**: {'✅ PASSED' if self.overall_passed else '❌ FAILED'}",
            f"**Total Findings**: {self.total_findings}",
            "",
        ]
        for result in self.scanner_results:
            status = "✅" if result.passed else "❌"
            lines.append(f"## {status} {result.scanner}")
            lines.append("")
            if result.findings:
                lines.append("**Findings:**")
                for finding in result.findings:
                    lines.append(f"- {finding}")
                lines.append("")
            if result.message:
                lines.append(f"**Message**: {result.message}")
                lines.append("")
        return "\n".join(lines)


_SECRET_PATTERNS = [
    (re.compile(r"(password|pwd|pass|secret|token|api_key|auth)\s*[=:]\s*'?[^' ]+'?", re.IGNORECASE), "Hardcoded credential pattern"),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-]{20,}"), "Bearer token pattern"),
    (re.compile(r"github_token\s*[=:]\s*'?[A-Za-z0-9_\-]+'?"), "GitHub token pattern"),
    (re.compile(r"aws_access_key\s*[=:]\s*'?[A-Z0-9]{16,}'?"), "AWS access key pattern"),
    (re.compile(r"sk_live_[A-Za-z0-9_\-]{20,}"), "Stripe secret key pattern"),
]


def scan_bandit(target_path: Path, exclude_paths: list | None = None) -> ScanResult:
    exclude_args = []
    if exclude_paths:
        for ep in exclude_paths:
            exclude_args.extend(["--exclude", ep])

    try:
        result = subprocess.run(
            ["bandit", "-r", str(target_path), "-f", "json"] + exclude_args,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout
        if not output:
            output = result.stderr

        try:
            bandit_output = json.loads(output)
        except json.JSONDecodeError:
            return ScanResult(
                passed=True,
                scanner="bandit",
                message=f"Bandit scan completed (raw output): {result.returncode}",
                details={"raw_returncode": result.returncode},
            )

        issues = bandit_output.get("results", [])
        high_medium_issues = [
            f"{issue.get('filename', 'unknown')}:{issue.get('line', 0)}: {issue.get('issue_text', 'N/A')} (severity: {issue.get('issue_severity', 'N/A')})"
            for issue in issues
            if issue.get("issue_severity") in ("HIGH", "MEDIUM")
        ]

        passed = len(high_medium_issues) == 0

        return ScanResult(
            passed=passed,
            scanner="bandit",
            message="Bandit scan passed" if passed else f"Found {len(high_medium_issues)} high/medium severity issues",
            findings=high_medium_issues,
            details={
                "total_issues": len(issues),
                "high_medium_count": len(high_medium_issues),
                "metrics": bandit_output.get("metrics", {}),
            },
        )
    except FileNotFoundError:
        return ScanResult(
            passed=True,
            scanner="bandit",
            message="Bandit not installed, skipping scan",
            details={"skipped": True},
        )
    except subprocess.TimeoutExpired:
        return ScanResult(
            passed=False,
            scanner="bandit",
            message="Bandit scan timed out after 60 seconds",
            findings=["Bandit scan timeout"],
        )
    except Exception as e:
        return ScanResult(
            passed=False,
            scanner="bandit",
            message=f"Bandit scan failed: {e}",
            findings=[str(e)],
        )


def scan_pip_audit(target_path: Path) -> ScanResult:
    requirements_file = target_path / "requirements.txt"
    if not requirements_file.exists():
        return ScanResult(
            passed=True,
            scanner="pip-audit",
            message="No requirements.txt found, skipping pip-audit",
            details={"skipped": True},
        )

    try:
        result = subprocess.run(
            ["pip-audit", "-r", str(requirements_file), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        if not output:
            output = result.stderr

        try:
            pip_audit_output = json.loads(output)
        except json.JSONDecodeError:
            return ScanResult(
                passed=True,
                scanner="pip-audit",
                message=f"pip-audit scan completed (raw output): {result.returncode}",
                details={"raw_returncode": result.returncode},
            )

        vulnerabilities = pip_audit_output if isinstance(pip_audit_output, list) else pip_audit_output.get("vulnerabilities", [])

        vuln_findings = [
            f"{vuln.get('name', 'unknown')}=={vuln.get('version', 'N/A')}: {vuln.get('id', 'N/A')} - {vuln.get('description', 'N/A')[:100]}"
            for vuln in vulnerabilities
        ]

        passed = len(vuln_findings) == 0

        return ScanResult(
            passed=passed,
            scanner="pip-audit",
            message="pip-audit scan passed" if passed else f"Found {len(vuln_findings)} vulnerabilities",
            findings=vuln_findings,
            details={
                "total_vulnerabilities": len(vulnerabilities),
                "vuln_count": len(vuln_findings),
            },
        )
    except FileNotFoundError:
        return ScanResult(
            passed=True,
            scanner="pip-audit",
            message="pip-audit not installed, skipping scan",
            details={"skipped": True},
        )
    except subprocess.TimeoutExpired:
        return ScanResult(
            passed=False,
            scanner="pip-audit",
            message="pip-audit scan timed out after 120 seconds",
            findings=["pip-audit scan timeout"],
        )
    except Exception as e:
        return ScanResult(
            passed=False,
            scanner="pip-audit",
            message=f"pip-audit scan failed: {e}",
            findings=[str(e)],
        )


def scan_secrets(target_path: Path, file_extensions: list | None = None) -> ScanResult:
    if file_extensions is None:
        file_extensions = [".py", ".yaml", ".yml", ".json", ".txt", ".md", ".rst", ".conf", ".cfg", ".ini", ".env"]

    secret_findings = []
    scanned_files = 0

    if target_path.is_file():
        files_to_scan = [target_path]
    else:
        files_to_scan = []
        for ext in file_extensions:
            files_to_scan.extend(target_path.rglob(f"*{ext}"))

    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".factory", ".tox", ".eggs"}

    for file_path in files_to_scan:
        if any(skip_part in file_path.parts for skip_part in skip_dirs):
            continue

        if file_path.is_file() and file_path.stat().st_size < 1_000_000:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                scanned_files += 1

                for pattern, description in _SECRET_PATTERNS:
                    if pattern.search(content):
                        line_num = 1
                        for line in content.split("\n"):
                            if pattern.search(line):
                                secret_findings.append(
                                    f"{file_path}:{line_num}: {description} detected"
                                )
                            line_num += 1
            except Exception:
                continue

    passed = len(secret_findings) == 0

    return ScanResult(
        passed=passed,
        scanner="secret_detection",
        message="Secret scan passed" if passed else f"Found {len(secret_findings)} secret patterns",
        findings=secret_findings,
        details={
            "scanned_files": scanned_files,
            "patterns_checked": len(_SECRET_PATTERNS),
        },
    )


def run_security_scan(project_dir: Path, exclude_paths: list | None = None) -> SecurityReport:
    results = []

    bandit_result = scan_bandit(project_dir, exclude_paths=exclude_paths)
    results.append(bandit_result)

    pip_audit_result = scan_pip_audit(project_dir)
    results.append(pip_audit_result)

    secrets_result = scan_secrets(project_dir)
    results.append(secrets_result)

    overall_passed = all(r.passed for r in results)
    total_findings = sum(len(r.findings) for r in results)

    report = SecurityReport(
        scanner_results=results,
        overall_passed=overall_passed,
        total_findings=total_findings,
    )

    report_path = project_dir / ".factory" / "security_report.md"
    if project_dir / ".factory" not in [project_dir]:
        report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        report_path.write_text(report.to_markdown())
    except Exception:
        pass

    return report
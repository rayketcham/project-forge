"""Tests for GitHub integration (mocked gh CLI)."""

from unittest.mock import patch

import pytest

from project_forge.scaffold.github import create_issue, create_label, create_repo


class TestGitHub:
    @patch("project_forge.scaffold.github.subprocess.run")
    def test_create_repo(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "https://github.com/rayketcham/test-repo"
        mock_run.return_value.stderr = ""

        url = create_repo("test-repo", "A test repo")
        assert "test-repo" in url
        mock_run.assert_called_once()

    @patch("project_forge.scaffold.github.subprocess.run")
    def test_create_repo_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "already exists"

        with pytest.raises(RuntimeError, match="already exists"):
            create_repo("test-repo", "A test repo")

    @patch("project_forge.scaffold.github.subprocess.run")
    def test_create_issue(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "https://github.com/rayketcham/test-repo/issues/1"
        mock_run.return_value.stderr = ""

        url = create_issue("rayketcham/test-repo", "Test issue", "Body text")
        assert "issues/1" in url

    @patch("project_forge.scaffold.github.subprocess.run")
    def test_create_issue_with_labels(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "https://github.com/rayketcham/test-repo/issues/2"
        mock_run.return_value.stderr = ""

        url = create_issue("rayketcham/test-repo", "Test", "Body", labels=["idea", "feature"])
        assert "issues/2" in url
        call_args = mock_run.call_args[0][0]
        assert "--label" in call_args

    @patch("project_forge.scaffold.github.subprocess.run")
    def test_create_label(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        create_label("rayketcham/test-repo", "idea", "0e8a16", "Generated idea")
        mock_run.assert_called_once()

    @patch("project_forge.scaffold.github.subprocess.run")
    def test_create_label_already_exists(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "already exists"

        # Should not raise, just warn
        create_label("rayketcham/test-repo", "idea", "0e8a16")

#!/usr/bin/env python3
"""Tests for skilldoc.py"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import functions from skilldoc.py
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skilldoc


class TestParseFrontmatter:
    """Test YAML frontmatter parsing"""

    def test_parse_valid_frontmatter(self, tmp_path):
        """Test parsing valid YAML frontmatter"""
        skill_file = tmp_path / "SKILL.md"
        content = """---
name: test-skill
version: 1.0.0
depends:
  - git
  - curl
---
# Test Skill
This is a test skill.
"""
        skill_file.write_text(content)
        
        result = skilldoc.parse_frontmatter(str(skill_file))
        assert result is not None
        assert result['name'] == 'test-skill'
        assert result['version'] == '1.0.0'
        assert 'git' in result['depends']
        assert 'curl' in result['depends']

    def test_parse_no_frontmatter(self, tmp_path):
        """Test file without frontmatter returns None"""
        skill_file = tmp_path / "SKILL.md"
        content = """# Test Skill
This skill has no frontmatter.
"""
        skill_file.write_text(content)
        
        result = skilldoc.parse_frontmatter(str(skill_file))
        assert result is None

    def test_parse_invalid_yaml(self, tmp_path):
        """Test invalid YAML returns None"""
        skill_file = tmp_path / "SKILL.md"
        content = """---
name: test-skill
invalid: yaml: content [
---
# Test Skill
"""
        skill_file.write_text(content)
        
        result = skilldoc.parse_frontmatter(str(skill_file))
        assert result is None

    def test_parse_missing_file(self):
        """Test missing file returns None"""
        result = skilldoc.parse_frontmatter("/nonexistent/file.md")
        assert result is None


class TestCheckBinary:
    """Test binary dependency checking"""

    @patch('shutil.which')
    def test_check_binary_exists(self, mock_which):
        """Test when binary exists"""
        mock_which.return_value = "/usr/bin/git"
        result = skilldoc.check_binary("git")
        assert result == "/usr/bin/git"
        mock_which.assert_called_once_with("git")

    @patch('shutil.which')
    def test_check_binary_missing(self, mock_which):
        """Test when binary is missing"""
        mock_which.return_value = None
        result = skilldoc.check_binary("nonexistent-binary")
        assert result is None
        mock_which.assert_called_once_with("nonexistent-binary")


class TestExtractOpenClawMeta:
    """Test OpenClaw metadata extraction"""

    def test_extract_openclaw_meta_with_requires(self):
        """Test extracting metadata with requires section"""
        frontmatter = {
            'openclaw': {
                'requires': {
                    'bins': ['git', 'curl']
                },
                'os': ['darwin', 'linux']
            }
        }
        
        result = skilldoc.extract_openclaw_meta(frontmatter)
        assert 'git' in result['requires']['bins']
        assert 'curl' in result['requires']['bins']
        assert 'darwin' in result['os']

    def test_extract_openclaw_meta_empty(self):
        """Test extracting metadata from empty frontmatter"""
        result = skilldoc.extract_openclaw_meta({})
        assert result == {}

    def test_extract_openclaw_meta_none(self):
        """Test extracting metadata from None"""
        result = skilldoc.extract_openclaw_meta(None)
        assert result == {}


class TestScanSkills:
    """Test skill scanning functionality"""

    @patch('glob.glob')
    @patch('os.path.isdir')
    @patch('skilldoc.parse_frontmatter')
    @patch('skilldoc.extract_openclaw_meta')
    @patch('skilldoc.check_binary')
    def test_scan_skills_healthy(self, mock_check_binary, mock_extract_meta, 
                                 mock_parse, mock_isdir, mock_glob):
        """Test scanning healthy skills"""
        # Setup mocks
        mock_isdir.return_value = True
        mock_glob.return_value = ['/test/skills/git-skill/SKILL.md']
        mock_parse.return_value = {'description': 'A git skill'}
        mock_extract_meta.return_value = {
            'requires': {'bins': ['git']},
            'os': ['darwin']
        }
        mock_check_binary.return_value = '/usr/bin/git'
        
        with patch('platform.system', return_value='Darwin'):
            skills = skilldoc.scan_skills()
        
        assert len(skills) == 1
        skill = skills[0]
        assert skill['name'] == 'git-skill'
        assert skill['healthy'] is True
        assert skill['os_ok'] is True
        assert len(skill['issues']) == 0

    @patch('glob.glob')
    @patch('os.path.isdir')
    @patch('skilldoc.parse_frontmatter')
    @patch('skilldoc.extract_openclaw_meta')
    @patch('skilldoc.check_binary')
    def test_scan_skills_missing_binary(self, mock_check_binary, mock_extract_meta,
                                      mock_parse, mock_isdir, mock_glob):
        """Test scanning skills with missing binary"""
        # Setup mocks
        mock_isdir.return_value = True
        mock_glob.return_value = ['/test/skills/broken-skill/SKILL.md']
        mock_parse.return_value = {'description': 'A broken skill'}
        mock_extract_meta.return_value = {
            'requires': {'bins': ['nonexistent-binary']},
            'os': []
        }
        mock_check_binary.return_value = None  # Binary not found
        
        skills = skilldoc.scan_skills()
        
        assert len(skills) == 1
        skill = skills[0]
        assert skill['name'] == 'broken-skill'
        assert skill['healthy'] is False
        assert 'Missing binary: nonexistent-binary' in skill['issues']

    @patch('glob.glob')
    @patch('os.path.isdir')
    @patch('skilldoc.parse_frontmatter')
    @patch('skilldoc.extract_openclaw_meta')
    def test_scan_skills_os_mismatch(self, mock_extract_meta, mock_parse,
                                   mock_isdir, mock_glob):
        """Test scanning skills with OS mismatch"""
        # Setup mocks
        mock_isdir.return_value = True
        mock_glob.return_value = ['/test/skills/windows-skill/SKILL.md']
        mock_parse.return_value = {'description': 'A Windows-only skill'}
        mock_extract_meta.return_value = {
            'requires': {'bins': []},
            'os': ['win32']
        }
        
        with patch('platform.system', return_value='Darwin'):
            skills = skilldoc.scan_skills()
        
        assert len(skills) == 1
        skill = skills[0]
        assert skill['name'] == 'windows-skill'
        assert skill['healthy'] is False
        assert skill['os_ok'] is False
        assert any('OS mismatch' in issue for issue in skill['issues'])


class TestGetInstallHint:
    """Test install hint generation"""

    def test_get_install_hint_with_meta(self):
        """Test getting install hint from skill metadata"""
        skill = {
            'install_info': ['brew install git', 'apt install git']
        }
        
        hint = skilldoc.get_install_hint(skill)
        assert 'brew install git' in hint

    def test_get_install_hint_no_meta(self):
        """Test getting install hint without metadata"""
        skill = {
            'install_info': [],
            'required_bins': ['git']
        }
        
        with patch('platform.system', return_value='Darwin'):
            hint = skilldoc.get_install_hint(skill)
            # Should contain some installation suggestion
            assert len(hint) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
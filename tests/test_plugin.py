"""
Copyright 2019-2022 DataRobot, Inc. and its affiliates.
All rights reserved.
"""

import pytest
from mkdocs.structure.files import File
from mkdocs.structure.pages import Page

from mkdocs_redirects import plugin

existing_pages = [
    "README.md",
    "foo/README.md",
    "foo/bar/new.md",
    "foo/index.md",
    "foo/new.md",
    "index.md",
    "new.md",
    "new/README.md",
    "new/index.md",
    "100%.md",
    "the/fake.md",
]


@pytest.fixture
def run_redirect_test(monkeypatch, old_page, new_page, use_directory_urls):
    wrote = ()

    def write_html(site_dir, old_path, new_path, anchor_list):
        nonlocal wrote
        wrote = (old_path, new_path)

    monkeypatch.setattr(plugin, "write_html", write_html)

    plg = plugin.RedirectPlugin()
    plg.redirects = {old_page: new_page}
    plg.redirect_entries = plugin.build_redirect_entries(plg.redirects)
    plg.doc_pages = {
        path: File(path, "docs", "site", use_directory_urls) for path in existing_pages
    }
    plg.doc_pages["the/fake.md"].dest_path = "fake/destination/index.html"
    plg.doc_pages["the/fake.md"].url = plg.doc_pages["the/fake.md"]._get_url(use_directory_urls)

    config = dict(use_directory_urls=use_directory_urls, site_dir="site")
    for entry in plg.doc_pages.values():
        plg.on_page_content("", Page(None, entry, config), config, None)
    plg.on_post_build(config)

    return wrote


@pytest.fixture
def actual_redirect_target(run_redirect_test):
    assert bool(run_redirect_test)
    return run_redirect_test[1]


@pytest.fixture
def actual_written_file(run_redirect_test):
    assert bool(run_redirect_test)
    return run_redirect_test[0]


# Tuples of:
# * Left side of the redirect item
# * Right side of the redirect item
# * Expected destination URL written into the HTML file, use_directory_urls=False
# * Expected destination URL written into the HTML file, use_directory_urls=True
testdata = [
    ("old.md", "index.md", "index.html", "../"),
    ("old.md", "README.md", "index.html", "../"),
    ("old.md", "new.md", "new.html", "../new/"),
    ("old.md", "new/index.md", "new/index.html", "../new/"),
    ("old.md", "new/README.md", "new/index.html", "../new/"),
    ("foo/old.md", "foo/new.md", "new.html", "../new/"),
    ("foo/fizz/old.md", "foo/bar/new.md", "../bar/new.html", "../../bar/new/"),
    ("fizz/old.md", "foo/bar/new.md", "../foo/bar/new.html", "../../foo/bar/new/"),
    ("foo.md", "foo/index.md", "foo/index.html", "./"),
    ("foo.md", "foo/README.md", "foo/index.html", "./"),
    ("foo.md", "the/fake.md", "fake/destination/index.html", "../fake/destination/"),
    ("old.md", "index.md#hash", "index.html#hash", "../#hash"),
    ("old.md", "README.md#hash", "index.html#hash", "../#hash"),
    ("old.md", "new.md#hash", "new.html#hash", "../new/#hash"),
    ("old.md", "new/index.md#hash", "new/index.html#hash", "../new/#hash"),
    ("old.md", "new/README.md#hash", "new/index.html#hash", "../new/#hash"),
    ("foo/old.md", "foo/new.md#hash", "new.html#hash", "../new/#hash"),
    ("foo/fizz/old.md", "foo/bar/new.md#hash", "../bar/new.html#hash", "../../bar/new/#hash"),
    ("fizz/old.md", "foo/bar/new.md#hash", "../foo/bar/new.html#hash", "../../foo/bar/new/#hash"),
    ("foo.md", "foo/index.md#hash", "foo/index.html#hash", "./#hash"),
    ("foo.md", "foo/README.md#hash", "foo/index.html#hash", "./#hash"),
    ("foo.md", "the/fake.md#hash", "fake/destination/index.html#hash", "../fake/destination/#hash"),
    ("foo.md", "100%.md", "100%25.html", "../100%25/"),
    ("foo/fizz/old.md",) + ("https://example.org/old.md",) * 3,
]


@pytest.mark.parametrize("use_directory_urls", [False])
@pytest.mark.parametrize(["old_page", "new_page", "expected", "_"], testdata)
def test_relative_redirect_no_directory_urls(actual_redirect_target, expected, _):
    assert actual_redirect_target == expected


@pytest.mark.parametrize("use_directory_urls", [True])
@pytest.mark.parametrize(["old_page", "new_page", "_", "expected"], testdata)
def test_relative_redirect_directory_urls(actual_redirect_target, _, expected):
    assert actual_redirect_target == expected


# Tuples of:
# * Left side of the redirect item
# * Expected path of the written HTML file, use_directory_urls=False
# * Expected path of the written HTML file, use_directory_urls=True
testdata = [
    ("old.md", "old.html", "old/index.html"),
    ("foo/fizz/old.md", "foo/fizz/old.html", "foo/fizz/old/index.html"),
    ("foo/fizz/index.md", "foo/fizz/index.html", "foo/fizz/index.html"),
]


@pytest.mark.parametrize("use_directory_urls", [False])
@pytest.mark.parametrize("new_page", ["new.md"])
@pytest.mark.parametrize(["old_page", "expected", "_"], testdata)
def test_page_dest_path_no_directory_urls(actual_written_file, old_page, expected, _):
    assert actual_written_file == expected


@pytest.mark.parametrize("use_directory_urls", [True])
@pytest.mark.parametrize("new_page", ["new.md"])
@pytest.mark.parametrize(["old_page", "_", "expected"], testdata)
def test_page_dest_path_directory_urls(actual_written_file, old_page, _, expected):
    assert actual_written_file == expected


# ============================================================================
# Hash Redirect Test Suite
# ============================================================================

@pytest.fixture
def mock_write_html(monkeypatch):
    """Mock the write_html function to capture calls."""
    calls = []

    def mock_write(site_dir, old_path, new_path, anchor_list):
        calls.append((site_dir, old_path, new_path, anchor_list))

    monkeypatch.setattr(plugin, "write_html", mock_write)
    return calls


class TestHashRedirectGeneration:
    """Test suite for hash redirect generation functionality."""

    def test_gen_anchor_redirects_single_hash(self):
        """Test generating JavaScript redirects for a single hash."""
        anchor_list = [("#old-hash", "new-page.html#new-hash")]
        result = plugin.gen_anchor_redirects(anchor_list)

        expected = '''
        if (window.location.hash === "#old-hash") {
            location.href = "new-page.html#new-hash";
        }
        '''
        assert result.strip() == expected.strip()

    def test_gen_anchor_redirects_multiple_hashes(self):
        """Test generating JavaScript redirects for multiple hashes."""
        anchor_list = [
            ("#old-hash1", "new-page.html#new-hash1"),
            ("#old-hash2", "new-page.html#new-hash2"),
            ("#old-hash3", "new-page.html#new-hash3")
        ]
        result = plugin.gen_anchor_redirects(anchor_list)

        assert "if (window.location.hash === \"#old-hash1\")" in result
        assert "location.href = \"new-page.html#new-hash1\"" in result
        assert "if (window.location.hash === \"#old-hash2\")" in result
        assert "location.href = \"new-page.html#new-hash2\"" in result
        assert "if (window.location.hash === \"#old-hash3\")" in result
        assert "location.href = \"new-page.html#new-hash3\"" in result

    def test_gen_anchor_redirects_empty_list(self):
        """Test generating JavaScript redirects for empty anchor list."""
        result = plugin.gen_anchor_redirects([])
        assert result == ""


class TestHashRedirectJavaScriptInjection:
    """Test suite for JavaScript injection in existing pages."""

    @pytest.fixture
    def plugin_instance(self):
        """Create a plugin instance for testing."""
        plg = plugin.RedirectPlugin()
        plg.redirects = {
            "test-page.md#old-hash": "new-page.md#new-hash",
            "test-page.md#another-hash": "new-page.md#another-new-hash"
        }
        plg.redirect_entries = plugin.build_redirect_entries(plg.redirects)
        plg.doc_pages = {
            "test-page.md": File("test-page.md", "docs", "site", False),
            "new-page.md": File("new-page.md", "docs", "site", False)
        }
        return plg

    def test_on_page_content_with_hash_redirects(self, plugin_instance):
        """Test that JavaScript is injected for pages with hash redirects."""
        config = {"use_directory_urls": False}
        page = Page(None, plugin_instance.doc_pages["test-page.md"], config)

        original_html = "<html><body>Original content</body></html>"
        result = plugin_instance.on_page_content(original_html, page, config, None)

        # Should contain JavaScript redirects
        assert "<script>" in result
        assert "window.location.hash" in result
        assert "location.href" in result
        assert "old-hash" in result
        assert "new-hash" in result
        assert "another-hash" in result
        assert "another-new-hash" in result
        # Original content should be preserved
        assert "Original content" in result

    def test_on_page_content_without_hash_redirects(self, plugin_instance):
        """Test that no JavaScript is injected for pages without hash redirects."""
        config = {"use_directory_urls": False}
        page = Page(None, plugin_instance.doc_pages["new-page.md"], config)

        original_html = "<html><body>Original content</body></html>"
        result = plugin_instance.on_page_content(original_html, page, config, None)

        # Should return original HTML unchanged
        assert result == original_html

    def test_on_page_content_with_page_and_hash_redirects(self, plugin_instance):
        """Test JavaScript injection when both page and hash redirects exist."""
        plugin_instance.redirects["test-page.md"] = "new-page.md"
        plugin_instance.redirect_entries = plugin.build_redirect_entries(plugin_instance.redirects)

        config = {"use_directory_urls": False}
        page = Page(None, plugin_instance.doc_pages["test-page.md"], config)

        original_html = "<html><body>Original content</body></html>"
        result = plugin_instance.on_page_content(original_html, page, config, None)

        # Should still contain JavaScript for hash redirects
        assert "<script>" in result
        assert "window.location.hash" in result
        assert "Original content" in result


class TestHashRedirectHTMLGeneration:
    """Test suite for HTML file generation with hash redirects."""

    def test_no_directory_urls(self, mock_write_html):
        """Test HTML generation with multiple hash redirects."""
        plg = plugin.RedirectPlugin()
        plg.redirects = {
            "old-page.md#hash1": "new-page.md#new-hash1",
            "old-page.md#hash2": "new-page.md#new-hash2",
            "old-page.md#hash3": "new-page.md#new-hash3"
        }
        plg.redirect_entries = plugin.build_redirect_entries(plg.redirects)
        plg.doc_pages = {
            "new-page.md": File("new-page.md", "docs", "site", False)
        }

        config = {"use_directory_urls": False, "site_dir": "site"}
        plg.on_post_build(config)

        assert len(mock_write_html) == 1
        _, _, _, anchor_list = mock_write_html[0]
        assert anchor_list == [("#hash1", "new-page.html#new-hash1"), ("#hash2", "new-page.html#new-hash2"), ("#hash3", "new-page.html#new-hash3")]

    def test_directory_urls(self, mock_write_html):
        """Test HTML generation with multiple hash redirects."""
        plg = plugin.RedirectPlugin()
        plg.redirects = {
            "old-page.md#hash1": "new-page.md#new-hash1",
            "old-page.md#hash2": "new-page.md#new-hash2",
            "old-page.md#hash3": "new-page.md#new-hash3"
        }
        plg.redirect_entries = plugin.build_redirect_entries(plg.redirects)
        plg.doc_pages = {
            "new-page.md": File("new-page.md", "docs", "site", False)
        }

        config = {"use_directory_urls": True, "site_dir": "site"}
        plg.on_post_build(config)

        assert len(mock_write_html) == 1
        _, _, _, anchor_list = mock_write_html[0]
        assert anchor_list == [("#hash1", "../new-page/index.html/#new-hash1"), ("#hash2", "../new-page/index.html/#new-hash2"), ("#hash3", "../new-page/index.html/#new-hash3")]

    def test_external_url(self, mock_write_html):
        """Test hash redirects to external URLs."""
        plg = plugin.RedirectPlugin()

        plg.redirects = {"old-page.md#old-hash": "https://example.com/page#new-hash"}
        plg.redirect_entries = plugin.build_redirect_entries(plg.redirects)
        plg.doc_pages = {}

        config = {"use_directory_urls": False, "site_dir": "site"}
        plg.on_post_build(config)

        assert len(mock_write_html) == 1
        _, old_path, new_path, anchor_list = mock_write_html[0]
        assert anchor_list == [("#old-hash", "https://example.com/page#new-hash")]

    def test_empty_hash(self):
        """Test hash redirects with empty hash fragments."""
        redirects = {"old-page.md#": "new-page.md#"}
        result = plugin.build_redirect_entries(redirects)

        expected = {
            "old-page.md": {
                "hashes": [("#", "new-page.md#")],
                "overall": "new-page.md#"
            }
        }
        assert result == expected


class TestHashRedirectIntegration:
    """Integration tests for hash redirect functionality."""

    @pytest.fixture
    def integration_plugin(self):
        """Create a plugin instance for integration testing."""
        plg = plugin.RedirectPlugin()
        plg.redirects = {
            "old-page.md": "new-page.md",
            "old-page.md#section1": "new-page.md#new-section1",
            "old-page.md#section2": "new-page.md#new-section2",
            "another-page.md#old-hash": "external-page.md#new-hash"
        }
        plg.redirect_entries = plugin.build_redirect_entries(plg.redirects)
        plg.doc_pages = {
            "old-page.md": File("old-page.md", "docs", "site", False),
            "new-page.md": File("new-page.md", "docs", "site", False),
            "external-page.md": File("external-page.md", "docs", "site", False)
        }
        return plg

    def test_integration_hash_redirect_workflow(self, integration_plugin, mock_write_html):
        """Test the complete hash redirect workflow."""
        config = {"use_directory_urls": False, "site_dir": "site"}

        # Test page content injection
        page = Page(None, integration_plugin.doc_pages["old-page.md"], config)
        original_html = "<html><body>Content</body></html>"
        result = integration_plugin.on_page_content(original_html, page, config, None)

        # Should contain JavaScript for hash redirects
        assert "<script>" in result
        assert "section1" in result
        assert "section2" in result
        assert "new-section1" in result
        assert "new-section2" in result

        # Test post-build HTML generation
        integration_plugin.on_post_build(config)

        # Should generate HTML files for non-existing pages
        assert len(mock_write_html) == 1
        _, old_path, new_path, anchor_list = mock_write_html[0]
        assert old_path == "another-page.html"
        assert len(anchor_list) == 1
        assert anchor_list[0][0] == "#old-hash"

    def test_integration_directory_urls(self, integration_plugin, mock_write_html):
        """Test hash redirects with directory URLs enabled."""
        config = {"use_directory_urls": True, "site_dir": "site"}

        # Test page content injection
        page = Page(None, integration_plugin.doc_pages["old-page.md"], config)
        original_html = "<html><body>Content</body></html>"
        result = integration_plugin.on_page_content(original_html, page, config, None)

        # Should still contain JavaScript for hash redirects
        assert "<script>" in result
        assert "section1" in result
        assert "section2" in result

        # Test post-build HTML generation
        integration_plugin.on_post_build(config)

        # Should generate HTML files with directory structure
        assert len(mock_write_html) == 1
        _, old_path, new_path, anchor_list = mock_write_html[0]
        assert "another-page/index.html" in old_path
        assert len(anchor_list) == 1

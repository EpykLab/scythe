import unittest
from unittest.mock import Mock, patch
import json
from scythe.core.headers import HeaderExtractor


class TestHeaderExtractor(unittest.TestCase):
    """Unit tests for HeaderExtractor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = HeaderExtractor()
        self.mock_driver = Mock()
    
    def test_extract_target_version_success(self):
        """Test successful extraction of X-SCYTHE-TARGET-VERSION header."""
        # Mock performance logs with version header
        mock_logs = [
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '1.3.2',
                                    'Content-Type': 'text/html'
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        version = self.extractor.extract_target_version(self.mock_driver)
        
        self.assertEqual(version, '1.3.2')
        self.mock_driver.get_log.assert_called_once_with('performance')
    
    def test_extract_target_version_case_insensitive(self):
        """Test case-insensitive header extraction."""
        mock_logs = [
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/',
                                'headers': {
                                    'x-scythe-target-version': '2.0.1',  # lowercase
                                    'Content-Type': 'text/html'
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        version = self.extractor.extract_target_version(self.mock_driver)
        
        self.assertEqual(version, '2.0.1')
    
    def test_extract_target_version_no_header(self):
        """Test extraction when version header is not present."""
        mock_logs = [
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/',
                                'headers': {
                                    'Content-Type': 'text/html',
                                    'Server': 'nginx'
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        version = self.extractor.extract_target_version(self.mock_driver)
        
        self.assertIsNone(version)
    
    def test_extract_target_version_empty_logs(self):
        """Test extraction when no performance logs are available."""
        self.mock_driver.get_log.return_value = []
        
        version = self.extractor.extract_target_version(self.mock_driver)
        
        self.assertIsNone(version)
    
    def test_extract_target_version_with_url_filter(self):
        """Test extraction with URL filtering."""
        mock_logs = [
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://other.com/',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '1.0.0',
                                }
                            }
                        }
                    }
                })
            },
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://target.com/api',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '2.5.1',
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        # Should find version from target.com, not other.com
        version = self.extractor.extract_target_version(self.mock_driver, 'http://target.com')
        
        self.assertEqual(version, '2.5.1')
    
    def test_extract_target_version_malformed_json(self):
        """Test extraction handles malformed JSON gracefully."""
        mock_logs = [
            {
                'message': 'invalid json content'
            },
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '1.4.0',
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        version = self.extractor.extract_target_version(self.mock_driver)
        
        # Should skip malformed entry and find valid one
        self.assertEqual(version, '1.4.0')
    
    def test_extract_target_version_driver_exception(self):
        """Test extraction handles driver exceptions gracefully."""
        self.mock_driver.get_log.side_effect = Exception("Driver error")
        
        version = self.extractor.extract_target_version(self.mock_driver)
        
        self.assertIsNone(version)
    
    def test_find_version_header_exact_match(self):
        """Test _find_version_header with exact case match."""
        headers = {
            'X-SCYTHE-TARGET-VERSION': '3.1.4',
            'Content-Type': 'application/json'
        }
        
        version = self.extractor._find_version_header(headers)
        
        self.assertEqual(version, '3.1.4')
    
    def test_find_version_header_case_insensitive_match(self):
        """Test _find_version_header with case-insensitive match."""
        headers = {
            'x-scythe-target-version': '2.7.8',
            'content-type': 'application/json'
        }
        
        version = self.extractor._find_version_header(headers)
        
        self.assertEqual(version, '2.7.8')
    
    def test_find_version_header_mixed_case(self):
        """Test _find_version_header with mixed case."""
        headers = {
            'X-Scythe-Target-Version': '1.2.3-beta',
            'Content-Type': 'text/html'
        }
        
        version = self.extractor._find_version_header(headers)
        
        self.assertEqual(version, '1.2.3-beta')
    
    def test_find_version_header_not_found(self):
        """Test _find_version_header when header is not present."""
        headers = {
            'Content-Type': 'text/html',
            'Server': 'Apache'
        }
        
        version = self.extractor._find_version_header(headers)
        
        self.assertIsNone(version)
    
    def test_find_version_header_strips_whitespace(self):
        """Test _find_version_header strips whitespace from values."""
        headers = {
            'X-SCYTHE-TARGET-VERSION': '  2.0.0  '
        }
        
        version = self.extractor._find_version_header(headers)
        
        self.assertEqual(version, '2.0.0')
    
    def test_extract_all_headers_success(self):
        """Test successful extraction of all headers."""
        mock_logs = [
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '1.0.0',
                                    'Content-Type': 'text/html',
                                    'Server': 'nginx/1.18'
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        headers = self.extractor.extract_all_headers(self.mock_driver)
        
        expected_headers = {
            'X-SCYTHE-TARGET-VERSION': '1.0.0',
            'Content-Type': 'text/html',
            'Server': 'nginx/1.18'
        }
        
        self.assertEqual(headers, expected_headers)
    
    def test_extract_all_headers_empty(self):
        """Test extract_all_headers with no logs."""
        self.mock_driver.get_log.return_value = []
        
        headers = self.extractor.extract_all_headers(self.mock_driver)
        
        self.assertEqual(headers, {})
    
    def test_get_version_summary_with_versions(self):
        """Test get_version_summary with version data."""
        results = [
            {'target_version': '1.0.0'},
            {'target_version': '1.0.0'},
            {'target_version': '1.1.0'},
            {'target_version': None},  # No version
            {'target_version': '1.0.0'}
        ]
        
        summary = self.extractor.get_version_summary(results)
        
        expected_summary = {
            'total_results': 5,
            'results_with_version': 4,
            'unique_versions': ['1.0.0', '1.1.0'],
            'version_counts': {
                '1.0.0': 3,
                '1.1.0': 1
            }
        }
        
        self.assertEqual(summary['total_results'], expected_summary['total_results'])
        self.assertEqual(summary['results_with_version'], expected_summary['results_with_version'])
        self.assertEqual(set(summary['unique_versions']), set(expected_summary['unique_versions']))
        self.assertEqual(summary['version_counts'], expected_summary['version_counts'])
    
    def test_get_version_summary_no_versions(self):
        """Test get_version_summary with no version data."""
        results = [
            {'target_version': None},
            {'other_field': 'value'},
            {}
        ]
        
        summary = self.extractor.get_version_summary(results)
        
        expected_summary = {
            'total_results': 3,
            'results_with_version': 0,
            'unique_versions': [],
            'version_counts': {}
        }
        
        self.assertEqual(summary, expected_summary)
    
    def test_get_version_summary_empty_results(self):
        """Test get_version_summary with empty results list."""
        summary = self.extractor.get_version_summary([])
        
        expected_summary = {
            'total_results': 0,
            'results_with_version': 0,
            'unique_versions': [],
            'version_counts': {}
        }
        
        self.assertEqual(summary, expected_summary)
    
    @patch('scythe.core.headers.Options')
    def test_enable_logging_for_driver(self, mock_options):
        """Test that enable_logging_for_driver sets correct options."""
        mock_chrome_options = Mock()
        
        HeaderExtractor.enable_logging_for_driver(mock_chrome_options)
        
        # Verify the correct arguments and capabilities are set
        mock_chrome_options.add_argument.assert_any_call("--enable-logging")
        mock_chrome_options.add_argument.assert_any_call("--log-level=0")
        mock_chrome_options.set_capability.assert_called_once_with(
            "goog:loggingPrefs", 
            {"performance": "ALL"}
        )
    
    def test_extract_target_version_with_multiple_responses(self):
        """Test that most recent response is used when multiple responses exist."""
        mock_logs = [
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/old',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '1.0.0',
                                }
                            }
                        }
                    }
                })
            },
            {
                'message': json.dumps({
                    'message': {
                        'method': 'Network.responseReceived',
                        'params': {
                            'response': {
                                'url': 'http://example.com/new',
                                'headers': {
                                    'X-SCYTHE-TARGET-VERSION': '2.0.0',
                                }
                            }
                        }
                    }
                })
            }
        ]
        
        self.mock_driver.get_log.return_value = mock_logs
        
        # Should get most recent version (logs are processed in reverse order)
        version = self.extractor.extract_target_version(self.mock_driver)
        
        self.assertEqual(version, '2.0.0')


if __name__ == '__main__':
    unittest.main()
# Phase 1 Test Suite

This directory contains comprehensive test cases for Phase 1 of the GROW-RAG-MutualFundFAQAssistant data ingestion pipeline.

## Test Structure

### Unit Tests
- **`test_phase1_1_registry.py`** - Tests for Phase 1.1 (URL registry validation and scope filtering)
- **`test_phase1_2_fetch.py`** - Tests for Phase 1.2 (HTTP fetch, retries, robots.txt handling)
- **`test_phase1_3_normalize.py`** - Tests for Phase 1.3 (PDF/HTML → clean text normalization)
- **`test_phase1_4_manifest.py`** - Tests for Phase 1.4 (Manifest and provenance building)
- **`test_phase1_5_quality_gate.py`** - Tests for Phase 1.5 (Quality gate and handoff to Phase 2)

### Integration Tests
- **`test_integration_phase1.py`** - End-to-end tests for the complete Phase 1 pipeline

### Configuration
- **`conftest.py`** - Pytest configuration and shared fixtures
- **`__init__.py`** - Test package initialization

## Test Coverage

### Phase 1.1 - Registry Validation
- ✅ Schema validation
- ✅ URL format validation
- ✅ Duplicate ID detection
- ✅ Scope filtering
- ✅ Fetch list resolution
- ✅ Deterministic ordering

### Phase 1.2 - Fetch Engine
- ✅ HTTP request handling
- ✅ Retry mechanism
- ✅ Timeout handling
- ✅ Error handling
- ✅ File saving
- ✅ Content hashing

### Phase 1.3 - Normalization
- ✅ Content type detection
- ✅ HTML parsing (BeautifulSoup4)
- ✅ PDF parsing (PyMuPDF)
- ✅ Text cleaning
- ✅ Quality validation
- ✅ Batch processing

### Phase 1.4 - Manifest Building
- ✅ Document data merging
- ✅ Provenance tracking
- ✅ Statistics calculation
- ✅ Manifest generation
- ✅ File output

### Phase 1.5 - Quality Gate
- ✅ Coverage analysis
- ✅ Spot-check validation
- ✅ Content quality scoring
- ✅ Reproducibility checks
- ✅ Checklist generation
- ✅ Recommendations

## Running Tests

### Prerequisites
Install the required test dependencies:
```bash
pip install pytest pytest-mock pytest-cov
```

### Run All Tests
```bash
# From project root
python -m pytest tests/phase1/ -v

# From tests directory
python -m pytest phase1/ -v
```

### Run Specific Phase Tests
```bash
# Phase 1.1 only
python -m pytest tests/phase1/test_phase1_1_registry.py -v

# Phase 1.2 only
python -m pytest tests/phase1/test_phase1_2_fetch.py -v

# All unit tests (excluding integration)
python -m pytest tests/phase1/test_phase1_*.py -v -k "not integration"
```

### Run Integration Tests
```bash
python -m pytest tests/phase1/test_integration_phase1.py -v
```

### Run with Coverage
```bash
python -m pytest tests/phase1/ --cov=src/ingest --cov-report=html --cov-report=term
```

### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/phase1/ -m unit -v

# Integration tests only
python -m pytest tests/phase1/ -m integration -v

# Slow tests (if marked)
python -m pytest tests/phase1/ -m slow -v
```

## Test Data and Fixtures

The test suite uses comprehensive fixtures to provide:

- **Sample registry content** - Valid and invalid URL registries
- **Sample HTML content** - Realistic mutual fund web pages
- **Sample PDF content** - Mock PDF files for testing
- **Sample mutual fund text** - High-quality normalized content
- **Mock HTTP responses** - Simulated web server responses
- **Temporary directories** - Isolated test environments

## Mock Strategy

The tests use strategic mocking to:

1. **Avoid external dependencies** - HTTP requests are mocked
2. **Ensure deterministic results** - Random sampling is controlled
3. **Test error conditions** - Network failures, parsing errors
4. **Improve performance** - No real network calls

## Test Categories

### Unit Tests
- Test individual functions and classes in isolation
- Fast execution (< 1 second per test)
- Comprehensive coverage of edge cases
- Mock all external dependencies

### Integration Tests
- Test complete Phase 1 pipeline
- Test inter-phase dependencies
- Test file system interactions
- Test error propagation

## Performance Considerations

- **Unit tests**: Designed for fast execution
- **Integration tests**: May take longer due to file I/O
- **Mock usage**: Minimizes external dependencies
- **Parallel execution**: Tests can run in parallel

## Continuous Integration

These tests are designed to run in CI/CD environments:

- No external network dependencies
- Self-contained test data
- Deterministic results
- Clear pass/fail criteria

## Debugging Failed Tests

### Common Issues
1. **Import errors** - Ensure `src/` is in Python path
2. **File permissions** - Tests create temporary files
3. **Mock failures** - Check mock configuration
4. **Dependency issues** - Install required packages

### Debugging Tips
```bash
# Run with verbose output
python -m pytest tests/phase1/ -v -s

# Run specific test with debugging
python -m pytest tests/phase1/test_phase1_1_registry.py::TestScopeFilter::test_from_registry_with_exclude_doc_types -v -s

# Stop on first failure
python -m pytest tests/phase1/ -x -v

# Show local variables on failure
python -m pytest tests/phase1/ -v --tb=local
```

## Adding New Tests

When adding new tests:

1. **Follow naming convention** - `test_<functionality>_<scenario>`
2. **Use appropriate fixtures** - Leverage existing fixtures
3. **Add comprehensive assertions** - Test both success and failure cases
4. **Document test purpose** - Clear docstrings
5. **Mock external dependencies** - Keep tests isolated

## Test Maintenance

- **Regular updates** - Keep tests in sync with code changes
- **Coverage monitoring** - Aim for >90% coverage
- **Performance monitoring** - Ensure tests remain fast
- **Dependency updates** - Update mocks when dependencies change

## Troubleshooting

### PyYAML Issues
If PyYAML is not available, registry tests will be skipped. Install with:
```bash
pip install PyYAML
```

### BeautifulSoup4 Issues
HTML parsing tests require BeautifulSoup4. Install with:
```bash
pip install beautifulsoup4
```

### PyMuPDF Issues
PDF parsing tests require PyMuPDF. Install with:
```bash
pip install PyMuPDF
```

### Trafilatura Issues
Advanced text extraction tests require trafilatura. Install with:
```bash
pip install trafilatura
```

## Expected Test Results

A healthy test suite should show:
- ✅ All unit tests passing
- ✅ All integration tests passing
- ✅ High code coverage (>90%)
- ✅ Fast execution time
- ✅ No external dependencies required

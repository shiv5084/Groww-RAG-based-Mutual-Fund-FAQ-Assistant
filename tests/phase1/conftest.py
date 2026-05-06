"""Pytest configuration for Phase 1 tests."""

import pytest
import tempfile
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_registry_content():
    """Sample registry content for testing."""
    return {
        "current_iteration_scope": {
            "exclude_doc_types": ["pdf", "video"]
        },
        "urls": [
            {
                "id": "URL-001",
                "url": "https://example.com/fund1",
                "doc_type": "scheme_page",
                "scheme": None,
                "source_owner": "AMC",
                "verification_status": "verified"
            },
            {
                "id": "URL-002",
                "url": "https://example.com/fund2",
                "doc_type": "factsheet",
                "scheme": None,
                "source_owner": "AMC",
                "verification_status": "verified"
            },
            {
                "id": "URL-003",
                "url": "https://sebi.gov.in/guidance",
                "doc_type": "regulatory_guidance",
                "scheme": None,
                "source_owner": "SEBI",
                "verification_status": "pending_verification"
            }
        ]
    }


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HDFC Mutual Fund - Large Cap Fund</title>
        <meta name="description" content="Invest in HDFC Large Cap Fund for long-term growth">
    </head>
    <body>
        <header>
            <nav>
                <div class="logo">HDFC Mutual Fund</div>
            </nav>
        </header>
        
        <main>
            <section class="fund-overview">
                <h1>HDFC Large Cap Fund - Direct Plan</h1>
                <div class="fund-details">
                    <h2>Investment Objective</h2>
                    <p>The primary investment objective of the scheme is to generate long-term capital appreciation 
                    by investing in a diversified portfolio of predominantly large-cap equity and equity-related securities.</p>
                    
                    <h2>Key Features</h2>
                    <ul>
                        <li>Suitable for long-term wealth creation</li>
                        <li>Invests in established large-cap companies</li>
                        <li>Professional fund management</li>
                        <li>Regular NAV updates and portfolio rebalancing</li>
                        <li>Systematic Investment Plan (SIP) available</li>
                    </ul>
                    
                    <h2>Risk Factors</h2>
                    <p>Investors should understand that mutual fund investments are subject to market risks. 
                    The NAV of the scheme may fluctuate due to changes in the market value of the portfolio.</p>
                    
                    <h2>Who Should Invest?</h2>
                    <p>This fund is suitable for investors seeking:</p>
                    <ul>
                        <li>Long-term capital appreciation (3-5 years or more)</li>
                        <li>Exposure to large-cap equity investments</li>
                        <li>Professional management of equity portfolio</li>
                        <li>Regular income through dividends (optional)</li>
                    </ul>
                </div>
            </section>
            
            <section class="performance">
                <h2>Fund Performance</h2>
                <p>The fund has consistently delivered returns in line with large-cap benchmarks over the past 5 years. 
                The fund manager follows a disciplined investment approach focusing on quality companies with strong fundamentals.</p>
            </section>
        </main>
        
        <footer>
            <p>© 2023 HDFC Mutual Fund. All rights reserved.</p>
            <p>This is for informational purposes only. Please read the offer document carefully before investing.</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing (mock)."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Mutual Fund PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000204 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n299\n%%EOF"


@pytest.fixture
def sample_mutual_fund_text():
    """Sample mutual fund text content for testing."""
    return """
    HDFC Mutual Fund offers comprehensive investment solutions for Indian investors. 
    The HDFC Large Cap Fund is a popular equity scheme that focuses on investing in 
    large-capitalization companies with strong fundamentals and market leadership positions.
    
    Key Investment Features:
    - Investment Objective: Long-term capital appreciation through large-cap equity investments
    - Minimum Investment: ₹500 for SIP, ₹5000 for lump sum
    - Expense Ratio: 1.25% (Direct Plan)
    - Fund Manager: Mr. Prashant Jain
    - AUM: ₹25,000 crores (as of December 2023)
    
    Risk Considerations:
    This fund is suitable for investors with moderate to high risk tolerance. 
    The scheme invests primarily in equity and equity-related securities, which are subject to market risks.
    
    Systematic Investment Plan (SIP):
    Investors can invest regularly through SIP with minimum monthly investment of ₹500. 
    SIP helps in rupee cost averaging and disciplined investing approach.
    
    Tax Benefits:
    Equity-oriented mutual funds enjoy tax exemption on long-term capital gains (holding period > 1 year) 
    under Section 10(38) of the Income Tax Act, subject to conditions.
    
    NAV and Performance:
    The Net Asset Value (NAV) is calculated and published daily. 
    Historical performance shows consistent returns compared to benchmark indices.
    """


@pytest.fixture
def mock_http_response():
    """Mock HTTP response for testing."""
    from unittest.mock import Mock
    
    response = Mock()
    response.status_code = 200
    response.headers = {
        "content-type": "text/html",
        "content-length": "1000"
    }
    response.url = "https://example.com/fund"
    response.content = b"<html><body><h1>Test Content</h1></body></html>"
    response.raise_for_status.return_value = None
    return response


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow

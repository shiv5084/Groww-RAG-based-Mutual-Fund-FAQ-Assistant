"""
Intent router for Phase 4 query classification.

Lightweight classifier to determine if query should go to:
- Advisory/Comparative → Refusal template
- Performance/Returns → Factsheet URL only  
- Factual/Scheme/Process → Full RAG
"""

import re
from typing import Dict, List, Tuple
from .types import RouteLabel


class IntentRouter:
    """Lightweight intent router for query classification."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the intent router.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
        self._compile_patterns()
    
    def _default_config(self) -> Dict:
        """Default routing configuration."""
        return {
            "advisory_patterns": [
                r"\b(better|best|good|bad|worst|recommend|advice|suggest|should|which|compare|vs|versus|choose|pick|select|prefer|opinion|think|believe)\b",
                r"\b(invest|put money|allocate|portfolio|diversify|risk appetite|financial goals|investment strategy)\b",
                r"\b(worth it|good investment|bad investment|should i|can i|is it)\b",
                r"\b(advantage|disadvantage|pro|con|benefit|drawback)\b"
            ],
            "performance_patterns": [
                r"\b(returns|performance|profit|gain|loss|growth|decline|increase|decrease|rise|fall)\b",
                r"\b(nav|net asset value|price|cost|expense|fee|charge|load|exit load|entry load)\b",
                r"\b(historical|past|year|month|quarter|annual|monthly|1y|3y|5y|10y)\b",
                r"\b(percentage|percent|%|roi|irr|xirr|cagr)\b",
                r"\b(top performing|best performing|highest|lowest|ranking|rating)\b"
            ],
            "factual_patterns": [
                r"\b(what|how|where|when|who|why|explain|describe|define|details|information|about)\b",
                r"\b(scheme|plan|option|category|type|class|fund|amc|asset management|company)\b",
                r"\b(process|procedure|steps|how to|way to|method|approach)\b",
                r"\b(document|documentary|kyc|pan|aadhaar|verification|registration|account|open)\b",
                r"\b(tax|taxation|deduction|benefit|section|80c|80d|10|10da)\b",
                r"\b(lock-in|maturity|redemption|withdraw|switch|purchase|buy|sell)\b"
            ],
            "scheme_specific_patterns": [
                r"\b(elss|ppf|epf|nps|scss|ssy|fd|rd|mutual fund|sip|lumpsum|swp|stp)\b",
                r"\b(equity|debt|hybrid|balanced|arbitrage|gold|international|sector|thematic)\b",
                r"\b(large cap|mid cap|small cap|multi cap|flexi cap)\b"
            ],
            "refusal_keywords": [
                r"\b(advice|recommendation|suggestion|guidance|counsel|consult)\b",
                r"\b(financial planning|investment planning|portfolio advice)\b"
            ]
        }
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        self.compiled_patterns = {
            "advisory": [re.compile(pattern, re.IGNORECASE) for pattern in self.config["advisory_patterns"]],
            "performance": [re.compile(pattern, re.IGNORECASE) for pattern in self.config["performance_patterns"]],
            "factual": [re.compile(pattern, re.IGNORECASE) for pattern in self.config["factual_patterns"]],
            "scheme_specific": [re.compile(pattern, re.IGNORECASE) for pattern in self.config["scheme_specific_patterns"]],
            "refusal": [re.compile(pattern, re.IGNORECASE) for pattern in self.config["refusal_keywords"]]
        }
    
    def classify(self, query: str) -> RouteLabel:
        """
        Classify query intent.
        
        Args:
            query: User query string
            
        Returns:
            RouteLabel: Classification result
        """
        query_lower = query.lower().strip()
        
        # Check for explicit refusal keywords first
        if self._match_patterns(query_lower, "refusal"):
            return RouteLabel.ADVISORY
        
        # Score each category
        scores = {
            RouteLabel.ADVISORY: self._calculate_score(query_lower, "advisory"),
            RouteLabel.PERFORMANCE: self._calculate_score(query_lower, "performance"),
            RouteLabel.FACTUAL: self._calculate_score(query_lower, "factual")
        }
        
        # Apply heuristics for edge cases
        if self._match_patterns(query_lower, "scheme_specific"):
            # Scheme-specific queries are usually factual unless explicitly advisory
            if scores[RouteLabel.ADVISORY] > scores[RouteLabel.FACTUAL]:
                return RouteLabel.ADVISORY
            else:
                return RouteLabel.FACTUAL
        
        # Return highest scoring category
        return max(scores, key=scores.get)
    
    def _match_patterns(self, query: str, pattern_type: str) -> bool:
        """Check if query matches any pattern of given type."""
        return any(pattern.search(query) for pattern in self.compiled_patterns[pattern_type])
    
    def _calculate_score(self, query: str, pattern_type: str) -> float:
        """Calculate confidence score for pattern type."""
        matches = 0
        total_patterns = len(self.compiled_patterns[pattern_type])
        
        for pattern in self.compiled_patterns[pattern_type]:
            if pattern.search(query):
                matches += 1
        
        return matches / total_patterns if total_patterns > 0 else 0.0
    
    def get_classification_details(self, query: str) -> Dict:
        """
        Get detailed classification information.
        
        Args:
            query: User query string
            
        Returns:
            Dict with classification details and confidence scores
        """
        query_lower = query.lower().strip()
        
        scores = {
            "advisory": self._calculate_score(query_lower, "advisory"),
            "performance": self._calculate_score(query_lower, "performance"),
            "factual": self._calculate_score(query_lower, "factual")
        }
        
        route_label = self.classify(query)
        
        return {
            "query": query,
            "route_label": route_label.value,
            "confidence": scores[route_label.value],
            "all_scores": scores,
            "matched_patterns": self._get_matched_patterns(query_lower)
        }
    
    def _get_matched_patterns(self, query: str) -> Dict[str, List[str]]:
        """Get list of matched patterns for debugging."""
        matched = {}
        for pattern_type, patterns in self.compiled_patterns.items():
            if pattern_type not in ["advisory", "performance", "factual"]:
                continue
            
            matched_patterns = []
            for i, pattern in enumerate(patterns):
                if pattern.search(query):
                    matched_patterns.append(f"{pattern_type}_{i}")
            
            matched[pattern_type] = matched_patterns
        
        return matched
    
    def batch_classify(self, queries: List[str]) -> List[Dict]:
        """
        Classify multiple queries.
        
        Args:
            queries: List of query strings
            
        Returns:
            List of classification results
        """
        return [self.get_classification_details(query) for query in queries]

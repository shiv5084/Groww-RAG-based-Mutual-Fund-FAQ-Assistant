"""
Context packer for Phase 4 LLM context preparation.

Builds context bundles with system prompts, user context, and citations
for LLM generation based on route and retrieval results.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .types import RouteLabel, RetrievalResult, ContextBundle


class ContextPacker:
    """Context packer for building LLM-ready context bundles."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize context packer.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = {**self._default_config(), **(config or {})}
        # Load educational links from YAML file
        self._load_educational_links()
    
    def _default_config(self) -> Dict:
        """Default context packing configuration."""
        return {
            "system_prompts": {
                RouteLabel.ADVISORY: (
                    "You are a mutual fund information assistant. You must NOT provide investment advice, "
                    "recommendations, or comparisons. If the user asks for advice, recommendations, or comparisons, "
                    "politely decline and suggest they consult a financial advisor. Provide only factual information "
                    "about mutual fund processes and documentation."
                ),
                RouteLabel.PERFORMANCE: (
                    "You are a mutual fund information assistant. For performance/returns queries, provide only "
                    "a brief factual response and direct the user to the official factsheet for complete information. "
                    "Do not provide performance analysis or comparisons."
                ),
                RouteLabel.FACTUAL: (
                    "You are a mutual fund information assistant. Provide factual answers based only on the "
                    "provided context. If the context doesn't contain sufficient information, state this clearly "
                    "and suggest consulting official documentation. Never provide investment advice or recommendations."
                )
            },
            "max_context_length": 4000,  # Maximum context length in characters
            "include_metadata": True,  # Include chunk metadata in context
            "citation_format": "url",  # How to format citations: "url" or "chunk_id"
            "educational_links": []  # Will be loaded from YAML file
        }
    
    def _load_educational_links(self):
        """Load educational links from YAML file."""
        try:
            import yaml
            from pathlib import Path
            
            yaml_path = Path(__file__).parent.parent.parent / "doc" / "templates" / "refusal_educational_links.yaml"
            
            if yaml_path.exists():
                with open(yaml_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if 'links' in data:
                        # Extract URLs from the links dictionary
                        # Extract URLs from the links dictionary
                        educational_links = []
                        for link_key, link_data in data['links'].items():
                            if isinstance(link_data, dict) and 'url' in link_data:
                                educational_links.append(link_data['url'])
                        self.config["educational_links"] = educational_links
                        if 'default_refusal_template' in data:
                            self.config["default_refusal_template"] = data['default_refusal_template']
            else:
                logger.warning(f"Educational links file not found: {yaml_path}")
        except Exception as e:
            logger.warning(f"Failed to load educational links: {e}")
    
    def build_context(self, 
                      query: str, 
                      route_label: RouteLabel,
                      retrieval_results: List[RetrievalResult] = None) -> ContextBundle:
        """
        Build context bundle for LLM generation.
        
        Args:
            query: User query string
            route_label: Query route classification
            retrieval_results: List of retrieval results
            
        Returns:
            ContextBundle with all necessary context
        """
        retrieval_results = retrieval_results or []
        
        # Select primary and secondary chunks
        primary_chunk, secondary_chunks = self._select_chunks(retrieval_results)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(route_label, primary_chunk)
        
        # Build user context
        user_context = self._build_user_context(query, primary_chunk, secondary_chunks)
        
        # Determine citation URL
        citation_url = self._determine_citation_url(primary_chunk)
        
        # Create context bundle
        context_bundle = ContextBundle(
            query=query,
            route_label=route_label,
            primary_chunk=primary_chunk,
            secondary_chunks=secondary_chunks,
            system_prompt=system_prompt,
            user_context=user_context,
            citation_url=citation_url,
            created_at=datetime.now()
        )
        
        return context_bundle
    
    def _select_chunks(self, retrieval_results: List[RetrievalResult]) -> Tuple[Optional[RetrievalResult], List[RetrievalResult]]:
        """
        Select primary and secondary chunks from retrieval results.
        
        Args:
            retrieval_results: List of retrieval results
            
        Returns:
            Tuple of (primary_chunk, secondary_chunks)
        """
        if not retrieval_results:
            return None, []
        
        # Primary chunk is the first/highest scoring result
        primary_chunk = retrieval_results[0]
        secondary_chunks = retrieval_results[1:]  # Remaining chunks
        
        return primary_chunk, secondary_chunks
    
    def _build_system_prompt(self, route_label: RouteLabel, primary_chunk: Optional[RetrievalResult]) -> str:
        """
        Build system prompt based on route and context.
        
        Args:
            route_label: Query route classification
            primary_chunk: Primary retrieval result
            
        Returns:
            System prompt string
        """
        # Handle both enum and string keys
        system_prompts = self.config["system_prompts"]
        if route_label in system_prompts:
            base_prompt = system_prompts[route_label]
        elif route_label.value in system_prompts:
            base_prompt = system_prompts[route_label.value]
        else:
            raise KeyError(f"System prompt not found for route: {route_label}")
        
        # Add route-specific instructions
        if route_label == RouteLabel.ADVISORY:
            base_prompt += "\n\nIMPORTANT: You must refuse to provide any investment advice, recommendations, or comparisons."
            base_prompt += "\nIf the user asks for advice, respond with the refusal template and educational links."
        
        elif route_label == RouteLabel.PERFORMANCE:
            base_prompt += "\n\nIMPORTANT: For performance queries, provide only brief factual information."
            base_prompt += "\nAlways include the official factsheet URL for complete performance data."
        
        elif route_label == RouteLabel.FACTUAL:
            if primary_chunk:
                base_prompt += f"\n\nContext source: {primary_chunk.source_url}"
                base_prompt += "\nUse only the provided context to answer. If insufficient, state this clearly."
        
        return base_prompt
    
    def _build_user_context(self, 
                           query: str, 
                           primary_chunk: Optional[RetrievalResult],
                           secondary_chunks: List[RetrievalResult]) -> str:
        """
        Build user context with query and retrieved chunks.
        
        Args:
            query: User query string
            primary_chunk: Primary retrieval result
            secondary_chunks: Secondary retrieval results
            
        Returns:
            User context string
        """
        context_parts = [f"User Query: {query}"]
        
        if primary_chunk:
            context_parts.append("\nPrimary Context:")
            context_parts.append(self._format_chunk(primary_chunk))
        
        if secondary_chunks:
            context_parts.append("\nAdditional Context:")
            for i, chunk in enumerate(secondary_chunks, 1):
                context_parts.append(f"Context {i}:")
                context_parts.append(self._format_chunk(chunk))
        
        # Combine and truncate if necessary
        full_context = "\n".join(context_parts)
        
        if len(full_context) > self.config["max_context_length"]:
            # Truncate from the end (secondary context first)
            truncated = full_context[:self.config["max_context_length"]-3] + "..."
            return truncated
        
        return full_context
    
    def _format_chunk(self, chunk: RetrievalResult) -> str:
        """
        Format a retrieval result for context.
        
        Args:
            chunk: Retrieval result
            
        Returns:
            Formatted chunk string
        """
        formatted = f"Text: {chunk.text}"
        
        if self.config["include_metadata"]:
            metadata_parts = []
            
            if chunk.source_url:
                metadata_parts.append(f"Source: {chunk.source_url}")
            
            if chunk.doc_type:
                metadata_parts.append(f"Type: {chunk.doc_type}")
            
            if chunk.score is not None:
                metadata_parts.append(f"Score: {chunk.score:.3f}")
            
            if metadata_parts:
                formatted += f"\nMetadata: {' | '.join(metadata_parts)}"
        
        return formatted
    
    def _determine_citation_url(self, primary_chunk: Optional[RetrievalResult]) -> Optional[str]:
        """
        Determine the citation URL to display.
        
        Args:
            primary_chunk: Primary retrieval result
            
        Returns:
            Citation URL or None
        """
        if not primary_chunk:
            return None
        
        if self.config["citation_format"] == "url":
            return primary_chunk.source_url
        elif self.config["citation_format"] == "chunk_id":
            return f"chunk:{primary_chunk.chunk_id}"
        else:
            return primary_chunk.source_url
    
    def build_refusal_response(self, query: str) -> ContextBundle:
        """
        Build context bundle for advisory refusal response.
        
        Args:
            query: User query string
            
        Returns:
            ContextBundle for refusal response
        """
        # Use default template if available, otherwise build from educational links
        if "default_refusal_template" in self.config and self.config["educational_links"]:
            educational_url = self.config["educational_links"][0]  # Use first link
            refusal_prompt = self.config["default_refusal_template"].format(educational_url=educational_url)
        else:
            # Build refusal prompt from educational links
            links_text = ""
            for i, link in enumerate(self.config["educational_links"], 1):
                links_text += f"- Educational Resource {i}: {link}\n"
            
            refusal_prompt = (
                "I understand you're looking for guidance on mutual fund investments. "
                "However, I cannot provide investment advice, recommendations, or comparisons as I'm not a financial advisor. "
                "For personalized investment advice, please consult a qualified financial advisor who can assess your specific "
                f"financial situation, risk tolerance, and investment goals.\n\n"
                "For official information about mutual funds, you may refer to:\n"
                f"{links_text.strip()}"
            )
        
        return ContextBundle(
            query=query,
            route_label=RouteLabel.ADVISORY,
            system_prompt=self.config["system_prompts"].get(RouteLabel.ADVISORY) or self.config["system_prompts"].get(RouteLabel.ADVISORY.value),
            user_context=f"User Query: {query}\n\nResponse: {refusal_prompt}",
            citation_url=None,
            created_at=datetime.now()
        )
    
    def build_performance_response(self, 
                                  query: str, 
                                  factsheet_url: str) -> ContextBundle:
        """
        Build context bundle for performance-focused response.
        
        Args:
            query: User query string
            factsheet_url: URL to the relevant factsheet
            
        Returns:
            ContextBundle for performance response
        """
        performance_prompt = (
            "For detailed performance information, returns data, and historical performance, "
            "please refer to the official factsheet. This document contains comprehensive performance "
            "metrics, risk measures, and historical data as required by regulations."
        )
        
        return ContextBundle(
            query=query,
            route_label=RouteLabel.PERFORMANCE,
            system_prompt=self.config["system_prompts"].get(RouteLabel.PERFORMANCE) or self.config["system_prompts"].get(RouteLabel.PERFORMANCE.value),
            user_context=f"User Query: {query}\n\nResponse: {performance_prompt}\n\nFactsheet: {factsheet_url}",
            citation_url=factsheet_url,
            created_at=datetime.now()
        )
    
    def validate_context_bundle(self, bundle: ContextBundle) -> Dict[str, Any]:
        """
        Validate a context bundle for completeness.
        
        Args:
            bundle: Context bundle to validate
            
        Returns:
            Validation result with any issues
        """
        issues = []
        
        # Check required fields
        if not bundle.query:
            issues.append("Missing query")
        
        if not bundle.system_prompt:
            issues.append("Missing system prompt")
        
        if not bundle.user_context:
            issues.append("Missing user context")
        
        # Route-specific validation
        if bundle.route_label == RouteLabel.FACTUAL and not bundle.primary_chunk:
            issues.append("Factual queries require primary chunk")
        
        if bundle.route_label == RouteLabel.PERFORMANCE and not bundle.citation_url:
            issues.append("Performance queries require citation URL")
        
        # Length validation
        if len(bundle.user_context) > self.config["max_context_length"]:
            issues.append(f"User context exceeds max length ({len(bundle.user_context)} > {self.config['max_context_length']})")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "bundle_size": len(str(bundle))
        }

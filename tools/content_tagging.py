# Standard library imports
import logging
import re
from typing import Dict, List, Any, Optional, Set

class ContentTaggingTool:
    """Tool for categorizing and tagging content for better organization and discovery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize category dictionaries
        self._initialize_categories()
        
    def _initialize_categories(self):
        """Initialize predefined categories and keywords"""
        self.category_keywords = {
            "technology": ["tech", "ai", "software", "digital", "gadget", "innovation", "automation"],
            "business": ["entrepreneur", "startup", "business", "marketing", "sales", "strategy"],
            "education": ["learn", "tutorial", "education", "skills", "knowledge", "teaching"],
            "entertainment": ["fun", "humor", "comedy", "entertainment", "amusing", "laughter"],
            "lifestyle": ["life", "daily", "routines", "habits", "wellness", "living"],
            "health": ["fitness", "health", "wellness", "nutrition", "exercise", "diet"],
            "travel": ["travel", "destination", "journey", "adventure", "vacation", "explore"]
        }
        
    def generate_hashtags(self, content: str, platform: str, count: int = 10) -> List[str]:
        """
        Generate relevant hashtags based on content and target platform
        
        Args:
            content: The content text to analyze
            platform: Target platform for the hashtags
            count: Number of hashtags to generate
            
        Returns:
            List of recommended hashtags
        """
        self.logger.info(f"Generating hashtags for platform: {platform}")
        
        # Convert content to lowercase for better matching
        content_lower = content.lower()
        
        # Find matching categories
        matching_categories = []
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    if category not in matching_categories:
                        matching_categories.append(category)
        
        # Generate platform-specific hashtags
        platform_hashtags = []
        
        if platform.lower() == "instagram":
            platform_hashtags = ["#instadaily", "#instagood", "#igdaily"]
        elif platform.lower() == "tiktok":
            platform_hashtags = ["#tiktok", "#tiktokviral", "#foryou", "#fyp"]
        elif platform.lower() == "youtube":
            platform_hashtags = ["#youtubeshorts", "#subscribe", "#youtube"]
        elif platform.lower() == "linkedin":
            platform_hashtags = ["#linkedin", "#networking", "#professional"]
            
        # Generate category-specific hashtags
        category_hashtags = []
        for category in matching_categories:
            if category == "technology":
                category_hashtags.extend(["#tech", "#innovation", "#techtrends", "#digitallife"])
            elif category == "business":
                category_hashtags.extend(["#business", "#entrepreneur", "#success", "#growth"])
            elif category == "education":
                category_hashtags.extend(["#learning", "#education", "#knowledge", "#skills"])
            elif category == "entertainment":
                category_hashtags.extend(["#fun", "#entertainment", "#laugh", "#enjoyment"])
            elif category == "lifestyle":
                category_hashtags.extend(["#lifestyle", "#daily", "#life", "#livingwell"])
            elif category == "health":
                category_hashtags.extend(["#health", "#wellness", "#fitness", "#healthy"])
            elif category == "travel":
                category_hashtags.extend(["#travel", "#adventure", "#explore", "#journey"])
        
        # Find content-specific keywords
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content_lower)
        word_counts = {}
        for word in words:
            if word in word_counts:
                word_counts[word] += 1
            else:
                word_counts[word] = 1
                
        # Sort words by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        top_words = [word for word, count in sorted_words[:5]]
        
        # Create content-specific hashtags
        content_hashtags = [f"#{word}" for word in top_words]
        
        # Combine all hashtags and remove duplicates
        all_hashtags = platform_hashtags + category_hashtags + content_hashtags
        unique_hashtags = list(dict.fromkeys(all_hashtags))
        
        # Return the requested number of hashtags
        return unique_hashtags[:count]
    
    def identify_categories(self, content: str) -> Dict[str, float]:
        """
        Identify content categories with confidence scores
        
        Args:
            content: The content text to analyze
            
        Returns:
            Dictionary mapping categories to confidence scores
        """
        self.logger.info("Identifying content categories")
        
        # Convert content to lowercase for better matching
        content_lower = content.lower()
        
        # Calculate category matches
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            matches = 0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    matches += 1
            
            if matches > 0:
                # Calculate a simple confidence score based on matches
                confidence = min(1.0, matches / len(keywords) * 1.5)
                category_scores[category] = round(confidence, 2)
        
        # Ensure we have at least one category
        if not category_scores:
            category_scores["general"] = 0.5
            
        return category_scores
    
    def create_metadata(self, content: str, title: str, categories: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Create metadata for improved content discoverability
        
        Args:
            content: The content text to analyze
            title: Content title
            categories: Optional pre-identified categories
            
        Returns:
            Dictionary of metadata
        """
        self.logger.info("Creating content metadata")
        
        # Identify categories if not provided
        if categories is None:
            categories = self.identify_categories(content)
            
        # Extract keywords from content
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        word_set = set(words)
        
        # Filter out common words
        common_words = {"this", "that", "with", "from", "have", "will", "been", "when", "what", "where", "which"}
        keywords = [word for word in word_set if word not in common_words]
        
        # Generate a description
        description = title
        if len(content) > 200:
            description += " - " + content[:197] + "..."
        else:
            description += " - " + content
            
        # Create metadata
        metadata = {
            "title": title,
            "description": description,
            "categories": categories,
            "primary_category": max(categories.items(), key=lambda x: x[1])[0] if categories else "general",
            "keywords": keywords[:20],
            "content_length": len(content),
            "word_count": len(words)
        }
        
        return metadata
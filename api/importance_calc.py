def calculate_importance(content, category='observation'):
    """Calculate importance score for content.
    Returns a float between 0.1 and 1.0.
    
    Factors considered:
     - Content length and complexity
     - Emotional weight (exclamation marks, caps)
     - Presence of proper nouns and key entities
    """
    if not content:
        return 0.5
    content_lower = content.lower()
    score = 0.5  # base
    
    # category weight
    category_weights = {
        'world': 0.15,
        'experience': 0.12,
        'opinion': 0.05,
        'observation': 0.05
    }
    score += category_weights.get(category, 0.05)
    
    # length factor - sweet spot around 100-500 chars
    length = len(content)
    if length > 50:
        score += min(0.1, length / 1000)  # +0.1 max for very long content
    elif length < 20:
        score -= 0.1  # penalize very short
    
    # keyword bonuses
    high_importance_keywords = ['important', 'critical', 'urgent', 'essential', 'vital', 'key', 'significant',
                                 'remember', 'never forget', 'always', 'crucial', 'priority',
                                 'deadline', 'warning', 'alert', 'required', 'mandatory']
    for kw in high_importance_keywords:
        if kw in content_lower:
            score += 0.1
    
    # person/place references suggest higher importance
    proper_nouns = len(re.findall(r'[A-Z][a-z]+', content))
    score += min(0.1, proper_nouns * 0.02)
    
    return min(1.0, max(0.1, score))

def get_importance_level(importance: float) -> str:
    """Get human-readable importance level"""
    if importance >= 0.8:
        return 'critical'
    elif importance >= 0.6:
        return 'high'
    elif importance >= 0.4:
        return 'medium'
    elif importance >= 0.2:
        return 'low'
    else:
        return 'fleeting'

# -*- coding: utf-8 -*-
"""
Importance calculator for memories - analyzes content to determine significance
"""
import re
from typing import Optional

def calculate_importance(content: str, category: str = 'observation') -> float:
    """
    Calculate importance score (0.0-1.0) based on content analysis.

    Factors:
    - Content length (longer = slightly more important, up to 0.1)
    - Keywords indicating importance (decisions, fixes, critical info)
    - Category weight (world/experience > opinion/observation)
    - Structured data presence (code, urls, specific names)
    - Question vs statement (questions slightly less important)
    - Emotional weight (exclamation marks, caps)
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

    # high importance keywords
    high_keywords = [
        'fix', 'fixed', 'bug', 'error', 'issue', 'solved', 'solution',
        'deploy', 'production', 'critical', 'important', 'breaking',
        'api', 'endpoint', 'token', 'key', 'password', 'secret',
        'install', 'setup', 'configure', 'migration', 'upgrade',
        'remember', 'never forget', 'always', 'must', 'need to',
        'discovered', 'found out', 'learned', 'realized',
        'vulnerability', 'security', 'exploit', 'patch'
    ]
    for kw in high_keywords:
        if kw in content_lower:
            score += 0.08

    # medium importance keywords
    medium_keywords = [
        'improve', 'enhance', 'optimize', 'refactor', 'clean up',
        'pattern', 'design', 'architecture', 'structure',
        'preference', 'like', 'prefer', 'style', 'convention',
        'workflow', 'process', 'routine', 'habit'
    ]
    for kw in medium_keywords:
        if kw in content_lower:
            score += 0.04

    # technical indicators
    tech_patterns = [
        r'\b[a-z]+://\S+',  # urls
        r'`[^`]+`',  # inline code
        r'\b[\w-]+\.[\w-]+\b',  # file.extensions
        r'\$\w+',  # environment variables
        r'/[a-zA-Z_/]+',  # paths
        r'\b(?:class|def|function|const|let|var)\b',  # code keywords
    ]
    for pattern in tech_patterns:
        if re.search(pattern, content):
            score += 0.03

    # penalize casual/fleeting content
    casual_words = ['lol', 'haha', 'hm', 'hmm', 'uh', 'um', 'maybe', 'probably', 'idk']
    for word in casual_words:
        if word in content_lower:
            score -= 0.03

    # questions are slightly less permanent
    if content.strip().endswith('?'):
        score -= 0.05

    # emotional weight
    if content.count('!') > 1:
        score += min(0.05, content.count('!') * 0.01)

    # uppercase ratio (shouting = more important/fixed)
    upper_ratio = sum(1 for c in content if c.isupper()) / max(len(content), 1)
    if 0.1 < upper_ratio < 0.5:
        score += 0.03

    # clamp to 0.0-1.0
    return round(max(0.0, min(1.0, score)), 2)


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
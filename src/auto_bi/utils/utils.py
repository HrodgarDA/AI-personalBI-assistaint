import re
import logging

def levenshtein_ratio(s1: str, s2: str) -> float:
    """Calculates the Levenshtein distance ratio between two strings (0.0 to 1.0)."""
    if s1 == s2: return 1.0
    if not s1 or not s2: return 0.0
    
    rows = len(s1) + 1
    cols = len(s2) + 1
    distance = [[0 for _ in range(cols)] for _ in range(rows)]

    for i in range(1, rows):
        distance[i][0] = i
    for i in range(1, cols):
        distance[0][i] = i

    for col in range(1, cols):
        for row in range(1, rows):
            if s1[row-1] == s2[col-1]:
                cost = 0
            else:
                cost = 1
            distance[row][col] = min(distance[row-1][col] + 1,      # deletion
                                 distance[row][col-1] + 1,      # insertion
                                 distance[row-1][col-1] + cost) # substitution

    max_len = max(len(s1), len(s2))
    return (max_len - distance[row][col]) / max_len

logger = logging.getLogger(__name__)

# --- CONSTANTS ---

# Operations that are generic (not merchant names) — extract merchant from details instead
GENERIC_OPERATIONS = {
    "pagamento pos", "pagamento tramite pos",
    "pagamento effettuato su pos estero",
    "storno pagamento pos",
    "addebito diretto",
    "stipendio o pensione",
}

# Heuristic lists for distinguishing between businesses and private individuals
BUSINESS_INDICATORS = {
    "s.r.l.", "srl", "s.p.a.", "spa", "s.n.c.", "snc", "s.a.s.", "sas",
    "pizzeria", "ristorante", "bar", "cafe", "caffé", "trattoria", "osteria",
    "supermarket", "conad", "coop", "esselunga", "carrefour", "lidl", "eurospin",
    "farmacia", "tabacchi", "edicola", "stazione", "tamoil", "eni", "q8", "esso",
    "amazon", "ebay", "paypal", "apple", "google", "netflix", "spotify", "iliad",
    "vodafone", "telecom", "enel", "a2a", "iren", "latteria", "panificio", "pasticceria",
    "kebbab", "kebab", "burger", "shop", "store", "market", "outlet", "mall",
}

LINKING_PREPOSITIONS = {"da", "di", "del", "della", "degli", "dalle", "presso", "su", "in", "per"}


# --- MERCHANT CLEANING ---

def clean_merchant_name(name: str, custom_patterns: list = None, aliases: dict = None) -> str:
    """Clean a merchant name, with manual overrides having the highest priority."""
    if not name: return "Unknown"
    
    # 0. Apply manual aliases (case-insensitive lookup) - Highest Priority
    # We check the raw input first
    clean = name.strip()
    if aliases:
        lookup = {k.lower().strip(): v for k, v in aliases.items()}
        if clean.lower() in lookup:
            return lookup[clean.lower()]

    # 1. Apply custom patterns if provided
    if custom_patterns:
        for pattern in custom_patterns:
            try:
                clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)
            except Exception as e:
                logger.warning(f"Invalid custom regex '{pattern}': {e}")
                
    # 2. Remove trailing date patterns like "08/041312" or "VIA 28/"
    clean = re.sub(r'\s+\d{2}/\d{2,}.*$', '', clean)
    # 3. Remove trailing numbers
    clean = re.sub(r'\s+\d+$', '', clean)
    
    clean = clean.strip()
    
    # Check aliases again after cleaning (in case the alias matches the cleaned version)
    if aliases:
        lookup = {k.lower().strip(): v for k, v in aliases.items()}
        if clean.lower() in lookup:
            return lookup[clean.lower()]

    return clean[:50] if clean else "Unknown"


def clean_merchant_from_details(details: str, custom_patterns: list = None, aliases: dict = None) -> str:
    """Extract merchant name from dirty details field (Excel format)."""
    if not details or details.strip().upper() == "N.D":
        return "Unknown"
    
    text = details.strip()
    
    # 0. Apply custom patterns if provided
    if custom_patterns:
        for pattern in custom_patterns:
            try:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            except Exception as e:
                logger.warning(f"Invalid custom regex '{pattern}': {e}")

    # 1. Pattern: "Pagamento Su POS MERCHANT_NAME DD/MMHHMM Carta..."
    pos_match = re.match(r'(?:Pagamento\s+Su\s+POS\s+)(.+?)\s+\d{2}/\d{2}', text, re.IGNORECASE)
    if pos_match:
        return clean_merchant_name(pos_match.group(1), aliases=aliases)
    
    # 2. Pattern: "MERCHANT_NAME DD/MMHHMM Carta N.XXXX..."
    card_match = re.match(r'(.+?)\s+\d{2}/\d{2}\d{4}\s+Carta', text, re.IGNORECASE)
    if card_match:
        return clean_merchant_name(card_match.group(1), aliases=aliases)
    
    # 3. Pattern: "EFFETTUATO IL DD/MM/YYYY ... PRESSO MERCHANT_NAME"
    presso_match = re.search(r'PRESSO\s+(.+?)$', text, re.IGNORECASE)
    if presso_match:
        return clean_merchant_name(presso_match.group(1), aliases=aliases)
    
    # 4. Pattern: "Effettuato Il DD/MM/YYYY ... Presso Merchant Name"
    presso_match2 = re.search(r'Presso\s+(.+?)$', text, re.IGNORECASE)
    if presso_match2:
        return clean_merchant_name(presso_match2.group(1), aliases=aliases)
    
    # Fallback: first 50 chars cleaned of codes
    fallback = re.sub(r'COD\.?\s*(?:DISP\.?)?\s*\d+[/\s]*\w*', '', text)
    fallback = re.sub(r'\b\d{10,}\b', '', fallback)
    fallback = re.sub(r'\s+', ' ', fallback).strip()
    return clean_merchant_name(fallback, aliases=aliases)


def extract_merchant_from_excel(operation: str, details: str, custom_patterns: list = None, aliases: dict = None) -> str:
    """Main strategy to extract merchant from Excel fields."""
    op_lower = operation.strip().lower()
    
    # Generic operation?
    is_generic = any(op_lower.startswith(g) or op_lower == g for g in GENERIC_OPERATIONS)
    
    # Bonifico: extract recipient name
    if op_lower.startswith("bonifico"):
        for pattern in [r'(?:Disposto Da|A Favore Di)\s+(.+)', ]:
            match = re.search(pattern, operation, re.IGNORECASE)
            if match:
                return clean_merchant_name(match.group(1), aliases=aliases)
        return clean_merchant_name(operation, aliases=aliases)
    
    if not is_generic:
        return clean_merchant_name(operation, custom_patterns=custom_patterns, aliases=aliases)
    
    return clean_merchant_from_details(details, custom_patterns=custom_patterns, aliases=aliases)


# --- SEARCH QUERY UTILS ---

def clean_search_query(merchant_name: str) -> str:
    """Refine merchant name for cleaner web search."""
    if not merchant_name: return ""
    clean = merchant_name.lower()
    # Remove common irrelevant suffixes
    clean = re.sub(r'\b(via|v\.le|pza|piazza|corso)\b.*$', '', clean)
    clean = re.sub(r'\b(carta|pos|cod|disp)\b.*$', '', clean)
    # Remove numbers and special chars
    clean = re.sub(r'[\d\.\-\/]+', ' ', clean)
    # Collapse spaces
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def normalize_merchant_name(name: str) -> str:
    """
    Aggressive normalization for catalogue lookup.
    Example: 'PAYPAL *ZARA 6' -> 'zara'
    """
    if not name: return ""
    
    # 1. Lowercase and basic trim
    clean = name.lower().strip()
    
    # 2. Remove common prefixes and noise
    noise_patterns = [
        r'^paypal\s*\*?\s*',
        r'^sumup\s*\*?\s*',
        r'^pagamento\s+(?:su\s+)?pos\s*',
        r'^pos\s+',
        r'^storno\s+',
        r'\b(?:s\.?r\.?l\.?|s\.?p\.?a\.?|s\.?n\.?c\.?|s\.?a\.?s\.?)\b', # Business entities
    ]
    for pattern in noise_patterns:
        clean = re.sub(pattern, ' ', clean, flags=re.IGNORECASE)
        
    # 3. Remove dates (DD/MM or DD/MM/YYYY)
    clean = re.sub(r'\d{2}/\d{2}(?:\d{4})?\b', ' ', clean)
    
    # 4. Remove all remaining numbers
    clean = re.sub(r'\d+', ' ', clean)
    
    # 5. Remove special characters (except spaces)
    clean = re.sub(r'[^\w\s]', ' ', clean)
    
    # 6. Collapse spaces
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return clean


def is_valid_search_query(query: str) -> bool:
    """Heuristic to skip web searches for private person names."""
    if not query or len(query) < 3:
        return False
        
    # Heuristic: 2-3 words, all caps/capitalized, no business indicators
    words = query.strip().lower().split()
    if 2 <= len(words) <= 3:
        has_business_indicator = any(w in BUSINESS_INDICATORS for w in words)
        has_linking_preposition = any(w in LINKING_PREPOSITIONS for w in words)
        
        if not has_business_indicator and not has_linking_preposition:
            logger.debug(f"   Skipping likely person name search: '{query}'")
            return False
            
    return True

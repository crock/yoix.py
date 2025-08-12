from __future__ import annotations
from typing import Dict, List, Tuple, Any, Optional, Set
import re
from collections import defaultdict

CanonicalField = str
Mapping = Dict[CanonicalField, str]
Scores = Dict[CanonicalField, List[Dict[str, Any]]]

ALIASES: Dict[CanonicalField, List[str]] = {
    "name": ["name", "business_name", "company", "title", "listing_name"],
    "address": ["address", "street", "street1", "addr1", "line1"],
    "address2": ["address2", "street2", "addr2", "line2", "suite", "unit", "apt"],
    "city": ["city", "town", "locality"],
    "state": ["state", "province", "region", "state_province", "admin_area"],
    "postal_code": ["zip", "zipcode", "postal", "postal_code", "post_code", "postcode"],
    "country": ["country", "country_code", "nation", "iso2", "iso3"],
    "phone": ["phone", "tel", "telephone", "mobile", "cell", "contact_phone"],
    "email": ["email", "e-mail", "contact_email"],
    "website": ["website", "url", "link", "homepage", "site"],
    "lat": ["lat", "latitude", "y"],
    "lng": ["lng", "long", "longitude", "x"],
    "category": ["category", "type", "segment", "vertical"],
    "tags": ["tags", "keywords", "labels"],
    "description": ["description", "about", "summary", "blurb"],
    "hours": ["hours", "opening_hours", "open_hours", "schedule"],
    "price": ["price", "cost", "pricing", "price_level"],
    "rating": ["rating", "stars", "score"],
}

PHONE_RE = re.compile(r"\+?[\d\s().-]{7,}")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s]+$", re.I)
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I)

def norm(s: str) -> str:
    s = s.strip()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)       # split camelCase
    s = re.sub(r"[_\-.\/]+", " ", s)                 # normalize separators
    s = re.sub(r"\s+", " ", s)                       # collapse whitespace
    return s.lower().strip()

def tokens(s: str) -> Set[str]:
    return set(t for t in norm(s).split(" ") if t)

def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union

def edit_distance(a: str, b: str) -> int:
    A, B = norm(a), norm(b)
    la, lb = len(A), len(B)
    if la == 0: return lb
    if lb == 0: return la
    # DP with two rows
    prev = list(range(lb + 1))
    cur = [0] * (lb + 1)
    for i in range(1, la + 1):
        cur[0] = i
        ai = A[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == B[j - 1] else 1
            cur[j] = min(prev[j] + 1,        # deletion
                         cur[j - 1] + 1,      # insertion
                         prev[j - 1] + cost)  # substitution
        prev, cur = cur, prev
    return prev[lb]

def fuzzy_score(h: str, alias: str) -> float:
    h_n, a_n = norm(h), norm(alias)
    if h_n == a_n:
        return 1.0
    dist = edit_distance(h_n, a_n)
    max_len = max(len(h_n), len(a_n)) or 1
    return 1.0 - (dist / max_len)

def sniff_type(values: List[str]) -> Dict[CanonicalField, bool]:
    """Returns flags like {'email': True, 'phone': True} if enough samples match."""
    res: Dict[CanonicalField, bool] = {}
    sample = [str(v).strip() for v in values[:50] if v is not None and str(v).strip() != ""]
    n = len(sample)
    if n == 0:
        return res
    def count(pred) -> int:
        return sum(1 for v in sample if pred(v))
    if count(lambda v: EMAIL_RE.match(v)) >= max(2, int(n * 0.2)): res["email"] = True
    if count(lambda v: PHONE_RE.search(v)) >= max(2, int(n * 0.2)): res["phone"] = True
    if count(lambda v: URL_RE.match(v)) >= max(2, int(n * 0.2)): res["website"] = True
    if count(lambda v: v.replace('.', '', 1).lstrip('-').isdigit() and -90 <= float(v) <= 90) >= int(n * 0.6):
        res["lat"] = True
    if count(lambda v: v.replace('.', '', 1).lstrip('-').isdigit() and -180 <= float(v) <= 180) >= int(n * 0.6):
        res["lng"] = True
    return res

def auto_map_columns(
    headers: List[str],
    rows: List[Dict[str, Any]],
    learned_aliases: Optional[Dict[CanonicalField, List[str]]] = None,
    threshold: int = 75
) -> Tuple[Mapping, Scores]:
    """
    headers: list of CSV headers
    rows: sample rows (list of dicts) for data sniffing
    learned_aliases: optional extra aliases persisted from previous sessions
    returns (mapping, scores)
    """
    learned_aliases = learned_aliases or {}
    # Merge aliases
    all_aliases: Dict[CanonicalField, List[str]] = {
        k: list(dict.fromkeys(ALIASES.get(k, []) + learned_aliases.get(k, [])))
        for k in set(ALIASES) | set(learned_aliases)
    }

    header_norms = {h: {"norm": norm(h), "toks": tokens(h)} for h in headers}
    # Collect sample values by header
    samples_by_header: Dict[str, List[str]] = defaultdict(list)
    for r in rows:
        for h in headers:
            if h in r and r[h] is not None:
                samples_by_header[h].append(str(r[h]))

    sniff_flags: Dict[str, Dict[CanonicalField, bool]] = {
        h: sniff_type(samples_by_header.get(h, [])) for h in headers
    }

    scores: Scores = {}
    for field, alias_list in all_aliases.items():
        scored: List[Dict[str, Any]] = []
        for h in headers:
            hn = header_norms[h]
            sc = 0.0
            # exact alias
            if any(norm(a) == hn["norm"] for a in alias_list):
                sc += 100
            # token overlap
            if alias_list:
                alias_tok_max = max((jaccard(hn["toks"], tokens(a)) for a in alias_list), default=0.0)
                sc += 70 * alias_tok_max
                # fuzzy against best alias
                fuzzy_max = max((fuzzy_score(h, a) for a in alias_list), default=0.0)
                sc += 40 * fuzzy_max
            # data sniff bonus
            if sniff_flags[h].get(field):
                sc += 30
            # heuristics
            if field == "postal_code" and hn["norm"] in {"zip", "zipcode"}:
                sc += 10
            if field == "phone" and hn["norm"] in {"tel", "telephone"}:
                sc += 10
            # collision penalty
            if field == "state" and ("status" in hn["toks"]):
                sc -= 30
            scored.append({"header": h, "score": int(round(sc))})
        scores[field] = sorted(scored, key=lambda x: x["score"], reverse=True)

    mapping: Mapping = {}
    chosen_headers: Set[str] = set()
    for field, ranked in scores.items():
        best = next((s for s in ranked if s["header"] not in chosen_headers), None)
        if best and best["score"] >= threshold:
            mapping[field] = best["header"]
            chosen_headers.add(best["header"])

    return mapping, scores

# --- convenience: pick top-k candidates for a field (for CLI confirmations) ---
def top_candidates(scores: Scores, field: CanonicalField, k: int = 3) -> List[Tuple[str, int]]:
    ranked = scores.get(field, [])
    return [(r["header"], r["score"]) for r in ranked[:k]]

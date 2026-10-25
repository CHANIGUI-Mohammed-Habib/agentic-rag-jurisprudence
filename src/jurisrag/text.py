"""French text normalisation for the lexical index."""

import re
import unicodedata

import snowballstemmer

_stemmer = snowballstemmer.stemmer("french")
_TOKEN = re.compile(r"[a-z0-9]+")

# Function words plus boilerplate that appears in nearly every Cour de cassation decision.
STOPWORDS = set(
    """
    a au aux avec ce ces cet cette d dans de des du elle en et eux il ils je l la le les leur leurs
    lui m ma mais me meme mes moi mon n ne nos notre nous on ou par pas pour qu que qui s sa se ses
    son sur t ta te tes toi ton tu un une vos votre vous y c j est sont ete etre avoir a ont ainsi
    alors si sans sous entre comme dont plus tout tous toute toutes autre autres apres avant lors
    attendu considerant arret cour cassation article articles code alinea moyen moyens
    """.split()
)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> list[str]:
    words = _TOKEN.findall(strip_accents(text.lower()))
    return [_stemmer.stemWord(w) for w in words if w not in STOPWORDS and len(w) > 1]

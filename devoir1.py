"""
INF4083 - Langages de programmation - Automne 2026
Devoir 1 : Interpréteur lambda-calcul

Représentation des termes (arbres sous forme de tuples Python) :
    variable    : ('var', 'x')
    abstraction : ('abs', 'x', corps)
    application : ('app', gauche, droite)

Partie du codeur 1 : étapes 1, 2 et 5 (lexeur, parseur, affichage,
entiers de Church, addition, interface).

Remarque : addition() appelle normaliser() et betared2(), qui sont écrites par
le codeur 2 et ne sont pas définies dans cette partie.
"""

import string
import sys

# Les termes de Church (et donc les arbres) peuvent être profonds.
sys.setrecursionlimit(10000)


# ============================================================================
# SECTION CODEUR 1 - ÉTAPES 1 ET 2 : LEXEUR, PARSEUR, AFFICHAGE
# ============================================================================

# --- Noms des types de tokens (définis ici, et seulement ici) ---------------
# Le prof accepte PARENO/PARENF et PARO/PARF, mais encourage PARO/PARF.
# Si on veut changer de convention, il suffit de modifier ces deux lignes.
LAMBDA = "LAMBDA"
POINT = "POINT"
ESPACE = "ESPACE"
PARO = "PARO"
PARF = "PARF"
VAR = "VAR"

# --- Noms des types de nœuds de l'arbre -------------------------------------
VARIABLE = "var"
ABSTRACTION = "abs"
APPLICATION = "app"

# --- Erreurs ----------------------------------------------------------------


class ErreurLexicale(ValueError):
    """Caractère interdit rencontré par le lexeur."""


class ErreurSyntaxe(SyntaxError):
    """Terme mal formé détecté par le parseur."""


# --- Étape 1 : lexeur -------------------------------------------------------

_SYMBOLES = {
    "/": LAMBDA,
    ".": POINT,
    " ": ESPACE,
    "(": PARO,
    ")": PARF,
}

# Un nom de variable est une suite de lettres et de chiffres (ASCII).
_CARACTERES_VAR = frozenset(string.ascii_letters + string.digits)


def lexeur(s):
    """
    Découpe la chaîne s en une liste de paires (texte, type).

    Chaque espace est son propre token ESPACE (l'espace est l'application).
    Le lexeur ne vérifie PAS la grammaire : seule la validité des caractères
    est contrôlée. Tout caractère inconnu (+, tabulation, retour à la ligne...)
    lève une ErreurLexicale.
    """
    tokens = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in _SYMBOLES:
            tokens.append((c, _SYMBOLES[c]))
            i += 1
        elif c in _CARACTERES_VAR:
            debut = i
            while i < len(s) and s[i] in _CARACTERES_VAR:
                i += 1
            tokens.append((s[debut:i], VAR))
        else:
            raise ErreurLexicale(
                f"Erreur lexicale : caractère {c!r} interdit à la position {i}"
            )
    return tokens


# --- Étape 2 : parseur ------------------------------------------------------
#
# Grammaire utilisée (descente récursive, un sous-programme par règle) :
#
#   terme       ::= abstraction | application
#   abstraction ::= LAMBDA VAR POINT terme
#   application ::= atome ( ESPACE ( atome | abstraction ) )*
#   atome       ::= VAR | PARO terme PARF
#
# Chaque sous-programme _lire_xxx(a, i) lit à partir de l'indice i dans la
# liste de tokens a et retourne (arbre, indice du prochain token à lire).


def parseur(a):
    """
    Construit l'arbre de syntaxe à partir d'une liste de tokens (celle du
    lexeur). Lève une ErreurSyntaxe si le terme est mal formé.
    """
    if not a:
        raise ErreurSyntaxe("Erreur de syntaxe : terme vide")
    arbre, i = _lire_terme(a, 0)
    if i < len(a):
        # Il reste des tokens que la grammaire ne sait pas consommer.
        raise ErreurSyntaxe(_message_inattendu(a, i))
    return arbre


def _message_inattendu(a, i):
    if i >= len(a):
        return "Erreur de syntaxe : fin du terme inattendue"
    texte, type_token = a[i]
    return (
        f"Erreur de syntaxe : token inattendu {texte!r} ({type_token}) "
        f"à la position {i}"
    )


def _lire_terme(a, i):
    """terme ::= abstraction | application"""
    if i < len(a) and a[i][1] == LAMBDA:
        return _lire_abstraction(a, i)
    return _lire_application(a, i)


def _lire_abstraction(a, i):
    """abstraction ::= LAMBDA VAR POINT terme"""
    i = _consommer(a, i, LAMBDA)
    if i >= len(a) or a[i][1] != VAR:
        raise ErreurSyntaxe(
            _message_inattendu(a, i) + " (nom de variable attendu après '/')"
        )
    nom = a[i][0]
    i += 1
    i = _consommer(a, i, POINT)
    # RÈGLE DE PRÉCÉDENCE 2 : le corps est lu par _lire_terme, qui avale
    # tout ce qu'il peut (applications comprises) ; il s'arrête seulement
    # devant une parenthèse fermante ou à la fin de la liste. L'abstraction
    # va donc « le plus loin possible après le point ».
    corps, i = _lire_terme(a, i)
    return (ABSTRACTION, nom, corps), i


def _lire_application(a, i):
    """application ::= atome ( ESPACE ( atome | abstraction ) )*"""
    # RÈGLE DE PRÉCÉDENCE 1 : l'application s'associe à gauche. On lit un
    # premier atome, puis chaque nouvel argument est collé À DROITE de
    # l'arbre déjà construit : x y z donne ((x y) z).
    arbre, i = _lire_atome(a, i)
    while i < len(a) and a[i][1] == ESPACE:
        i += 1
        if i < len(a) and a[i][1] == LAMBDA:
            # Abstraction sans parenthèses en dernier argument : x /y.y
            # Elle avale tout jusqu'à la fin du bloc courant (règle 2).
            droite, i = _lire_abstraction(a, i)
        else:
            droite, i = _lire_atome(a, i)
        arbre = (APPLICATION, arbre, droite)
    return arbre, i


def _lire_atome(a, i):
    """atome ::= VAR | PARO terme PARF"""
    if i >= len(a):
        raise ErreurSyntaxe(
            "Erreur de syntaxe : fin du terme inattendue "
            "(variable ou '(' attendue)"
        )
    texte, type_token = a[i]
    if type_token == VAR:
        return (VARIABLE, texte), i + 1
    if type_token == PARO:
        terme, i = _lire_terme(a, i + 1)
        if i >= len(a) or a[i][1] != PARF:
            raise ErreurSyntaxe(
                _message_inattendu(a, i) + " (parenthèse fermante attendue)"
            )
        return terme, i + 1
    raise ErreurSyntaxe(_message_inattendu(a, i))


def _consommer(a, i, type_attendu):
    """Vérifie que le token en position i est du type attendu ; retourne i+1."""
    if i >= len(a) or a[i][1] != type_attendu:
        raise ErreurSyntaxe(
            _message_inattendu(a, i) + f" ({type_attendu} attendu)"
        )
    return i + 1


# --- Affichage --------------------------------------------------------------


def en_texte(a):
    """
    Retourne le terme sous forme de texte (syntaxe du devoir), avec le moins
    de parenthèses possible. Utile pour afficher et pour les tests :
    parseur(lexeur(en_texte(a))) redonne a.
    """
    if a[0] == VARIABLE:
        return a[1]
    if a[0] == ABSTRACTION:
        return "/" + a[1] + "." + en_texte(a[2])
    gauche, droite = a[1], a[2]
    texte_g = en_texte(gauche)
    if gauche[0] == ABSTRACTION:
        texte_g = "(" + texte_g + ")"
    texte_d = en_texte(droite)
    if droite[0] != VARIABLE:
        texte_d = "(" + texte_d + ")"
    return texte_g + " " + texte_d


def _etiquette(a):
    if a[0] == VARIABLE:
        return f"VAR {a[1]}"
    if a[0] == ABSTRACTION:
        return f"ABS /{a[1]}."
    return "APP"


def _enfants(a):
    if a[0] == ABSTRACTION:
        return [a[2]]
    if a[0] == APPLICATION:
        return [a[1], a[2]]
    return []


def _lignes_arbre(a, prefixe, dernier, racine):
    if racine:
        lignes = [_etiquette(a)]
        prefixe_enfants = ""
    else:
        lignes = [prefixe + ("`-- " if dernier else "|-- ") + _etiquette(a)]
        prefixe_enfants = prefixe + ("    " if dernier else "|   ")
    enfants = _enfants(a)
    for k, enfant in enumerate(enfants):
        lignes += _lignes_arbre(
            enfant, prefixe_enfants, k == len(enfants) - 1, False
        )
    return lignes


def affichage(a):
    """
    Affiche à l'écran le terme en texte, puis son arbre de syntaxe.
    Exemple pour (/x.x) y :

        Terme : (/x.x) y
        APP
        |-- ABS /x.
        |   `-- VAR x
        `-- VAR y
    """
    print("Terme : " + en_texte(a))
    for ligne in _lignes_arbre(a, "", True, True):
        print(ligne)


# ============================================================================
# SECTION CODEUR 1 - ÉTAPE 5 : ENTIERS DE CHURCH, ADDITION, INTERFACE
# ============================================================================

# Terme « successeur » : S = /n./f./x.f (n f x)
_TEXTE_SUCCESSEUR = "/n./f./x.f (n f x)"

# Nombre maximal de béta-réductions permis pour une addition.
_MAX_ITER_ADDITION = 1000000


def encoder_church(n):
    """
    Encode l'entier n >= 0 par l'entier de Church /f./x.f (f (... (f x))).
    Construction itérative (pas de récursion) pour supporter les grands n.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f"encoder_church : entier >= 0 attendu, reçu {n!r}")
    corps = (VARIABLE, "x")
    for _ in range(n):
        corps = (APPLICATION, (VARIABLE, "f"), corps)
    return (ABSTRACTION, "f", (ABSTRACTION, "x", corps))


def decoder_church(t):
    """
    Décode un entier de Church : retourne l'entier représenté par t.
    Lève une ValueError si t n'est pas de la forme /f./x.f (f (... x)).

    Les noms de variables ne sont pas supposés être « f » et « x » : le
    décodeur lit les noms dans le terme lui-même (le renommage de betared2
    peut les avoir changés).
    """
    erreur = ValueError(f"decoder_church : {t!r} n'est pas un entier de Church")
    if (
        not isinstance(t, tuple)
        or t[0] != ABSTRACTION
        or t[2][0] != ABSTRACTION
    ):
        raise erreur
    nom_f = t[1]
    nom_x = t[2][1]
    corps = t[2][2]
    if nom_f == nom_x:
        # /a./a.a : le a du corps est celui de l'abstraction intérieure.
        if corps == (VARIABLE, nom_x):
            return 0
        raise erreur
    compteur = 0
    while corps[0] == APPLICATION and corps[1] == (VARIABLE, nom_f):
        compteur += 1
        corps = corps[2]
    if corps != (VARIABLE, nom_x):
        raise erreur
    return compteur


def addition(m, n):
    """
    Additionne deux entiers m et n >= 0 avec les entiers de Church :
    encode m et n, réduit le terme M S N, puis décode le résultat.

    Utilise la béta-réduction CORRECTE (betared2) du codeur 2 :
    normaliser(t, reduction=betared2, max_iter=...) .
    """
    terme_m = encoder_church(m)
    terme_n = encoder_church(n)
    successeur = parseur(lexeur(_TEXTE_SUCCESSEUR))
    terme = (APPLICATION, (APPLICATION, terme_m, successeur), terme_n)
    forme_normale = normaliser(
        terme, reduction=betared2, max_iter=_MAX_ITER_ADDITION
    )
    return decoder_church(forme_normale)


def _lire_entier(invite):
    """Demande un entier >= 0 à l'utilisateur, jusqu'à obtenir une réponse valide."""
    while True:
        texte = input(invite).strip()
        try:
            valeur = int(texte)
        except ValueError:
            print("Entrée invalide : veuillez entrer un entier positif (ex. 4).")
            continue
        if valeur < 0:
            print("Entrée invalide : l'entier doit être positif.")
            continue
        return valeur


def interface_addition():
    """Petite interface : demande deux entiers et affiche leur somme."""
    print("Addition avec les entiers de Church")
    m = _lire_entier("Premier entier : ")
    n = _lire_entier("Deuxième entier : ")
    print(f"{m} + {n} = {addition(m, n)}")


if __name__ == "__main__":
    interface_addition()

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
# SECTION CODEUR 2 - ÉTAPES 3 ET 4 : RÉDUCTION, ALPHA-RENOMMAGE, ÉQUIVALENCE
# ============================================================================
#
# Représentation des termes (celle produite par le parseur du Codeur 1) :
#     variable    : ('var', 'x')
#     abstraction : ('abs', 'x', corps)      <- le nom est un TEXTE, pas un nœud
#     application : ('app', gauche, droite)
#
# Versions des fonctions :
#     NAÏVE    (étape 3, sans alpha-renommage) : substitution, betared
#     CORRECTE (étape 4, avec alpha-renommage) : substitution_correcte, betared2
#
# ORDRE DE DÉFINITION : _reduire_a_profondeur utilise `substitution` et
# normaliser utilise `betared` comme VALEUR PAR DÉFAUT d'un paramètre. Ces
# valeurs sont évaluées à la lecture du fichier : ces deux fonctions doivent
# donc être définies AVANT celles qui les utilisent. Ne pas réordonner.


# --- Variables libres et liées ----------------------------------------------


def variables_libres(t):
    """Ensemble des noms qui ont au moins une occurrence LIBRE dans t."""
    if t[0] == 'var':
        return {t[1]}
    if t[0] == 'app':
        return variables_libres(t[1]) | variables_libres(t[2])
    if t[0] == 'abs':
        return variables_libres(t[2]) - {t[1]}


def variables_liees(t, englobantes=frozenset()):
    """
    Ensemble des noms qui ont au moins une occurrence LIÉE dans t.
    'englobantes' : noms liés par les abstractions qui entourent t.
    """
    if t[0] == 'var':
        if t[1] in englobantes:
            return {t[1]}
        return set()
    if t[0] == 'app':
        return (variables_liees(t[1], englobantes)
                | variables_liees(t[2], englobantes))
    if t[0] == 'abs':
        return variables_liees(t[2], englobantes | {t[1]})


# --- Étape 3 : bêta-réduction NAÏVE -----------------------------------------


def substitution(t, x, n):
    """
    Substitution NAÏVE : remplace dans t les occurrences libres de la
    variable de nom x (une chaîne, ex. 'x') par le terme n.
    Pas d'alpha-renommage : une capture de variable est possible.
    """
    if t[0] == 'var':
        if t[1] == x:
            return n
        return t
    if t[0] == 'app':
        return ('app', substitution(t[1], x, n), substitution(t[2], x, n))
    if t[0] == 'abs':
        if t[1] == x:
            return t
        return ('abs', t[1], substitution(t[2], x, n))


def _est_redex(t):
    """Vrai si t est de la forme (/x.M) N."""
    return t[0] == 'app' and t[1][0] == 'abs'


def _profondeur_min_redex(t, p=0):
    """Profondeur du redex le plus proche de la racine (None s'il n'y en a pas)."""
    if _est_redex(t):
        return p
    if t[0] == 'var':
        return None
    if t[0] == 'abs':
        return _profondeur_min_redex(t[2], p + 1)
    g = _profondeur_min_redex(t[1], p + 1)
    d = _profondeur_min_redex(t[2], p + 1)
    if g is None:
        return d
    if d is None:
        return g
    return min(g, d)


def _reduire_a_profondeur(t, reste, subst=substitution):
    """
    Réduit le redex le plus à gauche situé exactement 'reste' niveaux
    sous t, en utilisant la fonction de substitution 'subst'.
    Retourne (nouveau_terme, a_reduit).
    """
    if reste == 0:
        if _est_redex(t):
            return subst(t[1][2], t[1][1], t[2]), True
        return t, False
    if t[0] == 'var':
        return t, False
    if t[0] == 'abs':
        corps, reduit = _reduire_a_profondeur(t[2], reste - 1, subst)
        if reduit:
            return ('abs', t[1], corps), True
        return t, False
    gauche, reduit = _reduire_a_profondeur(t[1], reste - 1, subst)
    if reduit:
        return ('app', gauche, t[2]), True
    droite, reduit = _reduire_a_profondeur(t[2], reste - 1, subst)
    if reduit:
        return ('app', t[1], droite), True
    return t, False


def betared(t):
    """
    Bêta-réduction NAÏVE : un seul pas, sur le redex le plus proche de la
    racine (le plus à gauche en cas d'égalité de profondeur), avec la
    substitution NAÏVE. Retourne t inchangé s'il n'a pas de redex.
    """
    p = _profondeur_min_redex(t)
    if p is None:
        return t
    nouveau, _ = _reduire_a_profondeur(t, p)
    return nouveau


def est_forme_normale(t):
    """Vrai si t ne contient aucun redex."""
    return _profondeur_min_redex(t) is None


def normaliser(t, reduction=betared, max_iter=1000):
    """
    Répète la réduction jusqu'à la forme normale, ou jusqu'à max_iter pas.
    Retourne le dernier terme calculé. Si la limite est atteinte, ce terme
    n'est pas forcément normal : le vérifier avec est_forme_normale().
    Compatible avec l'appel du Codeur 1 :
        normaliser(terme, reduction=betared2, max_iter=...)
    """
    for _ in range(max_iter):
        if est_forme_normale(t):
            return t
        t = reduction(t)
    return t


# --- Étape 4 : alpha-renommage et bêta-réduction CORRECTE -------------------


def noms_du_terme(t):
    """Tous les noms présents dans t : variables (libres ou liées) et noms d'abstractions."""
    if t[0] == 'var':
        return {t[1]}
    if t[0] == 'app':
        return noms_du_terme(t[1]) | noms_du_terme(t[2])
    if t[0] == 'abs':
        return {t[1]} | noms_du_terme(t[2])


def nom_frais(base, interdits):
    """Premier nom parmi base1, base2, ... qui n'est pas dans 'interdits'."""
    i = 1
    while base + str(i) in interdits:
        i += 1
    return base + str(i)


def renommage_necessaire(t, x, n):
    """
    t = ('abs', y, corps). Vrai si substituer x := n dans t risque de
    capturer une variable libre de n.
    """
    y, corps = t[1], t[2]
    return (y != x
            and y in variables_libres(n)
            and x in variables_libres(corps))


def alpha_renommer(t, nouveau):
    """
    t = ('abs', y, corps) devient ('abs', nouveau, corps[y := nouveau]).
    Précondition : 'nouveau' est absent de tous les noms de t.
    """
    if nouveau in noms_du_terme(t):
        raise ValueError(f"alpha_renommer : {nouveau!r} n'est pas un nom frais")
    ancien, corps = t[1], t[2]
    return ('abs', nouveau, substitution(corps, ancien, ('var', nouveau)))


def eviter_capture(t, x, n):
    """
    t = ('abs', y, corps). Si substituer x := n dans t risque une capture,
    retourne t alpha-renommé avec un nom frais ; sinon retourne t tel quel.
    """
    if renommage_necessaire(t, x, n):
        nouveau = nom_frais(t[1], noms_du_terme(t) | noms_du_terme(n))
        return alpha_renommer(t, nouveau)
    return t


def substitution_correcte(t, x, n):
    """
    Substitution CORRECTE : remplace dans t les occurrences libres de x
    par n, en renommant les variables liées pour éviter toute capture.
    (La version NAÏVE est substitution.)
    """
    if t[0] == 'var':
        if t[1] == x:
            return n
        return t
    if t[0] == 'app':
        return ('app',
                substitution_correcte(t[1], x, n),
                substitution_correcte(t[2], x, n))
    if t[0] == 'abs':
        if t[1] == x:
            return t
        t = eviter_capture(t, x, n)
        return ('abs', t[1], substitution_correcte(t[2], x, n))


def betared2(t):
    """
    Bêta-réduction CORRECTE : un pas, sur le redex le plus proche de la
    racine, avec substitution_correcte (renommage des variables liées).
    (La version NAÏVE est betared.)
    """
    p = _profondeur_min_redex(t)
    if p is None:
        return t
    nouveau, _ = _reduire_a_profondeur(t, p, substitution_correcte)
    return nouveau


# --- Équivalence à l'alpha-renommage près -----------------------------------


def equivalent(t1, t2):
    """
    Vrai si t1 et t2 sont identiques au renommage près des variables liées.
    (Ne réduit rien : (/x.x) y n'est pas équivalent à y.)
    """
    return _equivalents(t1, t2, {}, {}, 0)


def _equivalents(a, b, env_a, env_b, niveau):
    """
    env_a, env_b : dictionnaires nom -> niveau de l'abstraction qui le lie,
    pour chacun des deux arbres. niveau : nombre d'abstractions rencontrées
    depuis la racine (identique des deux côtés, car on avance en parallèle).
    """
    if a[0] != b[0]:
        return False
    if a[0] == 'var':
        lie_a = a[1] in env_a
        lie_b = b[1] in env_b
        if lie_a and lie_b:
            return env_a[a[1]] == env_b[b[1]]
        if not lie_a and not lie_b:
            return a[1] == b[1]
        return False
    if a[0] == 'app':
        return (_equivalents(a[1], b[1], env_a, env_b, niveau)
                and _equivalents(a[2], b[2], env_a, env_b, niveau))
    if a[0] == 'abs':
        nouveau_a = dict(env_a)
        nouveau_a[a[1]] = niveau
        nouveau_b = dict(env_b)
        nouveau_b[b[1]] = niveau
        return _equivalents(a[2], b[2], nouveau_a, nouveau_b, niveau + 1)

    
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

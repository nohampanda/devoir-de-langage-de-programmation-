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
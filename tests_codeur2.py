"""
Suite de tests du Codeur 2 (étapes 3 et 4) - INF4083, devoir 1.

Utilisation : placer ce fichier à côté du fichier fusionné reduction.py, puis
    python tests_codeur2.py              lance tous les tests
    python tests_codeur2.py --mesures    affiche aussi des temps pour l'addition

Si le fichier fusionné porte un autre nom, changer la ligne d'import.
"""

import contextlib
import io
import random
import sys
import time

from devoir1 import (
    lexeur, parseur, en_texte, affichage,
    encoder_church, decoder_church, addition
)
from reduction import *
import devoir1

devoir1.normaliser = normaliser
devoir1.betared2 = betared2

# ----------------------------------------------------------------------------
# Termes de référence
# ----------------------------------------------------------------------------
x = ('var', 'x'); y = ('var', 'y'); z = ('var', 'z'); w = ('var', 'w')
va = ('var', 'a'); vb = ('var', 'b')

T1 = ('abs', 'x', ('app', ('app', x, ('abs', 'z', y)), x))
T2 = ('abs', 'x', ('app', ('abs', 'y', x), ('app', x, z)))
T3 = ('app', ('abs', 'x', ('app', x, x)), ('abs', 'y', ('app', y, z)))
T4 = ('abs', 'x', ('abs', 'y', ('app', ('abs', 'u', x), y)))
T5 = ('app', x, ('abs', 'x', ('abs', 'z', ('app', ('app', x, y), z))))
TOUS = [T1, T2, T3, T4, T5]

N = ('abs', 'y', ('app', y, z))                       # /y.y z
zz = ('app', z, z)

omega_moitie = ('abs', 'x', ('app', x, x))
omega = ('app', omega_moitie, omega_moitie)

cap1 = ('app', ('abs', 'x', ('abs', 'y', x)), y)                          # (/x./y.x) y
cap2 = ('app', ('abs', 'x', ('abs', 'a', ('abs', 'y', x))), y)            # (/x./a./y.x) y
cap3 = ('app', ('abs', 'x', ('abs', 'y', ('app', ('abs', 'y', y), x))), y)  # (/x./y.(/y.y) x) y
mask = ('app', ('abs', 'x', ('abs', 'x', x)), y)                          # (/x./x.x) y
A = ('app', ('app', ('abs', 'x', ('abs', 'z', x)), ('abs', 'y', z)),
     ('abs', 'z', z))                                                      # TD 2, exercice 2 (reconstitué)

SUCCESSEUR = parseur(lexeur("/n./f./x.f (n f x)"))


def terme_addition(m, n):
    return ('app', ('app', encoder_church(m), SUCCESSEUR), encoder_church(n))


# ----------------------------------------------------------------------------
# Étape 3 : version naïve
# ----------------------------------------------------------------------------

def test_substitution_naive():
    assert substitution(('app', x, y), 'x', z) == ('app', z, y)
    assert substitution(('abs', 'x', x), 'x', y) == ('abs', 'x', x)           # masquage
    assert substitution(('app', ('abs', 'x', x), x), 'x', z) == ('app', ('abs', 'x', x), z)
    assert substitution(('abs', 'y', x), 'x', y) == ('abs', 'y', y)           # capture (voulue)


def test_betared():
    assert betared(('app', ('abs', 'x', x), y)) == y
    assert betared(T3) == ('app', N, N)
    assert betared(('app', x, y)) == ('app', x, y)                            # aucun redex
    t4 = ('app', ('abs', 'x', y), ('app', ('abs', 'z', z), w))
    assert betared(t4) == y                                                   # l'extérieur d'abord
    g = ('app', ('abs', 'a', va), x)
    d = ('app', ('abs', 'b', vb), y)
    assert betared(('app', g, d)) == ('app', x, d)                            # gauche d'abord
    assert betared(('abs', 'z', ('app', ('abs', 'x', x), y))) == ('abs', 'z', y)   # sous un lambda
    assert betared(('app', ('abs', 'x', ('abs', 'y', x)), y)) == ('abs', 'y', y)   # capture (voulue)
    assert betared(omega) == omega
    # redex profond à gauche, redex moins profond à droite : profondeur minimale
    P = ('app', ('abs', 'a', va), w)
    R = ('app', ('abs', 'b', vb), y)
    assert betared(('app', ('app', x, P), R)) == ('app', ('app', x, P), y)
    # T1 à T5
    assert betared(T1) == T1 and betared(T5) == T5
    assert betared(T2) == ('abs', 'x', x)
    assert betared(T4) == ('abs', 'x', ('abs', 'y', x))


def test_normaliser():
    assert normaliser(('app', x, y)) == ('app', x, y)
    assert normaliser(T3) == zz
    assert est_forme_normale(normaliser(T3))
    assert normaliser(T3, max_iter=3) == zz
    r = normaliser(T3, max_iter=2)
    assert r == ('app', N, z) and not est_forme_normale(r)
    r = normaliser(omega, max_iter=50)
    assert r == omega and not est_forme_normale(r)
    assert normaliser(T3, reduction=betared, max_iter=1000000) == zz
    assert normaliser(T3, max_iter=0) == T3
    assert normaliser(T1) == T1 and normaliser(T5) == T5
    assert normaliser(T2) == ('abs', 'x', x)
    assert normaliser(T4) == ('abs', 'x', ('abs', 'y', x))


# ----------------------------------------------------------------------------
# Étape 4 : variables libres/liées, alpha-renommage, version correcte
# ----------------------------------------------------------------------------

def test_variables_libres_liees():
    assert variables_libres(x) == {'x'}
    assert variables_libres(('app', x, y)) == {'x', 'y'}
    assert variables_libres(('abs', 'x', x)) == set()
    assert variables_libres(('abs', 'y', x)) == {'x'}
    assert variables_libres(('abs', 'x', ('abs', 'x', x))) == set()
    assert variables_libres(('abs', 'x', ('abs', 'y', ('app', ('app', x, y), z)))) == {'z'}
    assert variables_libres(('app', ('abs', 'x', x), x)) == {'x'}
    assert [variables_libres(t) for t in TOUS] == [{'y'}, {'z'}, {'z'}, set(), {'x', 'y'}]
    assert variables_liees(x) == set()
    assert variables_liees(('abs', 'x', x)) == {'x'}
    assert variables_liees(('abs', 'y', x)) == set()
    assert variables_liees(('abs', 'x', ('abs', 'x', x))) == {'x'}
    assert variables_liees(('app', ('abs', 'x', x), x)) == {'x'}
    assert variables_liees(('app', x, ('abs', 'x', x))) == {'x'}
    assert [variables_liees(t) for t in TOUS] == \
        [{'x'}, {'x'}, {'x', 'y'}, {'x', 'y'}, {'x', 'z'}]

    def occurrences(t):
        if t[0] == 'var':
            return {t[1]}
        if t[0] == 'app':
            return occurrences(t[1]) | occurrences(t[2])
        return occurrences(t[2])
    for t in TOUS:
        assert variables_libres(t) | variables_liees(t) == occurrences(t)


def test_alpha_renommage():
    assert noms_du_terme(('abs', 'y', x)) == {'x', 'y'}
    assert noms_du_terme(T2) == {'x', 'y', 'z'}
    assert noms_du_terme(T4) == {'x', 'y', 'u'}
    assert nom_frais('y', set()) == 'y1'
    assert nom_frais('y', {'y', 'y1'}) == 'y2'
    assert nom_frais('y1', {'y1'}) == 'y11'
    assert renommage_necessaire(('abs', 'y', x), 'x', y)
    assert not renommage_necessaire(('abs', 'x', x), 'x', y)
    assert not renommage_necessaire(('abs', 'y', z), 'x', y)
    assert not renommage_necessaire(('abs', 'y', x), 'x', z)
    assert not renommage_necessaire(('abs', 'y', ('abs', 'x', x)), 'x', y)
    assert renommage_necessaire(('abs', 'y', ('abs', 'z', x)), 'x', y)
    assert not renommage_necessaire(('abs', 'y', x), 'x', ('abs', 'y', y))
    assert alpha_renommer(('abs', 'x', x), 'v') == ('abs', 'v', ('var', 'v'))
    assert alpha_renommer(('abs', 'y', x), 'v') == ('abs', 'v', x)
    assert alpha_renommer(('abs', 'x', ('abs', 'x', x)), 'v') == ('abs', 'v', ('abs', 'x', x))
    assert alpha_renommer(('abs', 'y', ('app', ('abs', 'y', y), y)), 'v') == \
        ('abs', 'v', ('app', ('abs', 'y', y), ('var', 'v')))
    assert alpha_renommer(T2, 'v') == \
        ('abs', 'v', ('app', ('abs', 'y', ('var', 'v')), ('app', ('var', 'v'), z)))
    for t in [T1, T2, T4]:
        r = alpha_renommer(t, 'v')
        assert r[1] == 'v' and variables_libres(r) == variables_libres(t)
    for t, nom in [(('abs', 'y', ('abs', 'y1', y)), 'y1'),
                   (('abs', 'y', ('app', y, z)), 'z'),
                   (('abs', 'y', y), 'y')]:
        try:
            alpha_renommer(t, nom)
            assert False, "ValueError attendue"
        except ValueError:
            pass
    assert eviter_capture(('abs', 'y', x), 'x', y) == ('abs', 'y1', x)
    assert eviter_capture(('abs', 'y', z), 'x', y) == ('abs', 'y', z)
    assert eviter_capture(('abs', 'x', x), 'x', y) == ('abs', 'x', x)
    assert eviter_capture(('abs', 'y', x), 'x', ('app', y, ('var', 'y1'))) == ('abs', 'y2', x)
    assert eviter_capture(('abs', 'y', ('app', x, ('abs', 'y', y))), 'x', y) == \
        ('abs', 'y1', ('app', x, ('abs', 'y', y)))


def test_substitution_correcte():
    assert substitution_correcte(('abs', 'y', x), 'x', y) == ('abs', 'y1', y)
    assert substitution_correcte(('abs', 'y', x), 'x', z) == ('abs', 'y', z)       # sans capture
    assert substitution_correcte(('abs', 'x', x), 'x', y) == ('abs', 'x', x)       # masquage
    assert substitution_correcte(('app', x, ('abs', 'y', x)), 'x', y) == \
        ('app', y, ('abs', 'y1', y))
    # deux abstractions imbriquées à renommer : la récursion renomme chacune
    M = ('abs', 'y', ('abs', 'z', ('app', x, ('app', y, z))))
    arg = ('app', y, z)
    r = substitution_correcte(M, 'x', arg)
    assert r == ('abs', 'y1', ('abs', 'z1', ('app', ('app', y, z), ('app', ('var', 'y1'), ('var', 'z1')))))
    assert variables_libres(r) == {'y', 'z'}
    # sans capture possible, les deux substitutions coïncident
    fermes = [x, ('abs', 'a', va), ('app', x, ('abs', 'q', ('var', 'q')))]
    corps = [x, ('app', x, y), ('abs', 'y', ('app', x, y)), ('abs', 'x', x),
             ('abs', 'a', ('abs', 'b', ('app', x, ('app', va, vb)))), T1, T2, T4, T5]
    for m in corps:
        for n in [z, ('abs', 'q', ('var', 'q')), ('app', z, z)]:
            if not (variables_libres(n) & noms_du_terme(m)):
                assert substitution_correcte(m, 'x', n) == substitution(m, 'x', n)


def test_betared2():
    assert betared(cap1) == ('abs', 'y', y)                         # naïf : FAUX
    assert betared2(cap1) == ('abs', 'y1', y)                       # correct
    assert variables_libres(betared2(cap1)) == variables_libres(cap1) == {'y'}
    assert variables_libres(betared(cap1)) == set()
    assert betared(cap2) == ('abs', 'a', ('abs', 'y', y))
    assert betared2(cap2) == ('abs', 'a', ('abs', 'y1', y))
    assert betared(cap3) == ('abs', 'y', ('app', ('abs', 'y', y), y))
    assert betared2(cap3) == ('abs', 'y1', ('app', ('abs', 'y', y), y))
    assert betared(mask) == ('abs', 'x', x) == betared2(mask)
    sans_capture = ('app', ('abs', 'x', ('abs', 'y', x)), z)
    assert betared(sans_capture) == betared2(sans_capture) == ('abs', 'y', z)
    for t in TOUS:
        assert betared2(t) == betared(t)
    assert betared2(('app', x, y)) == ('app', x, y)
    assert betared2(omega) == omega
    P = ('app', ('abs', 'a', va), w)
    R = ('app', ('abs', 'b', vb), y)
    assert betared2(('app', ('app', x, P), R)) == ('app', ('app', x, P), y)
    # avec normaliser
    assert normaliser(A) == ('abs', 'y', ('abs', 'z', z))                      # naïf
    assert normaliser(A, reduction=betared2) == ('abs', 'y', z)                # correct
    assert not est_forme_normale(normaliser(A, reduction=betared2, max_iter=1))
    assert est_forme_normale(normaliser(A, reduction=betared2, max_iter=2))
    for t in TOUS:
        assert normaliser(t, reduction=betared2) == normaliser(t)


def test_equivalent():
    for t in TOUS:
        assert equivalent(t, t)
    assert equivalent(x, x)
    assert equivalent(('abs', 'x', x), ('abs', 'y', y))
    assert equivalent(('abs', 'x', ('abs', 'y', x)), ('abs', 'a', ('abs', 'b', va)))
    for t in [T1, T2, T4]:
        assert equivalent(t, alpha_renommer(t, 'v'))
    assert equivalent(parseur(lexeur("/x./y.x y")), parseur(lexeur("/u./v.u v")))
    assert not equivalent(('abs', 'x', ('abs', 'y', x)), ('abs', 'x', ('abs', 'y', y)))
    assert not equivalent(('app', x, y), ('app', y, x))
    assert not equivalent(('app', x, y), ('abs', 'x', y))
    assert not equivalent(T1, T2)
    assert not equivalent(('abs', 'x', x), ('abs', 'x', ('abs', 'y', x)))
    assert not equivalent(('app', ('abs', 'x', x), y), y)
    assert equivalent(('abs', 'x', y), ('abs', 'z', y))
    assert not equivalent(('abs', 'x', y), ('abs', 'x', z))
    assert not equivalent(x, y)
    assert not equivalent(('abs', 'x', y), ('abs', 'y', y))
    assert equivalent(('app', x, ('abs', 'x', x)), ('app', x, ('abs', 'y', y)))
    assert equivalent(('abs', 'x', ('abs', 'x', x)), ('abs', 'a', ('abs', 'b', vb)))
    assert equivalent(('abs', 'x', ('abs', 'x', x)), ('abs', 'y', ('abs', 'x', x)))
    assert not equivalent(('abs', 'x', ('abs', 'x', x)), ('abs', 'a', ('abs', 'b', va)))
    assert not equivalent(('abs', 'x', ('abs', 'x', x)), ('abs', 'x', ('abs', 'y', x)))
    assert not equivalent(('abs', 'x', ('abs', 'y', x)), ('abs', 'y', ('abs', 'x', x)))
    assert equivalent(betared2(cap1), ('abs', 'q', y))
    assert not equivalent(betared2(cap1), betared(cap1))
    assert equivalent(normaliser(A, reduction=betared2), ('abs', 'u', z))
    assert not equivalent(normaliser(A, reduction=betared2), normaliser(A))
    assert equivalent(normaliser(T3, reduction=betared2), zz)
    g = ('app', ('abs', 'x', x), x)
    assert equivalent(g, ('app', ('abs', 'y', y), x))
    assert not equivalent(g, ('app', ('abs', 'y', y), y))                  # détecte une mutation en place
    paires = [(T1, T2), (T3, T3), (('abs', 'x', y), ('abs', 'z', y)),
              (('abs', 'x', ('abs', 'y', x)), ('abs', 'y', ('abs', 'x', x)))]
    for p, q in paires:
        assert equivalent(p, q) == equivalent(q, p)


# ----------------------------------------------------------------------------
# Intégration avec le Codeur 1
# ----------------------------------------------------------------------------

def test_integration_parseur():
    assert parseur(lexeur("/x.(/y.x) (x z)")) == T2
    assert parseur(lexeur("/x./y.(/u.x) y")) == T4
    assert parseur(lexeur("(/x.x x) (/y.y z)")) == T3
    assert parseur(lexeur("(/x./z.x) (/y.z) (/z.z)")) == A
    r = parseur(lexeur("(/x./y.x) y"))
    assert r == cap1
    assert en_texte(betared(r)) == "/y.y"
    assert en_texte(betared2(r)) == "/y1.y"
    assert parseur(lexeur(en_texte(betared2(r)))) == betared2(r)
    assert en_texte(normaliser(T2, reduction=betared2)) == "/x.x"
    assert en_texte(normaliser(A, reduction=betared2)) == "/y.z"
    for t in TOUS + [cap1, cap2, cap3, A, normaliser(A, reduction=betared2)]:
        assert parseur(lexeur(en_texte(t))) == t
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        affichage(normaliser(T3, reduction=betared2))
    assert sortie.getvalue().splitlines()[0] == "Terme : z z"


def test_addition():
    for m in range(0, 6):
        for n in range(0, 6):
            assert addition(m, n) == m + n
    assert addition(12, 9) == 21
    assert addition(0, 30) == 30 and addition(30, 0) == 30
    for k in (0, 1, 7):
        assert decoder_church(encoder_church(k)) == k
    for m, n in [(0, 0), (1, 2), (3, 4), (5, 5)]:
        r = normaliser(terme_addition(m, n), reduction=betared2, max_iter=10000)
        assert est_forme_normale(r)
        assert decoder_church(r) == m + n
        assert equivalent(r, encoder_church(m + n))     # robuste aux noms produits par nom_frais


# ----------------------------------------------------------------------------
# Cas limites
# ----------------------------------------------------------------------------

def test_cas_limites():
    # Ω : ni forme normale, ni changement ; la limite arrête la boucle
    for red in (betared, betared2):
        assert red(omega) == omega
        for k in (0, 1, 5, 100):
            r = normaliser(omega, reduction=red, max_iter=k)
            assert r == omega and not est_forme_normale(r)
    # limite d'itérations : un résultat qui n'est pas normal est reconnu comme tel
    t = terme_addition(2, 2)
    k = 0
    while not est_forme_normale(normaliser(t, reduction=betared2, max_iter=k)):
        k += 1
    assert k > 1
    assert not est_forme_normale(normaliser(t, reduction=betared2, max_iter=k - 1))
    assert normaliser(t, reduction=betared2, max_iter=k) == \
        normaliser(t, reduction=betared2, max_iter=k + 50)    # stable une fois normal
    assert normaliser(t, reduction=betared2, max_iter=-3) == t
    # abstractions imbriquées : même nom à plusieurs niveaux
    assert normaliser(parseur(lexeur("(/x./x./x.x) y z w")), reduction=betared2) == w
    assert betared2(parseur(lexeur("(/x./x.x) y"))) == ('abs', 'x', x)
    # termes profonds
    def profond(n, prefixe):
        corps = ('var', prefixe + '0')
        for i in reversed(range(n)):
            corps = ('abs', prefixe + str(i), corps)
        return corps
    p1, p2 = profond(400, 'u'), profond(400, 'v')
    assert equivalent(p1, p2)
    assert variables_libres(p1) == set()
    assert variables_libres(('app', p1, y)) == {'y'}
    # substitution sans capture : aucun renommage inutile
    assert betared2(('app', ('abs', 'x', ('abs', 'y', x)), ('abs', 'q', ('var', 'q')))) == \
        ('abs', 'y', ('abs', 'q', ('var', 'q')))


# ----------------------------------------------------------------------------
# Propriétés sur des termes aléatoires
# ----------------------------------------------------------------------------

def _aleatoire(profondeur, rng):
    if profondeur == 0 or rng.random() < 0.2:
        return ('var', rng.choice('abcd'))
    if rng.random() < 0.4:
        return ('abs', rng.choice('abcd'), _aleatoire(profondeur - 1, rng))
    return ('app', _aleatoire(profondeur - 1, rng), _aleatoire(profondeur - 1, rng))


def _variante(t, env, compteur):
    """Renomme toutes les variables liées de t par q0, q1, ... (libres inchangées)."""
    if t[0] == 'var':
        return ('var', env.get(t[1], t[1]))
    if t[0] == 'app':
        return ('app', _variante(t[1], env, compteur), _variante(t[2], env, compteur))
    nom = 'q' + str(compteur[0])
    compteur[0] += 1
    env2 = dict(env)
    env2[t[1]] = nom
    return ('abs', nom, _variante(t[2], env2, compteur))


def _taille(t):
    if t[0] == 'var':
        return 1
    if t[0] == 'abs':
        return 1 + _taille(t[2])
    return 1 + _taille(t[1]) + _taille(t[2])


def _verifier_aleatoires(nombre, graine, max_iter=10, taille_max=4000):
    rng = random.Random(graine)
    echecs_naif = 0
    teste = 0
    for _ in range(nombre):
        t = _aleatoire(5, rng)
        v = _variante(t, {}, [0])
        assert equivalent(t, v)
        assert variables_libres(t) == variables_libres(v)
        r1, r2, r3 = t, v, t
        n1 = n2 = n3 = None
        for _ in range(max_iter):
            if _taille(r1) > taille_max or _taille(r2) > taille_max:
                break
            r1, r2 = betared2(r1), betared2(r2)
            assert variables_libres(r1) <= variables_libres(t)
        else:
            teste += 1
            # un terme et sa variante alpha donnent des résultats équivalents
            assert equivalent(r1, r2)
            # même chose avec la version naïve : compte les désaccords
            s1, s2 = t, v
            for _ in range(max_iter):
                s1, s2 = betared(s1), betared(s2)
            if not equivalent(s1, s2):
                echecs_naif += 1
    return teste, echecs_naif


def test_proprietes_aleatoires():
    teste, _ = _verifier_aleatoires(400, 2026)
    assert teste > 100          # assez de termes retenus pour que le test ait un sens


# ----------------------------------------------------------------------------
# Mesures (facultatif)
# ----------------------------------------------------------------------------

def mesures():
    print("\nMesures de temps pour addition(n, n) :")
    for n in (10, 50, 100, 200, 400):
        debut = time.perf_counter()
        resultat = addition(n, n)
        duree = time.perf_counter() - debut
        print(f"  addition({n}, {n}) = {resultat}   {duree:.3f} s")


def demo_limite_strategie():
    """Non lancé par défaut : montre la limite de la stratégie 'profondeur minimale'."""
    texte = "(/x.x) (/x.x) (/a./b.b) ((/w.w w) (/w.w w))"
    t = parseur(lexeur(texte))
    r = normaliser(t, reduction=betared2, max_iter=1000)
    print("terme          :", texte)
    print("forme normale ?", est_forme_normale(r))


TESTS = [
    test_substitution_naive, test_betared, test_normaliser,
    test_variables_libres_liees, test_alpha_renommage, test_substitution_correcte,
    test_betared2, test_equivalent,
    test_integration_parseur, test_addition, test_cas_limites,
    test_proprietes_aleatoires,
]


def lancer():
    echecs = 0
    for test in TESTS:
        try:
            test()
            print("OK    ", test.__name__)
        except AssertionError:
            echecs += 1
            import traceback
            print("ECHEC ", test.__name__)
            traceback.print_exc()
        except Exception as e:  # erreur inattendue (récursion, nom manquant...)
            echecs += 1
            print("ERREUR", test.__name__, "->", type(e).__name__, e)
    print(f"\n{len(TESTS) - echecs}/{len(TESTS)} groupes de tests réussis")
    return echecs


if __name__ == "__main__":
    code = lancer()
    if "--mesures" in sys.argv:
        mesures()
    sys.exit(1 if code else 0)

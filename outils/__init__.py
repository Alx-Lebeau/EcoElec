"""Outillage du cours : lecture des modules et des parcours, vérifications, génération des decks.

Vocabulaire (identifiants en anglais, données en français) :
    module      Module        unité de contenu autonome (modules/<id>/)
    parcours    Track         sélection ordonnée de modules (parcours/<nom>.yml)
    séance      Session       un créneau d'un parcours ; produit un deck
    base        base          contenu non marqué d'un module, présent partout
    option      option        couche ajoutée à la base : approfondissement | formel
"""

# Une option porte le nom de la marque qu'elle rend visible dans les slides.
OPTIONS = ("approfondissement", "formel")
OPTION_LABELS = {"approfondissement": "approfondissements", "formel": "formalisme"}


def options_label(options) -> str:
    """Libellé d'un choix d'options, dans l'ordre de OPTIONS : « base », « avec formalisme »…"""
    chosen = [OPTION_LABELS[o] for o in OPTIONS if o in options]
    return "avec " + " et ".join(chosen) if chosen else "base"

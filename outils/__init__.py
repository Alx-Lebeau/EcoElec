"""Outillage du cours : lecture des modules et des parcours, vérifications, génération des decks.

Vocabulaire (identifiants en anglais, données en français) :
    module      Module        unité de contenu autonome (modules/<id>/)
    parcours    Track         sélection ordonnée de modules (parcours/<nom>.yml)
    séance      Session       un créneau d'un parcours ; produit un deck
    profondeur  depth         essentiel | complet
    formalisme  formalism     intuitif | formel
"""

DEPTHS = ("essentiel", "complet")
FORMALISMS = ("intuitif", "formel")

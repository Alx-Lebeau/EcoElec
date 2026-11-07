--[[
Marques de contenu des slides.

  .approfondissement  visible dans la version complète seulement
  .formel             visible dans la version formelle seulement
  .intuitif           visible dans la version intuitive seulement
  .rappel             visible quand un module prérequis ne précède pas ce module
                      (attribut facultatif module="id" : ce prérequis-là seulement)

Une marque s'applique :
  - à une slide entière : `## Titre {.formel}` (jusqu'au titre suivant de même
    niveau ou de niveau supérieur, ou jusqu'au prochain `---`) ;
  - à un bloc : `::: {.formel}` … `:::` ;
  - à un passage dans une phrase : `[texte]{.intuitif}`.
Plusieurs marques sur un même élément se cumulent : il faut que toutes soient visibles.

Le générateur de decks (`ecoelec generer`) place avant chaque module un marqueur

  ::: {.ecoelec-module module="court-terme" profondeur="essentiel" formalisme="intuitif" manquants="systeme"}
  :::

qui fixe la version du contenu qui suit, jusqu'au marqueur suivant. `manquants`
liste les prérequis du module qui ne le précèdent pas dans le parcours.

Vue auteur (métadonnée `ecoelec: {vue: auteur}`) : tout est conservé et chaque
marque devient une classe marque-* (bandeau de couleur, voir commun/slides.scss).

Exécuté au stade pre-ast de Quarto, avant la création des callouts et figures.
--]]

local MARKS = {
  approfondissement = true,
  formel = true,
  intuitif = true,
  rappel = true,
}
local MARKER = "ecoelec-module"

-- Version du module en cours ; par défaut, tout ce qui n'est pas conditionnel au parcours.
local state = {
  depth = "complet",
  formalism = "formel",
  missing = {},
  author = false,
}

local function word_set(s)
  local set = {}
  for w in string.gmatch(s or "", "[^%s,]+") do
    set[w] = true
  end
  return set
end

local function marks_of(el)
  local found = {}
  for _, c in ipairs(el.classes) do
    if MARKS[c] then
      table.insert(found, c)
    end
  end
  return found
end

local function is_visible(mark, el)
  if mark == "approfondissement" then
    return state.depth == "complet"
  elseif mark == "formel" then
    return state.formalism == "formel"
  elseif mark == "intuitif" then
    return state.formalism == "intuitif"
  elseif mark == "rappel" then
    local target = el.attributes["module"]
    if target then
      return state.missing[target] == true
    end
    return next(state.missing) ~= nil
  end
  return true
end

local function keep(marks, el)
  if state.author then
    return true
  end
  for _, m in ipairs(marks) do
    if not is_visible(m, el) then
      return false
    end
  end
  return true
end

-- Retire les classes de marque (vue auteur : les remplace par marque-*).
local function strip_marks(el)
  local classes = pandoc.List()
  local had_recall = false
  for _, c in ipairs(el.classes) do
    if MARKS[c] then
      had_recall = had_recall or c == "rappel"
      if state.author then
        classes:insert("marque-" .. c)
      end
    else
      classes:insert(c)
    end
  end
  el.classes = classes
  if had_recall then
    el.attributes["module"] = nil
  end
  return el
end

-- Un bloc ou passage sans classe, identifiant ni attribut peut être déballé.
local function is_bare(el)
  return #el.classes == 0 and el.identifier == "" and #el.attributes == 0
end

local process_blocks

local function handle_span(s)
  local marks = marks_of(s)
  if #marks == 0 then
    return nil
  end
  if not keep(marks, s) then
    return {}
  end
  strip_marks(s)
  if is_bare(s) then
    return s.content
  end
  return s
end

local function handle_div(d)
  local marks = marks_of(d)
  if #marks > 0 and not keep(marks, d) then
    return {}
  end
  if #marks > 0 then
    strip_marks(d)
  end
  d.content = process_blocks(d.content)
  if #marks > 0 and is_bare(d) then
    return d.content
  end
  return d
end

-- Pour les autres blocs (paragraphes, listes, citations…) : marques imbriquées.
local nested = {
  traverse = "topdown",
  Div = function(d)
    return handle_div(d), false
  end,
  Span = function(s)
    return handle_span(s), false
  end,
}

process_blocks = function(blocks)
  local out = pandoc.Blocks({})
  local skip_level = nil -- niveau du titre de la slide marquée en cours de suppression

  for _, b in ipairs(blocks) do
    if b.t == "Div" and b.classes:includes(MARKER) then
      local a = b.attributes
      state.depth = a["profondeur"] or "complet"
      state.formalism = a["formalisme"] or "formel"
      state.missing = word_set(a["manquants"])
      skip_level = nil
    elseif b.t == "Header" then
      if skip_level and b.level <= skip_level then
        skip_level = nil
      end
      if not skip_level then
        local marks = marks_of(b)
        if #marks > 0 and not keep(marks, b) then
          skip_level = b.level
        else
          if #marks > 0 then
            strip_marks(b)
          end
          out:insert(b:walk(nested))
        end
      end
    elseif b.t == "RawBlock" and (b.format == "tex" or b.format == "latex") then
      -- Définitions de commun/_macros.qmd : déjà développées par pandoc à la
      -- lecture ; laissées dans le document, elles créeraient une slide vide.
    elseif b.t == "HorizontalRule" then
      skip_level = nil
      out:insert(b)
    elseif skip_level then
      -- contenu d'une slide marquée non visible : supprimé
    elseif b.t == "Div" then
      out:extend(pandoc.Blocks(handle_div(b)))
    else
      out:insert(b:walk(nested))
    end
  end
  return out
end

function Pandoc(doc)
  local meta = doc.meta.ecoelec
  if meta and meta.vue then
    state.author = pandoc.utils.stringify(meta.vue) == "auteur"
  end
  doc.blocks = process_blocks(doc.blocks)
  return doc
end

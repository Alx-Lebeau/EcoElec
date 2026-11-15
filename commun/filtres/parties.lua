--[[
Parties d'un module dans les slides.

Une slide ouvre une partie avec l'attribut `partie` sur son titre :

  ## Un système physique {partie="Système physique"}

La partie vaut pour les slides suivantes du même module, jusqu'à la suivante.
Chaque slide d'une partie reçoit :
  - `data-partie` : nom affiché en étiquette au-dessus du titre ;
  - `style="--partie: i; --parties: n"` : rang de la partie et nombre de parties
    du module, pour la barre de progression par partie (commun/slides.scss).

Le décompte repart à zéro à chaque module (marqueur `.ecoelec-module` posé par
`ecoelec generer`). Exécuté au stade pre-ast, avant marques.lua qui retire ces
marqueurs.
--]]

local MARKER = "ecoelec-module"

local function is_marker(b)
  return b.t == "Div" and b.classes:includes(MARKER)
end

-- Découpe les blocs de premier niveau en segments, un par module.
local function segments(blocks)
  local result, current = {}, {}
  for i, b in ipairs(blocks) do
    if is_marker(b) and #current > 0 then
      table.insert(result, current)
      current = {}
    end
    table.insert(current, i)
  end
  table.insert(result, current)
  return result
end

local function annotate(blocks, indices)
  -- Premier passage : parties du module, dans l'ordre d'apparition.
  local order, rank = {}, {}
  for _, i in ipairs(indices) do
    local b = blocks[i]
    if b.t == "Header" and b.level == 2 and b.attributes["partie"] then
      local name = b.attributes["partie"]
      if not rank[name] then
        table.insert(order, name)
        rank[name] = #order
      end
    end
  end
  if #order == 0 then
    return
  end
  -- Second passage : chaque slide porte la partie en cours.
  local current = nil
  for _, i in ipairs(indices) do
    local b = blocks[i]
    if b.t == "Header" and b.level == 1 then
      current = nil
    elseif b.t == "Header" and b.level == 2 then
      if b.attributes["partie"] then
        current = b.attributes["partie"]
        b.attributes["partie"] = nil
      end
      if current then
        b.attributes["data-partie"] = current
        b.attributes["style"] = string.format("--partie: %d; --parties: %d", rank[current], #order)
      end
    end
  end
end

function Pandoc(doc)
  for _, indices in ipairs(segments(doc.blocks)) do
    annotate(doc.blocks, indices)
  end
  return doc
end

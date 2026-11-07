--[[
Encadrés « Formalisation » du poly.

  ::: {.formalisation titre="Dualité et prix"}
  Développement mathématique…
  :::

devient un encadré titré « Formalisation : Dualité et prix », replié par défaut
dans la version HTML. Avec la métadonnée `ecoelec: {formalisation: false}`
(profil de poly sans formalisation), les encadrés sont supprimés.

Exécuté au stade pre-ast : le bloc est transformé en callout, que Quarto met
ensuite en forme pour chaque format.
--]]

local show = true

local function read_meta(meta)
  local cfg = meta.ecoelec
  if cfg and cfg.formalisation ~= nil then
    show = pandoc.utils.stringify(cfg.formalisation) ~= "false"
  end
end

local function to_callout(d)
  if not d.classes:includes("formalisation") then
    return nil
  end
  if not show then
    return {}
  end
  local title = "Formalisation"
  local subtitle = d.attributes["titre"]
  if subtitle and subtitle ~= "" then
    title = title .. "\u{00A0}: " .. subtitle
  end
  d.attributes["titre"] = nil
  d.classes:insert(1, "callout-note")
  d.attributes["title"] = title
  d.attributes["icon"] = "false"
  if FORMAT:match("html") then
    d.attributes["collapse"] = "true"
  end
  return d
end

return {
  { Meta = read_meta },
  { Div = to_callout },
}

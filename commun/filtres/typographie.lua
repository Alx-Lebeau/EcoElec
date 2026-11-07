--[[
Typographie française automatique, pour le poly et les slides.

  - espace insécable avant « : » et espace fine insécable avant « ; ! ? » ;
  - espaces fines insécables à l'intérieur des guillemets « ».

Le texte source s'écrit avec des espaces ordinaires (« Durée : 90 min ») ; le
filtre les remplace dans le rendu. Ne touche ni au code, ni aux maths, ni aux URL.
--]]

local NBSP = "\u{00A0}"        -- espace insécable
local NNBSP = "\u{202F}"       -- espace fine insécable

local BEFORE = {
  [":"] = NBSP,
  [";"] = NNBSP,
  ["!"] = NNBSP,
  ["?"] = NNBSP,
  ["»"] = NNBSP,
}

local function starts_with_punct(el)
  if el and el.t == "Str" then
    for p, space in pairs(BEFORE) do
      if el.text:sub(1, #p) == p then
        return space
      end
    end
  end
  return nil
end

local function ends_with_open_quote(el)
  return el and el.t == "Str" and el.text:sub(-#"«") == "«"
end

function Inlines(inlines)
  for i = 1, #inlines do
    local el = inlines[i]
    if el.t == "Space" or el.t == "SoftBreak" then
      local space = starts_with_punct(inlines[i + 1])
      if space then
        inlines[i] = pandoc.Str(space)
      elseif ends_with_open_quote(inlines[i - 1]) then
        inlines[i] = pandoc.Str(NNBSP)
      end
    end
  end
  return inlines
end

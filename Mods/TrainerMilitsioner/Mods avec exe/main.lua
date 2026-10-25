-- TrainerMilitsioner : lanceur
local src = debug.getinfo(1, "S").source:gsub("^@", "")
local DIR = src:match("(.*[/\\])") or ""
local chunk, err = loadfile(DIR .. "core.bin")
if not chunk then chunk, err = loadfile(DIR .. "core.lua") end
if not chunk then
    print("[TrainerMilitsioner] Chargement impossible : " .. tostring(err) .. "\n")
    return
end
chunk(DIR)

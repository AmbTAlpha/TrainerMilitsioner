local UEHelpers = require("UEHelpers")

local DIR = (...)
if type(DIR) ~= "string" then
    local src = debug.getinfo(1, "S").source:gsub("^@", "")
    DIR = src:match("(.*[/\\])") or ""
end
local CMD = DIR .. "commands.txt"

local S = {
    god = false,
    noclip = false,
    giant_safe = false,
    npc_invisible = false,
stealth_test = false,
    armed = false,
    speed = 600,
    up = false,
    down = false,
}

local WriteStatus = function() end

local function PC()
    local ok, pc = pcall(function()
        local value = UEHelpers.GetPlayerController()
        if value and value:IsValid() then return value end
        return nil
    end)
    if ok then return pc end
    return nil
end

local function Pawn()
    local ok, pawn = pcall(function()
        local pc = PC()
        if pc and pc.Pawn and pc.Pawn:IsValid() then return pc.Pawn end
        return nil
    end)
    if ok then return pawn end
    return nil
end

local function Source()
    local p = Pawn()
    if p and p.Source and p.Source:IsValid() then
        return p.Source
    end
    return nil
end

local GIANT_CACHE = nil
local function GetGiant()
    if GIANT_CACHE then
        local ok, valid = pcall(function() return GIANT_CACHE:IsValid() end)
        if ok and valid then return GIANT_CACHE end
        GIANT_CACHE = nil
    end
    local giants = FindAllOf("Giant")

    if giants then
        for _, giant in ipairs(giants) do
            if giant and giant:IsValid() then
                GIANT_CACHE = giant
                return giant
            end
        end
    end

    return nil
end

local function GetNPCs()
    return FindAllOf("CharacterNPC") or {}
end

local function ApplyGiantSafe(enabled, show_message)
    local giant = GetGiant()

    if not giant then
        if show_message then
            print("Geant pas encore trouve\n")
        end
        return false
    end

    local ok, err = pcall(function()
        giant:SetPlayerCatchingInvincibility(enabled)
        giant:SetLockHandDamage(enabled)
    end)

    if show_message then
        if ok then
            if enabled then
                print("Protection geant activee : capture + main bloquees\n")
            else
                print("Protection geant desactivee\n")
            end
        else
            print("Erreur protection geant: " .. tostring(err) .. "\n")
        end
    end

    return ok
end

local function ApplyNPCInvisible(enabled, show_message)
    local npcs = GetNPCs()
    local changed = 0

    for _, npc in ipairs(npcs) do
        if npc and npc:IsValid() then
            local ok = pcall(function()

                npc.PerceptionComponent:SetComponentTickEnabled(not enabled)
            end)

            if ok then
                changed = changed + 1
            end
        end
    end

    if show_message then
        if enabled then
            print("Mode discret PNJ actif sur " .. tostring(changed) .. " PNJ\n")
        else
            print("Mode discret PNJ desactive sur " .. tostring(changed) .. " PNJ\n")
        end
    end

    return changed
end

local STEALTH_BASE = {player = nil, perception = {}, giant = nil, tag = false}
local NOISE_PROPS = {"WalkNoiseMultiplier", "CrouchNoiseMultiplier", "SprintNoiseMultiplier", "JumpNoiseMultiplier", "DefaultLandingNoiseRadius"}
local GIANT_HEARING_PROPS = {"PlayerStepsHearingDistance", "PlayerSprintHearingDistance", "NoiseFromPlayerValue"}

local function StealthPlayerSide(enabled, errors)
    local p = Pawn()
    if p then
        local ok, err = pcall(function()
            if enabled then
                if not STEALTH_BASE.player or STEALTH_BASE.player.name ~= p:GetFullName() then
                    local saved = {}
                    for _, key in ipairs(NOISE_PROPS) do
                        local rok, v = pcall(function() return p[key] end)
                        if rok and type(v) == "number" then saved[key] = v end
                    end
                    STEALTH_BASE.player = {name = p:GetFullName(), values = saved}
                end
                for key in pairs(STEALTH_BASE.player.values) do p[key] = 0.0 end
                p.bWillBeSpottedByGiant = false
                p.bWillBeSpottedByGiant_Cached = false
            else
                if STEALTH_BASE.player and STEALTH_BASE.player.name == p:GetFullName() then
                    for key, v in pairs(STEALTH_BASE.player.values) do p[key] = v end
                end
                STEALTH_BASE.player = nil
            end
        end)
        if not ok then table.insert(errors, "joueur:" .. tostring(err)) end
    end
    local source = Source()
    if source then
        local ok, err = pcall(function()
            if enabled then
                source:SetStealthCoef(1000000.0)
                source:SetLightLevelMultiplier(0.0)
                source:SetForceLighted(false, 0.0)
                source:SetAggressionCause(false)
            else
                source:SetStealthCoef(1.0)
                source:SetLightLevelMultiplier(1.0)
                source:SetForceLighted(false, 0.0)
                source:SetAggressionCause(false)
            end
        end)
        if not ok then table.insert(errors, "source:" .. tostring(err)) end
    else
        table.insert(errors, "SourceComponent introuvable")
    end
end

local function StealthNPCSide(enabled, errors)
    local changed = 0
    for _, npc in ipairs(GetNPCs()) do
        local ok = pcall(function()
            if not npc or not npc:IsValid() then return end
            local perc = npc.PerceptionComponent
            if not perc or not perc:IsValid() then return end
            local key = perc:GetFullName()
            if enabled then
                if not STEALTH_BASE.perception[key] then
                    STEALTH_BASE.perception[key] = {pu = perc.PerceptionSpeedUp, au = perc.AggressionSpeedUp}
                end
                perc.PerceptionSpeedUp = 0.0
                perc.AggressionSpeedUp = 0.0
                perc:ResetAggression()
            else
                local base = STEALTH_BASE.perception[key]
                if base then
                    perc.PerceptionSpeedUp = base.pu
                    perc.AggressionSpeedUp = base.au
                end
                STEALTH_BASE.perception[key] = nil
            end
        end)
        if ok then changed = changed + 1 end
    end

    local giant = GetGiant()
    if giant then
        local ok, err = pcall(function()
            if enabled then
                if not STEALTH_BASE.giant or STEALTH_BASE.giant.name ~= giant:GetFullName() then
                    local saved = {}
                    for _, key in ipairs(GIANT_HEARING_PROPS) do
                        local rok, v = pcall(function() return giant[key] end)
                        if rok and type(v) == "number" then saved[key] = v end
                    end
                    STEALTH_BASE.giant = {name = giant:GetFullName(), values = saved}
                end
                for key in pairs(STEALTH_BASE.giant.values) do giant[key] = 0.0 end
                giant:SetSightSpeedMultiplier(0.0)
                giant:SetForceKnowsPlayerState(false)
                giant.bSightFocused = false
            else
                if STEALTH_BASE.giant and STEALTH_BASE.giant.name == giant:GetFullName() then
                    for key, v in pairs(STEALTH_BASE.giant.values) do giant[key] = v end
                end
                STEALTH_BASE.giant = nil
                giant:SetSightSpeedMultiplier(1.0)
                giant:ResetAggressionSpeed()
            end
        end)
        if not ok then table.insert(errors, "geant:" .. tostring(err)) end
    else
        table.insert(errors, "geant introuvable")
    end
    return changed
end

local function ApplyStealthTest(enabled, show_message)
    local errors = {}
    StealthPlayerSide(enabled, errors)
    local changed = StealthNPCSide(enabled, errors)
    if show_message then
        print("[FURTIVITE] actif=" .. tostring(enabled) .. " ; PNJ traites=" .. tostring(changed) .. "\n")
        local giant = GetGiant()
        if giant then
            local function read(label, fn)
                local ok, v = pcall(fn)
                print("[FURTIVITE]   " .. label .. "=" .. (ok and tostring(v) or "illisible") .. "\n")
            end
            read("geant.vitesse_perception", function() return giant.PerceptionComponent.PerceptionSpeedUp end)
            read("geant.vitesse_agressivite", function() return giant.PerceptionComponent.AggressionSpeedUp end)
            read("geant.valeur_agressivite", function() return giant.PerceptionComponent.AggressionValue end)
            read("geant.a_repere_le_joueur", function() return giant:HasSpottedPlayer() end)
        end
        for _, e in ipairs(errors) do print("[FURTIVITE ERREUR] " .. e .. "\n") end
    end
    return #errors == 0
end

local function SetFallProtection(enabled)
    local p = Pawn()

    if not p then
        return
    end

    pcall(function()
        p:SetIgnoreFallDamage(enabled)
    end)

    pcall(function()
        if enabled then
            p.MinFallDamageHeight = 1000000.0
            p.MaxFallDamageHeight = 1000001.0
        else
            p.MinFallDamageHeight = 250.0
            p.MaxFallDamageHeight = 800.0
        end
    end)
end

local function DumpProps()
    local p = Pawn()

    if not p then
        print("Pas de personnage pour props.txt\n")
        return
    end

    local out = io.open(DIR .. "props.txt", "w")

    if not out then
        print("Impossible de creer props.txt\n")
        return
    end

    local cls = p:GetClass()

    while cls and cls:IsValid() do
        out:write("=== " .. cls:GetFName():ToString() .. "\n")

        pcall(function()
            cls:ForEachProperty(function(prop)
                out:write(
                    prop:GetFName():ToString()
                    .. " : "
                    .. prop:GetClass():GetFName():ToString()
                    .. "\n"
                )
            end)
        end)

        cls = cls:GetSuperStruct()
    end

    out:close()
    print("props.txt ecrit\n")
end

local function DumpActors()
    local counts = {}

    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local name = a:GetClass():GetFName():ToString()
            counts[name] = (counts[name] or 0) + 1
        end
    end

    local out = io.open(DIR .. "actors.txt", "w")

    if not out then
        print("Impossible de creer actors.txt\n")
        return
    end

    for name, count in pairs(counts) do
        out:write(name .. " x" .. count .. "\n")
    end

    out:close()
    print("actors.txt ecrit\n")
end

local function ToggleNoclip()
    local p = Pawn()

    if not p and not S.noclip then
        print("Pas de personnage\n")
        return
    end

    S.noclip = not S.noclip
    S.up = false
    S.down = false

    if not p then
        return
    end

    pcall(function()
        if S.noclip then
            p.CharacterMovement.MaxFlySpeed = 2500
            p.CharacterMovement:SetMovementMode(5, 0)
            p:SetActorEnableCollision(false)
            print("Noclip + vol: actif\n")
        else
            p:SetActorEnableCollision(true)
            p.CharacterMovement:SetMovementMode(1, 0)
            print("Noclip + vol: inactif\n")
        end
    end)
end

local GOD_BASE = nil
local function ToggleGod()
    S.god = not S.god
    local p = Pawn()
    if p then
        pcall(function()
            if S.god then
                GOD_BASE = {max = p.MaxHealth, health = p.Health, air = p.Air, airloss = p.AirLossRate, damageable = p.bCanBeDamaged}
            elseif GOD_BASE then
                p.MaxHealth = GOD_BASE.max
                p.Health = math.min(p.Health, GOD_BASE.max)
                p.Air = GOD_BASE.air
                p.AirLossRate = GOD_BASE.airloss
                p.bCanBeDamaged = GOD_BASE.damageable
                GOD_BASE = nil
            end
        end)
    end
    SetFallProtection(S.god)
    print("God mode: " .. tostring(S.god) .. "\n")
end

local function ToggleGiantSafe()
    S.giant_safe = not S.giant_safe
    ApplyGiantSafe(S.giant_safe, true)
end

local function ToggleNPCInvisible()
    S.npc_invisible = not S.npc_invisible
    ApplyNPCInvisible(S.npc_invisible, true)
end

local function ToggleStealthTest()
    S.stealth_test = not S.stealth_test
    ApplyStealthTest(S.stealth_test, true)
end

local ITEM_CLASSES = {}
local function LoadItemFile(name)
    local file = io.open(DIR .. name, "r")
    if not file then return false end
    for line in file:lines() do
        local id, label, path = line:match("^([^\t]+)\t([^\t]+)\t([^\t\r]+)")
        if id and id ~= "id" and not ITEM_CLASSES[id] then ITEM_CLASSES[id] = path end
    end
    file:close()
    return true
end
local function LoadAllItems()
    ITEM_CLASSES = {}
    if not LoadItemFile("items_catalog.tsv") then print("[SPAWN ERREUR] Catalogue absent\n") end
    LoadItemFile("items_discovered.tsv")
end
LoadAllItems()

local SCAN_SKIP_PATH = {"Widget", "/UI/", "/Anim", "Cinematic", "Sequence", "DEV_", "/Debug", "/Test", "/Developers/", "Tutor", "Landscape", "/Maps/", "/Audio/", "/FX/", "/Niagara"}
local SCAN_SKIP_CLASSES = {"/Script/Engine.Pawn", "/Script/Engine.Controller", "/Script/Engine.Info", "/Script/Engine.HUD", "/Script/Engine.Volume", "/Script/Engine.CameraActor", "/Script/Engine.Light", "/Script/Engine.LevelScriptActor"}

local function ScanItems()
    local actorClass = StaticFindObject("/Script/Engine.Actor")
    local skipClasses = {}
    for _, path in ipairs(SCAN_SKIP_CLASSES) do
        local ok, cls = pcall(StaticFindObject, path)
        if ok and cls and cls:IsValid() then table.insert(skipClasses, cls) end
    end
    local known = {}
    for _, path in pairs(ITEM_CLASSES) do known[path] = true end
    local classes = FindAllOf("BlueprintGeneratedClass") or {}
    local rows, seen = {}, {}
    for _, cls in ipairs(classes) do
        pcall(function()
            if not cls:IsValid() then return end
            local path = cls:GetFullName():match("^%S+%s+(/Game/.+)$")
            if not path or known[path] or seen[path] then return end
            local name = path:match("%.([^%.]+)$")
            if not name or not name:match("_C$") or name:match("^SKEL_") or name:match("^REINST_") then return end
            for _, word in ipairs(SCAN_SKIP_PATH) do
                if path:find(word, 1, true) then return end
            end
            if actorClass and actorClass:IsValid() and not cls:IsChildOf(actorClass) then return end
            for _, skip in ipairs(skipClasses) do
                if cls:IsChildOf(skip) then return end
            end
            seen[path] = true
            local category = "Divers trouvés"
            if path:find("/Items/", 1, true) then category = "Objets trouvés"
            elseif path:find("/Interactive_Actors/", 1, true) then category = "Interactifs trouvés"
            elseif path:find("/Props/", 1, true) or path:find("/Environment/", 1, true) then category = "Décor trouvé" end
            table.insert(rows, {id = name, path = path, category = category})
        end)
    end
    table.sort(rows, function(x, y) return x.id < y.id end)
    local out = io.open(DIR .. "items_discovered.tsv", "w")
    if not out then error("Impossible d'ecrire items_discovered.tsv") end
    out:write("id\tlabel\tpath\tstatus\tcategory\tinternal\n")
    for _, row in ipairs(rows) do
        local internal = row.id:gsub("_C$", "")
        out:write(row.id .. "\t" .. internal .. "\t" .. row.path .. "\tdecouvert\t" .. row.category .. "\t" .. internal .. "\n")
    end
    out:close()
    LoadAllItems()
    print("[SCAN] " .. #rows .. " nouvelles classes trouvees (items_discovered.tsv)\n")
end

local CAT_TRACKERS = {}
local LAST_SPAWNED_CAT = nil

local function CatRead(label, getter)
    local ok, value = pcall(getter)
    if ok then return label .. "=" .. tostring(value) end
    return label .. "=lecture_indisponible"
end

local function CatSnapshot(actor, phase)
    local ok, err = pcall(function()
        if not actor or not actor:IsValid() then
            print("[CHAT DIAG] phase=" .. phase .. " acteur=invalide_ou_supprime\n")
            return
        end
        local details = {"phase=" .. phase, "acteur=" .. actor:GetFullName()}
        table.insert(details, CatRead("position", function()
            local pos = actor:K2_GetActorLocation()
            return string.format("%.1f,%.1f,%.1f", pos.X, pos.Y, pos.Z)
        end))
        table.insert(details, CatRead("cache", function() return actor.bHidden end))
        table.insert(details, CatRead("echelle", function()
            local scale = actor:GetActorScale3D()
            return string.format("%.3f,%.3f,%.3f", scale.X, scale.Y, scale.Z)
        end))
        table.insert(details, CatRead("mesh", function()
            local mesh = actor.StaticMeshComponent0
            if not mesh or not mesh:IsValid() then return "composant_absent" end
            return mesh:GetFullName()
        end))
        table.insert(details, CatRead("mesh_visible", function() return actor.StaticMeshComponent0.bVisible end))
        table.insert(details, CatRead("mesh_cache", function() return actor.StaticMeshComponent0.bHiddenInGame end))
        table.insert(details, CatRead("mesh_asset", function()
            local asset = actor.StaticMeshComponent0.StaticMesh
            if not asset or not asset:IsValid() then return "absent" end
            return asset:GetFullName()
        end))
        print("[CHAT DIAG] " .. table.concat(details, " | ") .. "\n")
    end)
    if not ok then print("[CHAT DIAG ERREUR] " .. tostring(err) .. "\n") end
end

local function TrackCat(actor)
    LAST_SPAWNED_CAT = actor
    CatSnapshot(actor, "immediat")
    if #CAT_TRACKERS >= 8 then table.remove(CAT_TRACKERS, 1) end
    table.insert(CAT_TRACKERS, {actor = actor, checks = 0})
end

local function RevealLastCat()
    local actor = LAST_SPAWNED_CAT
    if not actor or not actor:IsValid() then
        print("[CHAT ESSAI] Aucun dernier chat valide ; cree un chat avant cet essai\n")
        return
    end
    local ok, err = pcall(function() actor:SetActorHiddenInGame(false) end)
    print("[CHAT ESSAI] visibilite_acteur=" .. tostring(ok) .. (ok and "" or " erreur=" .. tostring(err)) .. "\n")
    local mesh_ok, mesh_err = pcall(function()
        local mesh = actor.StaticMeshComponent0
        if not mesh or not mesh:IsValid() then error("Composant de mesh absent") end
        mesh:SetHiddenInGame(false, true)
        mesh:SetVisibility(true, true)
    end)
    print("[CHAT ESSAI] visibilite_mesh=" .. tostring(mesh_ok) .. (mesh_ok and "" or " erreur=" .. tostring(mesh_err)) .. "\n")
    CatSnapshot(actor, "apres_essai_visibilite")
end

LoopAsync(1000, function()
    if #CAT_TRACKERS > 0 then
        ExecuteInGameThread(function()
            for index = #CAT_TRACKERS, 1, -1 do
                local entry = CAT_TRACKERS[index]
                entry.checks = entry.checks + 1
                CatSnapshot(entry.actor, "controle_" .. tostring(entry.checks))
                if entry.checks >= 3 then table.remove(CAT_TRACKERS, index) end
            end
        end)
    end
    return false
end)

local TRAINER_SPAWNS = {}
local MOVE_BASE = nil
local MOVE_OPTIONS = {jump = nil, gravity = nil}
local function TrainerClean(value)
    return tostring(value):gsub("[\t\r\n]", " ")
end
local function TrainerNumber(value, low, high)
    local n = tonumber(value)
    if not n or n ~= n or n == math.huge or n == -math.huge or n < low or n > high then
        error("Valeur hors limites")
    end
    return n
end
local function PruneSpawns()
    for i = #TRAINER_SPAWNS, 1, -1 do
        local ok, valid = pcall(function() return TRAINER_SPAWNS[i].actor:IsValid() end)
        if not ok or not valid then table.remove(TRAINER_SPAWNS, i) end
    end
end
local function RegisterTrainerSpawn(actor, id)
    PruneSpawns()
    table.insert(TRAINER_SPAWNS, {actor = actor, id = id})
end

local function SpawnItem(id)
    local stage = "catalogue"
    local ok, err = pcall(function()
        PruneSpawns()
        if #TRAINER_SPAWNS >= 100 then error("Limite de 100 spawns suivis atteinte ; nettoie tes spawns") end
        local path = ITEM_CLASSES[id]
        if not path then error("Identifiant inconnu : " .. tostring(id)) end
        print("[SPAWN DIAG] id=" .. id .. " path=" .. path .. "\n")
        stage = "personnage"
        local pawn = Pawn()
        if not pawn then error("Charge une partie") end
        local world = pawn:GetWorld()
        if not world or not world:IsValid() then error("World introuvable") end
        stage = "recherche_classe"
        local cls = StaticFindObject(path)
        local experimental = id == "BPA_Cat_C" or id == "BP_Key_PC06_Painter_C"
        if not cls or not cls:IsValid() then
            stage = "chargement_classe"
            if type(LoadAsset) ~= "function" then error("LoadAsset indisponible") end
            local assetpath = path:match("^(.+)%.")
            print("[SPAWN DIAG] tentative LoadAsset=" .. assetpath .. "\n")
            local loaded_ok = pcall(LoadAsset, assetpath)
            cls = StaticFindObject(path)
            if not loaded_ok then print("[SPAWN DIAG] LoadAsset a echoue pour " .. assetpath .. "\n") end
        end
        if not cls or not cls:IsValid() then error("Classe absente de la memoire") end
        print("[SPAWN DIAG] classe trouvee=" .. cls:GetFullName() .. "\n")
        stage = "creation_acteur"
        local loc = pawn:K2_GetActorLocation()
        local forward = pawn:GetActorForwardVector()
        local actor = world:SpawnActor(cls,
            {X = loc.X + forward.X * 180, Y = loc.Y + forward.Y * 180, Z = loc.Z + 50},
            {Pitch = 0, Yaw = 0, Roll = 0})
        if not actor or not actor:IsValid() then error("SpawnActor a retourne un objet invalide") end
        print("[SPAWN] Cree : " .. actor:GetFullName() .. "\n")
        RegisterTrainerSpawn(actor, id)
        if id == "BPA_Cat_C" then TrackCat(actor) end
    end)
    if not ok then
        print("[SPAWN ERREUR] id=" .. tostring(id) .. " etape=" .. stage .. " erreur=" .. tostring(err) .. "\n")
    end
end

local SPAWN_QUEUE = {}
local function QueueTrainerSpawn(id, count)
    count = TrainerNumber(count or "1", 1, 3)
    if count ~= math.floor(count) then error("Quantite entiere requise") end
    if not ITEM_CLASSES[id] then error("Item inconnu") end
    if #SPAWN_QUEUE > 0 then error("Lot de spawn encore en cours") end
    for i = 1, count do table.insert(SPAWN_QUEUE, id) end
end
LoopAsync(350, function()
    if #SPAWN_QUEUE > 0 then
        ExecuteInGameThread(function()
            if #SPAWN_QUEUE > 0 then SpawnItem(table.remove(SPAWN_QUEUE, 1)) end
        end)
    end
    return false
end)

local function DeleteTrainerSpawns(all)
    SPAWN_QUEUE = {}
    PruneSpawns()
    local first = all and 1 or #TRAINER_SPAWNS
    local requested = 0
    for i = #TRAINER_SPAWNS, math.max(1, first), -1 do
        local entry = TRAINER_SPAWNS[i]
        local ok, err = pcall(function() entry.actor:K2_DestroyActor() end)
        if ok then
            requested = requested + 1
            table.remove(TRAINER_SPAWNS, i)
        else
            print("[TRAINER ERREUR] destruction=" .. tostring(err) .. "\n")
        end
    end
    print("[TRAINER] Demandes de destruction de mes spawns=" .. tostring(requested) .. "\n")
end

local ACTION_SEQ = 0
local function ActionResult(module, status, message)
    ACTION_SEQ = ACTION_SEQ + 1
    local file = io.open(DIR .. "trainer_action_result.tsv", "w")
    if file then
        file:write("module\tstatus\tmessage\tseq\n")
        file:write(TrainerClean(module) .. "\t" .. TrainerClean(status) .. "\t" .. TrainerClean(message) .. "\t" .. tostring(ACTION_SEQ) .. "\n")
        file:close()
    end
    print("[RESULTAT] " .. module .. " " .. status .. " " .. message .. "\n")
end

local function CaptureMovement(p)
    if not MOVE_BASE or MOVE_BASE.name ~= p:GetFullName() then
        local mv = p.CharacterMovement
        MOVE_BASE = {name = p:GetFullName(), speed = mv.MaxWalkSpeed, jump = mv.JumpZVelocity, gravity = mv.GravityScale, profiles = nil}
        local saved = {}
        local ok = pcall(function()
            mv.WalkModeProfiles:ForEach(function(key, value)
                local row = value:get()
                saved[tostring(key:get())] = {WalkSpeed = row.WalkSpeed, CameraFOV = row.CameraFOV, TurnRateScale = row.TurnRateScale, FadeOpacity = row.FadeOpacity}
            end)
        end)
        if ok and next(saved) then MOVE_BASE.profiles = saved end
    end
    return MOVE_BASE
end
local function ApplyWalkProfiles(mv, original, factor)
    if not original.profiles then return false, "Profils non accessibles ; MaxWalkSpeed seulement" end
    local updated = 0
    local ok, err = pcall(function()
        mv.WalkModeProfiles:ForEach(function(key, value)
            local base = original.profiles[tostring(key:get())]
            if not base then error("Profil non capture ; refuse") end
            value:set({WalkSpeed = base.WalkSpeed * factor, CameraFOV = base.CameraFOV, TurnRateScale = base.TurnRateScale, FadeOpacity = base.FadeOpacity})
            updated = updated + 1
        end)
    end)
    if not ok then return false, "Profils partiellement/integralement refuses : " .. tostring(err) end
    return updated > 0, "Profils modifies=" .. tostring(updated)
end
local function SetTrainerMovement(kind, value)
    local p = Pawn()
    if not p then error("Charge une partie") end
    local original = CaptureMovement(p)
    local mv = p.CharacterMovement
    local before = mv.MaxWalkSpeed
    if kind == "restore" then
        local profile_ok, detail = ApplyWalkProfiles(mv, original, 1.0)
        MOVE_OPTIONS.speed_factor, MOVE_OPTIONS.jump, MOVE_OPTIONS.gravity = nil, nil, nil
        mv.MaxWalkSpeed = original.speed
        mv.JumpZVelocity = original.jump
        mv.GravityScale = original.gravity
        S.speed = original.speed
        local status = original.profiles and not profile_ok and "PARTIEL" or "OK"
        ActionResult("movement_default", status, "Retour aux valeurs capturees ; " .. detail)
    elseif kind == "speed_factor" then
        local factor = TrainerNumber(value, 0.5, 4)
        local profile_ok, detail = ApplyWalkProfiles(mv, original, factor)
        MOVE_OPTIONS.speed_factor = factor
        S.speed = original.speed * factor
        mv.MaxWalkSpeed = S.speed
        ActionResult("movement_speed", profile_ok and "OK" or "PARTIEL", "Vitesse x" .. factor .. " ; MaxWalkSpeed " .. before .. " -> " .. mv.MaxWalkSpeed .. " ; " .. detail .. " ; effet dans le jeu a verifier")
    elseif kind == "jump" then
        MOVE_OPTIONS.jump = TrainerNumber(value, 0.25, 4)
        mv.JumpZVelocity = original.jump * MOVE_OPTIONS.jump
        ActionResult("movement_jump", "OK", "JumpZVelocity lu=" .. tostring(mv.JumpZVelocity))
    elseif kind == "gravity" then
        MOVE_OPTIONS.gravity = TrainerNumber(value, 0.1, 3)
        mv.GravityScale = original.gravity * MOVE_OPTIONS.gravity
        ActionResult("movement_gravity", "OK", "GravityScale lu=" .. tostring(mv.GravityScale))
    else error("Reglage inconnu") end
end

local function TrainerSnapshot(request_id)
    local values = {request_id = request_id or "manual", timestamp = tostring(os.time())}
    local function read(key, fn)
        local ok, result = pcall(fn)
        values[key] = ok and TrainerClean(result) or "indisponible"
    end
    PruneSpawns()
    values.spawns = tostring(#TRAINER_SPAWNS)
    values.queued = tostring(#SPAWN_QUEUE)
    read("npcs", function() return #(FindAllOf("CharacterNPC") or {}) end)
    read("giants", function() return #(FindAllOf("Giant") or {}) end)
    values.giant_found = tostring(GetGiant() ~= nil)
    local file = assert(io.open(DIR .. "trainer_state.tsv", "w"))
    file:write("key\tvalue\n")
    for key, value in pairs(values) do file:write(key .. "\t" .. tostring(value) .. "\n") end
    file:close()
end
local function TrainerCommand(line)
    local parts = {}
    for word in line:gmatch("%S+") do table.insert(parts, word) end
    local cmd = parts[1]
    if cmd == "spawn" then QueueTrainerSpawn(parts[2], parts[3])
    elseif cmd == "spawn_delete_last" then DeleteTrainerSpawns(false)
    elseif cmd == "spawn_clear" then DeleteTrainerSpawns(true)
    elseif cmd == "movement" then SetTrainerMovement(parts[2], parts[3])
    elseif cmd == "speed1" then SetTrainerMovement("speed_factor", "1")
    elseif cmd == "speed2" then SetTrainerMovement("speed_factor", "2")
    elseif cmd == "trainer_snapshot" then TrainerSnapshot(parts[2])
    elseif cmd == "scan_items" then ScanItems()
    else return false end
    return true
end

local function RunCommand(line)
    local cmd = line:match("^(%S+)")

    if not cmd then
        return
    end

    print("CMD recue: " .. line .. "\n")

    local module_ok, handled = pcall(function() return TrainerCommand(line) end)
    if not module_ok then
        print("[TRAINER ERREUR] " .. tostring(handled) .. "\n")
        ActionResult(cmd, "ERREUR", tostring(handled))
        return
    end
    if handled then return end

    local p = Pawn()

    if cmd == "cat_reveal" then
    RevealLastCat()

elseif cmd == "god" then
        ToggleGod()

    elseif cmd == "noclip" then
        ToggleNoclip()

    elseif cmd == "giant_safe" then
        ToggleGiantSafe()

    elseif cmd == "npc_invisible" then
        ToggleNPCInvisible()

elseif cmd == "stealth_test" then
    ToggleStealthTest()

    elseif cmd == "props" then
        DumpProps()

    elseif cmd == "actors" then
        DumpActors()
    end
end

local function ReadFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local data = f:read("*a")
    f:close()
    return data
end

local function AtomicWrite(path, content)
    local tmp = path .. ".tmp"
    local f = io.open(tmp, "w")
    if not f then return false end
    f:write(content)
    f:close()
    os.remove(path)
    return os.rename(tmp, path)
end

local STATUS_SEQ = 0
WriteStatus = function()
    STATUS_SEQ = STATUS_SEQ + 1
    local function b(v) return v and "1" or "0" end
    AtomicWrite(DIR .. "trainer_status.tsv",
        "key\tvalue\n"
        .. "armed\t" .. b(S.armed) .. "\n"
        .. "god\t" .. b(S.god) .. "\n"
        .. "noclip\t" .. b(S.noclip) .. "\n"
        .. "giant_safe\t" .. b(S.giant_safe) .. "\n"
        .. "npc_invisible\t" .. b(S.npc_invisible) .. "\n"
        .. "stealth_test\t" .. b(S.stealth_test) .. "\n"
        .. "speed\t" .. b(MOVE_OPTIONS.speed_factor and MOVE_OPTIONS.speed_factor > 1) .. "\n"
        .. "seq\t" .. tostring(STATUS_SEQ) .. "\n"
        .. "time\t" .. tostring(os.time()) .. "\n")
end

local function MenuAlive()
    local value = tonumber(ReadFile(DIR .. "menu_alive.txt") or "")
    return value ~= nil and math.abs(os.time() - value) < 5
end

local function LaunchMenu()
    if MenuAlive() then return end
    local base = DIR:gsub("/", "\\")
    local exe = base .. "..\\TrainerMilitsioner.exe"
    local f = io.open(exe, "rb")
    if f then
        f:close()
        os.execute('start "" "' .. exe .. '"')
        return
    end
    local script = base .. "menu.py"
    f = io.open(script, "rb")
    if f then
        f:close()
        os.execute('where pyw >nul 2>&1 && (start "" pyw "' .. script .. '") || (start "" pythonw "' .. script .. '")')
        return
    end
    print("[TRAINER] Menu introuvable\n")
end

local function DisableAll()
    pcall(function()
        if S.god then ToggleGod() end
        if S.noclip then ToggleNoclip() end
        if S.giant_safe then S.giant_safe = false ApplyGiantSafe(false, false) end
        if S.npc_invisible then S.npc_invisible = false ApplyNPCInvisible(false, false) end
        if S.stealth_test then S.stealth_test = false ApplyStealthTest(false, false) end
        S.up = false
        S.down = false
    end)
    pcall(function() SetTrainerMovement("restore") end)
end

local function SetArmed(on)
    if on == S.armed then
        if on then LaunchMenu() end
        WriteStatus()
        return
    end
    S.armed = on
    if on then
        print("[TRAINER] ACTIVE\n")
        SPAWN_QUEUE = {}
        LaunchMenu()
    else
        print("[TRAINER] DESACTIVE : tout est remis par defaut\n")
        DisableAll()
    end
    WriteStatus()
end

local FLIGHT = {seq = nil, changed = os.clock()}
local function UpdateFlightInput()
    local up, down = false, false
    local data = ReadFile(DIR .. "trainer_input.tsv")
    if data then
        local seq, u, d = data:match("^(%d+)\t(%d)\t(%d)")
        if seq then
            if seq ~= FLIGHT.seq then
                FLIGHT.seq = seq
                FLIGHT.changed = os.clock()
            end
            if os.clock() - FLIGHT.changed < 0.6 then
                up, down = u == "1", d == "1"
            end
        end
    end
    S.up, S.down = up, down
end

local function Run(line)
    local cmd = line:match("^(%S+)")
    if not cmd then return end
    if cmd == "arm_on" then SetArmed(true) return end
    if cmd == "arm_off" then SetArmed(false) return end
    if cmd == "arm_toggle" then SetArmed(not S.armed) return end
    if not S.armed then
        print("[TRAINER] Commande ignoree : trainer desactive (touche d'activation en jeu)\n")
        return
    end
    RunCommand(line)
    WriteStatus()
end

local CONFIG = {toggle_key = "F7"}
do
    local data = ReadFile(DIR .. "trainer_config.ini")
    if data then
        for key, value in data:gmatch("([%w_]+)%s*=%s*([^\r\n]+)") do
            CONFIG[key] = value:gsub("%s+$", "")
        end
    end
end
local TOGGLE_KEY = Key and Key[CONFIG.toggle_key]
if TOGGLE_KEY then
    RegisterKeyBind(TOGGLE_KEY, function()
        ExecuteInGameThread(function()
            if S.armed and not MenuAlive() then
                LaunchMenu()
            else
                SetArmed(not S.armed)
            end
        end)
    end)
    print("[TRAINER] Touche d'activation : " .. CONFIG.toggle_key .. "\n")
else
    print("[TRAINER] Touche inconnue dans trainer_config.ini : " .. tostring(CONFIG.toggle_key) .. "\n")
end

local CMD_PROCESSING = DIR .. "commands.processing"
LoopAsync(250, function()

    local probe = io.open(CMD, "r")
    if probe then
        local size = probe:seek("end")
        probe:close()
        if size and size > 0 then
            os.remove(CMD_PROCESSING)
            if os.rename(CMD, CMD_PROCESSING) then
                local file = io.open(CMD_PROCESSING, "r")
                local content = file and file:read("*a")
                if file then file:close() end
                os.remove(CMD_PROCESSING)
                if content and #content > 0 then
                    for line in content:gmatch("[^\r\n]+") do
                        ExecuteInGameThread(function()
                            Run(line)
                        end)
                    end
                end
            end
        end
    end
    return false
end)

local function MovementLoopNeeded()
    return S.god or S.noclip or MOVE_OPTIONS.jump or MOVE_OPTIONS.gravity or MOVE_OPTIONS.speed_factor
end

LoopAsync(50, function()
    if not MovementLoopNeeded() then return false end
    ExecuteInGameThread(function()
        local p = Pawn()

        if not p then
            return
        end

        pcall(function()
            local mv = p.CharacterMovement

            local original = CaptureMovement(p)
            if MOVE_OPTIONS.jump then mv.JumpZVelocity = original.jump * MOVE_OPTIONS.jump end
            if MOVE_OPTIONS.gravity then mv.GravityScale = original.gravity * MOVE_OPTIONS.gravity end
            if MOVE_OPTIONS.speed_factor then mv.MaxWalkSpeed = S.speed end

            if S.god then
                p.bCanBeDamaged = false
                p.MaxHealth = 100000.0
                p.Health = 100000.0
                p.Air = 100000.0
                p.AirLossRate = 0.0
                p:SetIgnoreFallDamage(true)
                p.MinFallDamageHeight = 1000000.0
                p.MaxFallDamageHeight = 1000001.0
            end

            if S.noclip then
                UpdateFlightInput()
                mv.MaxFlySpeed = 2500
                mv:SetMovementMode(5, 0)
                p:SetActorEnableCollision(false)

                if S.up then
                    p:AddMovementInput({ X = 0, Y = 0, Z = 1 }, 1.0, false)
                end

                if S.down then
                    p:AddMovementInput({ X = 0, Y = 0, Z = -1 }, 1.0, false)
                end
            end
        end)
    end)

    return false
end)

LoopAsync(2000, function()
    ExecuteInGameThread(function()
        if S.giant_safe then
            ApplyGiantSafe(true, false)
        end

        if S.npc_invisible then
            ApplyNPCInvisible(true, false)
        end

        if S.stealth_test then
            ApplyStealthTest(true, false)
        end
        WriteStatus()
    end)

    return false
end)

WriteStatus()
print("TrainerMilitsioner v6 charge : appuie sur " .. tostring(CONFIG.toggle_key) .. " en jeu pour activer le trainer\n")

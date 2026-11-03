# Militsioner Trainer

🇬🇧 [English](#english) · 🇫🇷 [Français](#français)

---

<a name="english"></a>
## 🇬🇧 English

A single-player trainer for the **Militsioner Demo** (Steam). Press **F7** in game to open a menu and toggle god mode, noclip, stealth against the giant, speed, and spawn items from a catalog of about a hundred objects. Press **F7** again to turn everything off and restore the original values.

It runs on top of [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/experimental-latest). **Single-player only.**

📦 Download: Nexus Mods page *(add your link here)*

### Features
| Feature | Shortcut |
|---|---|
| Open/close the trainer and menu | `F7` |
| God mode (no damage, no fall damage, no air loss) | `Shift+F1` |
| Giant protection (it cannot catch you) | `Shift+F2` |
| NPC discretion (reduced NPC reactions) | `Shift+F3` |
| Player stealth (the giant sees/hears you much less) | `Shift+F4` |
| Noclip + fly (`Space` up, `C` or `Ctrl` down) | `Shift+F5` |
| Fast speed (x2) | `Shift+F8` |
| Spawn the selected catalog item | `F6` |

All shortcuts can be changed in the menu. Speed, jump and gravity are adjustable with sliders.

### Requirements
- Militsioner Demo (Steam)
- UE4SS **experimental-latest** (`zDEV-UE4SS...`) installed in `TallProject\Binaries\Win64\`
- Game in windowed or borderless mode (the menu is a separate window)

### Installation
1. Install UE4SS.
2. Extract the release zip into the game's root folder (the one containing `TallProject`) and merge folders. Or copy the `TrainerMilitsioner` folder into `...\TallProject\Binaries\Win64\ue4ss\Mods\`.
3. Start the game, load your save, press **F7**.

To uninstall, delete `ue4ss\Mods\TrainerMilitsioner`.

### How it works (transparency)
The mod has two parts that talk to each other **only through small text files** in the mod's `Scripts` folder:

| File | Role |
|---|---|
| [`core.lua`](core.lua) + [`main.lua`](main.lua) | UE4SS Lua mod running inside the game. Reads commands, applies the cheats through the game's own objects, writes its state. The release ships `core.lua` compiled to Lua bytecode (`core.bin`); `main.lua` is a tiny loader. |
| [`menu.py`](menu.py) | The menu window (Python + customtkinter), packaged as `GUI.exe` with PyInstaller. |
| [`items_catalog.tsv`](items_catalog.tsv) | Catalog of spawnable items (display name ⇄ internal game class). |
| [`build_release.py`](build_release.py), [`BUILD_EXE.bat`](BUILD_EXE.bat) | Rebuild the release zip from these sources. |

What the code does that may look unusual to a scanner, and why:
- **No internet access.** There is no HTTP/network code. `menu.py` only opens a socket bound to `127.0.0.1:47931` so that a second copy of the menu does not open (single-instance lock).
- **`GetAsyncKeyState` (user32).** Used to read only the configured shortcut keys (F-keys with/without Shift) and, while noclip is on, `Space`, `C` and `Ctrl`. The shortcuts are only acted upon while the **game window is in the foreground**. Nothing is recorded or stored.
- **`os.execute` in `core.lua`.** Used once, to start `GUI.exe` from the mod's folder (`start "" "...\GUI.exe"`).
- **Files read/written:** only inside the mod's own folder (`commands.txt`, `trainer_status.tsv`, `trainer_input.tsv`, `trainer_preferences.json`, ...).
- **PyInstaller `.exe`.** Python executables built with PyInstaller are sometimes flagged by heuristic/machine-learning antivirus engines. The full source is in this repository.

### Rebuild it yourself
Install Python 3.10+, then run `BUILD_EXE.bat`. The zip is created in the `release` folder.

### Notes
- The game is a demo: an update may break some features.
- Item names are descriptive translations of the game's internal names, not official ones.
- Back up your save before using the trainer.

Thanks to the [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) team.

---

<a name="français"></a>
## 🇫🇷 Français

Un trainer solo pour la **démo de Militsioner** (Steam). Appuie sur **F7** en jeu pour ouvrir un menu et activer god mode, noclip, furtivité face au géant, vitesse, et faire apparaître des objets depuis un catalogue d'une centaine d'objets. Un deuxième appui sur **F7** coupe tout et remet les valeurs d'origine.

Il fonctionne grâce à [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/experimental-latest). **Jeu solo uniquement.**

📦 Téléchargement : page Nexus Mods *(ajoute ton lien ici)*

### Fonctions
| Fonction | Raccourci |
|---|---|
| Ouvrir/fermer le trainer et le menu | `F7` |
| God mode (plus de dégâts, de dégâts de chute, de manque d'air) | `Maj+F1` |
| Protection contre le géant (il ne peut plus t'attraper) | `Maj+F2` |
| Discrétion face aux PNJ (réactions réduites) | `Maj+F3` |
| Furtivité du joueur (le géant te voit/entend beaucoup moins) | `Maj+F4` |
| Noclip + vol (`Espace` monte, `C` ou `Ctrl` descend) | `Maj+F5` |
| Vitesse rapide (x2) | `Maj+F8` |
| Faire apparaître l'objet sélectionné | `F6` |

Tous les raccourcis sont modifiables dans le menu. Vitesse, saut et gravité se règlent avec des curseurs.

### Ce qu'il faut
- Militsioner Demo (Steam)
- UE4SS **experimental-latest** (`zDEV-UE4SS...`) installé dans `TallProject\Binaries\Win64\`
- Jeu en mode fenêtré ou fenêtré sans bordure (le menu est une fenêtre à part)

### Installation
1. Installe UE4SS.
2. Extrais le zip dans le dossier racine du jeu (celui qui contient `TallProject`) et fusionne les dossiers. Ou copie le dossier `TrainerMilitsioner` dans `...\TallProject\Binaries\Win64\ue4ss\Mods\`.
3. Lance le jeu, charge ta partie, appuie sur **F7**.

Pour désinstaller, supprime `ue4ss\Mods\TrainerMilitsioner`.

### Fonctionnement (transparence)
Le mod est en deux parties qui ne communiquent que **par de petits fichiers texte** dans le dossier `Scripts` du mod :

| Fichier | Rôle |
|---|---|
| [`core.lua`](core.lua) + [`main.lua`](main.lua) | Mod Lua UE4SS qui tourne dans le jeu. Lit les commandes, applique les effets via les objets du jeu, écrit son état. La release fournit `core.lua` compilé en bytecode Lua (`core.bin`) ; `main.lua` est un petit chargeur. |
| [`menu.py`](menu.py) | La fenêtre du menu (Python + customtkinter), empaquetée en `GUI.exe` avec PyInstaller. |
| [`items_catalog.tsv`](items_catalog.tsv) | Catalogue des objets (nom affiché ⇄ classe interne du jeu). |
| [`build_release.py`](build_release.py), [`BUILD_EXE.bat`](BUILD_EXE.bat) | Reconstruisent le zip de la release à partir de ces sources. |

Ce que fait le code et qui peut paraître inhabituel pour un scanner, et pourquoi :
- **Aucun accès à internet.** Il n'y a aucun code réseau HTTP. `menu.py` ouvre seulement un socket sur `127.0.0.1:47931` pour éviter d'ouvrir deux fenêtres de menu (verrou d'instance unique).
- **`GetAsyncKeyState` (user32).** Sert à lire uniquement les touches de raccourci configurées (touches F avec/sans Maj) et, quand le noclip est actif, `Espace`, `C` et `Ctrl`. Les raccourcis ne sont pris en compte que quand la **fenêtre du jeu est au premier plan**. Rien n'est enregistré ni stocké.
- **`os.execute` dans `core.lua`.** Utilisé une seule fois, pour lancer `GUI.exe` depuis le dossier du mod (`start "" "...\GUI.exe"`).
- **Fichiers lus/écrits :** uniquement dans le dossier du mod (`commands.txt`, `trainer_status.tsv`, `trainer_input.tsv`, `trainer_preferences.json`, ...).
- **`.exe` PyInstaller.** Les exécutables Python faits avec PyInstaller sont parfois signalés par les antivirus heuristiques ou à apprentissage automatique. Le code source complet est dans ce dépôt.

### Le reconstruire toi-même
Installe Python 3.10+ puis lance `BUILD_EXE.bat`. Le zip est créé dans le dossier `release`.

### À savoir
- Le jeu est une démo : une mise à jour peut casser certaines fonctions.
- Les noms d'objets sont des traductions descriptives des noms internes du jeu, pas les noms officiels.
- Fais une sauvegarde de ta partie avant d'utiliser le trainer.

Merci à l'équipe d'[UE4SS](https://github.com/UE4SS-RE/RE-UE4SS).

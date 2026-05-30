import sys
import pygame
import pygame_menu
from pygame_menu import themes

screenW, screenH = 1280, 720
fps = 60
title = "Moon Race"
levels = ["levels/level1.txt", "levels/level2.txt"]
white = (240, 240, 250)
black = (10, 10, 20)
portalJumpColor = (120, 220, 120)
portalGravityColor = (180, 120, 240)
portalJetpackColor = (250, 180, 70)
import assets
from player import Player
from level import Level
from effects import ParticleSystem, Camera

MENU, LOADING, GAME, CUTSCENE, NAME_INPUT = "menu", "loading", "game", "cutscene", "name_input"
updateLoading = pygame.USEREVENT + 1

pygame.init()
pygame.font.init()
pygame.mixer.init()

surface = pygame.display.set_mode((screenW, screenH))
pygame.display.set_caption(title)
clock = pygame.time.Clock()

state = NAME_INPUT
selectedLevel = 0
playerName = "Astronaut"
nameInput = ""
nameCursorVisible = True
nameCursorTimer = 0.0
gameScene = None
assetsLoaded = False
attempts = 1

assets.playMusic("music_menu")

# --- cutscene ---
def applyHologramEffect(surf):
    w, h = surf.get_size()
    out = surf.copy().convert_alpha()
    try:
        import numpy as np
        arr = pygame.surfarray.pixels3d(out)
        gray = (arr[:,:,0]*0.299 + arr[:,:,1]*0.587 + arr[:,:,2]*0.114).astype(np.uint8)
        arr[:,:,0] = (gray * 0.10).astype(np.uint8)   # very little red
        arr[:,:,1] = (gray * 0.65).astype(np.uint8)   # some green for cyan-blue
        arr[:,:,2] = (gray * 1.00).astype(np.uint8)   # full blue
        del arr
        # make portrait semi-transparent for hologram translucency
        alpha = pygame.surfarray.pixels_alpha(out)
        alpha[:] = (alpha * 0.80).astype(np.uint8)
        del alpha
    except ImportError:
        tint = pygame.Surface((w, h))
        tint.fill((25, 140, 255))
        out.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    # blue scanlines, denser than MGS
    scanline = pygame.Surface((w, 1), pygame.SRCALPHA)
    scanline.fill((0, 20, 80, 100))
    for y in range(0, h, 2):
        out.blit(scanline, (0, y))
    return out

commanderPortrait = applyHologramEffect(assets.loadImg("commander_portrait", (600, 600)))

def buildDialogue(name):
    return [
        f"{name}! The lunar research base is collapsing. A catastrophic structural failure has triggered a chain reaction throughout all sectors.",
        "Your only hope is the emergency escape rocket at the far end of the facility. You need to reach it NOW.",
        "The base's experimental portal network is still active. Each portal changes how you move — jump boosters, gravity inverters, jetpacks.",
        f"Use whatever it takes to reach that rocket. The whole crew is counting on you. Good luck, {name}.",
    ]

dialogue = buildDialogue(playerName)
dialogueIndex = 0
cutsceneFading = False
cutsceneFadeAlpha = 0.0
cutsceneFadeOverlay = pygame.Surface((screenW, screenH))
cutsceneFadeOverlay.fill((0, 0, 0))
dlgFont  = pygame.font.SysFont("consolas", 22)
nameFont = pygame.font.SysFont("consolas", 24)
hintFont = pygame.font.SysFont("consolas", 18)
skipBtn  = pygame.Rect(screenW - 120, 20, 100, 36)


def wrapText(text, font, maxWidth):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = current + (" " if current else "") + word
        if font.size(test)[0] <= maxWidth:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# --- name input ---
nameInputFont = pygame.font.SysFont("consolas", 32)
nameTitleFont = pygame.font.SysFont("consolas", 52)

def handleNameInputEvent(event):
    global playerName, nameInput, state, dialogue
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_RETURN:
            name = nameInput.strip()
            if name:
                playerName = name
                dialogue = buildDialogue(playerName)
                state = CUTSCENE
        elif event.key == pygame.K_BACKSPACE:
            nameInput = nameInput[:-1]
        elif event.unicode and event.unicode.isprintable() and len(nameInput) < 16:
            nameInput += event.unicode


def drawNameInput():
    surface.fill((0, 0, 0))

    title = nameTitleFont.render("MOON RACE", True, (120, 200, 255))
    surface.blit(title, title.get_rect(center=(screenW // 2, screenH // 4)))

    prompt = nameInputFont.render("Commander Hayes needs your callsign.", True, (180, 180, 200))
    surface.blit(prompt, prompt.get_rect(center=(screenW // 2, screenH // 2 - 70)))

    # input box
    boxW, boxH = 420, 58
    boxX = screenW // 2 - boxW // 2
    boxY = screenH // 2 - boxH // 2
    pygame.draw.rect(surface, (15, 15, 30), (boxX, boxY, boxW, boxH), border_radius=4)
    pygame.draw.rect(surface, (80, 150, 255), (boxX, boxY, boxW, boxH), 2, border_radius=4)

    cursor = "|" if nameCursorVisible else " "
    inputSurf = nameInputFont.render(nameInput + cursor, True, white)
    surface.blit(inputSurf, (boxX + 16, boxY + (boxH - inputSurf.get_height()) // 2))

    hint = pygame.font.SysFont("consolas", 18).render("ENTER to continue", True, (100, 100, 120))
    surface.blit(hint, hint.get_rect(center=(screenW // 2, screenH // 2 + 65)))


def handleCutsceneEvent(event):
    global state, dialogueIndex, cutsceneFading
    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
        if not cutsceneFading:
            dialogueIndex += 1
            if dialogueIndex >= len(dialogue):
                dialogueIndex = len(dialogue) - 1  # keep last line visible during fade
                cutsceneFading = True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if skipBtn.collidepoint(event.pos):
            dialogueIndex = 0
            state = MENU            # skip bypasses the fade


def drawCutscene():
    surface.fill((0, 0, 0))

    # commander portrait — centered horizontally, above the dialogue box
    if commanderPortrait:
        pw = commanderPortrait.get_width()
        px = (screenW - pw) // 2
        py = 40
        surface.blit(commanderPortrait, (px, py))

    # dialogue box
    boxH = 170
    boxY = screenH - boxH - 20
    boxX = 20
    boxW = screenW - 40

    boxSurf = pygame.Surface((boxW, boxH), pygame.SRCALPHA)
    boxSurf.fill((15, 15, 25, 235))
    surface.blit(boxSurf, (boxX, boxY))
    pygame.draw.rect(surface, (180, 180, 200), (boxX, boxY, boxW, boxH), 2, border_radius=4)

    # speaker name above the box
    nameSurf = nameFont.render("Commander Hayes", True, (120, 200, 255))
    surface.blit(nameSurf, (boxX + 16, boxY - 30))

    # wrapped dialogue text
    lines = wrapText(dialogue[dialogueIndex], dlgFont, boxW - 32)
    for i, line in enumerate(lines):
        surface.blit(dlgFont.render(line, True, white), (boxX + 16, boxY + 16 + i * 30))

    # progress indicator  e.g. "2 / 4"
    prog = hintFont.render(f"{dialogueIndex + 1} / {len(dialogue)}", True, (100, 100, 120))
    surface.blit(prog, (boxX + 16, boxY + boxH - 26))

    # continue hint
    hint = hintFont.render("SPACE — Continue", True, (120, 120, 140))
    surface.blit(hint, (boxX + boxW - hint.get_width() - 16, boxY + boxH - 26))

    # skip button
    pygame.draw.rect(surface, (40, 40, 60), skipBtn, border_radius=4)
    pygame.draw.rect(surface, (120, 120, 150), skipBtn, 1, border_radius=4)
    skipLabel = hintFont.render("SKIP >>", True, white)
    surface.blit(skipLabel, skipLabel.get_rect(center=skipBtn.center))

    # black fade overlay drawn on top of everything
    if cutsceneFading:
        cutsceneFadeOverlay.set_alpha(int(cutsceneFadeAlpha))
        surface.blit(cutsceneFadeOverlay, (0, 0))


# --- menu ---
def setPlayerName(name):
    global playerName
    playerName = name


def setLevel(value, idx):
    global selectedLevel
    selectedLevel = idx


def startGame():
    global state
    assets.stopMusic()
    state = LOADING
    progress.set_value(0)
    pygame.time.set_timer(updateLoading, 20)


def quitGame():
    pygame.quit()
    sys.exit()

# menu building
mainMenu = pygame_menu.Menu("Moon Race", screenW, screenH, theme=themes.THEME_DARK)
mainMenu.add.selector("Level: ", [("Cave", 0), ("Surface", 1)], onchange=setLevel)
mainMenu.add.button("Play", startGame)
mainMenu.add.button("Quit", quitGame)

loadingMenu = pygame_menu.Menu("Loading...", screenW, screenH, theme=themes.THEME_DARK)
progress = loadingMenu.add.progress_bar("Progress", progressbar_id="pb1", default=0, width=500)


# --- game ---
# initialization of all varaibles needed to run the game, all are stored in the game scene dictionary
def startGameScene(retry=False):
    global state, gameScene, attempts
    # fresh start (from menu) resets to 1, a retry bumps the count
    if retry:
        attempts = attempts + 1
    else:
        attempts = 1
    gs = {
        "level": None,
        "cam": Camera(),
        "particles": ParticleSystem(),
        "player": None,
        "state": "play",
        "deathTimer": 0.0,
        "winTimer": 0.0,
        "font": pygame.font.Font(None, 28),
    }
    lvl = Level(levels[selectedLevel], selectedLevel)
    sx, sy = lvl.spawn
    gs["level"] = lvl
    gs["player"] = Player(sx, sy)
    assets.playMusic(f"music_level{selectedLevel + 1}")
    gameScene = gs
    state = GAME


# keybinds
def handleGameEvent(event):
    global state, gameScene
    gs = gameScene
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            assets.stopMusic()
            assets.playMusic("music_menu")
            state = MENU
            return
        if event.key == pygame.K_r:
            startGameScene(retry=True)
            return
        if event.key == pygame.K_SPACE and gs["state"] == "play":
            gs["player"].onSpacePressed()


# update the game in each frame, includes all sprites and game logic
def updateGame(dt):
    global state, gameScene
    gs = gameScene
    keys = pygame.key.get_pressed()

    # play state
    if gs["state"] == "play":
        gs["player"].onSpaceHeld(keys[pygame.K_SPACE])
        gs["player"].update(dt, gs["level"])

        # check for win
        if gs["level"].updateCamera(gs["cam"], dt, gs["player"]):
            gs["state"] = "win"
            gs["winTimer"] = 120
            assets.playSfx("portal")

        # check for collision with traps
        playerRect = gs["player"].rect()
        for _ch, hb in gs["level"].hazardsNear(playerRect):
            if playerRect.colliderect(hb):
                gs["state"] = "dying"
                gs["deathTimer"] = 70
                assets.playSfx("death")
                gs["particles"].deathBurst(
                    gs["player"].x + gs["player"].w / 2,
                    gs["player"].y + gs["player"].h / 2
                )
                gs["cam"].addShake(0.9)
                break

        # check for collision with portals
        for mode, portalRect in gs["level"].portalsNear(playerRect):
            if playerRect.colliderect(portalRect):
                if mode != gs["player"].mode:
                    gs["player"].setMode(mode)
                    assets.playSfx("portal")
                    cx, cy = portalRect.centerx, portalRect.centery
                    sparkColor = {
                        "jump": portalJumpColor,
                        "gravity": portalGravityColor,
                        "jetpack": portalJetpackColor,
                    }[mode]
                    gs["particles"].portalSparks(cx, cy, sparkColor)

        # trail particles appear when on ground
        if gs["player"].onGround:
            # when gravity is flipped the player stands on the ceiling, so the
            # trail should come off the top of the player, not the bottom
            if gs["player"].gravitySign < 0:
                trailY = gs["player"].y + 2
            else:
                trailY = gs["player"].y + gs["player"].h - 2
            gs["particles"].trail(gs["player"].x, trailY)

        # jetpack particles when jetpack
        if gs["player"].mode == "jetpack" and gs["player"].thrusting:
            gs["particles"].jetpackFlame(
                gs["player"].x + gs["player"].w / 2,
                gs["player"].y + gs["player"].h
            )

        # out of bounds check
        if gs["player"].y > gs["level"].worldH:
            gs["state"] = "dying"
            gs["deathTimer"] = 70
            assets.playSfx("death")
            gs["particles"].deathBurst(
                gs["player"].x + gs["player"].w / 2,
                gs["player"].y + gs["player"].h / 2
            )
            gs["cam"].addShake(0.9)
        elif gs["player"].y < -gs["player"].h:
            gs["state"] = "deathSpin"
            gs["player"].spinTimer = 60.0
            gs["player"].spinFallTimer = 20.0
            gs["player"].vy = 2.0
            assets.playSfx("death")


    # death
    elif gs["state"] == "dying":
        gs["deathTimer"] -= dt
        if gs["deathTimer"] <= 0:
            startGameScene(retry=True)

    # top death
    elif gs["state"] == "deathSpin":
        gs["player"].updateSpin(dt)
        if gs["player"].spinTimer <= 0:
            gs["state"] = "dying"
            gs["deathTimer"] = 70
            gs["particles"].deathBurst(
                gs["player"].x + gs["player"].w / 2,
                gs["player"].y + gs["player"].h / 2
            )
            gs["cam"].addShake(0.9)


    # win
    elif gs["state"] == "win":
        gs["winTimer"] -= dt
        if gs["winTimer"] <= 0:
            assets.stopMusic()
            assets.playMusic("music_menu")
            state = MENU

    # update camera and particles every frame
    gs["cam"].update(dt)
    gs["particles"].update(dt)


# draw everything, follow the logic of update then this is called to draw
def drawGame():
    gs = gameScene
    ox, oy = gs["cam"].shakeOffset()
    gs["level"].draw(surface, gs["cam"].x)
    if gs["state"] == "play":
        gs["player"].draw(surface, gs["cam"].x)
    elif gs["state"] == "deathSpin":
        gs["player"].drawSpin(surface, gs["cam"].x)
    gs["particles"].draw(surface, gs["cam"].x)

    # the current mode
    modeLabel = f"MODE: {gs['player'].mode.upper()}"
    t = gs["font"].render(modeLabel, True, white)
    surface.blit(t, (20 + ox, 16 + oy))

    # the current attempt number
    at = gs["font"].render(f"ATTEMPT {attempts}", True, white)
    surface.blit(at, (screenW - at.get_width() - 20 + ox, 16 + oy))

    # messages to display win or lose
    if gs["state"] == "dying":
        t = gs["font"].render("you died - retrying...", True, (255, 120, 120))
        surface.blit(t, t.get_rect(center=(screenW // 2, screenH // 2)))
    elif gs["state"] == "win":
        t = gs["font"].render("you reached the rocket!", True, (180, 255, 180))
        surface.blit(t, t.get_rect(center=(screenW // 2, screenH // 2)))


# main loop
running = True
while running:
    # get current frame
    dt = min(clock.tick(fps) / (1000 / 60), 1000)
    events = pygame.event.get()
    # just check for any events including key presses and states
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        if state == NAME_INPUT:
            handleNameInputEvent(event)

        if state == CUTSCENE:
            handleCutsceneEvent(event)

        if state == LOADING and event.type == updateLoading:
            val = progress.get_value()
            progress.set_value(val + 1)
            if val + 1 >= 100:
                pygame.time.set_timer(updateLoading, 0)
                if not assetsLoaded:
                    assets.loadAll()
                    assetsLoaded = True
                startGameScene()

        if state == GAME:
            handleGameEvent(event)

    surface.fill(black)

    if state == NAME_INPUT:
        nameCursorTimer += dt
        if nameCursorTimer >= 30:
            nameCursorTimer = 0
            nameCursorVisible = not nameCursorVisible
        drawNameInput()
    elif state == CUTSCENE:
        if cutsceneFading:
            cutsceneFadeAlpha = min(255, cutsceneFadeAlpha + 4 * dt)
            if cutsceneFadeAlpha >= 255:
                cutsceneFading = False
                cutsceneFadeAlpha = 0.0
                dialogueIndex = 0
                state = MENU
        drawCutscene()
    elif state == MENU:
        mainMenu.update(events)
        mainMenu.draw(surface)
    elif state == LOADING:
        loadingMenu.update(events)
        loadingMenu.draw(surface)
    elif state == GAME:
        updateGame(dt)
        drawGame()

    pygame.display.flip()

pygame.quit()
import sys
import pygame
import random
import math
import pygame_menu
from pygame_menu import themes
import assets
from player import Player
from level import Level
from effects import ParticleSystem, Camera, ScreenFlash, PortalGlow, StarField, GravityFlipEffect
import os

screenW, screenH = 1280, 720
fps = 60
title = "Moon Race"
levels = ["levels/level1.txt", "levels/level2.txt"]
white = (240, 240, 250)
black = (10, 10, 20)
portalJumpColor = (120, 220, 120)
portalGravityColor = (180, 120, 240)
portalJetpackColor = (250, 180, 70)
font_path = os.path.join(os.environ['WINDIR'], 'Fonts', 'consola.ttf')

MENU, LOADING, GAME, CUTSCENE, NAME_INPUT, FLYAWAY = "menu", "loading", "game", "cutscene", "name_input", "flyaway"
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
dlgFont = pygame.font.Font(font_path, 22)
nameFont = pygame.font.Font(font_path, 24)
hintFont = pygame.font.Font(font_path, 18)
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
nameInputFont = pygame.font.Font(font_path, 32)
nameTitleFont = pygame.font.Font(font_path, 52)

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
    hint = pygame.font.Font(font_path, 18).render("ENTER to continue", True, (100, 100, 120))
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

portalColors = {
    "jump": portalJumpColor,
    "gravity": portalGravityColor,
    "jetpack": portalJetpackColor,
}

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
        "flash": ScreenFlash(),
        "portalGlow": PortalGlow(),
        "gravityFlip": GravityFlipEffect(),
        "stars": StarField(150),
        "fireworkTimer": 0.0,
        "prevOnGround": False,
        "prevVy": 0.0,
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

    gs["flash"].update(dt)
    gs["portalGlow"].update(dt)
    gs["gravityFlip"].update(dt)

    #play state
    if gs["state"] == "play":
        prevVy = gs["player"].vy
        prevOnGround = gs["player"].onGround
        justFlipped = gs["player"].gravityFlipped
        gs["player"].gravityFlipped = False

        gs["player"].onSpaceHeld(keys[pygame.K_SPACE])
        gs["player"].update(dt, gs["level"])

        #gravity flip effect
        if justFlipped and gs["player"].mode == "gravity":
            px = gs["player"].x + gs["player"].w / 2
            py = gs["player"].y + gs["player"].h / 2
            flippingUp = gs["player"].gravityTarget < 0
            gs["gravityFlip"].trigger(px, py, flippingUp)
            gs["particles"].gravityFlipBurst(px, py, flippingUp)
            gs["cam"].addShake(0.25)

            #dust on landings
        if gs["player"].onGround and not prevOnGround and abs(prevVy) > 5:
            px = gs["player"].x + gs["player"].w / 2
            py = gs["player"].y + gs["player"].h
            gs["particles"].landDust(px, py)

        # check for win
        if gs["level"].updateCamera(gs["cam"], dt, gs["player"]):
            gs["state"] = "win"
            gs["winTimer"] = 180
            gs["fireworkTimer"] = 0
            assets.playSfx("portal")
            gs["flash"].trigger((200, 255, 200), 20)

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
                gs["flash"].trigger((255, 60, 60), 22)
                break

        # check for collision with portals
        for mode, portalRect in gs["level"].portalsNear(playerRect):
            if playerRect.colliderect(portalRect):
                if mode != gs["player"].mode:
                    gs["player"].setMode(mode)
                    assets.playSfx("portal")
                    cx, cy = portalRect.centerx, portalRect.centery
                    sparkColor = portalColors[mode]
                    gs["particles"].portalSparks(cx, cy, sparkColor)
                    gs["flash"].trigger(sparkColor, 14)

        # trail particles appear when on ground
        if gs["player"].onGround:
            # when gravity is flipped the player stands on the ceiling, so the
            # trail should come off the top of the player, not the bottom
            if gs["player"].gravitySign < 0:
                trailY = gs["player"].y + 2
            else:
                trailY = gs["player"].y + gs["player"].h - 2
            gs["particles"].trail(gs["player"].x, trailY, mode=gs["player"].mode)

    # jetpack particles when jetpack
        if gs["player"].mode == "jetpack" and gs["player"].thrusting:
            px = gs["player"].x + gs["player"].w / 2
            py = gs["player"].y + gs["player"].h
            gs["particles"].jetpackFlame(px, py)
            gs["particles"].jetpackSideVents(px, gs["player"].y + gs["player"].h / 2)
            gs["particles"].jetpackAura(px, gs["player"].y + gs["player"].h / 2)

        # jetpack ignition burst (one-shot on thrust start)
        if gs["player"].thrustStarted:
            gs["player"].thrustStarted = False
            px = gs["player"].x + gs["player"].w / 2
            py = gs["player"].y + gs["player"].h / 2
            gs["particles"].jetpackIgnition(px, py)

        #spike ambient glow
        if random.random() < 0.25:
            spikes = gs["level"].allHazardsVisible(int(gs["cam"].x), screenW)
            if spikes:
                _ch, hb = random.choice(spikes)
                gs["particles"].spikeGlow(hb.centerx, hb.centery)

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
            gs["flash"].trigger((255, 60, 60), 22)
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
            gs["flash"].trigger((255, 60, 60), 22)

    # win
    elif gs["state"] == "win":
        gs["winTimer"] -= dt
        gs["fireworkTimer"] -= dt
        if gs["fireworkTimer"] <= 0:
            gs["fireworkTimer"] = random.uniform(12, 25)
            fx = random.uniform(200, screenW - 200)
            fy = random.uniform(80, screenH - 150)
            gs["particles"].winFireworks(fx + gs["cam"].x, fy)
            gs["flash"].trigger(
                random.choice([(255, 220, 50), (100, 220, 255), (180, 100, 255)]),
                8
            )
        if gs["winTimer"] <= 0:
            assets.stopMusic()
            if selectedLevel == 1:
                startFlyaway()
            else:
                state = MENU

    # update camera and particles every frame
    gs["cam"].update(dt)
    gs["particles"].update(dt)

def startFlyaway():
    global state, flyawayScene
    ship_img = assets.img["spaceship"]
    sw, sh = ship_img.get_size()
    # Start centred, just below screen bottom, then fly up and off-screen
    flyawayScene = {
        "ship_x": screenW / 2 - sw / 2,
        "ship_y": float(screenH + 20),      # start just below screen
        "ship_vy": -2.0,                     # initial upward speed (pixels/frame-unit)
        "ship_accel": -0.08,                 # accelerate upward each frame
        "ship_wobble": 0.0,                  # horizontal sway timer
        "phase": "rise",                     # rise → gone → done
        "timer": 0.0,
        "stars": StarField(200),
        "particles": ParticleSystem(),
        "flame_timer": 0.0,
        "alpha": 255,
        "font": pygame.font.Font(None, 52),
        "small_font": pygame.font.Font(None, 32),
        "text_alpha": 0,
        "text_timer": 0.0,
    }
    state = FLYAWAY

def updateFlyaway(dt):
    global state, flyawayScene
    fs = flyawayScene
    ship_img = assets.img["spaceship"]
    sw, sh = ship_img.get_size()

    fs["timer"] += dt

    if fs["phase"] == "rise":
        # Accelerate upward
        fs["ship_vy"] += fs["ship_accel"] * dt
        fs["ship_y"] += fs["ship_vy"] * dt

        # Gentle horizontal wobble
        fs["ship_wobble"] += 0.04 * dt
        fs["ship_x"] = screenW / 2 - sw / 2 + math.sin(fs["ship_wobble"]) * 18

        # Engine flame particles
        fs["flame_timer"] -= dt
        if fs["flame_timer"] <= 0:
            fs["flame_timer"] = 2
            cx = fs["ship_x"] + sw / 2
            cy = fs["ship_y"] + sh
            for _ in range(5):
                color = random.choice([(255,180,60),(255,120,30),(255,220,80),(200,80,20)])
                angle = random.uniform(math.pi * 0.4, math.pi * 0.6)
                spd = random.uniform(4, 9)
                fs["particles"].spawn(
                    cx + random.uniform(-10, 10), cy,
                    math.cos(angle) * spd * 0.3,
                    math.sin(angle) * spd,
                    life=25, color=color, radius=random.randint(4, 9), gravity=0.05, glow=True
                )
            # Exhaust smoke
            for _ in range(3):
                fs["particles"].spawn(
                    cx + random.uniform(-8, 8), cy + random.uniform(5, 20),
                    random.uniform(-0.5, 0.5), random.uniform(1.5, 3.0),
                    life=40, color=(180,160,140), radius=random.randint(5,10), gravity=0.0, glow=False
                )

        # Random star sparkles while rising
        if random.random() < 0.3:
            fx = random.uniform(0, screenW)
            fy = random.uniform(0, screenH * 0.6)
            fs["particles"].spawn(fx, fy, 0, 0, life=20,
                                  color=(255,255,200), radius=2, glow=True)

        # Fade in text after ship clears screen centre
        if fs["ship_y"] < screenH * 0.35:
            fs["text_alpha"] = min(255, fs["text_alpha"] + int(4 * dt))

        # Ship exits screen top → start fade-out phase
        if fs["ship_y"] + sh < 0:
            fs["phase"] = "fade"
            fs["fade_timer"] = 90.0

    elif fs["phase"] == "fade":
        fs["fade_timer"] -= dt
        fs["alpha"] = max(0, int(255 * (fs["fade_timer"] / 90.0)))
        if fs["fade_timer"] <= 0:
            fs["phase"] = "done"

    elif fs["phase"] == "done":
        assets.stopMusic()
        state = MENU

    fs["stars"].draw(surface, 0)   # drawn in update for ordering
    fs["particles"].update(dt)

def drawFlyaway():
    fs = flyawayScene
    surface.fill((5, 5, 18))        # deep space black
    fs["stars"].draw(surface, 0)

    ship_img = assets.img["spaceship"]
    sw, sh = ship_img.get_size()

    # Draw ship (with alpha fade if fading out)
    if fs["phase"] in ("rise",):
        surface.blit(ship_img, (int(fs["ship_x"]), int(fs["ship_y"])))
    elif fs["phase"] == "fade":
        fade_surf = ship_img.copy()
        fade_surf.set_alpha(fs["alpha"])
        surface.blit(fade_surf, (int(fs["ship_x"]), int(fs["ship_y"])))

    fs["particles"].draw(surface, 0)

    # "Mission Complete" text fades in
    if fs["text_alpha"] > 0:
        big = fs["font"].render("MISSION COMPLETE", True, (180, 255, 180))
        big.set_alpha(fs["text_alpha"])
        surface.blit(big, big.get_rect(center=(screenW // 2, screenH // 2 + 60)))

        sub = fs["small_font"].render("Returning to base...", True, (140, 200, 255))
        sub.set_alpha(fs["text_alpha"])
        surface.blit(sub, sub.get_rect(center=(screenW // 2, screenH // 2 + 110)))

# draw everything, follow the logic of update then this is called to draw
def drawGame():
    gs = gameScene
    ox, oy = gs["cam"].shakeOffset()
    #draw star field before background
    gs["stars"].draw(surface, gs["cam"].x)
    gs["level"].draw(surface, gs["cam"].x, gs["portalGlow"], int(ox), int(oy))
    if gs["state"] == "play":
        gs["player"].draw(surface, gs["cam"].x)
        gs["gravityFlip"].draw(surface, gs["cam"].x)
    elif gs["state"] == "deathSpin":
        gs["player"].drawSpin(surface, gs["cam"].x)
    gs["particles"].draw(surface, gs["cam"].x)
    gs["flash"].draw(surface)  # draw flash in ALL states so death/deathSpin flash is visible

    # the current mode
    modeLabel = f"MODE: {gs['player'].mode.upper()}"
    t = gs["font"].render(modeLabel, True, white)
    surface.blit(t, (20 + ox, 16 + oy))

    # the current attempt number
    at = gs["font"].render(f"ATTEMPT {attempts}", True, white)
    surface.blit(at, (screenW - at.get_width() - 20 + ox, 16 + oy))

    # messages to display win or lose
    if gs["state"] == "dying":
        t = gs["font"].render("You died - Retrying...", True, (255, 120, 120))
        surface.blit(t, t.get_rect(center=(screenW // 2, screenH // 2)))
    elif gs["state"] == "win":
        t = gs["font"].render("You completed the objective!", True, (180, 255, 180))
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
    elif state == FLYAWAY:
        updateFlyaway(dt)
        drawFlyaway()

    pygame.display.flip()

pygame.quit()
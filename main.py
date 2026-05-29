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

MENU, LOADING, GAME = "menu", "loading", "game"
updateLoading = pygame.USEREVENT + 1

pygame.init()
pygame.font.init()
pygame.mixer.init()

surface = pygame.display.set_mode((screenW, screenH))
pygame.display.set_caption(title)
clock = pygame.time.Clock()

state = MENU
selectedLevel = 0
playerName = "Astronaut"
gameScene = None
assetsLoaded = False
attempts = 1            


def setPlayerName(name):
    global playerName
    playerName = name


def setLevel(value, idx):
    global selectedLevel
    selectedLevel = idx


def startGame():
    global state
    state = LOADING
    progress.set_value(0)
    pygame.time.set_timer(updateLoading, 20)


def quitGame():
    pygame.quit()
    sys.exit()

# menu building
mainMenu = pygame_menu.Menu("Moon Race", screenW, screenH, theme=themes.THEME_DARK)
mainMenu.add.text_input("Name: ", default="Astronaut", onchange=setPlayerName)
mainMenu.add.selector("Level: ", [("Cave", 0), ("Surface", 1)], onchange=setLevel)
mainMenu.add.button("Play", startGame)
mainMenu.add.button("Quit", quitGame)

loadingMenu = pygame_menu.Menu("Loading...", screenW, screenH, theme=themes.THEME_DARK)
progress = loadingMenu.add.progress_bar("Progress", progressbar_id="pb1", default=0, width=500)

# initialization of all varaibles needed to run the game, all are stored in the game scene dictionary
def startGameScene(retry=False):
    global state, gameScene, attempts
    # fresh start (from menu) resets to 1, a retry bumps the count
    if retry : 
        attempts = attempts + 1 
    else :
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

        # trail particels appear whehn on ground
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
        if gs["player"].y > gs["level"].worldH or gs["player"].y < -gs["player"].h:
            gs["state"] = "dying"
            gs["deathTimer"] = 70
            assets.playSfx("death")
            gs["particles"].deathBurst(
                gs["player"].x + gs["player"].w / 2,
                gs["player"].y + gs["player"].h / 2
            )
            gs["cam"].addShake(0.9)

    # death
    elif gs["state"] == "dying":
        gs["deathTimer"] -= dt
        if gs["deathTimer"] <= 0:
            startGameScene(retry=True)

    # win
    elif gs["state"] == "win":
        gs["winTimer"] -= dt
        if gs["winTimer"] <= 0:
            assets.stopMusic()
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

    if state == MENU:
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

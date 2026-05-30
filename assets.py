import os
import pygame

screenW, screenH = 1280, 720
tile = 40

img = {}
sfx = {}
anim = {}    

# directory paths so we can make the absolute path easier
spriteDir = os.path.join(os.path.dirname(__file__), "assets", "sprites")
audioDir = os.path.join(os.path.dirname(__file__), "assets", "audio")
assetsDir = os.path.join(os.path.dirname(__file__), "assets")


# when something is missing, this is called to replace that image with a pink box
def missingRect(size):
    s = pygame.Surface(size, pygame.SRCALPHA)
    s.fill((255, 0, 220, 255))
    pygame.draw.rect(s, (40, 0, 40), s.get_rect(), 2)
    pygame.draw.line(s, (40, 0, 40), (0, 0), size, 2)
    pygame.draw.line(s, (40, 0, 40), (0, size[1]), (size[0], 0), 2)
    return s

# loading image function
def loadImg(key, targetSize=None, crop=False):
    # we first make the absoluate path to the image file based on image file name
    path = os.path.join(spriteDir, key + ".png")
    # if doesnt exist then print error
    if not os.path.isfile(path):
        print(f"[assets] missing sprite: {path}")
        return missingRect(targetSize or (tile, tile))
    # save it as a surface and resize if resize is needed
    surf = pygame.image.load(path).convert_alpha()
    # crop away transparent padding 
    if crop:
        bbox = surf.get_bounding_rect()
        surf = surf.subsurface(bbox).copy()
    if targetSize and surf.get_size() != targetSize:
        surf = pygame.transform.scale(surf, targetSize)
    return surf

# to load animations from a sheet
def loadSheet(key, cols, rows, states, targetH=52):
    path = os.path.join(spriteDir, key + ".png")
    if not os.path.isfile(path):
        print(f"[assets] missing sheet: {path}")
        for name in states:
            anim[name] = [missingRect((tile, tile))]
        return
    sheet = pygame.image.load(path).convert_alpha()
    # just get size of each frame, we do that by dividing total width with number of columns and height by number of rows
    fw = sheet.get_width() // cols
    fh = sheet.get_height() // rows

    def frameAt(n):                      
        idx = n - 1
        r, c = idx // cols, idx % cols
        return sheet.subsurface(pygame.Rect(c * fw, r * fh, fw, fh)).copy()

    # grab every frame we'll use
    allNums = [n for nums in states.values() for n in nums]
    union = None
    for n in allNums:
        bb = frameAt(n).get_bounding_rect()
        union = bb if union is None else union.union(bb)

    # resizing each sprite in the sheet
    scale = targetH / union.height
    tw = max(1, int(union.width * scale))
    for name, nums in states.items():
        anim[name] = [pygame.transform.scale(frameAt(n).subsurface(union), (tw, targetH)) for n in nums]

# same as above but for background
def loadBackground(key):
    path = os.path.join(spriteDir, key + ".png")
    # if background image is missing then just draw it in
    if not os.path.isfile(path):
        print(f"[assets] missing background: {path}")
        fallback = pygame.Surface((screenW, screenH))
        fallback.fill((10, 10, 25))
        return fallback
    surf = pygame.image.load(path).convert()
    surf = pygame.transform.scale(surf, (screenW, screenH))
    return surf

# load sound effect
def loadSfx(key):
    # check each possible audio file extension type 
    for ext in (".wav", ".ogg", ".mp3"):
        path = os.path.join(assetsDir, "sfx", key + ext)
        if os.path.isfile(path):
            return pygame.mixer.Sound(path)
    print(f"[assets] missing sfx: {key}")
    return None

# play music 
def playMusic(name, volume=0.4, loop=True):
    # make path
    for ext in (".ogg", ".mp3", ".wav"):
        path = os.path.join(assetsDir, "music", name + ext)
        # if found setup music and play
        if os.path.isfile(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            if (loop):
                pygame.mixer.music.play(-1)
            else :
                pygame.mixer.music.play(0)
            return True
    print(f"[assets] missing music: {name}")
    return False

# stop music 
def stopMusic():
    pygame.mixer.music.stop()

# play sfx
def playSfx(key):
    if sfx.get(key):
        sfx[key].play()

# load all assets into the dictionaries for easier access
def loadAll():
    tileSz = (tile, tile)
    portalSz = (tile * 2, tile * 2)
    img["astronaut"]     = loadImg("astronaut", tileSz)
    # astronaut animation
    loadSheet("AstronautAnimated-Sheet", 6, 6, {"run":  list(range(13, 20)),"jump": list(range(26, 31)),})
    img["block"]         = loadImg("block", tileSz, crop=True)
    img["spikeUp"]       = loadImg("spike_up", tileSz, crop=True)
    img["spikeDown"]     = loadImg("spike_down", tileSz, crop=True)
    img["portalJump"]    = loadImg("portal_jump", portalSz)
    img["portalGravity"] = loadImg("portal_gravity", portalSz)
    img["portalJetpack"] = loadImg("portal_jetpack", portalSz)
    img["spaceship"]     = loadImg("spaceship", (tile * 5, tile * 12), crop=True)
    img["caveExit"]      = loadImg("cave_exit", (tile * 3, tile * 5))
    img["bgLevel1"]      = loadBackground("bg_level1")
    img["bgLevel2"]      = loadBackground("bg_level2")
    img["earth"]        = loadImg("earth", (125, 125), crop=True)

    sfx["jump"]         = loadSfx("jump")
    sfx["death"]        = loadSfx("death")
    sfx["portal"]       = loadSfx("portal")
    sfx["thrust"]       = loadSfx("thrust")
    sfx["gravity_flip"] = loadSfx("gravity_flip")
    sfx["land"]         = loadSfx("land")
    for s in sfx.values():
        if s:
            s.set_volume(0.2)

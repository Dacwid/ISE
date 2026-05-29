import pygame
tile = 40
gravity = 0.55
jumpVelocity = -12.0
terminalVelocity = 16.0
jetpackThrust = -0.9
gravityFlipLerp = 0.06
gravityFloat = 0.25        # weaker pull in gravity mode = more floaty drift
gravityFloatMaxSpeed = 8.0 # lower terminal speed in gravity mode = slower fall
coyoteFrames = 6
animSkip = {"run":4, "jump": 4}   # frames to wait per anim state (higher = slower)
modeJump, modeGravity, modeJetpack = "jump", "gravity", "jetpack"
from assets import img, anim, playSfx


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w, self.h = tile - 6, tile - 6
        self.vy = 0.0
        self.onGround = False
        self.coyoteTimer = 0.0
        self.alive = True

        self.mode = modeJump

        self.gravitySign = 1.0
        self.gravityTarget = 1.0

        self.thrusting = False

        # animation state
        self.frameIndex = 0
        self.animTimer = 0.0

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # change mode of player when stepping into portal
    def setMode(self, newMode):
        if newMode == self.mode:
            return
        self.mode = newMode
        if newMode == modeGravity:
            self.gravitySign, self.gravityTarget = 1.0, 1.0
        self.thrusting = False

    # jump based on mode
    def onSpacePressed(self):
        if self.mode == modeJump:
            # jump if grounded recently (coyote time), not just this exact frame.
            # onGround flickers while resting, so checking a small timer fixes dropped jumps.
            if self.coyoteTimer > 0:
                self.vy = jumpVelocity
                self.coyoteTimer = 0
                playSfx("jump")
            # if in gravity switching mode then switch gravity
        elif self.mode == modeGravity:
            self.gravityTarget *= -1
            playSfx("gravity_flip")

    # hold space for jetpack
    def onSpaceHeld(self, held):
        if self.mode == modeJetpack:
            was = self.thrusting
            self.thrusting = held
            if held and not was:
                playSfx("thrust")
            if not held and was:
                pass

    # update player
    def update(self, dt, level):
        if self.mode == modeJump:
            self.updateJump(dt)
        elif self.mode == modeGravity:
            self.updateGravity(dt)
        elif self.mode == modeJetpack:
            self.updateJetpack(dt)

        self.vy = max(-terminalVelocity, min(terminalVelocity, self.vy))

        self.moveAndCollide(dt, level)

        # refresh coyote timer
        if self.onGround:
            self.coyoteTimer = coyoteFrames
        else:
            self.coyoteTimer = max(0, self.coyoteTimer - dt)

        self.animate(dt)

    # pick which animation is playing and advance its frame on a timer.
    # use coyoteTimer (stable) not onGround (flickers every frame while resting)
    def animate(self, dt):
        state = "run" if self.coyoteTimer > 0 else "jump"
        frames = anim.get(state) or anim.get("run") or [img["astronaut"]]
        self.animTimer += dt
        if self.animTimer >= animSkip.get(state, 6):
            self.animTimer = 0
            self.frameIndex = (self.frameIndex + 1) % len(frames)
        # keep index valid if the current state has fewer frames
        if self.frameIndex >= len(frames):
            self.frameIndex = 0

    def updateJump(self, dt):
        self.vy += gravity * dt

    def updateGravity(self, dt):
        # checks gravity based on gravity sign, and if the gravity changes, instead of instantly flipping, it flips smoothly 
        new = self.gravitySign + (self.gravityTarget - self.gravitySign) * gravityFlipLerp * dt
        self.gravitySign = new
        # use the weaker float pull + lower speed cap so the drift feels floaty
        self.vy += gravityFloat * self.gravitySign * dt
        self.vy = max(-gravityFloatMaxSpeed, min(gravityFloatMaxSpeed, self.vy))


    def updateJetpack(self, dt):
        if self.thrusting:
            self.vy += jetpackThrust * dt
        else:
            self.vy += gravity * dt

    def moveAndCollide(self, dt, level):
        dx = 0
        self.x += dx

        self.y += self.vy * dt
        self.onGround = False
        playerRect = self.rect()
        for tileRect in level.solidTilesNear(playerRect):
            if not playerRect.colliderect(tileRect):
                continue
            if self.vy > 0:
                #landing
                self.y = tileRect.top - self.h
                self.vy = 0
                if self.gravitySign >= 0:
                    self.onGround = True
            elif self.vy < 0:
                #hit ceiling
                self.y = tileRect.bottom
                self.vy = 0
                if self.gravitySign < 0:
                    self.onGround = True
            playerRect = self.rect()

    # draw player
    def draw(self, surf, camX):
        # grab the current animation frame (fall back to static sprite if no frames)
        state = "run" if self.coyoteTimer > 0 else "jump"
        frames = anim.get(state) or anim.get("run") or [img["astronaut"]]
        sprite = frames[self.frameIndex % len(frames)]

        flipped = self.mode == modeGravity and self.gravitySign < 0
        if flipped:
            sprite = pygame.transform.flip(sprite, False, True)

        sw, sh = sprite.get_size()
        # center horizontally on the hitbox
        sx = int(self.x - camX + self.w / 2 - sw / 2)
        # normal: feet at hitbox bottom. flipped: feet at hitbox top (standing on ceiling)
        if flipped:
            sy = int(self.y)
        else:
            sy = int(self.y + self.h - sh)
        surf.blit(sprite, (sx, sy))

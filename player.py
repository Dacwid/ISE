import pygame
tile = 40
gravity = 0.55
jumpVelocity = -12.0
terminalVelocity = 16.0
jetpackThrust = -0.9
gravityFlipLerp = 0.06
modeJump, modeGravity, modeJetpack = "jump", "gravity", "jetpack"
from assets import img, playSfx


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w, self.h = tile - 6, tile - 6
        self.vy = 0.0
        self.onGround = False
        self.alive = True

        self.mode = modeJump

        self.gravitySign = 1.0
        self.gravityTarget = 1.0

        self.thrusting = False

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
            # plays the jump sound and jumps if on ground
            if self.onGround:
                self.vy = jumpVelocity
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

    def updateJump(self, dt):
        self.vy += gravity * dt

    def updateGravity(self, dt):
        # checks gravity based on gravity sign, and if the gravity changes, instead of instantly flipping, it flips smoothly 
        new = self.gravitySign + (self.gravityTarget - self.gravitySign) * gravityFlipLerp * dt
        self.gravitySign = new
        self.vy += gravity * self.gravitySign * dt


    def updateJetpack(self, dt):
        # GOAL: while space is held -> push up. otherwise -> fall normally.
        # HINT 1 (held): self.vy += jetpackThrust * dt    (thrust is negative = up)
        # HINT 2 (not held): self.vy += gravity * dt
        # HINT 3: it's flappy-bird-ish. tune jetpackThrust and gravity in constants.py
        #         if it feels too floaty or too sharp.

        # TODO: if self.thrusting: apply upward thrust
        # TODO: else: apply normal gravity
        pass

    def moveAndCollide(self, dt, level):
        dx = 0
        self.x += dx

        self.y += self.vy * dt
        self.onGround = False
        playerRect = self.rect()
        for tileRect in level.solidTilesNear(playerRect):
            if not playerRect.colliderect(tileRect):
                continue
            # TODO (collision resolve):
            # 1) figure out if you came in from the TOP (vy > 0) or BOTTOM (vy < 0)
            #    in gravity mode you can hit a ceiling and want onGround=True too.
            # 2) snap self.y to tileRect.top - self.h  (landed on top of block)
            #    or to tileRect.bottom               (banged head, or stood on ceiling)
            # 3) zero out self.vy
            # 4) set self.onGround = True when grounded against the current
            #    gravity direction (positive sign -> top-hit, negative -> bottom-hit)
            pass

    # draw player
    def draw(self, surf, camX):
        sprite = img["astronaut"]
        if self.mode == modeGravity and self.gravitySign < 0:
            sprite = pygame.transform.flip(sprite, False, True)
        sx, sy = int(self.x - camX), int(self.y)
        surf.blit(sprite, (sx - 3, sy - 3))

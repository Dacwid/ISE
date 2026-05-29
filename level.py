import pygame
screenW = 1280
tile = 40
scrollSpeed = 4
modeJump, modeGravity, modeJetpack = "jump", "gravity", "jetpack"
from assets import img

legendSolid = {"#"}
legendHazard = {"^", "v"}
legendPortal = {"J": modeJump, "G": modeGravity, "F": modeJetpack}


class Level:
    # loads level from text file into a grid
    def __init__(self, path, idx):
        self.idx = idx
        rows = []
        with open(path) as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith(";"):
                    continue
                rows.append(line)

        # find longest row and makes all rows the same length by adding . to the end
        self.cols = max(len(r) for r in rows)
        # counted number of rows
        self.rowsN = len(rows)
        rows = [r.ljust(self.cols, ".") for r in rows]
        self.grid = rows

        # calculated world size in pixels by multiplying column and rows by tilesize
        self.worldW = self.cols * tile
        self.worldH = self.rowsN * tile

        # load bg based on level
        bgKey = "bgLevel" + str(idx + 1)
        self.bg = img[bgKey]

        # default end point = the spot the player reaches when the camera is fully scrolled
        # (player sits 200px from the left, camera maxes at worldW - screenW)
        self.endX = self.worldW - screenW + 200
        for y in range(self.rowsN):
            for x in range(self.cols):
                if self.grid[y][x] == "E":
                    self.endX = x * tile

        # set player spanw point which is 2 tiles from left and 4 tiles from bottom
        self.spawn = (2 * tile, (self.rowsN - 4) * tile)

    def updateCamera(self, cam, dt, player):
        # scroll camera based on scroll speed
        cam.x += scrollSpeed * dt
        # stop the camera so it halts exactly when the end point reaches the
        # player's anchor (200px from left). keep ~screenW-200 of level past the
        # end marker so no empty space shows when you arrive.
        maxX = self.endX - 200
        if cam.x > maxX:
            cam.x = maxX
        # player is based on camera position + 200 pixels
        player.x = cam.x + 200
        # win check
        if player.x >= self.endX:
            return True
        return False        

    # get the cell type of the given coordinates, could be a solid, hazard, portal, or empty
    def cell(self, cx, cy):
        if 0 <= cy < self.rowsN and 0 <= cx < self.cols:
            return self.grid[cy][cx]
        return "."

    # find all the solid tiles that are nearest to the specified hitbox in the input, used for collision detection
    def solidTilesNear(self, rect):
        results = []
        # works by checking all cells that are exactly next to the hitbox and all that are solid is put into the results dict
        x0 = max(0, rect.left // tile - 1)
        x1 = min(self.cols - 1, rect.right // tile + 1)
        y0 = max(0, rect.top // tile - 1)
        y1 = min(self.rowsN - 1, rect.bottom // tile + 1)
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                if self.cell(cx, cy) in legendSolid:
                    results.append(pygame.Rect(cx * tile, cy * tile, tile, tile))
        return results

    # same as funciton avobe but for hazards 
    def hazardsNear(self, rect):
        results = []
        x0 = max(0, rect.left // tile - 1)
        x1 = min(self.cols - 1, rect.right // tile + 1)
        y0 = max(0, rect.top // tile - 1)
        y1 = min(self.rowsN - 1, rect.bottom // tile + 1)
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                ch = self.cell(cx, cy)
                if ch in legendHazard:
                    hb = pygame.Rect(cx * tile + 8, cy * tile + 14, tile - 16, tile - 18)
                    results.append((ch, hb))
        return results

    # again but for portals
    def portalsNear(self, rect):
        results = []
        x0 = max(0, rect.left // tile - 1)
        x1 = min(self.cols - 1, rect.right // tile + 1)
        y0 = max(0, rect.top // tile - 1)
        y1 = min(self.rowsN - 1, rect.bottom // tile + 1)
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                ch = self.cell(cx, cy)
                if ch in legendPortal:
                    results.append((legendPortal[ch], pygame.Rect(cx * tile, cy * tile, tile, tile)))
        return results

    def draw(self, surf, camX):
        bgX = -int(camX * 0.3) % self.bg.get_width()
        surf.blit(self.bg, (-bgX, 0))
        if bgX > 0:
            surf.blit(self.bg, (self.bg.get_width() - bgX, 0))

        # convert camera pixel position to tile columns to find which tiles are visible
        x0 = max(0, int(camX) // tile - 1)
        x1 = min(self.cols - 1, (int(camX) + screenW) // tile + 1)
        # loop all rows but only the visible columns and draws each cell
        for cy in range(self.rowsN):
            # only cells in camera range
            for cx in range(x0, x1 + 1):
                ch = self.grid[cy][cx]
                if ch == "#":
                    surf.blit(img["block"], (cx * tile - camX, cy * tile))
                elif ch == "^":
                    surf.blit(img["spikeUp"], (cx * tile - camX, cy * tile))
                elif ch == "v":
                    surf.blit(img["spikeDown"], (cx * tile - camX, cy * tile))
                elif ch in legendPortal:
                    key = {modeJump: "portalJump",
                           modeGravity: "portalGravity",
                           modeJetpack: "portalJetpack"}[legendPortal[ch]]
                    # portal art is 2x2 tiles
                    surf.blit(img[key], (cx * tile - camX - tile // 2, cy * tile - tile // 2))
                elif ch == "E":
                    # cave (level 1) ends at a cave exit, surface (level 2) ends at the rocket
                    endKey = "spaceship" if self.idx == 1 else "caveExit"
                    surf.blit(img[endKey], (cx * tile - camX, cy * tile - tile * 3))

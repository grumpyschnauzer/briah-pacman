# Briah Pac-Man

This version fixes the movement bug where Briah only rotated and the bots appeared frozen.

## Run

```bash
pip install pygame
python briah_pacman.py
```

## Controls

- Enter / Space / any movement key: start
- Arrow keys or WASD: move Briah
- P: pause/unpause
- R: restart after win or game over

## What changed

Movement is now tile-to-tile with a target tile. The old version snapped actors back to the center of the same tile every frame, so the sprite could rotate without actually traveling to the next tile.


## Visual-only update

This package keeps the previous working movement/gameplay code and only updates:
- Briah's asset to a transparent, more realistic head-only sprite
- power-up coins to purple bone-shaped dog treats
- simple WAV sounds loaded through the existing sound hooks

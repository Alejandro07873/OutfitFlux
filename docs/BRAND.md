# 🎨 Brand kit

**Name:** OutfitFlux. Use the full name; do not abbreviate it to OF.

**Voice:** clear, friendly and practical. Explain actions instead of exposing internal implementation details.

| Token | Value |
| --- | --- |
| Graphite | `#111113` |
| Dark surface | `#1c1c1e` |
| Light background | `#f3f6fb` |
| Blue accent | `#0a84ff` |
| Violet accent | `#8b5cf6` |

## Editable resources

- `docs/media/banner.svg`: editable vector header. Change text, colors and positions in any SVG editor or text editor.
- `branding/outfitflux.png`: original raster icon artwork.
- `branding/outfitflux.ico`: multi-resolution Windows icon.
- `scripts/capture_screenshots.py`: reproducible screenshots of the actual app in English.

The icon depicts overlapping costume silhouettes. The PNG is raster artwork, not a layered vector file. The banner is the editable vector resource. Screenshots show the UI using locally generated game thumbnails; no mod binaries are included.

The live wordmark uses `ui/animated_wordmark.py`: a moving gradient clipped to text glyphs. Edit the gradient colors and 4.8-second cycle there. It uses Qt painting and does not need a video or sprite sheet.

import json
from PIL import Image, ImageOps

game = "sf6"
pack = "pixel_art"
customZoom = 1.4
targetW = 256
targetH = 256

game_config = json.load(
    open(f"../../StreamHelperAssets/games/{game}/base_files/config.json"))

print(game_config)

pack_config = json.load(
    open(f"../../StreamHelperAssets/games/{game}/{pack}/config.json"))

print(pack_config)

for char_data in game_config["character_to_codename"].values():
    startgg_name = char_data["smashgg_name"]

    img = Image.open(
        f'../../StreamHelperAssets/games/{game}/{pack}/{pack_config.get("prefix")}{char_data["codename"]}{pack_config.get("postfix")}0.png')

    originalW = img.width
    originalH = img.height

    proportional_zoom = 1

    # For cropped assets, zoom to fill
    # Calculate max zoom
    zoom_x = targetW / originalW
    zoom_y = targetH / originalH

    minZoom = 1
    rescalingFactor = 1

    if pack_config.get("rescaling_factor"):
        rescalingFactor = pack_config.get("rescaling_factor")

    uncropped_edge = pack_config.get("uncropped_edge", [])

    if not uncropped_edge or len(uncropped_edge) == 0:
        if zoom_x > zoom_y:
            minZoom = zoom_x
        else:
            minZoom = zoom_y
    else:
        if (
            "u" in uncropped_edge and
            "d" in uncropped_edge and
            "l" in uncropped_edge and
            "r" in uncropped_edge
        ):
            customZoom = 1.2  # Add zoom in for uncropped assets
            minZoom = customZoom * proportional_zoom * rescalingFactor
        elif (
            not "l" in uncropped_edge and
            not "r" in uncropped_edge
        ):
            minZoom = zoom_x
        elif (
            not "u" in uncropped_edge and
            not "d" in uncropped_edge
        ):
            minZoom = zoom_y
        else:
            minZoom = customZoom * proportional_zoom * rescalingFactor

    zoom = max(minZoom, customZoom * minZoom)

    # Centering
    xx = 0
    yy = 0

    eyesight = pack_config.get("eyesights").get(char_data["codename"])["0"]

    if not eyesight:
        eyesight = {
            "x": originalW / 2,
            "y": originalH / 2
        }

    xx = -eyesight["x"] * zoom + targetW / 2

    maxMoveX = targetW - originalW * zoom

    if not uncropped_edge or not "l" in uncropped_edge:
        if (xx > 0):
            xx = 0

    if not uncropped_edge or not "r" in uncropped_edge:
        if (xx < maxMoveX):
            xx = maxMoveX

    yy = -eyesight["y"] * zoom + targetH / 2

    maxMoveY = targetH - originalH * zoom

    if not uncropped_edge or not "u" in uncropped_edge:
        if (yy > 0):
            yy = 0

    if not uncropped_edge or not "d" in uncropped_edge:
        if (yy < maxMoveY):
            yy = maxMoveY

    img = img.resize(
        (int(originalW*zoom), int(originalH*zoom)), Image.BILINEAR)
    img = img.crop((
        int(-xx),
        int(-yy),
        int(-xx+targetW),
        int(-yy+targetH)
    ))

    img = ImageOps.mirror(img)

    img.save(f"./{game}/{startgg_name}.png")

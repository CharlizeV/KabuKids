# Kivy normalized RGBA format: (R, G, B, A) where R, G, B, A are between 0.0 and 1.0

#RGBA converter
def rgba_from_255(r, g, b, a=255):
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)

PRIMARY_COLOR = rgba_from_255(255, 255, 255, 255) # white
SECONDARY_COLOR = rgba_from_255(25, 110, 59, 255) #dark green
ACCENT_COLOR = rgba_from_255(254, 188, 65, 255) #yellow

SUPER_LIGHT = rgba_from_255(151, 181, 118, 255) #very light gray

DARK_COLOR = rgba_from_255(141, 106, 75, 255) #dark brown
LIGHT_COLOR = rgba_from_255(95, 134, 53, 255) #light green
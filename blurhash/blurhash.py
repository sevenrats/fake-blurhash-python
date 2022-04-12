"""
Pure python blurhash decoder with no additional dependencies, for
both de- and encoding.

Very close port of the original Swift implementation by Dag Ågren.

Extended to demonstrate a novel decoding algorithm by Austin Crandall

"""
import math
from time import time

from PIL import Image, ImageFilter

import numpy


# Alphabet for base 83
alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"+"abcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~"
alphabet_values = dict(zip(alphabet, range(len(alphabet))))


def base83_decode(base83_str):
    """
    Decodes a base83 string, as used in blurhash, to an integer.
    """
    value = 0
    for base83_char in base83_str:
        value = value * 83 + alphabet_values[base83_char]
    return value


def base83_encode(value, length):
    """
    Decodes an integer to a base83 string, as used in blurhash.

    Length is how long the resulting string should be. Will complain
    if the specified length is too short.
    """
    if int(value) // (83 ** (length)) != 0:
        raise ValueError("Specified length is too short to encode given value.")

    result = ""
    for i in range(1, length + 1):
        digit = int(value) // (83 ** (length - i)) % 83
        result += alphabet[int(digit)]
    return result


def srgb_to_linear(value):
    """
    srgb 0-255 integer to linear 0.0-1.0 floating point conversion.
    """
    value = float(value) / 255.0
    if value <= 0.04045:
        return value / 12.92
    return math.pow((value + 0.055) / 1.055, 2.4)


def sign_pow(value, exp):
    """
    Sign-preserving exponentiation.
    """
    return math.copysign(math.pow(abs(value), exp), value)


def linear_to_srgb(value):
    """
    linear 0.0-1.0 floating point to srgb 0-255 integer conversion.
    """
    value = max(0.0, min(1.0, value))
    if value <= 0.0031308:
        return int(value * 12.92 * 255 + 0.5)
    return int((1.055 * math.pow(value, 1 / 2.4) - 0.055) * 255 + 0.5)


def blurhash_components(blurhash):
    """
    Decodes and returns the number of x and y components in the given blurhash.
    """

    # Decode metadata
    size_info = base83_decode(blurhash[0])
    size_y = int(size_info / 9) + 1
    size_x = (size_info % 9) + 1

    return size_x, size_y


def blurhash_decode(blurhash, width, height, punch=1.0, linear=False, show_time=False):
    """
    Decodes the given blurhash to an image of the specified size.

    Returns the resulting image a list of lists of 3-value sRGB 8 bit integer
    lists. Set linear to True if you would prefer to get linear floating point
    RGB back.

    The punch parameter can be used to de- or increase the contrast of the
    resulting image.

    As per the original implementation it is suggested to only decode
    to a relatively small size and then scale the result up, as it
    basically looks the same anyways.
    """
    t0 = time()
    if len(blurhash) < 6:
        raise ValueError("BlurHash must be at least 6 characters long.")

    # Decode metadata
    size_info = base83_decode(blurhash[0])
    size_y = int(size_info / 9) + 1
    size_x = (size_info % 9) + 1

    quant_max_value = base83_decode(blurhash[1])
    real_max_value = (float(quant_max_value + 1) / 166.0) * punch

    # Make sure we at least have the right number of characters
    if len(blurhash) != 4 + 2 * size_x * size_y:
        raise ValueError("Invalid BlurHash length.")

    # Decode DC component
    dc_value = base83_decode(blurhash[2:6])
    colours = [
        (
            srgb_to_linear(dc_value >> 16),
            srgb_to_linear((dc_value >> 8) & 255),
            srgb_to_linear(dc_value & 255),
        )
    ]

    # Decode AC components
    for component in range(1, size_x * size_y):
        ac_value = base83_decode(blurhash[4 + component * 2: 4 + (component + 1) * 2])
        colours.append(
            (
                sign_pow((float(int(ac_value / (19 * 19))) - 9.0) / 9.0, 2.0)
                * real_max_value,
                sign_pow((float(int(ac_value / 19) % 19) - 9.0) / 9.0, 2.0)
                * real_max_value,
                sign_pow((float(ac_value % 19) - 9.0) / 9.0, 2.0) * real_max_value,
            )
        )

    # Return image RGB values, as a list of lists of lists,
    # consumable by something like numpy or PIL.
    pixels = []
    for y in range(height):
        pixel_row = []
        for x in range(width):
            pixel = [0.0, 0.0, 0.0]

            for j in range(size_y):
                for i in range(size_x):
                    basis = math.cos(
                        math.pi * float(x) * float(i) / float(width)
                    ) * math.cos(math.pi * float(y) * float(j) / float(height))
                    colour = colours[i + j * size_x]
                    pixel[0] += colour[0] * basis
                    pixel[1] += colour[1] * basis
                    pixel[2] += colour[2] * basis
            if not linear:
                pixel_row.append(
                    [
                        linear_to_srgb(pixel[0]),
                        linear_to_srgb(pixel[1]),
                        linear_to_srgb(pixel[2]),
                    ]
                )
            else:
                pixel_row.append(pixel)
        pixels.append(pixel_row)
    t1 = time()
    if show_time:
        print("Decode Time: ", t1 - t0)
    return pixels


def blurhash_fake_decode(blurhash, width, height, punch=1.0, show_time=False):
    """
    Decodes the given blurhash to a list of (x, y, (r,g,b)) tuples, with one tuple per element,
    where x and y are the centerpoint of each element, and r, g, b
    describe the color of the tile to render.

    The punch parameter can be used to de- or increase the contrast of the
    resulting image.

    Contrary to the original implementation, the size at which you render has
    very little impact on performance.
    """
    t0 = time()
    size_x, size_y = blurhash_components(blurhash)

    quant_max_value = base83_decode(blurhash[1])
    real_max_value = (float(quant_max_value + 1) / 166.0) * punch

    # Make sure we at least have the right number of characters
    if len(blurhash) != 4 + 2 * size_x * size_y:
        raise ValueError("Invalid BlurHash length.")

    # Decode DC component
    dc_value = base83_decode(blurhash[2:6])
    colours = [
        (
            srgb_to_linear(dc_value >> 16),
            srgb_to_linear((dc_value >> 8) & 255),
            srgb_to_linear(dc_value & 255),
        )
    ]

    # Decode AC components
    for component in range(1, size_x * size_y):
        ac_value = base83_decode(blurhash[4 + component * 2: 4 + (component + 1) * 2])
        colours.append(
            (
                sign_pow((float(int(ac_value / (19 * 19))) - 9.0) / 9.0, 2.0)
                * real_max_value,
                sign_pow((float(int(ac_value / 19) % 19) - 9.0) / 9.0, 2.0)
                * real_max_value,
                sign_pow((float(ac_value % 19) - 9.0) / 9.0, 2.0) * real_max_value,
            )
        )

    # Return a list of tuples, where each tuple is (x, y, (R,G,B))
    # Each tuple defines the centerpoint of an element, and the
    # color of the pixel at that coordinate
    elements = []
    for i in range(int(size_x * size_y)):
        c = i + 1  # correct index
        row = math.ceil(c / size_x)
        column = c % size_x if c % size_x != 0 else size_x
        row_height = height / size_y
        column_width = width / size_x
        x = (column_width / 2) + (column_width * (column - 1))
        y = (row_height / 2) + (row_height * (row - 1))
        pixel = [0.0, 0.0, 0.0]
        for j in range(size_y):
            for i in range(size_x):
                basis = math.cos(
                    math.pi * float(x) * float(i) / float(width)
                ) * math.cos(math.pi * float(y) * float(j) / float(height))
                colour = colours[i + j * size_x]
                pixel[0] += colour[0] * basis
                pixel[1] += colour[1] * basis
                pixel[2] += colour[2] * basis
        pixel = (
            linear_to_srgb(pixel[0]),
            linear_to_srgb(pixel[1]),
            linear_to_srgb(pixel[2]),
        )
        element = (int(x), int(y), pixel)
        elements.append(element)
    t1 = time()
    if show_time:
        print("Decode Time: ", t1 - t0)
    return elements


def blurhash_show(blurhash, width, height, punch=1.0, show_time=False):
    """
    Draws and shows an image using the original pure Python blurhash method.
    Optionally print the run time for the command with 'show_time = True'
    """
    t0 = time()
    im = Image.fromarray(
        numpy.array(
            blurhash_decode(blurhash, width, height, punch=punch, show_time=show_time)
        ).astype("uint8")
    )
    t1 = time()
    if show_time:
        print("Draw Time: ", t1 - t0)
    im.show()


def blurhash_show_fake(
    blurhash, width, height, punch=1.0, blur_divisor=4, show_time=False
):
    """
    Draws and shows an image using the fake blurhash method, decoding to a short list of tuples.
    Optionally print the run time for the command with 'show_time = True'
    """
    t0 = time()
    size_x, size_y = blurhash_components(blurhash)
    width, height = int(width), int(height)
    elem_width = int(width / size_x)
    elem_height = int(height / size_y)
    elements = blurhash_fake_decode(
        blurhash, width, height, punch=punch, show_time=show_time
    )
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    for elem in elements:
        tile = Image.new("RGB", (width, height), elem[2])
        canvas.paste(
            tile, (int((elem[0]) - elem_width / 2), int((elem[1]) - elem_height / 2))
        )
    final = canvas.filter(
        ImageFilter.GaussianBlur(elem_width / blur_divisor)
    )
    t1 = time()
    if show_time:
        print("Draw Time: ", t1 - t0)
    final.show()


def blurhash_encode(image, components_x=4, components_y=4, linear=False):
    """
    Calculates the blurhash for an image using the given x and y component counts.

    Image should be a 3-dimensional array, with the first dimension being y, the second
    being x, and the third being the three rgb components that are assumed to be 0-255
    srgb integers (incidentally, this is the format you will get from a PIL RGB image).

    You can also pass in already linear data - to do this, set linear to True. This is
    useful if you want to encode a version of your image resized to a smaller size (which
    you should ideally do in linear colour).
    """
    if components_x < 1 or components_x > 9 or components_y < 1 or components_y > 9:
        raise ValueError("x and y component counts must be between 1 and 9 inclusive.")
    height = float(len(image))
    width = float(len(image[0]))

    # Convert to linear if neeeded
    image_linear = []
    if not linear:
        for y in range(int(height)):
            image_linear_line = []
            for x in range(int(width)):
                image_linear_line.append(
                    [
                        srgb_to_linear(image[y][x][0]),
                        srgb_to_linear(image[y][x][1]),
                        srgb_to_linear(image[y][x][2]),
                    ]
                )
            image_linear.append(image_linear_line)
    else:
        image_linear = image

    # Calculate components
    components = []
    max_ac_component = 0.0
    for j in range(components_y):
        for i in range(components_x):
            norm_factor = 1.0 if (i == 0 and j == 0) else 2.0
            component = [0.0, 0.0, 0.0]
            for y in range(int(height)):
                for x in range(int(width)):
                    basis = (
                        norm_factor
                        * math.cos(math.pi * float(i) * float(x) / width)
                        * math.cos(math.pi * float(j) * float(y) / height)
                    )
                    component[0] += basis * image_linear[y][x][0]
                    component[1] += basis * image_linear[y][x][1]
                    component[2] += basis * image_linear[y][x][2]

            component[0] /= width * height
            component[1] /= width * height
            component[2] /= width * height
            components.append(component)

            if not (i == 0 and j == 0):
                max_ac_component = max(
                    max_ac_component,
                    abs(component[0]),
                    abs(component[1]),
                    abs(component[2]),
                )

    # Encode components
    dc_value = (
        (linear_to_srgb(components[0][0]) << 16)
        + (linear_to_srgb(components[0][1]) << 8)
        + linear_to_srgb(components[0][2])
    )

    quant_max_ac_component = int(
        max(0, min(82, math.floor(max_ac_component * 166 - 0.5)))
    )
    ac_component_norm_factor = float(quant_max_ac_component + 1) / 166.0

    ac_values = []
    for r, g, b in components[1:]:
        ac_values.append(
            int(
                max(
                    0.0,
                    min(
                        18.0,
                        math.floor(
                            sign_pow(r / ac_component_norm_factor, 0.5) * 9.0 + 9.5
                        ),
                    ),
                )
            )
            * 19
            * 19
            + int(
                max(
                    0.0,
                    min(
                        18.0,
                        math.floor(
                            sign_pow(g / ac_component_norm_factor, 0.5) * 9.0 + 9.5
                        ),
                    ),
                )
            )
            * 19
            + int(
                max(
                    0.0,
                    min(
                        18.0,
                        math.floor(
                            sign_pow(b / ac_component_norm_factor, 0.5) * 9.0 + 9.5
                        ),
                    ),
                )
            )
        )

    # Build final blurhash
    blurhash = ""
    blurhash += base83_encode((components_x - 1) + (components_y - 1) * 9, 1)
    blurhash += base83_encode(quant_max_ac_component, 1)
    blurhash += base83_encode(dc_value, 4)
    for ac_value in ac_values:
        blurhash += base83_encode(ac_value, 2)

    return blurhash

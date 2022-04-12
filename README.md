# fake-blurhash-python

This is a modified version of Lorenz Diener's blurhash library, extended to demonstrate a novel decoding algorithm.
This code uses spec blurhashes, so your existing blurhash infrastructure will work, unmodified. Instead of calculating every single pixel, we:
 - Calculate a single pixel at the center of each element
 - Store the centerpoint and evaluated color in a list of (x, y, (R,G,B)) tuples.

 An example of rendering this data:
 - render each element as a solid tile with the sampled color.
 - apply gaussian blur to the composited image with a radius equal to 1/4 of the tile width
 
 My hope is that this psuedo-implementation will provide a guide to bring blurhash's functionality to low power devices,
 as it can be done with very simple drawing fundamentals.

 Please see the source code for full details, and test it on your existing blurhashes!

 Credit and thanks to:
 Dag Ågren https://github.com/DagAgren
 Lorenz Diener https://github.com/halcy

```python
import blurhash
import PIL.Image
import numpy

PIL.Image.open("cool_cat_small.jpg")
# Result:
```
![A picture of a cool cat.](/cool_cat_small.jpg?raw=true "A cool cat.")
```python
blurhash.encode(numpy.array(PIL.Image.open("cool_cat_small.jpg").convert("RGB")))
# Result: 'UBL_:rOpGG-oBUNG,qRj2so|=eE1w^n4S5NH'

#Compare the original pure python implementation:
blurhash.show('UBL_:rOpGG-oBUNG,qRj2so|=eE1w^n4S5NH', 128,128, show_time=True)
# Result:
# Decode Time:  2.5773730278015137
# Draw Time:  2.62654185295105

```
![Blurhash example output: A blurred cool cat.](/blurhash_example.png?raw=true "Blurhash example output: A blurred cool cat.")

```python
# To the fake version:
blurhash.show_fake('UBL_:rOpGG-oBUNG,qRj2so|=eE1w^n4S5NH', 128,128, show_time=True)
# Result:
# Decode Time:  0.0025682449340820312
# Draw Time:  0.03584718704223633


```
![Blurhash example output: An IMPOSTER blurred cool cat.](/fake_blurhash_example_bd4.png?raw=true "Blurhash example output: An IMPOSTER blurred cool cat.")

You can fine-tune your own implementation by changing the relationship between the tile size and the blur radius:

![Blurhash example output: An IMPOSTER blurred cool cat.](/fake_blurhash_example_bd3.png?raw=true "Blurhash example output: An IMPOSTER blurred cool cat.")
    
Blurhash is an algorithm that lets you transform image data into a small text representation of a blurred version of the image. This is useful since this small textual representation can be included when sending objects that may have images attached around, which then can be used to quickly create a placeholder for images that are still loading or that should be hidden behind a content warning. https://github.com/woltapp/blurhash

This library contains a pure-python implementation of the blurhash algorithm by Lorenz Diener, closely following the original swift implementation by Dag Ågren. It was further extended to demonstrate this novel pseudo-implementation in the hopes of bringing blurhash's functionality to low-power devices.

The drawing implementation in this library's "show_fake" function is solely for the purpose of visualizing the faked blurhash, it has not been optimized in any way.


It exports eight functions:
* "encode" to do the actual encoding of blurhash strings
* "decode" and "fake_decode" to generate drawable data from the blurhash
* "show" and "show_fake" to illustrate the appearance of each implementation
* "components" returns the number of components x- and y components of a blurhash
* "srgb_to_linear" and "linear_to_srgb" are colour space conversion helpers

Have a look at example.py for an example of how to use all of these working together.

Documentation for each function:

```python
blurhash.encode(image, components_x = 4, components_y = 4, linear = False):
"""
Calculates the blurhash for an image using the given x and y component counts.

Image should be a 3-dimensional array, with the first dimension being y, the second
being x, and the third being the three rgb components that are assumed to be 0-255 
srgb integers (incidentally, this is the format you will get from a PIL RGB image).

You can also pass in already linear data - to do this, set linear to True. This is
useful if you want to encode a version of your image resized to a smaller size (which
you should ideally do in linear colour).
"""

blurhash.decode(blurhash, width, height, punch = 1.0, linear = False)
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

blurhash.fake_decode(blurhash, width, height, punch = 1.0, show_time = False):
"""
Decodes the given blurhash to a list of (x, y, (r,g,b)) tuples, with one tuple per element,
where x and y are the centerpoint of each element, and r, g, b
describe the color of the tile to render.

The punch parameter can be used to de- or increase the contrast of the
resulting image.

Contrary to the original implementation, the size at which you render has
very little impact on performance.
"""

blurhash_show(blurhash, width, height, punch = 1.0, show_time = False):
"""
Draws and shows an image using the original pure Python blurhash method.
Optionally print the run time for the command with 'show_time = True'
"""

blurhash_show_fake(blurhash, width, height, punch = 1.0, blur_divisor = 4, show_time = False):
"""
Draws and shows an image using the fake blurhash method, decoding to a short list of tuples.
Optionally print the run time for the command with 'show_time = True'
"""

blurhash_components(blurhash):
"""
Decodes and returns the number of x and y components in the given blurhash.
"""

blurhash.srgb_to_linear(value):
"""
srgb 0-255 integer to linear 0.0-1.0 floating point conversion.
"""
    
blurhash.linear_to_srgb(value):
"""
linear 0.0-1.0 floating point to srgb 0-255 integer conversion.
"""
```
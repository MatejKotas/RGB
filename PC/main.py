from RGB import RGB
from album import Album
from threading import Thread

album = Album()
rgb = RGB()

Thread(target=rgb.run).start()
album.start()
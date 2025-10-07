# Album Cover Display

## Note: Only works with Spotify

This addon uses the Spotify API to fetch the album cover of the song that is currently playing and display it fullscreen, usually on a seperate monitor.

## Instructions

### Part 1: Spotify Developer Dashboard

1. Go to [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard)
2. Press Create App
3. Put whatever app name and description you want.
4. Put the following in **Redirect URIs**
```
http://127.0.0.1:8081
```
5. Check the checkbox **Web API**
6. Click Save

### Part 2: Setup the program
1. Find example.env
2. Create a copy of example.env and name it .env
3. Put your ID and Secret into .env
4. Put Enable=1 instead of Enable=0 in .env
5. Run the program.
6. The first time you run the program, a webpage will ask you to log in and give the program access to the API. Do as it says.
7. If prompted, copy the url you were redirected to after allowing API access and paste it in the console.

Note: If the image doesn't refresh automatically (sometimes it done't when a song is skipped) you may force a refresh by either:

1. Typing "refresh" in the console and pressing enter.
2. Clicing the image. (Click on the image twice, once to make it the active window, and another time to register the click)
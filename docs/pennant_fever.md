Pennant Fever is a recreation of the long out-of-print Avalon Hill board game called Pennant Race. It was a tabletop baseball dice and card game that simulated baseball games, but in a very abstracted/meta way. You wouldnt actually simulate the game inning by inning, rather you would generate the result of the game with a few dice rolls. This allowed you to simulate a full season fairly quickly. The game still used rosters (historical rosters were provided) and players had basic ratings. The object of the game was to put together the most optimal lineup throughout the season and manage things like injuries and fatigue along the way. The game was not in print very long but did earn a cult following and some dedicated fans improved upon the original rules to add a little more depth. I started making a computerized version of it recently (python) and adding my own features and improvements, while trying to stay faithful to the spirit of the game.

What exists:

1. The simulator itself - command line only, and essentially the core game engine that would simulate an entire season, along with the playoffs and print the results to the console. This was designed to help test game logic as well as engine accuracy.
2. A game generator module - this program generates a fictional league (in the style of modern MLB) for use in the game engine. It creates the necessary data files for the game engine to run a full season, like it would with historical rosters.
3. A historical player/roster import module - designed to import real seasons into the game
4. Support files - i have quite a few data files adapted and/or used from other games ive been working on - my own historical databases adapted specifically for this game, name files, ballpark data, schools, geo-economic city data etc

What needs to be done:

- i recently added logic in the game to support 'splits' for batter and pitcher ratings (vs LHP/RHP). the game gen module and the game itself support this, but the historical import/gen module does not, so the hsitorical rosters wont work with the current version of the game bc they do not output this field yet (and there is no fallback logic). that module needs to be updated for splits as well.
- the game needs a visual interface using pygame, which ive used successfully in similar games.
- the game needs to have an interactive component - essentially we need to build out from the game engine when thats completely stable so the user/player can take control of a team (while the ai runs the rest of the league), run the league (day by day, week by week etc) while being able to set lineups, make roster changes, etc. the games should be saveable
- the data in the game needs to be saved into a sql db and the schema created at the inception of the league (ie when the game generator module runs and produces data). this db is what the game should be saving everything into going forward
- the game needs a dashboard/game manager module where the user can manage their rosters, see stats, make transactions, get updates, change settings etc. this module is essentially the 'boot up module' - splash screen, then menu screen (load saved game, create new game etc)

Pennant Fever is a recreation of the long out-of-print Avalon Hill board game called Pennant Race. It was a tabletop baseball dice and card game that simulated baseball games, but in a very abstracted/meta way. You wouldnt actually simulate the game inning by inning, rather you would generate the result of the game with a few dice rolls. This allowed you to simulate a full season fairly quickly. The game still used rosters (historical rosters were provided) and players had basic ratings. The object of the game was to put together the most optimal lineup throughout the season and manage things like injuries and fatigue along the way. The game was not in print very long but did earn a cult following and some dedicated fans improved upon the original rules to add a little more depth. I started making a computerized version of it recently (python) and adding my own features and improvements, while trying to stay faithful to the spirit of the game.

What exists:

1. The simulator itself - command line only, and essentially the core game engine that would simulate an entire season, along with the playoffs and print the results to the console. This was designed to help test game logic as well as engine accuracy.
2. A game generator module - this program generates a fictional league (in the style of modern MLB) for use in the game engine. It creates the necessary data files for the game engine to run a full season, like it would with historical rosters.
3. A historical player/roster import module - designed to import real seasons into the game
4. Support files - i have quite a few data files adapted and/or used from other games ive been working on - my own historical databases adapted specifically for this game, name files, ballpark data, schools, geo-economic city data etc

What needs to be done:

- i recently added logic in the game to support 'splits' for batter and pitcher ratings (vs LHP/RHP). the game gen module and the game itself support this, but the historical import/gen module does not, so the hsitorical rosters wont work with the current version of the game bc they do not output this field yet (and there is no fallback logic). that module needs to be updated for splits as well.
- the game needs a visual interface using pygame, which ive used successfully in similar games. the visual aesthetic will be simple/old school. i had initially looked into curses as an option but i think technically it would actually be more difficult to implement and i dont want a TUI/CLI. i just want it to kind of look like that. this is a text only sim, theres no animation so the resource usage will be minimal esp if theres an ascii-vibe to it.
- the game needs to have an interactive component - essentially we need to build out from the game engine when thats completely stable so the user/player can take control of a team (while the ai runs the rest of the league), run the league (day by day, week by week etc) while being able to set lineups, make roster changes, etc. the games should be saveable
- the data in the game needs to be saved into a sql db and the schema created at the inception of the league (ie when the game generator module runs and produces data). this db is what the game should be saving everything into going forward
- the game needs a dashboard/game manager module where the user can manage their rosters, see stats, make transactions, get updates, change settings etc. this module is essentially the 'boot up module' - splash screen, then menu screen (load saved game, create new game etc)
- i started expanding the game to move beyond the simplicity of the original player reatings system into something a bit more modern and better quantifiable. batters now have batting (which shoul,d reallh be renamed to contact), power and eye. these 3 are use to calcuate the BV (batter value). from the game itself: player_bv = player.batting + player.eye + (player.power * 0.6). pitching is much more limited to start_value or relief_value, which are the primary indicator of pitcher skill/ability. i wanted to have something complementary for the pitchers as well - like stuff, command, movement. perhaps those 3 can, like the BV, can be weighted and combined to produce the final starter or reliever value. the ideal scenario would be to figure out some algorithms where we could make the individual batter/pitcher ratings more meaningful. the game doesnt understand the concept of walks, strikeouts, base hits - its all in the service of run calculation. so how would something like batter's eye impact things? or what if the pitcher is a strikeout artist facing a group of power hitters with poor eye ratings? we can be as granular or general as we want with the ratings, but id like to make something like pitcher's command for example, actually produce a meaningful impact on the game, rather than just being a number used to calculate the value in the end.
- is there a way we can generate a simple box score based on the result of the game we generate? we have a few bits of data like HRs, earned/unearned runs, innings pitched but not much beyond that bc the game is heavily abstracted. if we can leverage the player ratings along with the results, could we produce constistent plausible results? and im talking about a simple old school newspaper style box score, not sabrmetrics, or fangraphs stuff. AB/R/H/HR/RBI/SB - IP/H/ER/R/BB/K/HR - ideally we would count doubles, triples to produce OBP, SLG as well.
- closer logic for relief pitching?

References:

- i have been working on an american football sim that has many of the aforementioned tools, modules and data except its far more advanced at this point. so there are a lot of things to examine there we can use in this game. the game gen modules are actually quite similar, ive used that structure in a few other projects. one thing the football game does have this game does not is the game manager, which is quite advanced at thos point so it will be worth studying the structure so we can re-use/adapt the code for this game. bc this game is simpler, we shouldnt need the full complexity of the football game's game manager.

Files:
- GENERATIVE_NAMES_DIR/first_names_weighted_baseball.xlsx
- GENERATIVE_NAMES_DIR/surnames_weighted_master.xlsx
-
- generativeprojects/weather/usa and /japan
-


# TEAM STRUCTURE
"team_id": 30,
"team_city": "Baltimore",
"team_name": "Orioles",
"team_colors": {
    "primary": "#948904",
    "complementary": "#6B76FB"
},
"ballpark_name": "Camden Yards",
"home_field_advantage": 0,
"stadium_value": -1,
"league_name": "Major League Baseball",
"division_name": "East Division",
"unearned_runs_chart": {
    "3": 0,
    "4": 1,
    "5": 0,
    "6": 0,
    "7": 1,
    "8": 1,
    "9": 2,
    "10": 2
}

# BATTER STRUCTURE
"name": "Broc Cruikshank",
"race": "White",
"age": 29,
"height": 199,
"weight": 98,
"origin": "USA",
"school": "Washington Hs", 
"school_type": "HS",
"position": "1B",
"secondary_position": null,
"bats": "L",
"throws": "R",
"archetype": "regular starter",
"draft": null,
"role": "Starter",
"batting": 4,
"power": 6,
"eye": 0,
"splits_L": 1,
"splits_R": 3,
"speed": 5,
"fielding": -1,
"potential": 6,
"clutch": 0,
"injury": -1,
"makeup": 0,
"morale": 0,
"popularity": 0,
"contract": 0,
"salary": 0,
"service_time": 0,
"scouting_report": "Broc Cruikshank is a 29-year-old L handed batter who plays 1B. An everyday player who contributes consistently both at the plate and in the field. He's a contact hitter who consistently puts the ball in play. His bat delivers home runs effortlessly. He has a poor eye at the plate, frequently chasing pitches out of the zone. He's an average runner, capable of taking extra bases when needed. In summary, Broc Cruikshank has shown promise with 6 power and 5 speed. He is expected to be a key player in the future."

# PITCHER STRUCTURE
"name": "John Temple",
"race": "White",
"age": 28,
"height": 193,
"weight": 98,
"origin": "USA",
"school": "East Carolina",
"school_type": "COL",
"position": "RP",
"secondary_position": null,
"bats": "L",
"throws": "L",
"archetype": "filler arm",
"draft": null,
"type": "Reliever",
"start_value": 0.5,
"endurance": 0.5,
"rest": 8,
"cg_rating": 666,
"sho_rating": 666,
"splits_L": -1,
"splits_R": -2,
"relief_value": 0.5,
"fatigue": 0.5,
"potential": 0,
"injury": -3,
"makeup": 0,
"morale": 0,
"popularity": 0,
"salary": 0,
"contract": 0,
"service_time": 0,
"scouting_report": "John Temple is a 28-year-old L handed pitcher. Fills out the minor league rosters, nothing more. He's a liability as a starter, struggling to get through the lineup more than once. He's a one-inning specialist who struggles to maintain his stuff over multiple frames. He's a liability out of the bullpen, often giving up runs in key moments. He tires easily and needs long recovery times between outings. In summary, John Temple has demonstrated strong endurance with a starting value of 0.5 and reliable relief value of 0.5. He is expected to be a key contributor in the pitching staff."

'''
# PRIORITY NEED TO QUASH THIS BUG AttributeError: 'NoneType' object has no attribute 'fatigue_cache'
# ALSO looks like we have scenarios where (starting) pitcher allowed only unearned runs and but was either getting a win, or they other pitcher would get a loss (partly as a result of very low BVs the hit negative territory and get normalised to 0), also these types of shutouts not getting recognised as a shutout
# need to add clutch for extra inning relief pitcher calc (PROBABLY A GOOD IDEA TO ACTUALLY ADD IT TO PITCHER GEN FIRST LOL)
# create mechanic where if speed chart is invoked, we also check catchers throwing rating (will need to make that rating in the player gen)
# need to decrease injury length
# starters pulled early (for exceeding run threshold) are not getting enough runs assigned to them in some cases. they should get the majority of them in that circumstance
# relief pitcher fatigue tracking as a function of batters faced within X amount of days
# fielding bonus for double play partnerships (eg, if one fielding rating is called, check to see if its 2B/SS and potentially add partners fielding rating too)
# all extra inning games end in 1 run difference, need some variety?
# GAMES BEHIND is being calculated incorrectly. 
# need to add team_city to standings
# need to add loggers to playoffs esp for pitcher rest/fatigue/last days started tracking
# are we counting off days for teams in schedule? ie even though game days proceed in order (1, 2, 3, 4, 5 etc), not every team plays each game day (ie travel day) so are we then giving that team a day off for rotation/rest purposes?
# it looks like teams that have poor offense and good (or at least average) pitching (2023 brewers, yankees) have poor records consistently prolly bc we are weighted heavier on batting ratings vs pitching ratings; when calculating BV we use batting and eye but not power, which is likely also penalising these teams (these are IRL teams)
# may have to start considering separate roster management program (trades, promoting/demoting, dfa, contracts, etc) and possible a more robust db like postgres
# need to get players injury rating involved in injury class calcs
# player retirements, depends on archetype and age vs decline age diff (also consider stats somehow) - prolly needs to be in a different module altogether - preobably a separate module (GM)
# something wrong with last start day being reset in playoffs? leading to the short-rested starter prob we see at beginning of season
# dont forget to finish getting CLI worked in 
# if extra innings, make sure CG/SHO is nullified
# determining defense. we do have a roll for a fielding position modifier (for a specific position). but what if we (also?) used a team modifier that took into account every fielder (basically totaling up the fielding ratings)?
# need to add section that will factor in manager ratings, weather, HFA, etc (and see above for fielding). perhaps one use of manager ratings would be in extra innings, before we use dice as tie breakers
# add indiv stat tracking
# need to round off runs in various places and BV values
# do i need self.makeup in class Player and class Pitcher?
# ballpark can have more specific modifiers (power, contact, etc), perhaps a fielding mod if its turf or grass, etc. same for dome or not
# leadership attribute - this could help mitigate low morale, or increase morale when i get around to making team morale calcs (morale should be a high number for granularitys sake and also we will be adding quite a bit throughout the year for things like wins, losses, streaks, personal achivements/stats, making the playoffs, under/overperforming, etc)
# i can make indiv morale calc function just to start counting it appropriately, will actually have impact in game when i make GM module (***these last 2 are related to the fic player module qv)
# relief pitcher usage in blowouts, when losing by x amount of runs we need to see if SP was pulled early and then how to handle relief pitchers as far as how many, total ip, and any potential position players used (mlb rule: allowed when losing by 8+, winning by 10+ or extra_innings) - would need to prioritize using lower quality relievers to mop up innings depending on the score
# future idea: we move away from the literal dice-roll mechanic to a more normal probability based on 0.0 - 1.0 then scale those ratings to 20-80 for players, this could be used to make a 2.0 version of game that generates individual game data (we dont actually play the game play by play but generate what happened)
# two-way players?
# not enough team shutouts (in MLB 2023, there were 35 CG, 21 complete game shutouts, 309 team shutouts, we look pretty good on the former 2 but way short on the latter)
# is higher white die consistently good for offense and bad for defense? 
# start working on getting manager mechanics involved in game resolution
# pitcher abuse point: how many innings pitched on short rest or fatigued if relief pitcher
# any connection to fatigue/injuries and playing regularly on astroturf?
'''
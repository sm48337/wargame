# Installation

To run this inside of a Docker container the following steps need to be executed.

* Clone the repository by executing `git clone https://github.com/sm48337/wargame.git`
* Run this command inside of the directory to build the image `docker build -t wargame .`
* Run this command to run the server `docker run -p 5000:5000 wargame`

The application should be available on `http://127.0.0.1:5000/`.

# Usage

First you will be redirected to a login form.
If you do not have an account you need to go to the register link and enter your username and password.

After this you'll land on the home page.
Here you can create a new game or view an existing game you're a part of.

## Team creation

If you go to the game creation screen you'll be presented with a form asking you to assemble two teams.
Red Team represents Russia, and the Blue Team represents the UK.
Each team has five entities whose control can be split between multiple players by assigning them.

After players have been assigned to their entities and team names were chosen the game may be created.

# How to play

The game consists of 12 rounds (months) with the teams taking turns.
The turns are timed and automatically finish after 3 minutes are up.

The goal of the game is to end the game with more Victory Points than the opponent by achieving goals such as attacking opponent's entities and by defending yourself while building up wealth.

The exact goals and many other rule explanations are available in Appendices A and B [this paper](2019haggmanaphd.pdf).

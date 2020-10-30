# HatBot
A Discord bot to play Hat (a charades-style game) virtually.

#### Gameplay
Once every player has joined the game, the bot will create a private text channel for each player.  Each player must enter 4 (or some other predetermined number) words in their text channel; the bot will take these words and put them in the 'hat'.  Once all the words are in the hat, the game begins.  Every player is assigned a partner to give clues to.  On your turn, the bot will give you words drawn from the hat, and you have 30 seconds to get your partner to guess as many words as possible by giving them clues (the types of clues you can give are limited based on the round).  Once 30 seconds are up, it is the next person's turn.  Once all of the words have been guessed, they are put back into the hat and the next round begins; after 3 rounds, the game is over.

#### Clue restrictions
Round 1: You may give any clue you like.

Round 2: You may only give one-word clues.

Round 3: You may only give clues in mime.

#### List of commands
`!start` -> Start the game.

`!join` -> Join the game.  (Each player must type the !join command.)

`!wpp` -> Set the number of words each person will enter.

`!done` -> Indicate that all players have joined.

`!words` -> Add words to the "hat" by typing space-separated words (for example, if playing with 3 words per person, type "!words word1 word2 word3")

`!begin` -> Begin your turn -- starts a 30 second timer and starts giving words. 

`!n` -> Get the next word.

`!skip` -> Skip a word.

`!restart` -> Shortcut to start a new game with the same people without having to join again.

`!finish` -> Ends the game.

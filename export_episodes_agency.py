"""
Grizzly Knights — Agency-driven episode exporter

Spawns character agents from /universe/characters/*.yaml at scene time,
runs a Director-orchestrated multi-agent scene, threads continuity
forward, and writes prose .txt episodes for ElevenReader.

Usage:  python export_episodes_agency.py [episode_number]
        python export_episodes_agency.py 1     # just episode 1
        python export_episodes_agency.py       # all 4
"""

import re
import sys
import copy
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich import box

ROOT = Path(__file__).parent
console = Console()
load_dotenv(ROOT / ".env")

from engine.agency_engine import (
    EpisodePlan, build_model, run_episode_sync,
)

OUTPUT_DIR = ROOT / "episodes_text"


# ─── Episode plans — explicit continuous beats per scene ──────────────────────
# Each scene declares its own location, time, and situation. The next scene's
# situation references the previous beat. No random per-act shuffles.

EPISODES = [
    EpisodePlan(
        number  = 1,
        title   = "Before Anyone Noticed",
        cast    = ["felicia_hardy", "wade_wilson"],
        logline = (
            "Wednesday afternoon at the Cheesecake Factory. No mission. No "
            "reason. Nobody knows they're friends. Two people who found each "
            "other outside the binary, splitting fries and not explaining "
            "themselves to anyone."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Cheesecake Factory — booth in the back, by the window",
                "time": "Wednesday, 2:47 PM",
                "situation": (
                    "Felicia and Wade are already two margaritas deep "
                    "(Felicia: top-shelf reposado on the rocks with salt; "
                    "Wade: frozen mango monstrosity that is mostly sugar "
                    "and grenadine because his palate is a war crime). "
                    "The breadsticks have arrived. They have not ordered "
                    "food yet. They are mid-conversation about somebody "
                    "they both know in a biblical sense and somebody only "
                    "one of them does. This is the first scene of the "
                    "entire universe — establish the world by establishing "
                    "what this friendship actually looks like when nobody "
                    "is watching. They are NOT polite. They are not "
                    "sanitized. They are crude, fluent, comfortable, and "
                    "frank about sex, about Peter Parker, about Wade's "
                    "body, about Felicia's line of work, about whoever "
                    "either of them is currently or recently fucking. "
                    "Establish the texture of the universe in this scene."
                ),
            },
            {
                "act": 1,
                "location": "Cheesecake Factory — same booth",
                "time": "Wednesday, 3:12 PM",
                "situation": (
                    "Same booth, twenty-five minutes later. Third round "
                    "ordered. Food has arrived — Felicia got the avocado "
                    "egg rolls, Wade got the fried mac and cheese balls "
                    "and the chicken parm and an extra side of fries. "
                    "The conversation has drifted toward something real — "
                    "one of them brings up a job that went bad recently, "
                    "or somebody they lost, in the casual way people in "
                    "their line of work actually bring those things up. "
                    "The other absorbs it without making it a moment."
                ),
            },
            {
                "act": 2,
                "location": "Cheesecake Factory — same booth, fourth round",
                "time": "Wednesday, 3:48 PM",
                "situation": (
                    "Still the same booth. Plates cleared except for the "
                    "ruins of the chicken parm. Fourth round in. Wade is "
                    "starting to get loose in the way that means his "
                    "humor is sharper, not softer. Felicia is at the "
                    "point where she stops pretending she has anywhere "
                    "else to be. Something from earlier surfaces — about "
                    "a person, about a body count, about a thing one of "
                    "them did and has not told anybody else."
                ),
            },
            {
                "act": 2,
                "location": "Cheesecake Factory — sidewalk just outside the entrance",
                "time": "Wednesday, 5:02 PM",
                "situation": (
                    "They closed out a $340 tab and walked out together. "
                    "Standing on the sidewalk now. Neither has called a "
                    "car. Felicia is lighting a cigarette — she smokes "
                    "Dunhills when she drinks and only when she drinks. "
                    "Wade is watching her do it and saying something "
                    "filthy about it. They are buzzed, not drunk. The "
                    "afternoon is not over."
                ),
            },
            {
                "act": 3,
                "location": "Felicia's brownstone — rooftop, two blocks from the restaurant",
                "time": "Wednesday, 5:41 PM",
                "situation": (
                    "They walked here together. Felicia brought him up "
                    "to her roof. She has never done that with anyone "
                    "else and she does not announce that fact. Wade "
                    "noticed anyway. There is a bottle of Don Julio 1942 "
                    "she keeps up here, and two glasses she rinsed off "
                    "at the kitchen sink before they came up. The city "
                    "is going gold. Neither of them is in a hurry."
                ),
            },
            {
                "act": 3,
                "location": "Felicia's brownstone — rooftop, later",
                "time": "Wednesday, 6:34 PM",
                "situation": (
                    "Same rooftop. The sun is gone. Half the Don Julio "
                    "is gone. Wade is sprawled on the edge with his feet "
                    "hanging over the street. Felicia is sitting against "
                    "the parapet. Neither of them has spoken for a "
                    "minute. This is the end of the day. One of them "
                    "will leave first. It will not be a goodbye scene — "
                    "it will be the kind of ending two people have when "
                    "they already know they will be doing this again."
                ),
            },
        ],
    ),
    EpisodePlan(
        number  = 2,
        title   = "The System",
        cast    = ["tony_stark", "jessica_jones", "clint_barton"],
        logline = (
            "Tony is managing. Jessica is functional. Clint is fine. None of "
            "them believe the other two. Three people who know exactly what "
            "they are doing to themselves and have decided to keep doing it "
            "anyway."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Stark's Manhattan workshop — sub-basement",
                "time": "Thursday, 1:14 AM",
                "situation": (
                    "Tony has been awake for thirty-six hours. He is "
                    "working on something that does not need to be done "
                    "tonight. Jessica is here because Tony asked her to "
                    "consult on a case he is not paying her for. She "
                    "arrived an hour ago and has not taken her coat off."
                ),
                "cast": ["tony_stark", "jessica_jones"],
            },
            {
                "act": 1,
                "location": "Stark's Manhattan workshop — sub-basement",
                "time": "Thursday, 2:03 AM",
                "situation": (
                    "Same workshop. Clint walks in unannounced. He has a "
                    "key. He did not call ahead. He looks like he has been "
                    "somewhere he should not have been. Jessica has not "
                    "left."
                ),
            },
            {
                "act": 2,
                "location": "Stark's Manhattan workshop — sub-basement",
                "time": "Thursday, 2:41 AM",
                "situation": (
                    "Same room. The pretense of the consult is over. "
                    "Nobody has named why Clint is here. Tony is still "
                    "working. Jessica is now drinking from a coffee mug "
                    "that is not coffee."
                ),
            },
            {
                "act": 2,
                "location": "Stark's Manhattan workshop — kitchenette upstairs",
                "time": "Thursday, 3:17 AM",
                "situation": (
                    "Tony went up for ice. The others followed. Smaller "
                    "room. Harder to avoid each other. Someone says "
                    "something true by accident."
                ),
            },
            {
                "act": 2,
                "location": "Stark's Manhattan workshop — kitchenette upstairs",
                "time": "Thursday, 3:46 AM",
                "situation": (
                    "Same kitchenette. The accidental true thing did not "
                    "get dismissed. None of them have moved. None of them "
                    "are pretending to be okay anymore — but none of them "
                    "are doing anything about it either."
                ),
            },
            {
                "act": 3,
                "location": "Stark's Manhattan workshop — rooftop helipad",
                "time": "Thursday, 4:52 AM",
                "situation": (
                    "Tony walked up to the roof to smoke a cigarette he is "
                    "not supposed to smoke. Clint followed. Jessica is "
                    "still downstairs. Pre-dawn. Cold. The two of them on "
                    "the helipad. Neither of them is going to fix the "
                    "other one tonight."
                ),
                "cast": ["tony_stark", "clint_barton"],
            },
            {
                "act": 3,
                "location": "Stark's Manhattan workshop — sub-basement, departing",
                "time": "Thursday, 5:33 AM",
                "situation": (
                    "Back downstairs. Jessica is putting her coat on for "
                    "real this time. Clint is half-asleep on the couch. "
                    "Tony is back at the bench. None of them slept. The "
                    "scene ends the way it started — three people managing."
                ),
            },
        ],
    ),
    EpisodePlan(
        number  = 3,
        title   = "What Gets Said",
        cast    = ["sam_wilson", "bucky_barnes", "steve_rogers"],
        logline = (
            "The three of them in a room. What Steve carries. What Sam "
            "sees. What Bucky does not say. The conversation that keeps "
            "almost happening and then does not."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Sam's apartment in Delacroix — kitchen",
                "time": "Saturday, 11:18 AM",
                "situation": (
                    "Sam is cooking lunch. Bucky arrived an hour ago, "
                    "uninvited but expected. Steve is supposed to be here "
                    "by noon. Sam is not asking why all three of them are "
                    "in his kitchen on a Saturday."
                ),
                "cast": ["sam_wilson", "bucky_barnes"],
            },
            {
                "act": 1,
                "location": "Sam's apartment in Delacroix — kitchen",
                "time": "Saturday, 12:09 PM",
                "situation": (
                    "Steve walks in nine minutes late. He brought nothing. "
                    "He apologizes for the timing in the way that means he "
                    "is not actually apologizing. Sam serves the food."
                ),
            },
            {
                "act": 2,
                "location": "Sam's apartment in Delacroix — back porch",
                "time": "Saturday, 1:24 PM",
                "situation": (
                    "Food eaten. The three of them moved to the porch. "
                    "Beer instead of plates. Sam has stopped working. The "
                    "conversation has not landed anywhere real yet, and "
                    "all three of them know it."
                ),
            },
            {
                "act": 2,
                "location": "Sam's apartment in Delacroix — back porch",
                "time": "Saturday, 2:11 PM",
                "situation": (
                    "Same porch. Sam asks Steve something direct. Steve "
                    "answers in the way that means he is not going to "
                    "answer. Bucky has not spoken in fifteen minutes."
                ),
            },
            {
                "act": 2,
                "location": "Sam's apartment in Delacroix — back porch",
                "time": "Saturday, 2:53 PM",
                "situation": (
                    "Bucky finally says one sentence. It is not what any of "
                    "them expected. Nobody moves. The porch gets quieter."
                ),
            },
            {
                "act": 3,
                "location": "Sam's apartment in Delacroix — dock at the back of the property",
                "time": "Saturday, 4:18 PM",
                "situation": (
                    "Sam and Steve walked down to the water. Bucky stayed "
                    "on the porch. The dock is for the boat Sam is "
                    "restoring with his nephews. Steve says one true thing "
                    "and Sam absorbs it."
                ),
                "cast": ["sam_wilson", "steve_rogers"],
            },
            {
                "act": 3,
                "location": "Sam's apartment in Delacroix — driveway",
                "time": "Saturday, 5:47 PM",
                "situation": (
                    "Both visitors are leaving. Steve and Bucky to the same "
                    "car. Sam standing in his driveway. Nothing got "
                    "resolved. Something landed. Sam goes back inside."
                ),
            },
        ],
    ),
    EpisodePlan(
        number  = 4,
        title   = "Parker Luck",
        cast    = ["peter_parker", "mary_jane_watson", "felicia_hardy"],
        logline = (
            "Peter, MJ, and Felicia in the same orbit for one afternoon. MJ "
            "sees everything. Felicia sees everything MJ sees. Peter is the "
            "only one who does not notice what is happening."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Joe's Coffee in the East Village",
                "time": "Sunday, 11:02 AM",
                "situation": (
                    "MJ texted Peter to meet her here. He is fifteen "
                    "minutes late. He arrives now. He has been swinging — "
                    "his hair is wrong and one knuckle is split. MJ "
                    "notices both without naming either."
                ),
                "cast": ["peter_parker", "mary_jane_watson"],
            },
            {
                "act": 1,
                "location": "Joe's Coffee in the East Village",
                "time": "Sunday, 11:34 AM",
                "situation": (
                    "Same coffee shop. Felicia walks in. She did not know "
                    "they were here. She immediately knows she is going to "
                    "stay anyway. She comes over to their table."
                ),
            },
            {
                "act": 2,
                "location": "Joe's Coffee in the East Village",
                "time": "Sunday, 12:01 PM",
                "situation": (
                    "Felicia sits down without being asked. MJ does not "
                    "object. Peter is doing the thing he does when he is "
                    "trying to manage two relationships at once. Both "
                    "women see it. Only one is amused."
                ),
            },
            {
                "act": 2,
                "location": "East Village — walking up Avenue A",
                "time": "Sunday, 12:48 PM",
                "situation": (
                    "They left together. The three of them walking. Peter "
                    "is in the middle. He is talking too much. MJ catches "
                    "Felicia's eye over the top of his head and they share "
                    "something he does not see."
                ),
            },
            {
                "act": 2,
                "location": "Tompkins Square Park — bench by the dog run",
                "time": "Sunday, 1:21 PM",
                "situation": (
                    "They sat down. Peter is between them. Felicia says "
                    "something that lands sharper than it sounded. Peter "
                    "is still half-tracking; MJ is fully tracking."
                ),
            },
            {
                "act": 3,
                "location": "Tompkins Square Park — bench by the dog run",
                "time": "Sunday, 2:14 PM",
                "situation": (
                    "Felicia stands up to leave. She and MJ exchange a "
                    "look that is not hostile. Peter is finally starting "
                    "to register that something happened. Felicia walks "
                    "away."
                ),
            },
            {
                "act": 3,
                "location": "Peter's walk back toward the F train with MJ",
                "time": "Sunday, 2:48 PM",
                "situation": (
                    "Peter and MJ walking together toward the subway. "
                    "Peter finally asks the question. MJ answers honestly. "
                    "Neither of them is angry. The afternoon ends."
                ),
                "cast": ["peter_parker", "mary_jane_watson"],
            },
        ],
    ),

    # ── Episode 5 ─────────────────────────────────────────────────────────
    EpisodePlan(
        number  = 5,
        title   = "The Argument That Doesn't End",
        cast    = ["frank_castle", "matt_murdock"],
        logline = (
            "Frank and Matt in the back booth of a Hell's Kitchen dive "
            "neither of them should be at. The argument they have been "
            "having for years is the only conversation either of them "
            "knows how to have with the other one. Neither of them is "
            "trying to win tonight. They just keep showing up for it."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Josie's Bar — back booth, near the busted jukebox",
                "time": "Thursday, 10:47 PM",
                "situation": (
                    "Frank is already in the booth when Matt walks in. "
                    "Two empty bottles of Schlitz and a third one open. "
                    "Frank set this up — text, no preamble, address, time. "
                    "Matt came. Frank slides the second bottle across the "
                    "table. Matt takes off his glasses and sets them down "
                    "where Frank can see he did. This is how they meet. "
                    "They have done it before. The conversation tonight "
                    "is about a body. Specifically a guy Matt left "
                    "breathing two nights ago who Frank thinks should "
                    "not be."
                ),
            },
            {
                "act": 1,
                "location": "Josie's Bar — back booth",
                "time": "Thursday, 11:09 PM",
                "situation": (
                    "Same booth. Third round. Frank has not raised his "
                    "voice and is not going to. Matt has not made a moral "
                    "speech and is not going to. They are working the "
                    "specifics — name, address, the kid the guy hurt, the "
                    "kid Matt thinks the guy could still help. Frank is "
                    "skeptical of the second kid existing."
                ),
            },
            {
                "act": 2,
                "location": "Josie's Bar — back booth",
                "time": "Thursday, 11:38 PM",
                "situation": (
                    "Fourth round. The argument has gotten quieter, which "
                    "for them means it has gotten more honest. Frank says "
                    "something specific about a body he has been carrying "
                    "since 2007. Matt does not therapize it. He just sits "
                    "with it."
                ),
            },
            {
                "act": 2,
                "location": "Josie's Bar — back alley behind the kitchen door",
                "time": "Friday, 12:14 AM",
                "situation": (
                    "Frank went out to smoke. Matt followed him. Two "
                    "Catholic men in an alley behind a bar. Frank is "
                    "smoking a Marlboro Red. Matt does not smoke but he "
                    "is standing close enough to be inside it. They are "
                    "not done arguing. They are just outside now."
                ),
            },
            {
                "act": 3,
                "location": "Hell's Kitchen — walking east on 49th",
                "time": "Friday, 12:46 AM",
                "situation": (
                    "They left together. They are walking the same "
                    "direction without having agreed to. Frank is going "
                    "to do something tonight. Matt has not stopped him. "
                    "Neither of them has named what is about to happen."
                ),
            },
            {
                "act": 3,
                "location": "Hell's Kitchen — corner of 11th Ave and 49th",
                "time": "Friday, 1:03 AM",
                "situation": (
                    "They stop at the corner. They split here. Frank goes "
                    "north. Matt goes south. The argument is not over. It "
                    "is just paused until the next time. One of them says "
                    "one short thing before they part. The other one "
                    "answers it."
                ),
            },
        ],
    ),

    # ── Episode 6 ─────────────────────────────────────────────────────────
    EpisodePlan(
        number  = 6,
        title   = "Three Ways to Be Untouchable",
        cast    = ["logan", "natasha_romanoff", "jessica_jones"],
        logline = (
            "Three people who learned to be untouchable through different "
            "doors and ended up at the same bar at 2 AM in Brooklyn. None "
            "of them planned to be here together. None of them is leaving "
            "until the bottle is empty."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Skinny Dennis — back of the bar, near the kitchen pass",
                "time": "Tuesday, 1:52 AM",
                "situation": (
                    "Jessica is already two-thirds into a bottle of "
                    "Knob Creek she did not order — the bartender just "
                    "knew. Natasha walks in. She did not expect to see "
                    "Jess and does not say hello. She just sits down. "
                    "They have not spoken in fourteen months. Country "
                    "music on the jukebox. No conversation yet."
                ),
                "cast": ["jessica_jones", "natasha_romanoff"],
            },
            {
                "act": 1,
                "location": "Skinny Dennis — back of the bar",
                "time": "Tuesday, 2:11 AM",
                "situation": (
                    "Logan comes in. He smells the room before he sees "
                    "it. He knows both of them. He sits down. The "
                    "bartender brings him a Molson without asking. They "
                    "are now three. Nobody has said anything important."
                ),
            },
            {
                "act": 2,
                "location": "Skinny Dennis — back of the bar",
                "time": "Tuesday, 2:34 AM",
                "situation": (
                    "Second round all around. Logan starts a story about "
                    "a thing that happened in 1974 he has never told "
                    "anybody. Natasha matches it with one of hers. "
                    "Jessica does not match. She just listens. The "
                    "matching is the conversation."
                ),
            },
            {
                "act": 2,
                "location": "Skinny Dennis — back of the bar",
                "time": "Tuesday, 3:02 AM",
                "situation": (
                    "Third round. Last call was twenty minutes ago and "
                    "the bartender is letting them stay. Natasha says one "
                    "thing about Clint that she would not say sober. "
                    "Logan does not flinch. Jessica laughs in a way "
                    "neither of them has heard from her in years."
                ),
            },
            {
                "act": 3,
                "location": "Skinny Dennis — sidewalk out front",
                "time": "Tuesday, 3:41 AM",
                "situation": (
                    "Bar closed. They are on the sidewalk on Metropolitan. "
                    "Logan is lighting a cigar. Natasha is on her phone. "
                    "Jessica is just standing there. None of them is "
                    "calling a car yet."
                ),
            },
            {
                "act": 3,
                "location": "Williamsburg — Bedford and N 7th",
                "time": "Tuesday, 4:08 AM",
                "situation": (
                    "They walked a few blocks together. They are at the "
                    "Bedford L stop. Three different directions home. "
                    "They are about to split. Whatever they came in with "
                    "is not what they are leaving with."
                ),
            },
        ],
    ),

    # ── Episode 7 ─────────────────────────────────────────────────────────
    EpisodePlan(
        number  = 7,
        title   = "Younger Than They Were",
        cast    = ["kate_bishop", "kamala_khan", "felicia_hardy"],
        logline = (
            "Kate and Kamala in the cheap seats. Felicia in the booth "
            "behind them. The conversation that happens when a "
            "twenty-six-year-old mentor meets two twenty-year-olds who "
            "are watching what their lives might look like in five years."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Veselka on 2nd Ave — corner booth, 3 AM crowd",
                "time": "Saturday, 2:51 AM",
                "situation": (
                    "Kate and Kamala just left a shitty open mic Kate "
                    "dragged Kamala to. They are at Veselka. Kate is "
                    "eating pierogies and drinking black coffee. Kamala "
                    "got the cherry blintzes and a Diet Coke. They are "
                    "decompressing the night. Felicia is in the booth "
                    "behind them, alone, finishing a Manhattan and a "
                    "borscht. She is recognizable to both of them."
                ),
                "cast": ["kate_bishop", "kamala_khan"],
            },
            {
                "act": 1,
                "location": "Veselka — corner booth",
                "time": "Saturday, 3:08 AM",
                "situation": (
                    "Felicia gets up to leave, pauses at their booth. "
                    "Kate says something to her. Felicia sits down on the "
                    "edge of their booth bench. She is not in a hurry now."
                ),
            },
            {
                "act": 2,
                "location": "Veselka — corner booth",
                "time": "Saturday, 3:31 AM",
                "situation": (
                    "Felicia is fully sat. She ordered another Manhattan. "
                    "Kate is asking her a question Kamala would not have "
                    "asked yet. Felicia answers honestly in a way that "
                    "neither of them expected."
                ),
            },
            {
                "act": 2,
                "location": "Veselka — corner booth",
                "time": "Saturday, 3:59 AM",
                "situation": (
                    "Same booth. The conversation has gone where these "
                    "conversations go — bodies, men, the work, who pays "
                    "you, what it costs. Kamala is now talking too. "
                    "Felicia is treating them as adults."
                ),
            },
            {
                "act": 3,
                "location": "2nd Ave sidewalk outside Veselka",
                "time": "Saturday, 4:34 AM",
                "situation": (
                    "All three on the sidewalk. Felicia is about to "
                    "leave. She gives Kate her number. She does not give "
                    "Kamala her number. Kate notices. Kamala does too "
                    "but does not say anything about it."
                ),
            },
            {
                "act": 3,
                "location": "Kate's apartment — walking the last block on E 9th",
                "time": "Saturday, 4:58 AM",
                "situation": (
                    "Kate and Kamala walking back to Kate's. They are "
                    "talking about Felicia. Kamala is honest about what "
                    "she saw. Kate is honest about what she wanted. "
                    "Neither of them is a kid anymore by the end of "
                    "this walk."
                ),
                "cast": ["kate_bishop", "kamala_khan"],
            },
        ],
    ),

    # ── Episode 8 ─────────────────────────────────────────────────────────
    EpisodePlan(
        number  = 8,
        title   = "Chess With the Devil",
        cast    = ["charles_xavier", "erik_lehnsherr"],
        logline = (
            "Charles and Erik. A chess board. Forty years of the same "
            "argument. Neither of them is going to convert the other "
            "one. Both of them keep showing up anyway."
        ),
        scenes  = [
            {
                "act": 1,
                "location": "Salem Center, NY — Xavier mansion, the small library",
                "time": "Sunday, 4:14 PM",
                "situation": (
                    "Erik arrived an hour ago. Unannounced. He always is. "
                    "Charles had Hank pour them both a Macallan 18. The "
                    "chess board is already out. Erik is white. Three "
                    "moves in. The students are away for the weekend. "
                    "Neither man pretends he is not happy to see the "
                    "other. Neither of them admits it either."
                ),
            },
            {
                "act": 1,
                "location": "Salem Center, NY — Xavier mansion, the small library",
                "time": "Sunday, 4:47 PM",
                "situation": (
                    "Eight moves in. Erik mentions a thing that happened "
                    "in Berlin in 1962. Charles corrects a detail. Erik "
                    "lets him be right. The argument starts."
                ),
            },
            {
                "act": 2,
                "location": "Salem Center, NY — Xavier mansion, the small library",
                "time": "Sunday, 5:33 PM",
                "situation": (
                    "Mid-game. Charles has lost a knight. Erik has lost "
                    "a bishop. The argument has moved from history to "
                    "the present — a kid Erik thinks Charles is losing "
                    "to the world. Charles does not concede. He also "
                    "does not deny it."
                ),
            },
            {
                "act": 2,
                "location": "Salem Center, NY — Xavier mansion, the back terrace",
                "time": "Sunday, 6:19 PM",
                "situation": (
                    "Charles asked Erik to wheel him out to the terrace. "
                    "Erik did it without making it a thing. The chess "
                    "game is paused. They are watching the light go off "
                    "the lawn. Erik says one thing about Magda. Charles "
                    "does not have a chess move for it."
                ),
            },
            {
                "act": 3,
                "location": "Salem Center, NY — Xavier mansion, the small library",
                "time": "Sunday, 7:42 PM",
                "situation": (
                    "Back inside. Game resumed. Erik is going to win in "
                    "four moves and they both know it. They are not "
                    "playing for the game anymore. They are playing for "
                    "the time."
                ),
            },
            {
                "act": 3,
                "location": "Salem Center, NY — Xavier mansion, the front portico",
                "time": "Sunday, 8:31 PM",
                "situation": (
                    "Erik is leaving. The car he came in is at the foot "
                    "of the steps. He pauses on the portico. He does not "
                    "promise to come back. Charles does not ask him to. "
                    "They both know."
                ),
            },
        ],
    ),
]


# ─── Prose formatter ──────────────────────────────────────────────────────────

def _short_first(name_upper: str) -> str:
    return name_upper.split()[0].title() if name_upper.split() else "they"


def _name_from_key(key: str) -> str:
    return " ".join(p.title() for p in key.split("_"))


def _name_upper_from_key(key: str) -> str:
    return key.replace("_", " ").upper()


# ─── Stage-direction cleanup ──────────────────────────────────────────────────
# Defect class: agent emits stage directions, first-person action narration,
# or bare action verbs INSIDE the dialogue payload. These render in curly
# quotes and get spoken by TTS in the character's voice — catastrophic.
# This module strips them at the prose layer so the cleanup runs on every
# cook (live and post-hoc on already-shipped artifacts).

_STAGE_VERBS = (
    r"grin(?:s|ned|ning)?|smirk(?:s|ed|ing)?|paus(?:e|es|ed|ing)|"
    r"shift(?:s|ed|ing)?|lean(?:s|ed|ing)?|tak(?:e|es|ing)|"
    r"flick(?:s|ed|ing)?|tilt(?:s|ed|ing)?|sigh(?:s|ed|ing)?|"
    r"breath(?:e|es|ed|ing)|exhal(?:e|es|ed|ing)|inhal(?:e|es|ed|ing)|"
    r"nod(?:s|ded|ding)?|shak(?:e|es|ing)|cross(?:es|ed|ing)?|"
    r"tap(?:s|ped|ping)?|drum(?:s|med|ming)?|pull(?:s|ed|ing)?|"
    r"push(?:es|ed|ing)?|slid(?:e|es|ing)|glanc(?:e|es|ed|ing)|"
    r"smil(?:e|es|ed|ing)|frown(?:s|ed|ing)?|laugh(?:s|ed|ing)?|"
    r"chuckl(?:e|es|ed|ing)|clear(?:s|ed|ing)?|whisper(?:s|ed|ing)?|"
    r"murmur(?:s|ed|ing)?|mutter(?:s|ed|ing)?|wip(?:e|es|ed|ing)|"
    r"rub(?:s|bed|bing)?|snap(?:s|ped|ping)?|roll(?:s|ed|ing)?|"
    r"walk(?:s|ed|ing)?|step(?:s|ped|ping)?|sit(?:s|ting)?|"
    r"stand(?:s|ing)?|ris(?:e|es|ing)|fall(?:s|ing)?|"
    r"drop(?:s|ped|ping)?|lift(?:s|ed|ing)?|rais(?:e|es|ed|ing)|"
    r"lower(?:s|ed|ing)?|reach(?:es|ed|ing)?|gestur(?:e|es|ed|ing)|"
    r"point(?:s|ed|ing)?|wav(?:e|es|ed|ing)|shrug(?:s|ged|ging)?|"
    r"wink(?:s|ed|ing)?|blink(?:s|ed|ing)?|star(?:e|es|ed|ing)|"
    r"gaz(?:e|es|ed|ing)|peer(?:s|ed|ing)?|circl(?:e|es|ed|ing)|"
    r"swirl(?:s|ed|ing)?|fix(?:es|ed|ing)?|slap(?:s|ped|ping)?|"
    r"cock(?:s|ed|ing)?|crook(?:s|ed|ing)?|arch(?:es|ed|ing)?|"
    r"curv(?:e|es|ed|ing)?|clap(?:s|ped|ping)?|hover(?:s|ed|ing)?|"
    r"twirl(?:s|ed|ing)?|stretch(?:es|ed|ing)?|brushes?|brushed|brushing|"
    r"trac(?:e|es|ed|ing)|trail(?:s|ed|ing)?|hooks?|hooked|hooking|"
    r"twitch(?:es|ed|ing)?|jerk(?:s|ed|ing)?"
)

_STAGE_NOUN_SUBJ = (
    r"voice|smile|grin|eyes?|hands?|fingers?|nails?|lips?|jaw|"
    r"shoulders?|chin|hips?|thigh|head"
)


def _clean_dialogue_payload(text: str) -> "str | None":
    """Strip stage directions / action narration from a raw agent dialogue
    payload. Returns the spoken-words-only text, or None if the entire
    payload was stage direction (caller should drop the block).
    """
    if not text:
        return None
    t = text.strip()
    if not t:
        return None

    # ── Pass 1: leading first-person action prefix followed by an
    # inner-single-quoted dialogue block — keep everything after the
    # inner-single-open. Require WHITESPACE-OR-PUNCT before the inner
    # curly-single so contractions ("I don't know") don't trigger this
    # path (the apostrophe in "don't" shares the same character).
    #   "I lean out the window. 'Catnip, you're ...'"  →  "Catnip, you're ..."
    m = re.match(
        r"^(?:I|My|Maybe\s+I)\b[^\u2018']{1,400}?[\s.,!?;:][\u2018'](.*)$",
        t, re.DOTALL,
    )
    if m:
        rest = m.group(1).strip()
        # strip a trailing inner-single-close if it's the very last char
        # (no letter immediately before it — that would be a contraction)
        rest = re.sub(r"(?<!\w)[\u2019'](?=\s*$)|[\u2019']\s*$", "", rest).strip()
        t = rest

    # ── Pass 2: strip inner-single-quoted stage-direction inserts.
    #   "...claws.' Grins under the mask. 'Still..."
    #   "...his.' takes a drag, watching Wade '...habits..."
    t = re.sub(
        r"[\u2018']\s*(?:" + _STAGE_VERBS + r")\b[^\u2018\u2019']{0,300}?"
        r"[\u2019']",
        " ",
        t, flags=re.IGNORECASE,
    )

    # ── Pass 3: split into sentences, drop pure-stage-direction sentences.
    sentences = re.split(r"(?<=[.!?\u2026])\s+", t)
    kept: list[str] = []
    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue
        # First-person possessive body-part as subject is intrinsically
        # stage direction — characters don't *say* "My hands find the edge."
        # Drop the whole sentence regardless of verb.
        if re.match(
            r"^(?:My|His|Her)\s+(?:" + _STAGE_NOUN_SUBJ + r")\b",
            s_strip, re.IGNORECASE,
        ):
            continue
        # First-person action: "I lean back...", "Maybe I lean in...",
        # "I let...", "I look at them now", "I find the edge".
        if re.match(
            r"^(?:Maybe\s+)?I\s+(?:" + _STAGE_VERBS
            + r"|let|tap|look|find|watch|feel|catch)\b",
            s_strip, re.IGNORECASE,
        ):
            continue
        # Bare lowercase action: "slow clap", "clears throat", "grins"
        if (
            re.match(r"^(?:" + _STAGE_VERBS + r")\b[^.!?]{0,40}\.?$",
                     s_strip, re.IGNORECASE)
            and len(s_strip.split()) <= 5
        ):
            continue
        # Bare lowercase fragment with no capital letter and no sentence
        # structure — e.g. "slow clap", "soft sigh", "slow clap,".
        # Drop only if short, lowercase, no real sentence punctuation.
        if (
            len(s_strip.split()) <= 4
            and s_strip == s_strip.lower()
            and not re.search(r"[.!?\u2026]", s_strip)
            and re.match(r"^[a-z][a-z,\s\-']+$", s_strip)
        ):
            continue
        kept.append(s_strip)

    if not kept:
        return None
    cleaned = " ".join(kept).strip()

    # ── Pass 4: strip mid-sentence stage-direction phrases.
    #   "...Tiger! clears throat Felicia, articulate..."
    cleaned = re.sub(
        r"\s+\b(?:" + _STAGE_VERBS + r")\s+(?:throat|head|shoulders?|hands?|"
        r"his|her|toward|back|away|under|over)\b[^.,!?]*",
        " ",
        cleaned, flags=re.IGNORECASE,
    )

    # ── Pass 5: drop orphan inner curly-single-quote pairs left over.
    # CRITICAL: do NOT strip a curly single that is between two letters
    # (e.g. apostrophe in "you're", "I'm", "don't"). Only strip when
    # the curly single is at a word boundary on at least one side.
    cleaned = re.sub(r"[\u2018\u2019]\s+[\u2018\u2019]", "", cleaned)
    cleaned = re.sub(r"(?<=\s)[\u2018\u2019](?=\s)", "", cleaned)
    # Strip a LEADING curly-single only if it has no matching close
    # later in the cleaned text (otherwise it's a legitimate sub-quote
    # opener like ‘Interesting’).
    if re.match(r"^[\u2018\u2019]", cleaned):
        rest = cleaned[1:]
        if not re.search(r"[\u2018\u2019]", rest):
            cleaned = rest.lstrip()
    # Strip a TRAILING curly-single only if it has no matching open
    # earlier in the cleaned text.
    if re.search(r"[\u2018\u2019]\s*$", cleaned):
        head = re.sub(r"[\u2018\u2019]\s*$", "", cleaned)
        if not re.search(r"[\u2018\u2019]", head):
            cleaned = head.rstrip()

    # ── Pass 5b: stitch dangling punctuation left over from inner-strip.
    # e.g. "just the faintest ." → "just the faintest."
    cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)
    # Drop orphan single-punctuation tokens between words ("word . word").
    cleaned = re.sub(r"(?<=\w)\s+\.\s+(?=[A-Z])", ". ", cleaned)
    # Strip a leading stranded punctuation token: ". The game..."
    cleaned = re.sub(r"^[.,;:]\s+", "", cleaned)

    # ── Pass 6: collapse whitespace.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None


_PIP_WORDS_RX = (
    r"Time|Space|Reality|There|Here|Listen|Pressure|Silence|Decision|"
    r"Focus|Shifts|Shift|Impact|Late|Motion|Personal|Momentum|Control|"
    r"Reclaimed|Now|Wait|Pause|Breath|Still|Stillness|Quiet|Calm"
)


def _strip_leading_pips(text: str) -> str:
    """Strip leading agent-emitted state-marker pips fused to the start
    of a narrator paragraph: 'Time. The glow...' -> 'The glow...'
    Repeats so 'Time. Motion. The glow...' collapses fully.
    """
    out = text.lstrip()
    while True:
        m = re.match(
            r"^(?:" + _PIP_WORDS_RX + r")\.\s+(?=[A-Z])",
            out,
        )
        if not m:
            break
        out = out[m.end():]
    return out


def _is_bare_pip_paragraph(p: str) -> bool:
    """Detect agent-emitted state-marker pips that leaked into narrator
    prose: single-word or 2-3 word capitalized abstract nouns like
    "Time.", "Listen.", "Pressure.", "Control. Reclaimed.", "Silence,
    shaped by sound."
    Real prose paragraphs are much longer; pips are <= 4 words and
    consist of capitalized abstract-noun tokens.
    """
    s = p.strip().rstrip(".")
    if not s:
        return False
    # Reject anything wrapped in quotes (dialogue), starts with lowercase,
    # contains commas with sentence-like content, or is long.
    if s.startswith("\u201c") or s.startswith('"'):
        return False
    if len(s) > 60:
        return False
    # Tokens split on period, comma, semicolon
    tokens = re.split(r"[.,;:]\s*", s)
    tokens = [t.strip() for t in tokens if t.strip()]
    if not tokens or len(tokens) > 4:
        return False
    PIP_WORDS = {
        "time", "space", "reality", "there", "here", "listen",
        "pressure", "silence", "decision", "focus", "shifts",
        "impact", "late", "motion", "personal", "momentum",
        "control", "reclaimed", "now", "wait", "pause", "breath",
        "still", "stillness", "quiet", "calm",
    }
    for tok in tokens:
        words = tok.split()
        if len(words) > 3:
            return False
        for w in words:
            base = w.strip("\u201c\u201d\u2018\u2019\"'").lower()
            if base not in PIP_WORDS:
                return False
    return True


_SPEAKER_FINGERPRINTS = {
    "wade_wilson": [
        "tiger", "spidey", "kitten", "sweetheart", "katana",
        "tequila", "deadpool", "sugar", "honey", "babe",
        "spandex", "merc", "chimichang", "spider-mouse",
        "spider-bear", "sweet cheeks", "tiger!", "darling",
    ],
    "felicia_hardy": [
        "tiger", "spider", "spidey", "darling", "catnip",
        "kitty", "claws", "purr", "noir", "diamond",
        "feline", "cat", "stake", "stalking",
    ],
    "peter_parker": [
        "wade,", "felicia,", "web-shoot", "web shoot",
        "mary-jane", "queens", "responsibility", "spider-",
        "aunt may", "j. jonah",
    ],
}


def _strip_inner_singles(text: str) -> str:
    """Remove ‘…’ inner sub-quoted spans (reported speech) before doing
    vocative/self-address detection — characters often quote each other
    saying "Wade," or "Felicia," and that must not count as the outer
    speaker addressing them."""
    return re.sub(r"\u2018[^\u2019]{0,400}\u2019", "", text)


def _infer_speaker(text: str, prev_speaker: str | None,
                   recent_speakers: list[str]) -> str | None:
    """Guess the speaker of an untagged dialogue paragraph using
    fingerprint keywords + simple alternation. Returns a roster key
    ('felicia_hardy', 'wade_wilson', 'peter_parker') or None when no
    confident guess can be made.
    """
    # Use a vocative-check view that excludes inner sub-quotes
    # (reported speech), but use the full text for keyword scoring.
    t = text.lower()
    t_voc = _strip_inner_singles(t)
    scores: dict[str, int] = {k: 0 for k in _SPEAKER_FINGERPRINTS}
    for key, marks in _SPEAKER_FINGERPRINTS.items():
        for mk in marks:
            if mk in t:
                scores[key] += 1
    # Vocative-as-strong-negative: a speaker addressing X by name
    # ("Wade, buddy,…", "Felicia!") cannot themselves be X. Heavier
    # penalty than the generic self-mention rule below, because
    # vocative form is unambiguous second-person address. Uses the
    # inner-single-stripped view so reported speech ("‘Wade, I have
    # to live here.’" inside a Wade story) doesn't count.
    if re.search(r"\bwade[,!\?]", t_voc):
        scores["wade_wilson"] -= 5
    if re.search(r"\bfelicia[,!\?]", t_voc):
        scores["felicia_hardy"] -= 5
    if re.search(r"\b(peter|parker|spidey|spider-?man)[,!\?]", t_voc):
        scores["peter_parker"] -= 5
    # Self-reference penalty: a speaker rarely says their own name
    # in non-vocative position (story reference, third-person quip).
    if "wade" in t_voc and not re.search(r"\bwade[,!\?]", t_voc):
        scores["wade_wilson"] -= 2
    if "felicia" in t_voc and not re.search(r"\bfelicia[,!\?]", t_voc):
        scores["felicia_hardy"] -= 2
    if ("peter" in t_voc or "parker" in t_voc) and not re.search(
            r"\b(peter|parker)[,!\?]", t_voc):
        scores["peter_parker"] -= 2
    # Alternation: prefer NOT the previous speaker.
    if prev_speaker:
        scores[prev_speaker] = scores.get(prev_speaker, 0) - 1
    # Pick the highest positive score.
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if ranked and ranked[0][1] > 0 and (
        len(ranked) == 1 or ranked[0][1] > ranked[1][1]
    ):
        return ranked[0][0]
    # Fall back to non-previous-speaker alternation.
    if prev_speaker:
        alternatives = [k for k in scores.keys() if k != prev_speaker]
        if len(alternatives) == 1:
            return alternatives[0]
    return None


def _first_name_for_tag(key: str) -> str:
    return {
        "felicia_hardy": "Felicia",
        "wade_wilson": "Wade",
        "peter_parker": "Peter",
        "mary_jane_watson": "Mary-Jane",
        "matt_murdock": "Matt",
    }.get(key, key.split("_")[0].title())


def clean_existing_prose(prose: str) -> str:
    """Apply dialogue cleanup to already-assembled prose. Operates on
    paragraphs wrapped in curly-double-quotes (the canonical dialogue
    form emitted by scripts_to_prose). Used to remediate shipped
    artifacts without re-cooking, and also re-applied as a post-pass
    inside scripts_to_prose so future cooks ship clean prose.
    """
    # ── Preserve UATU_OPENING_LITANY / UATU_CLOSING_OATH verbatim.
    # The litany legitimately begins with bare pip words ("Time.",
    # "Space.", "Reality.") which would otherwise be stripped by the
    # narrator-state-marker filter. Carve those regions out before
    # cleaning, then splice them back at the end.
    from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH  # noqa: E402
    _LIT = UATU_OPENING_LITANY.strip()
    _OATH = UATU_CLOSING_OATH.strip()
    _LIT_TOKEN = "\x00LITANY_PLACEHOLDER\x00"
    _OATH_TOKEN = "\x00OATH_PLACEHOLDER\x00"
    if _LIT and _LIT in prose:
        prose = prose.replace(_LIT, _LIT_TOKEN)
    if _OATH and _OATH in prose:
        prose = prose.replace(_OATH, _OATH_TOKEN)
    out_paras: list[str] = []
    last_speaker: str | None = None
    recent: list[str] = []
    for para in prose.split("\n\n"):
        p = para.strip()
        if not p:
            out_paras.append("")
            continue
        # Preserve sentinel paragraphs verbatim.
        if p in (_LIT_TOKEN, _OATH_TOKEN):
            out_paras.append(p)
            continue
        # ── Drop bare-pip narrator state markers.
        if _is_bare_pip_paragraph(p):
            continue
        # ── If a narrator paragraph starts with fused pips ("Time. The..."),
        # strip them and continue with the substantive prose.
        if not p.startswith("\u201c"):
            stripped = _strip_leading_pips(p)
            if stripped != p:
                p = stripped
                if not p.strip():
                    continue
        m = re.match(
            r"^\u201c(.+?)\u201d(\s+([A-Z][a-zA-Z\-]+)\s+(said|asked)\.)?\s*$",
            p, re.DOTALL,
        )
        if not m:
            # Non-dialogue paragraph — keep but reset last_speaker.
            out_paras.append(p)
            if not p.startswith("*"):
                last_speaker = None
            continue
        inner = m.group(1)
        tag = m.group(2) or ""
        tag_name = (m.group(3) or "").lower()
        # ── Normalize NESTED outer-quote pairs to single-quote sub-quotes.
        # Agents sometimes emit “…” inside an outer “…” dialogue paragraph.
        # That's broken outer-balance and unreadable. Downgrade interior
        # curly-doubles to curly-singles before any further cleaning.
        inner = inner.replace("\u201c", "\u2018").replace("\u201d", "\u2019")
        # Also normalize stray straight double-quotes the same way.
        inner = re.sub(r'(?<![A-Za-z])"|"(?![A-Za-z])', "\u2019", inner)
        cleaned = _clean_dialogue_payload(inner)
        if cleaned is None:
            continue  # entire payload was stage direction — drop paragraph
        # ── Repair Pass-1 fragment-residue: "Felicia said." paragraphs
        # where the cleaner left orphan letter fragments. e.g. leftover
        # "s a sharper edge in her eyes" from stripped first-person verb.
        cleaned = re.sub(
            r"\.\s+s\s+a\s+(sharper|softer|harder|warmer|colder)\s+[^.]+\.?",
            ".", cleaned,
        )
        # ── L303-style: "Then, as if [stage dir], I [verb] the glass."
        # Drop sentences that match the pattern.
        sents = re.split(r"(?<=[.!?\u2026])\s+", cleaned)
        keep = []
        for sent in sents:
            if re.match(
                r"^(Then,?\s+)?as if[^.]{1,200}\bI\s+(pick|swirl|lift|raise|"
                r"hover|trail|brush|stretch|let|tap|drum|tilt|glance|lean|"
                r"breathe|exhale|inhale|nod|shake|sigh|smile|smirk)\b",
                sent, re.IGNORECASE,
            ):
                continue
            # "I pick up my glass again" style outside as-if framing too
            if re.match(
                r"^I\s+(pick|swirl|lift|hover|trail|brush|stretch|let|tap|"
                r"drum|tilt|glance|lean)\s+(up|down|at|the|my|a|her|his)",
                sent, re.IGNORECASE,
            ):
                continue
            # "The faintest smirk, like I'm already steps ahead." (stage dir)
            if re.match(
                r"^The\s+faintest\s+(smirk|grin|smile|frown|laugh)",
                sent, re.IGNORECASE,
            ):
                continue
            keep.append(sent)
        cleaned = " ".join(keep).strip()
        if not cleaned:
            continue
        # ── Fix truncated trailing fragments like "Call it..," → "Call it..."
        cleaned = re.sub(r"\.\.+,\s*$", "\u2026", cleaned)
        cleaned = re.sub(r",\s*$", "", cleaned)
        # ── Drop orphan trailing "Second/Third/Next clue—," style fragments:
        # an incomplete enumeration item that the agent cut off mid-thought.
        cleaned = re.sub(
            r"\s+(?:Second|Third|Next|Final|Last)\s+clue[:\s—\-,]*$",
            "", cleaned, flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*[—\-]\s*,?\s*$", "\u2026", cleaned)
        # ── Determine the speaker.
        if tag_name in ("felicia", "wade", "peter"):
            speaker = {"felicia": "felicia_hardy",
                       "wade": "wade_wilson",
                       "peter": "peter_parker"}[tag_name]
            # SELF-ADDRESS SANITY: if the cooked tag claims X said, but the
            # body addresses X in vocative form ("Wade, buddy,…"), that's a
            # speaker mis-attribution from the swarm. Re-infer instead.
            # Strip inner-single-quoted reported speech first so quoting
            # someone else saying "Wade," doesn't trip the check.
            voc_patterns = {
                "felicia_hardy": r"\bfelicia[,!\?]",
                "wade_wilson":   r"\bwade[,!\?]",
                "peter_parker":  r"\b(peter|parker)[,!\?]",
            }
            voc_view = _strip_inner_singles(cleaned)
            if re.search(voc_patterns[speaker], voc_view, re.IGNORECASE):
                reinferred = _infer_speaker(cleaned, last_speaker, recent)
                if reinferred and reinferred != speaker:
                    speaker = reinferred
        else:
            speaker = _infer_speaker(cleaned, last_speaker, recent)
        # ── Final ending punctuation + tag re-emission.
        if cleaned[-1] not in ".,!?\u2026":
            cleaned = cleaned + "."
        # Always re-emit a speaker tag (drop "same-speaker omits tag" rule).
        if speaker:
            verb = "asked" if cleaned.rstrip().endswith("?") else "said"
            if cleaned[-1] in ".!?\u2026":
                inner_for_tag = cleaned[:-1] + "," if cleaned[-1] == "." else cleaned
            else:
                inner_for_tag = cleaned + ","
            tag_str = f" {_first_name_for_tag(speaker)} {verb}."
            out_paras.append(f"\u201c{inner_for_tag}\u201d{tag_str}")
            last_speaker = speaker
            recent.append(speaker)
            if len(recent) > 6:
                recent.pop(0)
        else:
            # No confident speaker — leave punctuation as-is, no tag.
            out_paras.append(f"\u201c{cleaned}\u201d")
            last_speaker = None
    out = "\n\n".join(out_paras)
    # Collapse runs of blank paragraphs left behind by dropped pips.
    out = re.sub(r"\n{3,}", "\n\n", out)
    # Restore litany/oath verbatim from sentinels.
    out = out.replace(_LIT_TOKEN, _LIT).replace(_OATH_TOKEN, _OATH)
    if not out.endswith("\n"):
        out += "\n"
    return out


def scripts_to_prose(scripts: list, plan: EpisodePlan) -> str:
    from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH

    # APT-09 normalization pass: strip any narrator blocks that already
    # carry the Uatu opening litany or closing oath so we don't double-
    # bookend. Detect via stable anchor substrings from the canonical
    # strings (we never mutate the canonical litany/oath themselves).
    # Idempotent: a second call sees the same already-clean input.
    _OPEN_ANCHORS = (
        "I am the Watcher. I am your guide through these vast new realities.",
        "Time.\n\nSpace.\n\nReality.",
    )
    _CLOSE_ANCHORS = (
        "For I am the Watcher.",
        "I have watched. I will continue to watch.",
    )

    def _is_bookend_narration(block) -> bool:
        if getattr(block, "type", None) != "narrator":
            return False
        txt = getattr(block, "text", "") or ""
        return (
            any(a in txt for a in _OPEN_ANCHORS)
            or any(a in txt for a in _CLOSE_ANCHORS)
        )

    cleaned_scripts = []
    for s in scripts:
        kept_blocks = [b for b in s.blocks if not _is_bookend_narration(b)]
        if len(kept_blocks) != len(s.blocks):
            s_clean = copy.copy(s)
            s_clean.blocks = kept_blocks
            cleaned_scripts.append(s_clean)
        else:
            cleaned_scripts.append(s)
    scripts = cleaned_scripts

    paragraphs: list[str] = []
    paragraphs.append(f"Episode {plan.number}: {plan.title}")
    paragraphs.append("Grizzly Knights")
    paragraphs.append(plan.logline)

    # Uatu opens the show
    paragraphs.append("* * *")
    paragraphs.append(UATU_OPENING_LITANY.strip())

    last_speaker: str | None = None

    for s in scripts:
        paragraphs.append("* * *")
        last_speaker = None

        for b in s.blocks:
            if b.type == "narrator":
                text = re.sub(r"\*+", "", b.text).strip()
                # Strip any wrapping quotes the LLM added around the narration —
                # straight ", curly " ", or angle « ». Iterate in case nested.
                for _ in range(3):
                    stripped = re.sub(
                        r'^[\s]*["\u201c\u201d\u00ab\u00bb]+\s*', '', text)
                    stripped = re.sub(
                        r'\s*["\u201c\u201d\u00ab\u00bb]+[\s]*$', '', stripped)
                    if stripped == text:
                        break
                    text = stripped
                text = text.strip()
                # Drop bare-pip state markers ("Time.", "Listen.", etc.)
                if text and _is_bare_pip_paragraph(text):
                    text = ""
                # Strip fused leading pips ("Time. The glow ..." → "The glow ...")
                if text:
                    text = _strip_leading_pips(text)
                if text:
                    paragraphs.append(text)
                last_speaker = None

            elif b.type == "dialogue":
                text = re.sub(r"\*+", "", b.text).strip()
                text = re.sub(r"\s*\([^)]{1,80}\)\s*", " ", text).strip()
                if not text:
                    continue
                # Strip stage directions / first-person action narration
                # from the dialogue payload. May return None if the entire
                # payload was stage direction — drop the block.
                cleaned = _clean_dialogue_payload(text)
                if not cleaned:
                    continue
                text = cleaned
                if text[-1] not in ".!?\u2026":
                    text = text + "."
                quoted = f"\u201c{text}\u201d"
                key = b.character or ""
                short = _short_first(_name_upper_from_key(key)) if key else "they"
                # Always emit a speaker tag so every dialogue paragraph in
                # the prose layer (and every line in the TTS sidecar) is
                # unambiguous. Same-speaker continuation lines used to be
                # untagged; that left readers and TTS guessing.
                verb = "asked" if text.rstrip().endswith("?") else "said"
                paragraphs.append(f"{quoted} {short} {verb}.")
                last_speaker = key

    # Uatu closes the show
    paragraphs.append("* * *")
    paragraphs.append(UATU_CLOSING_OATH.strip())

    # Fix period-before-tag → comma
    out = "\n\n".join(paragraphs) + "\n"
    out = re.sub(
        r"(\u201c[^\u201d]+?)\.(\u201d)\s+([A-Z][a-zA-Z]+)\s+(said|asked)\.",
        r"\1,\2 \3 \4.",
        out,
    )
    out = _normalize_inner_quotes(out)
    # Belt-and-suspenders: run the prose-layer cleaner once more on the
    # fully-assembled text to catch anything the per-block cleaner missed
    # (e.g. cross-paragraph artifacts).
    out = clean_existing_prose(out)
    return out


# ─── TTS sidecar ──────────────────────────────────────────────────────────────

_DIALOGUE_TAG_RE = re.compile(
    r'^\u201c(.+?)[,\.\?!\u2026]?\u201d\s+([A-Z][a-zA-Z\-]+)\s+(said|asked)\.\s*$',
    re.DOTALL,
)
_BARE_QUOTE_RE = re.compile(r'^\u201c(.+?)\u201d\.?\s*$', re.DOTALL)


def _normalize_inner_quotes(prose: str) -> str:
    """Inside an outer curly-quoted dialogue span, swap any inner straight
    double-quotes to single curly quotes so TTS engines see unambiguous
    speech boundaries. Idempotent."""
    def _swap(m: re.Match) -> str:
        inner = m.group(1)
        # alternate ' ‘ / ’ for opening/closing inner straight pairs
        out_chars: list[str] = []
        open_next = True
        for ch in inner:
            if ch == '"':
                out_chars.append("\u2018" if open_next else "\u2019")
                open_next = not open_next
            else:
                out_chars.append(ch)
        return "\u201c" + "".join(out_chars) + "\u201d"
    return re.sub(r"\u201c([^\u201c\u201d]*)\u201d", _swap, prose)


def prose_to_tts_script(prose: str) -> str:
    """Convert finished prose into a speaker-tagged TTS sidecar.

    Format (one block per line):
      [NARRATOR] text…
      [FELICIA] "dialogue text"
      [SCENE BREAK]

    Bare quote paragraphs (no `X said.` tag) inherit the last speaker.
    Multi-line paragraphs are collapsed to a single line so every output
    line begins with a `[TAG]` marker — TTS engines expect one tagged
    utterance per line.
    """
    lines_out: list[str] = []
    last_speaker = "NARRATOR"
    for para in prose.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if p == "* * *":
            lines_out.append("[SCENE BREAK]")
            last_speaker = "NARRATOR"
            continue
        # Collapse any internal newlines (multi-line narrator paragraphs)
        # to a single space so the tagged line is one utterance.
        p_flat = re.sub(r"\s*\n\s*", " ", p).strip()
        m = _DIALOGUE_TAG_RE.match(p_flat)
        if m:
            body, name, _verb = m.group(1).strip(), m.group(2).upper(), m.group(3)
            lines_out.append(f'[{name}] "{body}"')
            last_speaker = name
            continue
        m = _BARE_QUOTE_RE.match(p_flat)
        if m:
            body = m.group(1).strip()
            lines_out.append(f'[{last_speaker}] "{body}"')
            continue
        # narrator prose (or anything we don't recognize)
        lines_out.append(f"[NARRATOR] {p_flat}")
        last_speaker = "NARRATOR"
    return "\n".join(lines_out) + "\n"


# ─── Main ─────────────────────────────────────────────────────────────────────

def export_one(plan: EpisodePlan, model) -> Path | None:
    console.rule(f"[bold cyan]Episode {plan.number} — {plan.title}[/bold cyan]")
    console.print(f"[dim]Cast: {', '.join(plan.cast)}  |  Scenes: {len(plan.scenes)}[/dim]\n")

    def on_scene(script):
        ndlg = sum(1 for b in script.blocks if b.type == "dialogue")
        nnar = sum(1 for b in script.blocks if b.type == "narrator")
        console.print(
            f"  [dim]Act {script.act} · Scene {script.scene_number} — "
            f"{script.location[:48]}... — {ndlg} dialogue / {nnar} narration[/dim]"
        )

    try:
        scripts = run_episode_sync(plan, model, on_scene=on_scene)
    except Exception as e:
        console.print(f"[red]Episode {plan.number} failed: {type(e).__name__}: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

    prose = scripts_to_prose(scripts, plan)
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / f"{plan.number:02d} - {plan.title}.txt"
    out.write_text(prose)
    words = len(prose.split())
    kb = out.stat().st_size / 1024
    console.print(f"  [green]→ {out.name}[/green] [dim]({words} words, {kb:.1f} KB)[/dim]")

    # Auto-chronicle: Uatu reads the episode and updates persistent world state
    try:
        from engine.uatu import chronicle_episode
        meta = {
            "number":  plan.number,
            "title":   plan.title,
            "cast":    plan.cast,
            "logline": getattr(plan, "logline", ""),
        }
        delta = chronicle_episode(out, meta)
        n_chars = len(delta.get("characters") or {})
        n_rels  = len(delta.get("relationships") or {})
        n_facts = len(delta.get("world_facts") or [])
        console.print(
            f"  [dim cyan]chronicle updated — {n_chars} chars, "
            f"{n_rels} rels, {n_facts} facts[/dim cyan]"
        )
    except Exception as e:
        console.print(f"  [yellow]chronicle update failed: {type(e).__name__}: {e}[/yellow]")

    return out


def main():
    only = None
    if len(sys.argv) > 1:
        try:
            only = int(sys.argv[1])
        except ValueError:
            pass

    model = build_model("gpt-4o")
    written: list[Path] = []
    for plan in EPISODES:
        if only is not None and plan.number != only:
            continue
        p = export_one(plan, model)
        if p:
            written.append(p)

    console.print()
    console.rule("[green]Export complete[/green]")
    console.print(Panel(
        "\n".join(f"• {p.name}" for p in written) or "[red]No files produced[/red]",
        title=f"Files in {OUTPUT_DIR}", border_style="green", box=box.ROUNDED
    ))


if __name__ == "__main__":
    main()

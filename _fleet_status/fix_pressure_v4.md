# fix_pressure_v4 — full-episode floor follow-up

## What changed after the 9-minute proof

- `cook_ep01_pressure_proof_v3.py` now has a coded full-episode floor: at least 6 scenes and 3200 final words before a clean close can be considered.
- The driver now treats `evidence_substring` as non-terminal pressure movement. It can close a scene, but it no longer resolves the episode pressure. Terminal pressure resolution is limited to `bring_in_plus_action`, `pending_subject_dialogue`, or `named_refusal`.
- `engine/agency_engine.py` now carries summon-pending even when a scene also has non-terminal evidence movement.
- `_line_is_tool_artifact()` now rejects lowercase/protocol tool-call leaks such as `take_action(...)` and `<<TOOL:TakeAction>>...`.
- `tests/swarm_04_no_tool_error_in_transcript.py` now covers lowercase/protocol tool-call leakage.

## Validation run

- Syntax: `python -m py_compile cook_ep01_pressure_proof_v3.py engine/agency_engine.py engine/uatu.py` — PASS.
- Targeted checks run after filter/gate fixes: `swarm_04`, `pressure_10`, `pressure_11`, `pressure_12`, `pressure_13` — PASS.
- Live cook run: `_fleet_status/_v3_full_episode_cook_log_2.txt`.

## Shipped episode

- Episode: `episodes_text/_pressure_proof_v3/01 - Daydrunk, Deadly, and Devoted.txt`
- Audit: `episodes_text/_pressure_proof_v3/01 - audit.txt`
- Cook log: `_fleet_status/_v3_full_episode_cook_log_2.txt`

## Verdict against criteria

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| (a) Scene 1 cast exactly `{felicia_hardy, wade_wilson}` | PASS | Cook log: `run_scene(S1) cast=['felicia_hardy', 'wade_wilson']`. Peter appears only after scene-1 `BringInCharacter`. |
| (b) Peter summoned and takes an on-stage turn, or named-refused | PASS | Audit S1: `bring_in key='peter_parker'` with `is_pressure_progress=False`; audit S2: pressure resolves as `pending_subject_dialogue`; episode lines 73 and 81 are Peter on-stage dialogue. |
| (c) Episode runs >= 2 scenes | PASS | Audit: `# scenes_run: 7`; full floor also met: `# final_word_count: 3831`, `# estimated_audio_minutes: 25.5`. |
| (d) Episode closes cleanly, not forced | FAIL — FORCED-CLOSE-CAP | Audit S7: `FORCED-CLOSE`; audit corrected header: `# any_scene_forced_close: True`, `# clean_episode_close: False`, `# forced_close_episode: True`. |
| (e) Zero tool-artifact strings in dialogue | PASS | Search of cooked episode text found no `ERROR:`, `send_message`, `take_action`, `BringInCharacter`, `TakeAction`, `tool_use`, or `function_call` strings. Audit records dropped tool artifacts, but they did not reach dialogue. |
| (f) Cast = premise-explicit + BringInCharacter arrivals only; zero phantoms | PASS | Scene summaries contain only Felicia/Wade/Peter; S1 chronicle contains Peter `BringInCharacter`; no Johnny/MJ stage cast in final shipped episode. |
| (g) Narrator MJ references render `Mary-Jane` | PASS | Any MJ/Mary-Jane references in text are hyphenated as `Mary-Jane`; no `Mary Jane` miss-render found in cooked episode. |

## Final verdict

FORCED-CLOSE-CAP. The pressure and runtime gates now work, and the file is a full-length shipped artifact, but it is **not** a clean pass because scene 7 hit the scene turn cap.

## First 80 lines of cooked episode

```text
1. Episode 1: Daydrunk, Deadly, and Devoted
2. 
3. Grizzly Knights
4. 
5. Felicia Hardy and Wade Wilson hatch a reckless, debauched plan to loosen up Peter Parker, risking consequences for everyone involved.
6. 
7. * * *
8. 
9. Time.
10. 
11. Space.
12. 
13. Reality.
14. 
15. It is more than a linear path. It is a prism of endless possibility,
16. where a single choice can branch out into infinite realities, creating
17. alternate worlds from the ones you know.
18. 
19. In every one of those realities, the same people live with the same
20. minds. The same hungers. The same scars. The same compensatory
21. mechanisms they would never name out loud.
22. 
23. I am the Watcher. I am your guide through these vast new realities.
24. 
25. Follow me, and ponder the question — not "what if?"
26. 
27. The question, in this universe, is simpler.
28. 
29. What do they do when they think the mic is off?
30. 
31. These are their stories.
32. 
33. * * *
34. 
35. On a world I have watched for longer than its inhabitants have had a written language, there is a booth. Cream vinyl, two cracks repaired with brown duct tape. A plate of chicken madeira cooling untouched, cheesecake half-finished. Felicia's margarita is salt-rimmed; Wade's is sugar, fourth of the night. The vape pen rests between them, cherry-scented vapor ghosting into the air. They are here, but neither is really seated.
36. 
37. “Can't decide if you're about to say something profound, or if you're just picturing Peter in tights again. Let's hear it, Wade—what's on your mind?” Felicia asked.
38. 
39. “Alright, fine, you want the unedited 4K Netflix version? Peter, he’s—he's the itch I can't scratch and the scratch that makes the itch worse. Equal parts knight in shiny spandex and that frustrating squeaky wheel that keeps rolling into my headspace. Complicated? Yeah. But who isn’t? What do you want me to say, Felicia? That he's it? That he's not? That I'm just spinning circles trying to translate 'love' and 'lust' out of a language his guilt won't speak?” Wade asked.
40. 
41. “Alright, so we're actually doing this. Strategy time. We get Peter cornered—physically and emotionally—not in that martyr-in-a-spandex way he loves to dodge us with. He doesn't get to flip away, and he doesn't get to crack a joke, either,” Felicia said.
42. 
43. “I think about him all the time, Felicia. And it’s not just the idiot-clown surface stuff. It’s the way he works himself to fucking dust, the way he does it all without turning into what the world keeps throwing at him. That... heart. It’s infuriating and beautiful, and it hooks me in ways even I can’t wriggle out of. So yeah, I love him. I just don’t know how he’d survive admitting he even likes me back,” Wade said.
44. 
45. “If you're taking the risk to open that door with him, I won't let you do it alone. We'll rip the web-bandaid off together, Wade. Peter's good at hiding, but we're better. I'll handle the soft spots he tries to slide through—emotionally or otherwise—and you keep it raw. It'll hurt like hell, but maybe that's the point. You in?” Felicia asked.
46. 
47. Resolve.
48. 
49. “You want answers? Fine, let’s stop rehearsing—he's on his way. Keep your claws sharp, Felicia. This just went from playful sparring to live combat,” Wade said.
50. 
51. Purpose.
52. 
53. “Well, Peter, looks like you’re caught in our web this time. Sit down. We need to have a word—and it’s not one you’re going to dodge,” Felicia said.
54. 
55. Time.
56. 
57. “Time to own it, Tiger. You're not spinning out of this one,” Felicia said.
58. 
59. “Hey, Pete. No jokes. Not here. I'm standing as raw as I get, man. So tell me, Spider-Hamlet—are we ever gonna stop soliloquizing around what this is, or do you still need another few years agonizing about people who give a damn? Talk to me. Not the mask. Me,” Wade said.
60. 
61. Stillness.
62. 
63. * * *
64. 
65. Time.
66. 
67. “Well, Spider—are we going to pretend you’re not enjoying this, or should I keep both hands right where they are?” Felicia asked.
68. 
69. “I'm gonna need you to rephrase that, sunshine. That sentence got caught in a blender, took a tequila shot, and then crossed the street without looking both ways. Are we talkin' about Felicia’s deadly posture and her particular brand of oh-shit-she-might-kill-me sexy, or did auto-correct try to assassinate you mid-thought? Help a regeneratin’ degenerate out here—what’s the vibe? Physical dance of violence? Sexy pinning match? Or a reminder that Felicia Hardy knows how to keep a guy on edge? Spill it,” Wade said.
70. 
71. “Alright, kiddos, let's play nice for Daddy Wade, hmm? Felicia, your claws are showing—sexy as hell, by the way—and Peter, you’ve got that tragic 'puppy about to run into traffic' look. Shall we all take a deep breath and remember we're one big dysfunctional comic book family?”
72. 
73. “You know, I really missed high school group projects. You two arguing over who ate the glue while the volcano's actively on fire is exactly the energy I needed today,” Peter said.
74. 
75. Felicia's nails bite into the vinyl seat, her shoulders locked sharp as blades. Wade’s bouncing stops mid-pattern, the grin arriving too quick, too wide—off-beat to the room. Peter’s hand slicing the air cuts the silence clean, like glass finally cracking under pressure.
76. 
77. “Wade, where’s that famous wit of yours? Or are you too dazzled by the view to keep up?” Felicia asked.
78. 
79. “C’mon, don’t leave me at first base like some forgotten prom date, Felicia. Claws in, claws out—it’s your move, kitty. Or are we all waiting for Prince Parker here to find his balls and say something heroic?” Wade asked.
80. 
```

## Full pressure-resolution log

```text
# Scene 1 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'address', 'key': 'felicia_hardy'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'Take a deep breath, rub the back of my neck, and look Felicia in the eyes.', 'consequence': "Explicit clarity on Wade's feelings toward Peter provided to Felicia.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 7, 'actor': 'wade_wilson', 'kind': 'bring_in', 'key': 'peter_parker', 'how': 'texted and reluctantly arrives, still suited up from patrol, stepping cautiously into the space.'}  →  is_pressure_progress=False
    entry {'turn': 7, 'actor': 'wade_wilson', 'kind': 'address', 'key': 'felicia_hardy'}  →  is_pressure_progress=False
    entry {'turn': 9, 'actor': 'felicia_hardy', 'kind': 'address', 'key': 'peter_parker'}  →  is_pressure_progress=False
    entry {'turn': 11, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'I step into Peter’s space, just a little too close, locking eyes and cutting off any escape. "Peter Parker, you’re the problem we’re not letting you squirm away from tonight."', 'consequence': 'Peter Parker is explicitly named as the target of the intervention, making it impossible for him to deflect this conversation to Spider-Man or anyone else.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 11, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'Step towards Peter, close enough that it’s unavoidable, and pull off my mask, baring everything.', 'consequence': '', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Unknown recipient agent 'Peter_Parker'. Available agents: Felicia_Hardy, Wade_Wilson, Uatu"}  →  is_pressure_progress=False
    => moved=True kind=evidence_substring summon_pending=peter_parker summon_landed=-

# Scene 2 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'address', 'key': 'peter_parker'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'Lean in between them, placing a hand on each of their thighs, close enough to feel the heat radiating off them.', 'consequence': 'Felicia asserts control over the dynamic between Peter and Wade, setting an intentionally provocative tone.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "steps directly between Felicia and Peter, placing a firm hand on each of their shoulders, like the world's most awkward, unlicensed couples' therapist.", 'consequence': 'Wade inserts himself into the tension, forcing both Felicia and Peter to react to him.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': "Let my fingers curl slightly against Peter's thigh, just enough for him to catch the intent, and then draw back as if the moment is inconsequential.", 'consequence': "Recalibrates the pressure, allowing Peter's sarcasm to land but keeping the tension in play.", 'tags': ['lines_crossed'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'address', 'key': 'wade_wilson'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "leans in toward Felicia with a shit-eating grin, practically goading her by whispering, 'Oh, you wanna tangle with *this* hot mess? Be my guest. But let's not leave 'ol Web-Head hanging in suspense, huh?'", 'consequence': "Wade forces Felicia's focus back to a choice—escalate with him or turn her play back to Peter directly.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    => moved=True kind=pending_subject_dialogue summon_pending=- summon_landed=-

# Scene 3 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'address', 'key': 'peter_parker'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'I pick up a tube of bright red lipstick, swivel it halfway out like some obscene magic trick, and hold it up between myself and Felicia, eyebrow wag watching her reaction.', 'consequence': 'Attempt to make Felicia visibly amused or playfully annoyed to heighten the scene tension.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': "I step into a perfect reflection in the floor-to-ceiling mirror, aligning my silhouette with Peter's in the glass with deliberate asymmetry—his tension visible, mine invisible—and I angle toward Wade as if considering whether or not to strike.", 'consequence': '', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'I step between Peter and Felicia, dramatically smear the red lipstick straight across the mouth of my mask, and strike a pose flamboyant enough to derail a train.', 'consequence': 'Break the escalating Peter-Felicia tension with loud and absurd distraction.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Missing required parameter 'recipient_agent' for tool send_message."}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Missing required parameter 'recipient_agent' for tool send_message."}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Missing required parameter 'recipient_agent' for tool send_message."}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Missing required parameter 'recipient_agent' for tool send_message."}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 4 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 17, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'grab Felicia’s cocktail glass from her hand mid-sentence and down it in one flaming gulp', 'consequence': 'Wade escalates from verbal to physical, forcing the room to either explode or recalibrate around his chaos.', 'tags': ['drinks', 'lines_crossed'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 5 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "snatch the cigarette from Felicia's hand, take a dramatic puff, and strike the most ridiculous noir pose possible.", 'consequence': 'cut through the silence by dragging them into my absurdity.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "toss the cigarette towards Peter with a grin and mimic Felicia’s tone, 'Careful, Tiger, don’t get burned.'", 'consequence': "mirror Peter's motion to pull everyone deeper into the tension.", 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': 'take_action({"action":"lean back against the far wall, arms crossed, watching the two spar, not wanting to get pulled into their orbit just yet"})'}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': 'take_action({"action":"push off the wall and close the space between me and Felicia, stepping into her gravity, my mouth tugging into a half-smirk like I\'m up for the game, even if I should know bette'}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 6 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'lean against the wall, arms crossed, thinking for a second before answering', 'consequence': '', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 9, 'actor': 'wade_wilson', 'kind': 'action', 'action': "I grab Peter's wrist, stepping into his space, pulling him close enough that the weight of whatever this 'Genesis' thing is feels a hell of a lot like gravity forcing the moment.", 'consequence': 'This crosses the line from banter into demanding Peter trust my involvement, breaking the hypothetical safety net of disassociation.', 'tags': ['drinks', 'lines_crossed'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 9, 'actor': 'peter_parker', 'kind': 'action', 'action': 'run a hand through my hair, trying to pace my response and not just fire back', 'consequence': '', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 7 pressure-resolution log
  pressure: peter_parker_outburst_prevention subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "slump back dramatically in my seat, pointing at the martini glass like it's the Rosetta Stone of bad decisions.", 'consequence': "Felicia is now invited to defend her drink choice or deflect Wade's commentary.", 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'address', 'key': 'felicia_hardy'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "lean forward on the table, elbows loose but eyes narrowing just slightly, the edges of the clown act fraying as I glance Felicia's way and try to prod something useful.", 'consequence': 'The shift in demeanor reminds Felicia that Wade picks his tension-sponging for a reason.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'push the martini glass center-table like it’s a peace offering or, y’know, bait for the tension god.', 'consequence': 'Martini glass becomes both a focus shift and a playful challenge to the room.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'tilt my head, flick my eyes to Felicia, then back to the glass, and sniff conspicuously at the untouched martini while gesturing to my chest like it’s the best-case landing pad for the potential havoc.', 'consequence': 'The exaggerated display both dares and charms, coaxing Felicia or anyone else to make a move or break the tension.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'raise the edge of my mask just to my nose for dramatic flair as I lean slightly closer to the middle of the table, like I’m silently daring Felicia to lay her cards down next.', 'consequence': 'The move presses Felicia towards committing to a chosen lane in the tension or humor dynamic at play.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'forced close at turn cap 20; state_change_occurred=True pressure_progress=False'}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-
```

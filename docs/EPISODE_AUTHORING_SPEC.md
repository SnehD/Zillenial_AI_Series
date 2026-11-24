# Episode authoring spec (Zillenial Talk: AI From Zero to FDE)

You write ONE `episodes/ep-NNN-<slug>/episode.json` per curriculum episode. Content is data only; never edit src/ renderer code.
Read first: `curriculum/curriculum.json` (your episodes, their prerequisites, `fv` flags), `episodes/ep-015-what-is-a-token/episode.json` (the quality reference), `docs/POSTING_COPY.md` (caption style), `src/visuals_generic.py` (visual vocabulary).
Validate every file: `"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" src\validate_episode.py <file>` (must print `ok`). Fix all ERRORs.

## Voice and craft (non-negotiable)
- Sneha, a techie friend: curious, warm, witty by recognition (never forced slang, never childish). Story-first: hook -> relatable problem -> small fictional situation -> analogy -> technical reveal -> real technical example -> "where the analogy breaks" -> memorable takeaway.
- Two layers: a non-technical viewer gets the intuition AND an engineer would call it fundamentally accurate. Accuracy beats virality.
- Analogy is a teaching device, not a definition: say the actual technology in correct terms, and state where the analogy breaks (scene or phrase). Fill `analogy`, `analogy_breaks`, `actual_tech`.
- Continuity: only use terms introduced in earlier episodes (see `prerequisites` and all lower-numbered episodes in curriculum.json) or explain them on the spot. List newly introduced terms in `terms_introduced`.
- Do not reuse the previous episode's analogy. Vary hooks; do not start every episode with the same question pattern.
- Recurring characters (Maya nontechnical, Alex developer, Riya product, Sam security, Nova a fictional AI assistant that is NOT Claude) are mentioned in narration only when useful. Never imply Nova is an Anthropic product.
- Narration 110-170 words total (~55-70s). Each phrase is one spoken sentence or two short ones, <= 22 words.
- Phrase 0 of scene 0 is ALWAYS a short greeting, e.g. "Hey techies! Sneha here from Zillenial Talk." (small wording variations OK, keep "Zillenial Talk"). The renderer appends "Season N, episode M." to it automatically, so DO NOT write the season/episode yourself. The hook goes in phrase 1.
- The last scene is `endcard` with a teaser for the next episode + a sign-off that includes "I'm Sneha, and this is Zillenial Talk." (rotate wording; no begging for follows; value-driven).
- `say` = pronunciation override for TTS (the voice is Windows Zira). Write "Zillennial" in `say`, "A.I." for AI, "L L M" for LLM, "A P I" for API, "rag" for RAG, "M C P" for MCP, "J son" for JSON, "Claude" is fine, "Nova" fine, "R L H F" etc. Keep `text` (the caption) normal.
- `hl` = words to highlight in captions; entries must appear in the phrase text (punctuation-insensitive).

## Fact discipline (critical)
- Never invent commands, APIs, model names, limits, prices, security guarantees, certifications, product behavior, or company-specific FDE duties.
- Episodes flagged `"fv": true` in curriculum.json contain product/protocol-specific claims. Use WebFetch/WebSearch to read the OFFICIAL source (priority: official Anthropic docs for Claude/Claude Code/Anthropic programs; official Model Context Protocol docs for MCP; original docs for other technologies). If you read it, put the URLs in `"sources": [...]`, keep claims within what you read, and you may set status `FACT_CHECKED` ONLY then (validator requires sources). If you could not access official sources, keep status `SCRIPTED`, keep claims generic (no versions, numbers, names, feature lists), and write "Needs verification before publishing" in `fact_check_notes`.
- Never write a claim you cannot support. Prefer "often", "many", "can" over absolutes. Do not oversimplify safety/security (no "this makes it safe").
- Do NOT reproduce, paraphrase closely, or imply endorsement from Anthropic's FDE course. Write original explanations. Set `"credit"` to "Original storytelling by Zillenial Talk." (Sneha adds Anthropic learning credit herself where applicable; for FDE-path-adjacent episodes you may add `"fde_path_inspired_candidate": true`.)

## Required keys
episode, slug (kebab-case, matches the folder), level, title, status, status_note, prerequisites (episode numbers), learning_objective, analogy, analogy_breaks, actual_tech, terms_introduced, fact_check_notes, sources (only if fact checked), credit, takeaway, cta, voice (copy from ep 15), cover_icon ("none"), scenes, publishing{instagram_caption, youtube_title, youtube_description, hashtags[], thumbnail_text <= 14 chars}.
Folder name: `ep-NNN-<slug>` with NNN zero-padded to 3 digits.

## Scenes (4-6 per episode; each scene = 1-4 phrases; the visual reveals items in sync with phrase order)
Each scene: `{"id":"s1","visual":"<type>","card":{...},"phrases":[{"text":..,"say":..,"hl":[..]}], "stickers":[[emoji,x,y,size,t0]] (optional), "fx":[...] (optional)}`.
Allowed visuals and their `card`:
- `bigword`: {"word":"TOKEN","emoji":"🧩","sub":"...","sub2":"..."}  (a hero term; word <= 10 chars)
- `steps`: {"title":"...","steps":["a","b","c"],"foot":"..."}  (2-5 steps, labels <= 26 chars)
- `compare`: {"left":{"title","emoji","lines":[<=3]},"right":{...},"warn":"..."}  (left=analogy/before, right=reality/after)
- `loop`: {"center":"AGENT","nodes":["Think","Act","Observe"]}  (3-5 nodes, cycles)
- `stack`: {"title":"...","layers":["UI","Backend","Model API"]}  (architecture layers, 2-5)
- `chat`: {"messages":[{"who":"you","text":".."},{"who":"ai","text":".."}]}  (<=4 messages, short)
- `checklist`: {"title":"...","items":[{"text":"..","ok":true},{"text":"..","ok":false}]}  (2-5)
- `hub`: {"center":"MCP","spokes":["Calendar","Docs","Email"]}  (3-6)
- `card`: {"title":"ANALOGY LIMIT","lines":["..",".."],"foot":".."}  (<= 3 lines, <= 28 chars each; use for "where the analogy breaks" and takeaways)
- `endcard`: no card.
Legacy visuals (spam, cats, flow, breaks, takeaway, jargon, roadmap, recipe, chef) are forbidden for episodes > 3.
Vary visuals across scenes; at most 1 `card` in the middle. Text in visuals is short labels only (full explanation lives in narration + captions). Colors never carry meaning alone.
Stickers: optional emoji, [emoji,x,y,size,t0]; t0 = seconds or "p1"/"p2+0.5" (phrase start). Safe areas: x 80-1000, y 430-1250; avoid the central diagram area. Use 1-3 relevant emoji. If omitted, defaults are used.
Effects (`fx`): optional list of {"type":"confetti|sparkle|rays|punch|shake","at":"p2","x":540,"y":760}. Omit to use defaults. Use confetti only on a genuine "aha" moment.

## Publishing copy
Instagram: hook first line, 1-2 value lines, series label ("AI From Zero"), a comment-driving question, 5-8 relevant hashtags incl. #ZillenialTalk. YouTube title: concept + curiosity + "(AI From Zero #N) #Shorts"; description 2-3 lines + 3 hashtags. No income/guarantee claims, no engagement bait that misleads.

## Status
Use `SCRIPTED` (or `FACT_CHECKED` only with real sources). Never mark anything beyond that.

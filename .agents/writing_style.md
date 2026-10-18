# Writing style

Rules for everything a person reads: `README.md`, `CONTRIBUTING.md`,
`CHANGELOG.md`, `docs/**`, docstrings and comments. They are the
maintainer's standing requirements. The `docs-style-review` skill applies
them as a review pass.

## Audience

The reader has an advanced high-school hobbyist level of electronics and
reading. Define each term and math symbol on first use on a page, or link
its entry in `docs/glossary.md` (terms) or `docs/symbols.md` (symbols).
When you add a term or symbol, add it to the matching page.

Explain only the background needed to understand what the library does.
For deeper theory, cite a data sheet page or another reference.

## Language

American English spelling and idiom only: behavior, color, initialize,
analyze, center, license. Write "data sheet" as two words, as Analog Devices
does. Quote the data sheet exactly when quoting it.

## Docstrings and comments

- A docstring is one or two short paragraphs that teach what the code does.
  A terse parameter list is fine for constructors and main public functions.
  For more detail, point to a `docs/` page or a data sheet page.
- A comment exists only to help a person read the code: why a line is the
  way it is, or a data sheet page for a constant. Do not restate the code.
- Keep agent material out of code: step or phase labels, review IDs, notes
  to self, change history, and reminders aimed at agents. Constraints of
  that kind go in `.agents/`.

## Code layout

Black at 88 columns (`[tool.black]` in `pyproject.toml`). Separate logical
sections with blank lines. Prefer short, clear names over long ones;
public names change only with a changelog entry.

## Signs of AI writing to avoid

Derived from
[Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
and [Words to watch](https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Words_to_watch).
These patterns make text read as machine-written and hide the content.
They apply to commit messages too.

Vocabulary. Replace with plain words:

- AI favorites: additionally (sentence-initial), align with, boasts,
  bolstered, crucial, deep dive, delve, enduring, enhance, foster, garner,
  highlight (verb), interplay, intricate, key (adjective), landscape,
  leverage, meticulous, multifaceted, pivotal, prioritize, quietly, robust,
  showcase, steady, tapestry, testament, underscore, valuable, vibrant.
- Puffery: seamless, powerful, comprehensive, cutting-edge, innovative,
  remarkable, unique, elegant, effortless, streamlined.
- Editorializing: notably, it's important to note, worth noting, arguably,
  interestingly, essentially, actually, clearly, of course, simply, just
  (as filler).
- Copula avoidance: "serves as", "stands as", "acts as", "represents",
  "features", "offers". Write "is" or "has".
- Stiff verbs: utilize, facilitate, in order to, the fact that.

Sentences:

- No "-ing" tails (", ensuring ...", ", highlighting ...", ", making it
  ...").
- No negative parallelism for effect ("not just X, but Y", "it's not X,
  it's Y"). A real technical alternative ("use A, not B") is fine.
- No rule-of-three padding, and no cycling synonyms for one thing: pick
  "chip" or "device" and keep it.
- No significance inflation ("plays a key role", "this matters because")
  or vague attribution ("experts say").
- No closing summaries ("In summary", "Overall") and no hedging
  disclaimers.
- No chat-directed text ("Here is", "Let me know", "Feel free to") or
  unfilled placeholders.
- Vary sentence length.

Formatting:

- Sentence-case headings.
- No bold run-in headers in lists ("- **Thing:** text") and little bold
  overall.
- No em dashes, or " -- " used as one. Use commas, colons, parentheses or
  two sentences.
- No emoji, no "Conclusion" sections on short pages, and no table where a
  sentence would do.

Commit messages state what changed and why in plain words, without stacked
"improved, refined, enhanced" lists.

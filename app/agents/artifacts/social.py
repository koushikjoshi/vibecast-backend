from __future__ import annotations

from app.agents.artifacts._helpers import (
    brand_positioning,
    first_n,
    launch_date,
    pillar_lines,
    plan_pillars,
)
from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class XThreadGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.x_thread.value,
        studio=ArtifactStudio.social.value,
        title="X launch thread",
        description="7\u20139 post thread for X (Twitter).",
    )
    anthropic_max_tokens = 3000
    anthropic_thinking_budget = 1800
    anthropic_schema = (
        "{\n"
        '  "posts": array of 7-9 strings, each <= 275 characters including whitespace and line breaks. Post 1 is the hook and must be under 210 chars.,\n'
        '  "hashtags": array of 2-4 strings starting with #. Lowercase. No generic tags like #ai or #tech unless the post is literally about that category.,\n'
        '  "reply_guy_bait": string (optional single post <= 240 chars designed to be quote-tweeted; empty string if none fits the brand voice)\n'
        "}"
    )
    anthropic_instructions = (
        "You are writing the launch thread that will be pinned on the "
        "founder's X profile for the next month. It needs to be good "
        "enough that other founders quote-tweet it and reply.\n\n"
        "# The hook (post 1)\n"
        "The single most important sentence you will write in this "
        "entire artifact. It must do one of these three things:\n"
        "1. State a specific, unexpected fact ('We replaced a 4-person "
        "marketing team with 1 PMM and one agent pipeline. Today we're "
        "open-sourcing how.').\n"
        "2. Describe a concrete before/after ('Monday: 9 hours on a "
        "launch post. Today: 22 minutes. Here's the new workflow.').\n"
        "3. Name the problem the product solves in the reader's voice "
        "('If you've ever been the only marketer at a startup you know "
        "the feeling — it's 7pm, launch is Tuesday, and you have 12 "
        "artifacts to ship.').\n"
        "Never open with 'Excited to announce' or '🧵 A thread on'.\n\n"
        "# Structure of the thread\n"
        "- Post 1: hook (see above).\n"
        "- Post 2: what it is, in one sentence a skeptical engineer "
        "would accept.\n"
        "- Posts 3-5: one post per campaign pillar. Each post makes a "
        "specific claim and proves it with a mechanism, not an "
        "adjective. Include a concrete number when truthful.\n"
        "- Post 6: the honest trade-off / what it's NOT. This is the "
        "post that separates good threads from generic ones.\n"
        "- Post 7 (optional): a tiny story or customer vignette (only "
        "if the source material supports one).\n"
        "- Final post: link to the launch + a specific CTA ('Grab it', "
        "'Try the demo in 2 minutes'). Include a URL placeholder.\n\n"
        "# Craft rules\n"
        "- Write for mobile: each post should be scannable in 1.5 "
        "seconds.\n"
        "- Use line breaks inside posts to create rhythm. Short "
        "sentences. Hard returns.\n"
        "- First-person plural for the company. First-person singular "
        "when relating a personal story.\n"
        "- Numbers are allies: '22 minutes', '12 artifacts', '1 PMM'.\n"
        "- No emojis except at most one in post 1.\n"
        "- No 'thread 🧵' indicator. The format is obvious.\n"
        "- No clickbait ('You won't believe...')."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = plan_pillars(ctx)
        posts: list[str] = [
            f"Today we're shipping {project.name}.\n\n{positioning}",
            "Why now?\n\nMarketing teams are stuck between $20k/mo agencies and one overworked PMM. We built a third option: a multi-agent team that works on your brief.",
        ]
        for p in pillars[:3]:
            posts.append(f"{p.get('name', '')}\n\n{p.get('message', '')}")
        posts.append(
            "How it works:\n\n"
            "1. Upload a launch brief\n"
            "2. A CMO agent dispatches 17 specialists\n"
            "3. Every artifact is brand-checked\n"
            "4. You approve. We ship."
        )
        posts.append(
            "12 artifacts per project: blog, press, release notes, LinkedIn (2), X thread, HN, Product Hunt, emails (2), battle card, and a podcast episode."
        )
        posts.append(f"Start your first project \u2192 https://vibecast.ai ({launch_date(ctx)})")
        return {
            "posts": posts,
            "hashtags": ["#buildinpublic", "#marketing", "#ai"],
            "reply_guy_bait": "",
        }


class LinkedInCompanyGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.linkedin_company.value,
        studio=ArtifactStudio.social.value,
        title="LinkedIn \u2014 company post",
        description="LinkedIn post from the company page.",
    )
    anthropic_max_tokens = 2000
    anthropic_thinking_budget = 1200
    anthropic_schema = (
        "{\n"
        '  "post": string (1400-2500 chars, LinkedIn-formatted with intentional line breaks. Must render well with LinkedIn\'s "see more" truncation after ~210 chars on desktop \u2014 so the first 200 chars must be a complete, scroll-stopping thought.),\n'
        '  "cta": {"label": string (<=28 chars), "href": string}\n'
        "}"
    )
    anthropic_instructions = (
        "LinkedIn has a specific format. The first ~210 chars are "
        "visible before the 'see more' truncation. That opening must "
        "function as a standalone scroll-stopper.\n\n"
        "# Structure\n"
        "1. **Opening (first 2 lines, <=210 chars):** A complete "
        "thought. Specific. Declarative. Not a question. Not a tease.\n"
        "2. *(blank line)*\n"
        "3. **Context (3-4 short sentences):** What happened, why we "
        "built this, why now. No filler.\n"
        "4. *(blank line)*\n"
        "5. **Proof points (3-4 bullets using \u2022 character):** Each "
        "bullet starts with a concrete noun and includes a mechanism "
        "or number. Parallel structure.\n"
        "6. *(blank line)*\n"
        "7. **Closing line + CTA:** One sentence of closing. Then the "
        "CTA with a link placeholder.\n\n"
        "# Voice\n"
        "- LinkedIn-native rhythm: very short paragraphs, blank lines "
        "between each. But not every sentence on its own line \u2014 that "
        "reads as performative.\n"
        "- At most one emoji, and only if the brand voice allows it.\n"
        "- No 'I am humbled', 'I am thrilled', 'excited to share'.\n"
        "- No fake intimacy ('Picture this:', 'Imagine a world where').\n"
        "- No self-congratulation. Let the work speak."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = first_n(pillar_lines(ctx), 3)
        body = (
            f"Today we're shipping {project.name}.\n\n"
            f"{positioning}\n\n"
            "What that means in practice:\n"
            + "\n".join(
                f"\u2022 {p}"
                for p in (
                    pillars
                    or [
                        "One brief \u2192 a full launch kit.",
                        "Brand-safe by default.",
                        "Evidence-backed, GEO-structured content.",
                    ]
                )
            )
            + "\n\nRead the launch: https://vibecast.ai/launch"
        )
        return {
            "post": body,
            "cta": {"label": "Read the launch", "href": "https://vibecast.ai/launch"},
        }


class LinkedInFounderGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.linkedin_founder.value,
        studio=ArtifactStudio.social.value,
        title="LinkedIn \u2014 founder post",
        description="First-person launch post from the founder.",
    )
    anthropic_max_tokens = 2000
    anthropic_thinking_budget = 1400
    anthropic_schema = (
        "{\n"
        '  "post": string (900-1800 chars, first-person, LinkedIn-formatted). First 210 chars must work as a standalone scroll-stopper because LinkedIn truncates after that.,\n'
        '  "founder_persona_note": string (one line describing the assumed founder voice you used, e.g. "seasoned operator, dry, evidence-first")\n'
        "}"
    )
    anthropic_instructions = (
        "This is the founder talking to their network. It should sound "
        "like a human — specifically like a technical founder who has "
        "shipped before, not like a sales pitch.\n\n"
        "# Opening\n"
        "Start with a specific moment, observation, or concrete "
        "personal anecdote. Not 'I've been thinking about...'. Not "
        "'When I started my career...'. A moment.\n\n"
        "Example good opening: 'Last October I watched our head of "
        "growth push a Google Doc to the founder at 11pm, the night "
        "before launch, because nobody else could write the press "
        "release. Her kid had been asleep for three hours.'\n\n"
        "# Middle\n"
        "Connect the anecdote to the launch. Name the mechanism. "
        "Acknowledge trade-offs honestly. If source material supports "
        "a customer story or early metric, use one.\n\n"
        "# Closing\n"
        "One honest sentence about why this matters to the founder "
        "personally. Then 'Link in comments.' (or equivalent). Never "
        "'DM me' unless the persona would.\n\n"
        "# Craft rules\n"
        "- First-person singular. This is the founder, not the company.\n"
        "- No hashtags.\n"
        "- No emoji except possibly one.\n"
        "- No 'humbled and grateful'. No 'wild ride'.\n"
        "- Specific > vague every time.\n"
        "- If the source material doesn't mention the founder's name, "
        "write in a way that works for any founder."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        body = (
            "A year ago I was the first marketing hire at a B2B startup. "
            "I was doing blog, press, social, lifecycle, and podcast \u2014 alone. "
            "I missed half of them.\n\n"
            f"Today we're shipping {project.name}.\n\n"
            f"{positioning}\n\n"
            "This is the tool I wish I had when I was that one overwhelmed PMM. "
            "If that's you \u2014 give this a try.\n\nLink in comments."
        )
        return {
            "post": body,
            "founder_persona_note": "seasoned operator, direct, evidence-first",
        }


class HnShowGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.hn_show.value,
        studio=ArtifactStudio.social.value,
        title="HN 'Show HN' submission",
        description="Show HN title + first-comment body.",
    )
    anthropic_max_tokens = 2200
    anthropic_thinking_budget = 1500
    anthropic_schema = (
        "{\n"
        '  "title": string (Hacker News "Show HN:" title, 55-80 chars, MUST start with "Show HN: "),\n'
        '  "url": string (recommended submission URL \u2014 typically a clean product landing page),\n'
        '  "first_comment": string (700-1300 chars, founder-style, honest, technical)\n'
        "}"
    )
    anthropic_instructions = (
        "The HN audience is skeptical, technical, and allergic to "
        "marketing copy. You are writing for people who have shipped "
        "production systems and have strong opinions about them. They "
        "will read the first-comment technical summary and decide "
        "within 20 seconds whether this is worth engaging with.\n\n"
        "# Title craft\n"
        "- Must start with literal string 'Show HN: '.\n"
        "- Name the product, then a concrete one-phrase description.\n"
        "- No adjectives. No 'revolutionary'. No 'powerful'.\n"
        "- Good: 'Show HN: VibeCast \u2013 An agentic marketing team for B2B "
        "startups'.\n"
        "- Bad: 'Show HN: VibeCast \u2013 Revolutionize your marketing!'\n\n"
        "# First-comment structure\n"
        "1. Opening: 'Hi HN! Founder here.' or similar brief intro. One "
        "line.\n"
        "2. What it does, in one sentence. Plain.\n"
        "3. Technical summary: what's under the hood. Name the actual "
        "tools, models, libraries. Be specific: not 'uses LLMs' but "
        "'Claude Sonnet-4.5 via the Anthropic Messages API with "
        "extended thinking enabled, orchestrated through a custom "
        "supervisor/worker pattern'.\n"
        "4. What works well today.\n"
        "5. Honest limitations: 2-3 concrete things the product "
        "doesn't do or doesn't do well yet. This paragraph is "
        "non-optional. HN respects honesty more than any other "
        "audience.\n"
        "6. What feedback you're specifically asking for. End with "
        "'Happy to answer anything.' or a similar warm close.\n\n"
        "# Voice\n"
        "- Casual technical register. Contractions fine.\n"
        "- No adjectives unless they carry information.\n"
        "- No 'excited to share'. No 'delighted'.\n"
        "- Cite technical details. Show you've thought about "
        "architecture and trade-offs.\n"
        "- If there's prior art (similar tools, research papers), "
        "acknowledge it in one sentence."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        title = f"Show HN: {project.name} \u2014 {positioning}"
        first_comment = (
            "Hi HN! Founder here.\n\n"
            f"{project.name} is a multi-agent marketing team for B2B startups. "
            "You upload a launch brief, we spin up a CMO + 17 specialist agents, "
            "and you get a full launch kit (blog, press, social, email, podcast) "
            "ready for review in ~35 minutes.\n\n"
            "Under the hood: Claude Agent SDK for orchestration + supervised "
            "subagents, Anthropic web_search for live competitive research, "
            "GPT-image-1 for visuals, ElevenLabs for podcast audio.\n\n"
            "Would love feedback on the 12-artifact default and whether the "
            "Brand Guardian step feels strict enough. Happy to answer anything."
        )
        return {
            "title": title,
            "url": "https://vibecast.ai",
            "first_comment": first_comment,
        }


class ProductHuntGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.product_hunt.value,
        studio=ArtifactStudio.social.value,
        title="Product Hunt kit",
        description="Tagline + first comment + 4 gallery briefs.",
    )
    anthropic_max_tokens = 2500
    anthropic_thinking_budget = 1500
    anthropic_schema = (
        "{\n"
        '  "tagline": string (<= 60 chars, verb-optional; "A [noun] for [audience]" is a classic PH format),\n'
        '  "description": string (exactly 240-260 chars; Product Hunt truncates at ~260),\n'
        '  "topics": array of 3-5 lowercase Product Hunt topic slugs (e.g. "marketing", "artificial-intelligence"),\n'
        '  "first_comment": string (600-900 chars, founder intro),\n'
        '  "gallery_briefs": array of exactly 4 {"frame": int, "scene": string (concrete visual description, 1-2 sentences), "note": string (direction for the illustrator or image model)},\n'
        '  "maker_thank_you": string (a short single-line thank-you line the maker can post at the end of the day)\n'
        "}"
    )
    anthropic_instructions = (
        "Product Hunt voters make decisions in ~4 seconds based on the "
        "thumbnail, tagline, and first gallery image. Optimize for that.\n\n"
        "# Tagline\n"
        "- Under 60 chars.\n"
        "- Best formats: 'A [thing] for [audience]', 'The [thing] that "
        "[does surprising outcome]', or a short verb phrase.\n"
        "- No 'revolutionary'. No 'AI-powered' (PH voters are numb to "
        "it unless the AI is the actual differentiator). Use the "
        "product name naturally if it fits.\n\n"
        "# Description (240-260 chars)\n"
        "Every character matters. Lead with the mechanism. Include the "
        "target audience. Include one concrete outcome. End with a "
        "verb.\n\n"
        "# First comment\n"
        "The maker's first comment is read by ~40% of upvoters. It "
        "should: thank the hunter (if any), briefly tell the story of "
        "why you built this, name one specific thing you're proudest "
        "of, acknowledge one genuine limitation, and invite feedback. "
        "Warm and human. Contractions are good.\n\n"
        "# Gallery briefs\n"
        "These are prompts for the design team or image model. Each "
        "should describe:\n"
        "- `scene`: what the frame visually shows (a screenshot view, "
        "a workflow moment, a before/after, a system diagram).\n"
        "- `note`: specific direction on style, mood, color, emphasis. "
        "NOT marketing copy.\n"
        "Frame 1 is the hero; frames 2-3 show features or workflows; "
        "frame 4 is often a 'how it works' diagram or differentiator.\n\n"
        "# Maker thank-you\n"
        "One line the maker posts when going to sleep. Warm, specific, "
        "not cheesy. Reference a real moment from the day if possible."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        return {
            "tagline": f"{project.name}: A full marketing team on demand.",
            "description": positioning,
            "topics": ["marketing", "artificial-intelligence", "saas"],
            "first_comment": (
                f"Thanks for checking out {project.name}! We built this because "
                "every small B2B team we talked to had the same problem: one "
                "human marketer trying to do the work of five. This is a CMO + "
                "17 specialist agents that ship a full launch kit from a single "
                "brief. AMA!"
            ),
            "gallery_briefs": [
                {
                    "frame": 1,
                    "scene": "Hero shot of the VibeCast workspace with a project mid-run.",
                    "note": "Dark theme, show live trace panel on the right.",
                },
                {
                    "frame": 2,
                    "scene": "Campaign plan preview: positioning, 3 pillars, channel selection.",
                    "note": "Emphasize the 'approve plan' button.",
                },
                {
                    "frame": 3,
                    "scene": "Artifact grid with all 12 drafted deliverables.",
                    "note": "Use artifact-state color badges.",
                },
                {
                    "frame": 4,
                    "scene": "Podcast episode detail page: transcript + waveform + cover art.",
                    "note": "Show the RSS feed callout in the footer.",
                },
            ],
            "maker_thank_you": (
                "Wild day. Thanks to everyone who gave feedback \u2014 shipping "
                "three of your suggestions tomorrow."
            ),
        }

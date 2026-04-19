from __future__ import annotations

from app.agents.artifacts._helpers import (
    brand_positioning,
    first_n,
    launch_date,
    pillar_lines,
    target_competitor,
)
from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class CustomerEmailGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.customer_email.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Customer announcement email",
        description="Broadcast to existing customers on launch day.",
    )
    anthropic_max_tokens = 1700
    anthropic_thinking_budget = 0
    anthropic_schema = (
        "{\n"
        '  "from_name": string (sender display name, e.g. "Alex at Acme" \u2014 a real name humanizes better than "The Acme Team"),\n'
        '  "reply_to": string (plausible reply-to email address),\n'
        '  "subject": string (38-62 chars, no emoji unless brand voice explicitly allows it, sentence case or lowercase depending on brand),\n'
        '  "preview_text": string (75-115 chars, extends the subject, never just repeats it),\n'
        '  "body_md": string (markdown body, 900-1600 chars). MUST include H2 for "What\'s new", an unordered list of 3-4 changes with bold-led lines, and an H2 for "What you need to do" even if the answer is "nothing" (reassurance is valuable).,\n'
        '  "cta": {"label": string (verb-first, <= 28 chars), "href": string},\n'
        '  "postscript": string (optional P.S. line, <= 140 chars. A P.S. is the second-most-read part of an email. Use it to make one specific offer or point. Empty string if no good P.S. fits.)\n'
        "}"
    )
    anthropic_instructions = (
        "This email goes to existing paying customers. These are "
        "people who already trust you — don't sell to them, update "
        "them. The ideal mental model is an email from the founder "
        "to an old friend who happens to be a customer.\n\n"
        "# Subject + preview text\n"
        "- Subject is direct and scannable. It's not clickbait because "
        "the reader is already a customer — they open if it seems "
        "relevant.\n"
        "- Good subjects: 'Shipping today: <thing>', 'Your launch "
        "workflow just got faster', '<product>: 3 changes you can use "
        "this week'.\n"
        "- Bad subjects: 'Exciting news!', 'You're going to love this', "
        "'Introducing the future of <category>'.\n"
        "- Preview text is not a repeat of the subject. It extends it, "
        "gives one more specific detail.\n\n"
        "# Body structure\n"
        "1. **Greeting** (1 line). 'Hi,' or 'Hi there,'. Never 'Dear "
        "Valued Customer'.\n"
        "2. **Opening** (1-2 sentences). What's shipping today, in "
        "plain language. Include a number or concrete detail.\n"
        "3. **## What's new** (H2). 3-4 bullet items, each with a bold "
        "lead-phrase and 1 sentence of explanation.\n"
        "4. **## What you need to do** (H2). Always include this "
        "section. If the answer is 'nothing', say so reassuringly.\n"
        "5. **Closing** (1-2 sentences). Thank them for being on the "
        "journey. Sign off as a specific person or 'the <product> "
        "team'.\n"
        "6. Optional **P.S.** (see schema).\n\n"
        "# Voice\n"
        "- Warm, but informed. Talking to professionals, not "
        "customers-as-audience.\n"
        "- Contractions are fine.\n"
        "- No exclamation points except maybe one in the closing.\n"
        "- No 'we are thrilled to announce'. No 'excited to share'.\n"
        "- Sign-offs: 'Thanks for building with us.', 'Thanks for being "
        "along for the ride.', '— The <product> team'."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = first_n(pillar_lines(ctx), 3)
        return {
            "from_name": f"The {project.name} team",
            "reply_to": "team@vibecast.ai",
            "subject": f"Shipping today: {project.name}",
            "preview_text": positioning,
            "body_md": (
                "Hi there,\n\n"
                f"Today we're shipping **{project.name}** to all workspaces \u2014 "
                "no upgrade required.\n\n"
                "## What's new\n\n"
                + "\n".join(
                    f"- **{p}**"
                    for p in (
                        pillars
                        or [
                            "Agentic marketing pipeline with 12 default artifacts",
                            "Brand Guardian enforcement",
                            "Live trace for every run",
                        ]
                    )
                )
                + "\n\n## What you need to do\n\nNothing. The rollout is automatic.\n\n"
                f"Thanks for building with us.\n\n\u2014 The {project.name} team"
            ),
            "cta": {
                "label": "Explore the new workflow",
                "href": "https://vibecast.ai/app",
            },
            "postscript": "",
        }


class ProspectEmailGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.prospect_email.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Prospect nurture email",
        description="Cold-nurture email for active prospects.",
    )
    anthropic_max_tokens = 1500
    anthropic_thinking_budget = 0
    anthropic_schema = (
        "{\n"
        '  "from_name": string (a specific human name + title, e.g. "Koushik, co-founder at VibeCast"),\n'
        '  "reply_to": string (plausible personal reply-to address),\n'
        '  "subject": string (28-52 chars, lowercase or sentence case, low-key, looks like a personal email NOT a newsletter),\n'
        '  "preview_text": string (55-95 chars),\n'
        '  "body_md": string (400-750 chars, 3-5 short paragraphs). MUST include {{first_name}} once. MAY include one additional merge tag like {{company_name}} or {{pain_point}}. NO more than 2 merge tags total.,\n'
        '  "cta": {"label": string (<=30 chars), "href": string},\n'
        '  "ps_line": string (single-line P.S., <= 140 chars. P.S. lines lift reply rates materially. Use it for a specific low-friction offer. Empty string if none fits.)\n'
        "}"
    )
    anthropic_instructions = (
        "This email goes to a prospect who has engaged before but "
        "hasn't converted. They've met you once. They're busy. They "
        "get 40 sales emails a day and delete most of them in 1.2 "
        "seconds.\n\n"
        "Your goal: sound like a real human founder who remembers the "
        "last conversation, not a sequence step from Outreach.\n\n"
        "# Subject craft\n"
        "- Sounds like an email from a colleague, not a newsletter.\n"
        "- Lowercase or sentence case. No Title Case.\n"
        "- No brackets, no emoji, no personalization tokens in the "
        "subject.\n"
        "- Good: 'quick follow-up on <specific topic>', 'saw your post "
        "on <thing>', 'the thing I mentioned is live'.\n"
        "- Bad: 'Introducing...', 'URGENT:', 'You won't want to miss...'.\n\n"
        "# Body\n"
        "- Paragraph 1: reference the previous conversation "
        "specifically. Use {{first_name}} here.\n"
        "- Paragraph 2: the update — what you're launching. One or two "
        "sentences.\n"
        "- Paragraph 3: what's specifically relevant to them, based on "
        "what they said last time. Use a merge tag or specific noun "
        "from the ICP.\n"
        "- Paragraph 4: the ask. Low-friction. 'Want me to send a "
        "2-minute Loom?' or 'Worth a 15-min call this week?' Not "
        "'Let's sync'.\n"
        "- Paragraph 5: sign-off with first name only.\n\n"
        "# Voice\n"
        "- Sounds typed, not written.\n"
        "- Contractions everywhere. Sentence fragments OK.\n"
        "- Never 'I hope this email finds you well'.\n"
        "- Never 'circling back', 'touching base', 'bumping this up'.\n"
        "- Never use two em-dashes in one email.\n"
        "- NO buzzwords: 'synergy', 'streamline', 'leverage', "
        "'optimize', 'solution', 'best-in-class'.\n\n"
        "# P.S.\n"
        "The P.S. line is read even by people who delete the body. "
        "Use it for a specific, concrete offer (a link to a 90-second "
        "video, a one-pager, a specific case-study slug)."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        return {
            "from_name": "Koushik, co-founder at VibeCast",
            "reply_to": "koushik@vibecast.ai",
            "subject": f"{project.name} is live \u2014 one brief, 12 artifacts",
            "preview_text": "A full marketing team on demand.",
            "body_md": (
                "Hi {{first_name}},\n\n"
                f"When we last spoke you mentioned {{pain_point}}. "
                f"Today we launched {project.name} \u2014 a multi-agent marketing team "
                "that takes a launch brief and produces a full campaign kit in "
                "under an hour.\n\n"
                f"{positioning}\n\n"
                "If that sounds relevant, I'd love to show you the demo live "
                "or share a 2-minute Loom. Either works.\n\n"
                "Koushik"
            ),
            "cta": {
                "label": "Book 20 minutes",
                "href": "https://vibecast.ai/book",
            },
            "ps_line": "P.S. If you'd rather just see the output first, here's a 90-sec Loom walkthrough.",
        }


class BattleCardGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.battle_card.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Battle card",
        description="Sales battle card focused on the primary competitor.",
    )
    anthropic_max_tokens = 2200
    anthropic_thinking_budget = 0
    anthropic_schema = (
        "{\n"
        '  "vs": string (competitor name as chosen from the competitors list \u2014 use their exact company name),\n'
        '  "category_framing": string (one sentence on how to position the category itself, e.g. "we\'re not another writing tool, we\'re a supervised multi-agent pipeline"),\n'
        '  "one_liner": string (our differentiator, <= 160 chars, rep-speakable),\n'
        '  "discovery_questions": array of 3-5 strings (questions a rep can ask to surface whether our differentiation lands),\n'
        '  "when_we_win": array of 3-5 {"signal": string (concrete buyer signal, not an aspiration), "why": string (one sentence, speakable)},\n'
        '  "when_we_lose": array of 2-4 {"signal": string, "why": string} \u2014 honest losses only. Fake invincibility destroys trust with reps and prospects.,\n'
        '  "objection_handling": array of 4-6 {"objection": string (in the prospect\'s voice, not reframed), "reframe": string (the rep\'s response, 2-3 sentences)},\n'
        '  "landmines": array of 2-4 strings (things the competitor will try to make prospects believe about us \u2014 and how we handle them),\n'
        '  "proof_points": array of 3-5 strings (specific, citeable; no vague claims),\n'
        '  "pricing_framing": string (one short paragraph on how to talk about price when asked, without breaking any brand competitor_policy rules)\n'
        "}"
    )
    anthropic_instructions = (
        "This is a battle card for an Account Executive who is about "
        "to walk into a meeting where the prospect has specifically "
        "mentioned the competitor. It's a working document, not "
        "marketing collateral.\n\n"
        "# Craft rules\n"
        "- Every sentence should be something the rep can literally "
        "read out loud in a Zoom call. No marketing-brochure voice.\n"
        "- 'We' and 'they' are fine. Use the competitor's exact name.\n"
        "- Concrete > abstract, always. 'Cuts launch prep from 3 days "
        "to 45 minutes' > 'is faster'.\n\n"
        "# When we win\n"
        "Each entry has a `signal` (what the rep can actually observe "
        "in a discovery call — something the prospect said or "
        "revealed) and a `why` (the one-sentence reason we win in that "
        "situation). Don't list features; list buyer contexts.\n\n"
        "# When we lose\n"
        "Non-optional. List the real situations where the competitor "
        "is genuinely the better choice. This section is what makes "
        "reps trust the card. Examples: 'prospect needs on-prem "
        "deployment', 'prospect needs native ad-buying integrations "
        "we haven't built'.\n\n"
        "# Objection handling\n"
        "Objections must be in the PROSPECT's voice, verbatim. Write "
        "them as if transcribing a Gong call. Then the reframe is the "
        "rep's response \u2014 calm, honest, and short.\n"
        "Bad objection: 'Our brand voice is too specific for AI.'\n"
        "Good objection: 'Honestly, I've tried three of these tools "
        "and they all sound like AI wrote them.'\n\n"
        "# Landmines\n"
        "This is the killer section reps love. What will the "
        "competitor's sales team say about us that isn't fair? How "
        "should the rep preempt it?\n\n"
        "# Competitor policy\n"
        "Strictly respect the brand kit's `competitor_policy`. If it "
        "says 'name-compare allowed', name them. If it says "
        "'category-compare only', never name them — use categories."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        rival = target_competitor(ctx) or "the incumbent"
        positioning = brand_positioning(ctx)
        return {
            "vs": rival,
            "category_framing": (
                "We're not another writing tool. We're a supervised "
                "multi-agent pipeline with a Brand Guardian step."
            ),
            "one_liner": f"We win when {positioning.lower()}",
            "discovery_questions": [
                f"What did you like and not like about {rival}?",
                "How many people on your team touch a launch today, and at which steps?",
                "What's the last launch kit you shipped, and what broke?",
            ],
            "when_we_win": [
                {
                    "signal": f"Prospect says 'we tried {rival} but it sounded like AI wrote it'",
                    "why": "Brand Guardian enforces banned phrases + required disclaimers before output.",
                },
                {
                    "signal": "Solo PMM or founder-led marketing",
                    "why": "One brief in, full launch kit out. No ops overhead.",
                },
                {
                    "signal": "1+ launches per quarter",
                    "why": "The repeatable pipeline pays for itself on the second launch.",
                },
            ],
            "when_we_lose": [
                {
                    "signal": "Enterprise with deep in-house agency relationships",
                    "why": "Procurement cycle is long; the agency still ships faster at that level.",
                },
                {
                    "signal": "Team needs native social publishing or ad-buy integrations",
                    "why": "On the roadmap, not shipping today.",
                },
            ],
            "objection_handling": [
                {
                    "objection": f"We already use {rival}.",
                    "reframe": (
                        "That's great \u2014 most customers use us alongside, not "
                        "instead of. The difference: we produce the campaign kit; "
                        f"{rival} handles the ad spend."
                    ),
                },
                {
                    "objection": "Honestly, I've tried three of these tools and they all sound like AI wrote them.",
                    "reframe": (
                        "That's why every artifact passes a Brand Guardian step "
                        "against your banned phrases, tone, and required "
                        "disclaimers before it ever reaches your inbox. Want me "
                        "to show you the failure mode when I break the rules on "
                        "purpose?"
                    ),
                },
            ],
            "landmines": [
                f"{rival} reps will say we're 'just a wrapper'. We're a supervised multi-agent system with an explicit Brand Guardian and a traceable run log \u2014 not a prompt.",
            ],
            "proof_points": [
                "12 artifacts per project by default",
                "~35 min from brief \u2192 approval queue",
                "Immutable brand-kit versions",
            ],
            "pricing_framing": (
                "Lead with the cost-per-launch, not the monthly seat price. A "
                "PMM at $140k/yr is roughly $1,100 per launch day of "
                "fully-loaded time. Our per-project cost sits far below "
                "that at the volumes our ICP runs."
            ),
        }

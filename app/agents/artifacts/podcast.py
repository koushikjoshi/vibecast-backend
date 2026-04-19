from __future__ import annotations

from app.agents.artifacts._helpers import (
    brand_positioning,
    launch_date,
    pillar_lines,
    target_competitor,
)
from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class PodcastEpisodeGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.podcast_episode.value,
        studio=ArtifactStudio.podcast.value,
        title="Podcast episode (MP3 + transcript + cover + RSS)",
        description=(
            "6-minute two-host launch episode with transcript, cover art brief, "
            "and an RSS-ready metadata block."
        ),
    )
    anthropic_max_tokens = 6000
    anthropic_thinking_budget = 3500
    anthropic_schema = (
        "{\n"
        '  "episode_title": string (45-80 chars, NOT "Episode 1: <product> Launch"; use a hook-style title that would earn a click in a podcast app),\n'
        '  "episode_number": int,\n'
        '  "duration_sec": int (target 330-480),\n'
        '  "cold_open": string (a single short sentence <= 220 chars spoken over pre-intro audio that teases the most provocative moment from the episode),\n'
        '  "transcript": array of 18-28 {"t_sec": int (cumulative seconds from episode start), "speaker": "Nova" or "Arc", "line": string (actual spoken speech; contractions; occasional interjections like "yeah" or "right"; 1-4 sentences per line)},\n'
        '  "show_notes_md": string (markdown, 700-1400 chars, MUST include ## Episode summary, ## Chapters (with timestamps), ## Links, ## Transcript excerpts),\n'
        '  "pull_quotes": array of 2-3 strings (the most shareable lines from the episode, < 200 chars each, verbatim from transcript),\n'
        '  "cover_art_brief": {"style": string, "focal_object": string, "mood": string, "color_palette": string, "notes": string (explicit anti-cliche guidance for the image model)},\n'
        '  "rss_metadata": {"episode_title": string, "episode_number": int, "guid": string (stable slug), "duration_sec": int, "pub_date": string ISO date YYYY-MM-DD, "description": string (120-180 chars, written to survive truncation in podcast apps)},\n'
        '  "clip_suggestions": array of 2-3 {"t_start_sec": int, "t_end_sec": int, "why": string (one sentence on why this clip is the shareable one)},\n'
        '  "audio_status": "pending"\n'
        "}"
    )
    anthropic_instructions = (
        "You are writing the script for a short-form B2B podcast "
        "episode that will ship alongside a launch. Two hosts, real "
        "dialogue, 5.5-8 minutes total. Think 'Lenny Rachitsky's "
        "podcast' tone, not 'earnings call'.\n\n"
        "# Hosts\n"
        "- **Nova**: warm, curious, observational. Asks second-order "
        "questions. Tells small stories from the trenches.\n"
        "- **Arc**: skeptical, analytical, engineer-leaning. Pushes "
        "back on vague claims. Willing to name the elephant in the "
        "room.\n"
        "Their dynamic is: Nova frames, Arc stress-tests. Neither is "
        "cheerleading the product. They're genuinely trying to "
        "understand it together with the listener.\n\n"
        "# Episode arc\n"
        "1. **Cold open (0:00-0:10)**: a provocative line from later "
        "in the episode, delivered solo. Creates stakes before the "
        "intro music.\n"
        "2. **Intro (0:10-0:30)**: both hosts, introduce themselves, "
        "name the topic.\n"
        "3. **'What is this?' (0:30-1:15)**: Arc asks Nova to "
        "summarize in one sentence. Nova does. Arc asks one "
        "follow-up that forces Nova to be more specific.\n"
        "4. **Mechanism section (1:15-3:30)**: walk through how the "
        "product actually works. Each campaign pillar gets 25-45 "
        "seconds. Nova describes, Arc interrogates, Nova responds "
        "with a specific example or mechanism.\n"
        "5. **Skeptic section (3:30-5:00)**: Arc voices the real "
        "objection a listener would have ('Isn't this just ChatGPT "
        "with a UI?', 'How do you handle brand drift?'). Nova answers "
        "honestly, including one trade-off they haven't solved yet.\n"
        "6. **'Who is this NOT for?' (5:00-5:45)**: both hosts name "
        "specific buyer segments the product doesn't fit. This is "
        "trust-building.\n"
        "7. **Close (5:45-end)**: Nova's launch call to action with "
        "the date, where to go, what to try first.\n\n"
        "# Voice rules for speaker lines\n"
        "- Spoken speech, not written speech. Contractions, yes; "
        "subordinate clauses, rarely.\n"
        "- Sentence fragments OK. Interjections ('right', 'yeah', "
        "'wait') OK.\n"
        "- No speaker should monologue for more than ~30 seconds "
        "without a check-in from the other.\n"
        "- Include at least one small moment of genuine disagreement "
        "or friction. That's what makes a podcast feel real.\n"
        "- Do NOT write 'INTRO MUSIC' or stage directions; this is a "
        "transcript, not a script.\n"
        "- Never use phrases like 'In this episode we'll discuss...'.\n\n"
        "# Cover art brief\n"
        "Actively instruct AGAINST cliche: 'no robots', 'no glowing "
        "brains', 'no circuit boards', 'no gradients of purple and "
        "blue', 'no neon'. Push toward editorial, magazine-cover "
        "aesthetics.\n\n"
        "# Pull quotes + clip suggestions\n"
        "These are what the marketing team will turn into social "
        "clips. The pull_quotes MUST appear verbatim in the "
        "transcript. Clip suggestions should pick 15-40 second "
        "windows that stand alone as social-ready cuts."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = pillar_lines(ctx)
        rival = target_competitor(ctx) or "the incumbent vendors"

        transcript: list[dict] = [
            {
                "t_sec": 0,
                "speaker": "Nova",
                "line": (
                    "Welcome back to the VibeCast Launch Radar. "
                    f"I'm Nova, and today we're talking about {project.name}."
                ),
            },
            {
                "t_sec": 12,
                "speaker": "Arc",
                "line": f"And I'm Arc. Nova, in one sentence \u2014 what is {project.name}?",
            },
            {
                "t_sec": 20,
                "speaker": "Nova",
                "line": positioning,
            },
            {
                "t_sec": 35,
                "speaker": "Arc",
                "line": (
                    "OK, so let's break that down. What are the three promises "
                    "the team is making with this launch?"
                ),
            },
        ]
        t = 50
        for p in pillars[:3]:
            transcript.append(
                {
                    "t_sec": t,
                    "speaker": "Nova",
                    "line": p,
                }
            )
            t += 40
        transcript.append(
            {
                "t_sec": t,
                "speaker": "Arc",
                "line": (
                    f"My honest take: this is a direct challenge to how {rival} "
                    "has positioned themselves. The difference here is the "
                    "Brand Guardian \u2014 that's real."
                ),
            }
        )
        t += 35
        transcript.append(
            {
                "t_sec": t,
                "speaker": "Nova",
                "line": (
                    f"Launching today, {launch_date(ctx)}. Links in the "
                    "show notes. Thanks for listening."
                ),
            }
        )

        show_notes_md = (
            f"# {project.name} \u2014 Launch Radar\n\n"
            f"{positioning}\n\n"
            "## Chapters\n"
            + "\n".join(
                f"- {seg['t_sec']//60:02d}:{seg['t_sec']%60:02d} \u2014 {seg['speaker']}"
                for seg in transcript
            )
            + "\n\n## Links\n- https://vibecast.ai\n- https://vibecast.ai/launch"
        )

        cover_art_brief = {
            "style": "Editorial, high-contrast, dark base with a single accent color.",
            "focal_object": f"An abstract broadcast waveform overlaid with the word '{project.name}'.",
            "mood": "Confident, calm, evidence-first.",
            "notes": "Avoid clich\u00e9 AI iconography (no robots, no circuits).",
        }

        rss_metadata = {
            "episode_title": f"Launch: {project.name}",
            "episode_number": 1,
            "guid": f"vibecast-launch-{project.slug}",
            "duration_sec": t + 10,
            "pub_date": launch_date(ctx),
            "description": positioning,
        }

        return {
            "episode_title": f"Launch: {project.name}",
            "episode_number": 1,
            "duration_sec": t + 10,
            "cold_open": (
                f"\"A lot of launch tools claim to 'sound like your "
                f"brand'. The question is what happens when they don't.\""
            ),
            "transcript": transcript,
            "show_notes_md": show_notes_md,
            "pull_quotes": [positioning],
            "cover_art_brief": {
                **cover_art_brief,
                "color_palette": "Editorial duotone: near-black base with a single warm accent color.",
            },
            "rss_metadata": rss_metadata,
            "clip_suggestions": [
                {
                    "t_start_sec": 35,
                    "t_end_sec": 80,
                    "why": "Clean 45-second framing of what the product is, good for LinkedIn.",
                },
            ],
            "audio_status": "pending",
        }

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
    anthropic_max_tokens = 3500
    anthropic_schema = (
        "{\n"
        '  "episode_title": string,\n'
        '  "duration_sec": int (target 300-420),\n'
        '  "transcript": array of 14-22 objects {"t_sec": int, "speaker": "Nova" or "Arc", "line": string},\n'
        '  "show_notes_md": string (markdown, 400-900 chars, includes ## Chapters and ## Links),\n'
        '  "cover_art_brief": {"style": string, "focal_object": string, "mood": string, "notes": string},\n'
        '  "rss_metadata": {"episode_title": string, "episode_number": int, "guid": string, "duration_sec": int, "pub_date": string ISO date, "description": string},\n'
        '  "audio_status": "pending"\n'
        "}"
    )
    anthropic_instructions = (
        "Write a two-host launch podcast transcript. Hosts are Nova (warm, "
        "curious) and Arc (skeptical, analytical). Cover: hook, one-sentence "
        "'what is this?', the three campaign pillars, a moment of honest "
        "skepticism from Arc, a founder-style close from Nova. Speaker lines "
        "should feel like actual spoken speech \u2014 contractions, short "
        "sentences, occasional interjections. Duration target 5-7 minutes."
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
            "duration_sec": t + 10,
            "transcript": transcript,
            "show_notes_md": show_notes_md,
            "cover_art_brief": cover_art_brief,
            "rss_metadata": rss_metadata,
            "audio_status": "pending",
        }

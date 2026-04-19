from __future__ import annotations

from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts._helpers import (
    brand_positioning,
    launch_date,
    pillar_lines,
    target_competitor,
)
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
                    f"Welcome back to the VibeCast Launch Radar. "
                    f"I'm Nova, and today we're talking about {project.name}."
                ),
            },
            {
                "t_sec": 12,
                "speaker": "Arc",
                "line": (
                    f"And I'm Arc. Nova, in one sentence — what is {project.name}?"
                ),
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
                    "Brand Guardian — that's real."
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
            f"# {project.name} — Launch Radar\n\n"
            f"{positioning}\n\n"
            "## Chapters\n"
            + "\n".join(
                f"- {seg['t_sec']//60:02d}:{seg['t_sec']%60:02d} — {seg['speaker']}"
                for seg in transcript
            )
            + "\n\n## Links\n- https://vibecast.ai\n- https://vibecast.ai/launch"
        )

        cover_art_brief = {
            "style": "Editorial, high-contrast, dark base with a single accent color.",
            "focal_object": f"An abstract broadcast waveform overlaid with the word '{project.name}'.",
            "mood": "Confident, calm, evidence-first.",
            "notes": "Avoid cliché AI iconography (no robots, no circuits).",
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

#!/usr/bin/env python3
"""Record weekly plan loading UX for smoke demo (Playwright video + screenshots)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ARTIFACTS = Path("/opt/cursor/artifacts")
SCREENSHOTS = ARTIFACTS / "screenshots"
VIDEO_OUT = ARTIFACTS / "weekly-meal-builder-loading-smoke.mp4"


def main() -> int:
    from playwright.sync_api import sync_playwright

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    video_dir = ARTIFACTS / "playwright-videos"
    video_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(
            record_video_dir=str(video_dir),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(2500)

        body = page.inner_text("body")
        if "Loading recipes from Notion" in body:
            print("FAIL: Notion recipe loading visible on Get started")
            return 1

        page.screenshot(path=str(SCREENSHOTS / "01-get-started.png"), full_page=True)

        page.locator('button[kind="primary"]').filter(has_text="Continue").first.click()
        page.wait_for_timeout(3500)
        page.screenshot(path=str(SCREENSHOTS / "02-meal-count.png"), full_page=True)

        if "Loading recipes from Notion" in page.inner_text("body"):
            print("FAIL: Notion recipe loading visible on meal-count step")
            return 1

        if "How many meals this week?" not in page.inner_text("body"):
            print("FAIL: meal count step not visible")
            return 1

        meal_count_continue = page.locator('button[kind="primary"]').filter(has_text="Continue")
        if meal_count_continue.count() != 1:
            print(f"WARN: expected 1 meal-count Continue, saw {meal_count_continue.count()}")
        meal_count_continue.first.click()
        for index in range(6):
            page.wait_for_timeout(500)
            page.screenshot(
                path=str(SCREENSHOTS / f"03-loading-frame-{index}.png"),
                full_page=True,
            )
            if "Preparing your meal builder" in page.inner_text("body"):
                print(f"Captured inline loader at frame {index}")

        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREENSHOTS / "04-meal-builder.png"), full_page=True)

        if "Build my plan" not in page.inner_text("body"):
            print("FAIL: Build my plan not visible after Continue")
            return 1

        video = page.video
        page.close()
        context.close()
        browser.close()

        if video is None:
            print("FAIL: no video recorded")
            return 1
        webm = Path(video.path())
        video_out = VIDEO_OUT
        if shutil.which("ffmpeg"):
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(webm),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(video_out),
                ],
                check=True,
                capture_output=True,
            )
        else:
            video_out = ARTIFACTS / "weekly-meal-builder-loading-smoke.webm"
            shutil.copy(webm, video_out)

    print(f"OK: video at {video_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Aurora Ribbon Video Design

## Style Prompt

Convert the existing visual-test page directly into a loopable video: a dark, cinematic canvas with a translucent aurora ribbon, fine particle field, and the original Chinese title/subtitle. The output should feel identical to the source page, with no added narration, scene cuts, captions, logos, or explanatory elements.

## Colors

- Canvas: `#08080a`, `#0a0a0d`, `#11100e`, `#07070a`
- Text: `#fff9ef`, `rgba(247, 240, 232, 0.82)`
- Ribbon: jade `#14f2c2`, violet `#d15cff`, gold `#ffba57`, blue `#2e61ff`
- Halo: `#b9fff1`

## Typography

- Main heading: `"Noto Serif SC Local", serif`
- Subtitle and interface text: `"Noto Sans SC Local", sans-serif`

## Motion

- Single continuous 35-second visual loop.
- All motion must be timeline-driven and deterministic.
- The first rendered frame and the final rendered frame must return to the same phase for seamless looping.

## What Not To Do

- Do not add voiceover, music, sound effects, extra captions, transitions, or scene changes.
- Do not change the original page text.
- Do not introduce random per-render variation.
- Do not use non-looping elapsed-time animation.

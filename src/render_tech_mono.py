#!/usr/bin/env python3
"""Tech Mono kinetic explainer: off-white dot grid, IBM Plex Mono, ONE electric-blue
accent, editorial expo ease, optional video underlays (see README: Pexels).
Usage: python render_tech_mono.py words.json video_only.mp4 [--underlays u.json] [--preview 1 4.5]
"""
import kinetic
if __name__ == "__main__":
    kinetic.main("tech_mono.json")

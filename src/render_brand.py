#!/usr/bin/env python3
"""Brand-style kinetic explainer. Palette, fonts, logo, end-card copy all come from
a style JSON — copy styles/brand_example.json, set your own colours/font/logo.
Usage: python render_brand.py words.json video_only.mp4 --style styles/my_brand.json
"""
import kinetic
if __name__ == "__main__":
    kinetic.main("brand_example.json")

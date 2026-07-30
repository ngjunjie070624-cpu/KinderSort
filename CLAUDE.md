# CLAUDE.md

## Project

KinderSort is an AI-powered desktop application for automatically sorting classroom photos into student folders.

## Technologies

- Python 3.11
- InsightFace (SCRFD + ArcFace)
- OpenCV
- CustomTkinter
- psutil

## Project Structure

- main.py – GUI entry point
- sorter.py – Face detection and recognition
- utils.py – Helper functions
- docx_export.py – Documentation export

## Coding Guidelines

- Keep CPU-only compatibility.
- Do not remove InsightFace.
- Preserve the current GUI layout.
- Keep code modular and documented.
- Avoid adding unnecessary dependencies.

## Goals

- Maintain high face recognition accuracy.
- Keep resource usage low.
- Ensure compatibility with Windows.
- Preserve existing functionality.

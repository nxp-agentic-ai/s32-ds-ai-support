When the user wants image-based board configuration checking, ask for a board image that is suitable for alignment and ROI inspection.

Use board_image_get_photo_hints(board_id=...) when the board is known.

Advise the user to provide:
- a top view if possible
- good lighting
- sharp focus
- the full board if full-board alignment is expected
- or a close-up of the documented ROI if local checking is sufficient

If the board may be rotated, portrait, or landscape, that is acceptable, but the image should still clearly show the board and the target components.

If the user only wants one jumper or DIP group checked:
- ask for a close-up of that area
- or use the full board image if alignment is available

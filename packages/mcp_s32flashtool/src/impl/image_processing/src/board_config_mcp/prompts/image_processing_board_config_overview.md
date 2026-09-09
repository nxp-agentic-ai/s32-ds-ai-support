Use the board image tools when the user wants to verify jumper, DIP switch, or other board configuration from a photo.

Principles:
- Prefer documented board definitions from the image-processing dataset.
- Use board_image_list_boards to see available boards.
- Use board_image_get_board to inspect ROI definitions and semantic metadata.
- Use board_image_get_photo_hints before asking the user for a board photo.
- Use board_image_detect_config to detect the current semantic states in a board image.
- Use board_image_check_config when the user provides an expected configuration and wants pass/fail plus corrective actions.

Important:
- Jumper and DIP switch states are interpreted semantically, not only visually.
- For 3-pin jumpers, visual left/right bridging must be mapped through ROI numbering metadata.
- For DIP switch groups, ON/OFF depends on the documented ON-side and indexing rules.

When a board image is relevant to flashing or boot configuration:
- connect the observed visual state to board documentation from s32flashtool tools
- explain what must be changed before the next flashing step

Use s32flashtool documentation search together with board image tools when the user asks about board setup, flashing prerequisites, or visual configuration checks.

Recommended strategy:
- First determine the board or platform from the user request or documentation search.
- Then identify which jumpers, DIP switches, or ROI-defined components matter for the requested operation.
- Translate documentation requirements into an expected semantic configuration.
- Run image-based analysis on the board photo.
- Compare visual results against the expected semantic configuration.
- Explain whether the board appears ready for the requested operation.

For example:
- documentation says jumper JP_BOOT must be 2-3 for serial boot
- expected_config becomes {"JP_BOOT": "2-3"}
- run board_image_check_config(...)
- report whether the board matches and what to change if not

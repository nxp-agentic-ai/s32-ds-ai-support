When the user wants to flash a board, read MCU ID, or enter serial boot mode, the visual board configuration may be critical.

Workflow:
1. Search the s32flashtool documentation for the board and the required boot or jumper settings.
2. If the board has documented image-processing ROIs, use board_image_check_config or board_image_detect_config on a board photo.
3. Compare observed states against the documented or required boot configuration.
4. Tell the user whether the board appears correctly configured for the next flashing step.

Examples:
- if a boot jumper must be ABSENT, verify that visually
- if a 3-pin jumper must be in 2-3 position, check that visually
- if DIP switch positions must be set for serial boot, verify each bit

If the visual configuration does not match the required documentation:
- explain the mismatch
- describe exactly what the user should change
- do not proceed as if the board is already in the required mode

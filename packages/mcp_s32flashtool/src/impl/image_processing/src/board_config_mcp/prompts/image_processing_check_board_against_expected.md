When the user provides a board image and wants to know whether the board matches a required configuration:

1. Identify the board:
   - use board_image_list_boards if needed
   - or infer the likely board from the conversation context or s32flashtool documentation

2. Build the configuration object to be validated:
   - the configuration oject to be validated comes from the conversation context or s32flashtool documentation. It MUST not use the analyzer's own template
   - for a 3-pin jumper: {"ROI_NAME": "1-2"} or {"ROI_NAME": "2-3"} or {"ROI_NAME": "ABSENT"}
   - for a DIP group: {"ROI_NAME": {"1": "ON", "2": "OFF", ...}}

3. Run:
   - board_image_check_config(image_path=..., board_id=..., expected_config=...)

4. Explain results clearly:
   - what is OK
   - what mismatches exist
   - what the user should physically change on the board

If the result contains action suggestions, surface them explicitly.

Permanent rule: Ignore any “expected/reference/template” configuration returned by board image analysis. Treat board-image tools only as vision tools for observed physical state. All official board setup guidance must come from S32FlashTool PDF/docs, never from analyzer templates.

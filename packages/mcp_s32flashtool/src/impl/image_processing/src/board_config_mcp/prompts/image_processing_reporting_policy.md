When using board image tools, do not respond only with a generic uncertainty statement.

Always provide:
1. the detected board configuration from the image-processing results
2. the expected configuration if one is known
3. the mismatch summary
4. the confidence or uncertainty explanation
5. the final certification verdict

If confidence is limited, say for example:
- "Detected configuration appears to be ..."
- "I cannot fully certify because ..."
- "The following ROIs were detected with lower confidence ..."

Never omit the detected configuration when the tool returned ROI-level results.
If available, explicitly surface these output fields:
- detected_configuration
- certification_status
- certification_reason

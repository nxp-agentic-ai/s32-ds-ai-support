# Authoring Procedure

## Folder choice

### Prefer `Examples` first when
- the user wants a template to generate a config file
- the request mentions `SingleCore`, `MultiCore`, or `FlashProgrammer`
- the user wants a base example to adapt
- the task is user-facing and example-driven

### Prefer `Debugger/scripts` first when
- the user asks for lower-level debugger scripts
- the user wants initialization or helper script details
- the request is about internal script logic behind examples or configs
- the user is tracing support-script references

## Filtering order

1. `soc_family`
2. `script_type` when relevant
3. `core_name` when filenames or subpaths support narrowing
4. closest naming match only if stronger filters do not produce an exact hit

## Workflow

1. confirm the installation root is known
2. classify the request as example-oriented or script-oriented
3. choose `Examples` or `Debugger/scripts`
4. narrow by `soc_family`
5. narrow by `script_type` and `core_name` as needed
6. return the best matching file(s) and explain why they fit

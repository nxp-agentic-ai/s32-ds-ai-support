# Examples and Anti-Patterns

## Quick examples

- known install root + user wants a `SingleCore` template -> search
  `S32Debugger/Examples/<soc_family>/SingleCore` first
- user wants the init script behind a generated flow -> search
  `S32Debugger/Debugger/scripts/<soc_family>` first
- user asks for a `FlashProgrammer` example with only `soc_family` known ->
  search `Examples/<soc_family>/FlashProgrammer` and return the closest valid
  template
- user gives no install root -> stop and route to
  `s32debugger-discover-installation`

## Response cues

- which installation root was used
- which folder was searched first
- what filters were applied
- closest matching file(s)
- whether the result is an example template or support script
- what to do next with that file

## Anti-patterns

- mixing up `Examples` and `Debugger/scripts`
- claiming a support script is a user-facing template
- silently choosing a weak match when a key filter is missing
- skipping the explanation of why a file was selected

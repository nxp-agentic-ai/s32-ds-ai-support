# Authoring Procedure

## Workflow

1. Normalize the request.
2. Decide whether the request is observational-only or a true live-session /
   flash request.
3. If observational-only, check whether an interactive session is already
   active and explicitly meant to be reused.
4. Classify shape.
5. Classify programming/debug intent.
6. Determine whether startup/debug context already exists or must be
   established.
7. Choose the downstream skill or ordered routing path.
8. Ask for the smallest missing routing input when needed.
9. Keep any successfully established live session open unless the user asks to
   stop it.

## CCS-first observational rule

If the request is observational only, and no interactive debug session is
already active, route to CCS before any GDB path.

Observational requests include:
- probe sanity check
- target identification / target information
- core-state collection

If an interactive session is already active, reuse it only when the user
explicitly asks for that reuse.

## Routing rules

### Shapes
- single-core standalone live-debug session
- multicore standalone live-debug session
- flash-programming session
- other standalone fallback session

### Intents
- observational only
- live debug only
- flash programming only
- flash then debug from flash

### Preferred routes
1. observational-only sanity / target-info / core-state request with no active
   interactive session -> `s32debugger-ccs-execution-router`
2. clearly single-core live-debug request ->
   `s32debugger-start-singlecore-standalone-live-debug-session`
3. clearly multicore live-debug request ->
   `s32debugger-start-multicore-standalone-live-debug-session`
4. clearly flash-programming request -> establish required startup context if
   needed, then `s32debugger-flash-programming`
5. clearly flash-then-debug request -> establish matching startup path first,
   then `s32debugger-flash-programming`

## Flash-context rule

`s32debugger-flash-programming` is not always a zero-startup path. If the
required GDB/GTA/probe context does not already exist, establish or route to
that startup context first.

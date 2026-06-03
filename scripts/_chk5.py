content = open('templates/partials/schedule.html',
               'r', encoding='utf-8').read()
print(f'Size: {len(content)} chars, {content.count(chr(10))} lines')
checks = [
    # time rows always visible
    'TOTAL_SLOTS', 'for (var si = 0; si < TOTAL_SLOTS',
    # no corruption markers
    # mode toggle
    'schedSwitchMode', 'btn-manual', 'btn-auto',
    # chat panel
    'ai-chat-panel', 'panel.classList.add', 'chat-open',
    'chat-messages', 'chat-input', 'sendChatMessage', 'sendSuggestion',
    'typing-dot', 'initChat', 'chatInited',
    # timetable
    'renderTimetable', 'attachInteractionHandlers',
    'attachDrawHandlers', 'attachMoveHandlers', 'attachResizeHandlers',
    # modal
    'new-block-modal', 'confirmNewBlock', 'closeNewBlockModal',
    # api
    '/api/schedules', 'deleteEntry', 'confirmClearAll', 'updateEntry',
    # no old form remnants
]
all_ok = True
for c in checks:
    ok = c in content
    if not ok:
        all_ok = False
    print(f'  {"OK" if ok else "MISSING"}: {c}')
print('All OK!' if all_ok else 'Some MISSING.')

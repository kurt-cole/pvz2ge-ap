// Chat commands: the channel that lets a plain message in ANY Archipelago
// client -- including the stock text client -- drive the game client.
//
// The server rebroadcasts every chat line to the room as a PrintJSON with
// type "Chat", carrying the sending team and slot plus the raw text. These
// packets are built to that shape.
const C = require('./command_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);
const chat = (message, slot, team) =>
  ({ cmd: 'PrintJSON', type: 'Chat', slot: slot === undefined ? 1 : slot,
     team: team === undefined ? 0 : team, message });

// ── only this slot's messages, and only chat ─────────────────────────────────
C.reset({ coinGranted: 100, coinApplied: 100 });
if (C.handleChatCommand(chat('pvz2 ledger', 2))) fail('acted on another slot\'s message');
else ok('a message from another slot is ignored');

C.reset({});
if (C.handleChatCommand(chat('pvz2 ledger', 1, 3))) fail('acted on another team\'s message');
else ok('a message from another team is ignored');

C.reset({});
if (C.handleChatCommand({ cmd: 'PrintJSON', type: 'ItemSend', slot: 1, message: 'pvz2 ledger' }))
  fail('acted on a non-chat PrintJSON');
else ok('only type "Chat" is treated as a command channel');

C.reset({});
for (const other of ['hello', 'pvz2ledger', '!pvz2 ledger', '/pvz2 ledger', '']) {
  if (C.handleChatCommand(chat(other))) fail(`ordinary chat "${other}" was taken as a command`);
}
ok('ordinary chat, and the ! and / prefixes, are left alone');

// ── ledger reports without changing anything ─────────────────────────────────
C.reset({ coinGranted: 500, coinApplied: 500, gemGranted: 20, gemApplied: 20 },
        { coin: 500, gem: 20 });
if (!C.handleChatCommand(chat('pvz2 ledger'))) fail('ledger was not handled');
const led = C.logs.join(' | ');
if (!/coin: granted 500, applied 500, pending 0, on the save 500/.test(led))
  fail('ledger did not report the coin line: ' + led);
else if (!/gem: granted 20, applied 20, pending 0, on the save 20/.test(led))
  fail('ledger did not report the gem line: ' + led);
else ok('ledger reports granted, applied, pending and the live balance');
if (C.current().coin !== 500) fail('ledger changed the balance');
else ok('ledger is read-only');

// ── resync re-applies a wiped balance ────────────────────────────────────────
// The case this exists for: the save lost its money, but applied == granted so
// applyPendingCurrency() would never move again.
C.reset({ coinGranted: 580, coinApplied: 580, gemGranted: 121, gemApplied: 121 },
        { coin: 0, gem: 0 });
C.handleChatCommand(chat('pvz2 resync'));
if (C.current().coin !== 580 || C.current().gem !== 121)
  fail(`resync did not restore the balance: ${JSON.stringify(C.current())}`);
else ok('resync re-applies the full granted total to a wiped save');
if (C.state().coinApplied !== 580) fail('resync left applied wrong: ' + C.state().coinApplied);
else ok('...and applied is back in step with granted, so it will not repeat');
if (!C.svSt.calls) fail('resync did not persist the state');
else ok(`...and the state was saved (${C.svSt.calls} write(s))`);

// Running it twice must not stack: the second pass has nothing pending.
C.handleChatCommand(chat('pvz2 resync'));
if (C.current().coin !== 580) fail('a second resync granted the money again: ' + C.current().coin);
else ok('a second resync is a no-op, because applied is level with granted again');

// ── unknown command, and no player ───────────────────────────────────────────
C.reset({});
C.handleChatCommand(chat('pvz2 nonsense'));
if (!C.toasts.some(t => /Unknown command: nonsense/.test(t.msg)))
  fail('an unknown command said nothing');
else ok('an unknown command is reported rather than ignored');

C.reset({ coinGranted: 50, coinApplied: 50 }, null);
let threw = false;
try { C.handleChatCommand(chat('pvz2 resync')); } catch (e) { threw = true; }
if (threw) fail('resync threw with no player loaded');
else ok('resync with no player loaded does not throw');

// ── help lists every command ─────────────────────────────────────────────────
C.reset({});
C.handleChatCommand(chat('pvz2 help'));
const helpText = C.logs.join('\n');
for (const name of Object.keys(C.AP_CHAT_COMMANDS)) {
  if (!helpText.includes(C.AP_CHAT_PREFIX + ' ' + name))
    fail(`help does not list "${name}"`);
}
ok(`help lists all ${Object.keys(C.AP_CHAT_COMMANDS).length} commands`);

// A bare prefix defaults to help rather than doing nothing.
C.reset({});
C.handleChatCommand(chat('pvz2'));
if (!C.logs.length) fail('a bare "pvz2" said nothing');
else ok('a bare prefix falls back to help');

// Case and spacing are what a human actually types.
C.reset({ coinGranted: 10, coinApplied: 10 }, { coin: 10, gem: 0 });
C.handleChatCommand(chat('  PvZ2   Ledger  '));
if (!C.logs.length) fail('mixed case and padding were not accepted');
else ok('mixed case and extra spacing are accepted');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCHAT COMMANDS OK');
process.exit(failed ? 1 : 0);
